"""
main.py — CLI Entry Point for the Research Swarm

Usage:
    python -m automation.main execute "Your research prompt here"
    python -m automation.main report "Your prompt" --mode narrative-review
    python -m automation.main scaffold "Climate Science"
    python -m automation.main info

All behavior is driven by swarm_config.yml. Edit that file to
customize personas, tools, reviewer constraints, and LLM backend.
"""

import datetime
import json
import os
import shutil
from pathlib import Path

import typer
from dotenv import load_dotenv
from langchain_core.messages import AIMessage

from automation.config import (
    load_config,
    validate_env,
)
from automation.graph import build_graph

# Load environment configuration (.env)
load_dotenv()

app = typer.Typer(
    name="swarm",
    help="Research Swarm CLI — A configurable multi-agent research system built on LangGraph.",
    add_completion=False,
)

# ── Report-mode templates ─────────────────────────────────────────────────
REPORT_MODES = {
    "scoping-review": (
        "[REPORT MODE: SCOPING REVIEW] Follow JBI scoping review methodology. "
        "Include: scope and eligibility criteria, search strategy and databases used, "
        "a results charting table, and a discussion of evidence coverage and gaps. "
        "Do NOT provide clinical recommendations — summarise what the literature covers "
        "and where evidence is absent. "
    ),
    "narrative-review": (
        "[REPORT MODE: NARRATIVE REVIEW] Write a structured narrative review suitable "
        "for a psychiatric journal. Include: abstract, introduction, thematic synthesis "
        "of evidence organised by sub-topic, discussion, limitations, and conclusions. "
        "Use formal academic register throughout. "
    ),
    "evidence-brief": (
        "[REPORT MODE: EVIDENCE BRIEF] Write a concise evidence brief (target ~800 words) "
        "for a clinical or policy audience. Use plain language. Structure: "
        "3–5 key findings (bullet points), brief methods note, "
        "2–3 actionable clinical or policy implications, and a caveats paragraph. "
        "Avoid jargon; spell out all acronyms on first use. "
    ),
}

MATRIX_HEADER = (
    "# Knowledge Traceability Matrix\n\n"
    "| Source | Author/Agent | Claim | Method | Epistemic Tag |\n"
    "|--------|-------------|-------|--------|---------------|\n"
)


def _ensure_matrix_header(config: dict, task: str) -> None:
    """Create the traceability matrix with its table header if it does not exist,
    then append a run-separator line so each run's entries are clearly delimited."""
    matrix_path = Path(
        config["swarm"].get("traceability_matrix", "./Knowledge_Traceability_Matrix.md")
    )
    if not matrix_path.exists():
        matrix_path.write_text(MATRIX_HEADER, encoding="utf-8")

    run_stamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    task_preview = task[:80] + "…" if len(task) > 80 else task
    with open(matrix_path, "a", encoding="utf-8") as f:
        f.write(f"\n### Run: {run_stamp} | Task: {task_preview}\n\n")


def _write_run_metrics(config: dict, task: str, token_usage: dict) -> None:
    """Write per-run token/cost metrics to Drafts/run_metrics.json."""
    drafts_dir = Path(config["swarm"].get("output_dir", "./Drafts"))
    drafts_dir.mkdir(parents=True, exist_ok=True)

    # Rough cost estimate using gpt-4o list pricing ($/M tokens, 2025)
    input_price_per_m = 2.50
    output_price_per_m = 10.00
    input_tok = token_usage.get("input_tokens", 0)
    output_tok = token_usage.get("output_tokens", 0)
    est_cost = (input_tok * input_price_per_m + output_tok * output_price_per_m) / 1_000_000

    metrics = {
        "run_date": datetime.datetime.now().isoformat(timespec="seconds"),
        "task": task[:100] + "…" if len(task) > 100 else task,
        "model": f"{config['model']['provider']}/{config['model']['name']}",
        "input_tokens": input_tok,
        "output_tokens": output_tok,
        "total_tokens": token_usage.get("total_tokens", input_tok + output_tok),
        "estimated_cost_usd": round(est_cost, 4),
        "cost_note": "Estimate uses gpt-4o list pricing ($2.50/M input, $10/M output). "
                     "Adjust for your model and negotiated rates.",
    }

    metrics_path = drafts_dir / "run_metrics.json"
    with open(metrics_path, "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2)

    typer.secho(
        f"\n📊 Token usage: {input_tok:,} in / {output_tok:,} out "
        f"(est. ${est_cost:.4f})",
        fg=typer.colors.CYAN,
    )


def _run_graph(config: dict, prompt: str) -> None:
    """Core graph execution shared by `execute` and `report` commands."""
    try:
        warnings = validate_env(config)
        for w in warnings:
            typer.secho(f"⚠️  {w}", fg=typer.colors.YELLOW)
    except EnvironmentError as e:
        typer.secho(f"ENV ERROR: {e}", fg=typer.colors.RED)
        raise typer.Exit(code=1)

    _ensure_matrix_header(config, prompt)

    swarm_name = config["swarm"]["name"]
    typer.secho(f"🚀 Initializing {swarm_name} (multi-agent mode)...", fg=typer.colors.CYAN)

    graph = build_graph(config)

    initial_state = {
        "task": prompt,
        "messages": [],
        "agent_outputs": {},
        "agent_assignments": {},
        "next_agents": [],
        "next_instructions": "",
        "agent_call_count": 0,
        "reviewer_approved": False,
        "revision_count": 0,
        "token_usage": {},
    }

    try:
        typer.secho(f"\n🧠 [SWARM ACTIVE] Streaming agent interactions...\n", fg=typer.colors.BLUE)

        final_event = initial_state
        for event in graph.stream(initial_state, stream_mode="values"):
            final_event = event
            latest_msg = event.get("messages", [])
            if not latest_msg:
                continue
            msg = latest_msg[-1]

            if not hasattr(msg, "content") or not msg.content:
                continue

            content = str(msg.content)

            if content.startswith("[Orchestrator"):
                typer.secho(f"  ↳ {content}", fg=typer.colors.CYAN)
            elif content.startswith("[") and "]: " in content:
                typer.secho(f"  {content}", fg=typer.colors.GREEN)
            elif content.startswith("[Reviewer"):
                colour = typer.colors.GREEN if "APPROVED" in content else typer.colors.RED
                typer.secho(f"  {content}", fg=colour)
            elif hasattr(msg, "tool_calls") and msg.tool_calls:
                for tc in msg.tool_calls:
                    typer.secho(
                        f"    🔧 {tc['name']} ← {list(tc['args'].keys())}",
                        fg=typer.colors.YELLOW,
                    )

        typer.secho("\n✅ Task complete.", fg=typer.colors.GREEN)
        output_dir = config["swarm"].get("output_dir", "./Drafts")
        typer.secho(f"📂 Outputs saved to '{output_dir}/'", fg=typer.colors.CYAN)

        # Write token/cost metrics using the accumulated state from the final event
        _write_run_metrics(config, prompt, final_event.get("token_usage", {}))

    except Exception as e:
        typer.secho(f"Execution Error: {e}", fg=typer.colors.RED)
        raise typer.Exit(code=1)


@app.command()
def execute(prompt: str):
    """
    Execute an autonomous research task with the swarm.

    Pass a natural-language prompt describing what you want the agents to do.
    The swarm will search, reason, validate, and write outputs to the Drafts/ folder.

    Example:
        python -m automation.main execute "Review the psychiatric literature on PIU."
    """
    try:
        config = load_config()
    except (FileNotFoundError, ValueError) as e:
        typer.secho(f"CONFIG ERROR: {e}", fg=typer.colors.RED)
        raise typer.Exit(code=1)

    _run_graph(config, prompt)


@app.command()
def report(
    prompt: str,
    mode: str = typer.Option(
        "narrative-review",
        "--mode", "-m",
        help="Output format: scoping-review | narrative-review | evidence-brief",
    ),
):
    """
    Execute a structured research task with an explicit report format.

    Prepends a mode-specific template instruction to the prompt so the Journalist
    agent produces output in the correct format for the chosen report type.

    Modes:
      scoping-review    — JBI scoping review (coverage map, no recommendations)
      narrative-review  — Full academic narrative review with abstract and sections
      evidence-brief    — ~800-word plain-language brief for clinicians / policymakers

    Example:
        python -m automation.main report "Prevalence of PIU in adolescents" --mode evidence-brief
    """
    try:
        config = load_config()
    except (FileNotFoundError, ValueError) as e:
        typer.secho(f"CONFIG ERROR: {e}", fg=typer.colors.RED)
        raise typer.Exit(code=1)

    if mode not in REPORT_MODES:
        typer.secho(
            f"Unknown mode '{mode}'. Choose from: {', '.join(REPORT_MODES)}",
            fg=typer.colors.RED,
        )
        raise typer.Exit(code=1)

    template = REPORT_MODES[mode]
    full_prompt = template + prompt
    typer.secho(f"📋 Report mode: {mode}", fg=typer.colors.CYAN)
    _run_graph(config, full_prompt)


@app.command()
def scaffold(domain: str):
    """
    Scaffold a new domain-specific swarm configuration.

    Creates default persona directories and a starter swarm_config.yml
    so you can quickly customize the swarm for a new field.

    Example:
        python -m automation.main scaffold "Climate Science"
    """
    agents_dir = Path("agents")
    default_personas = {
        "Orchestrator": "Coordinates the swarm, synthesizes inputs, resolves conflicts, and dictates research direction.",
        "Researcher": "Deep domain expert who searches literature and external sources for evidence.",
        "Critic": "Quality assurance and adversarial review. Challenges assumptions and verifies citations.",
        "Scribe": "Neutral observer and documentarian. Writes all outputs to disk with professional formatting.",
    }

    typer.secho(f"\n🏗️  Scaffolding new swarm for: '{domain}'", fg=typer.colors.CYAN)

    for persona_name, description in default_personas.items():
        persona_dir = agents_dir / persona_name
        persona_dir.mkdir(parents=True, exist_ok=True)
        (persona_dir / "KB").mkdir(exist_ok=True)

        persona_file = persona_dir / "persona.md"
        if not persona_file.exists():
            persona_file.write_text(
                f"# {persona_name}\n"
                f"**Role**: {persona_name} for {domain}\n\n"
                f"## Core Mission\n"
                f"{description}\n\n"
                f"## Domain Focus\n"
                f"- (Define specific {domain} expertise areas here)\n\n"
                f"## Knowledge Base (KB) Focus\n"
                f"- (List key sources, standards, or frameworks for {domain})\n\n"
                f"## Behavior\n"
                f"- (Define behavioral rules and search triggers)\n",
                encoding="utf-8",
            )
            typer.secho(f"  ✅ Created: {persona_file}", fg=typer.colors.GREEN)
        else:
            typer.secho(f"  ⏭️  Exists:  {persona_file}", fg=typer.colors.YELLOW)

    config_file = Path("swarm_config.yml")
    if config_file.exists():
        typer.secho(
            f"\n⚠️  swarm_config.yml already exists. "
            f"Please edit it manually to update personas for '{domain}'.",
            fg=typer.colors.YELLOW,
        )
    else:
        typer.secho(
            f"\n💡 No swarm_config.yml found. "
            f"Copy the example from the repo and customize it.",
            fg=typer.colors.YELLOW,
        )

    typer.secho(
        f"\n🎉 Scaffolding complete! Next steps:\n"
        f"   1. Edit agents/*/persona.md files with {domain}-specific expertise\n"
        f"   2. Edit swarm_config.yml to register your personas and tools\n"
        f"   3. Drop reference documents into agents/*/KB/ folders\n"
        f"   4. Run: python -m automation.ingest  (to vectorize KB documents)\n"
        f"   5. Run: python -m automation.main execute \"Your first prompt\"",
        fg=typer.colors.CYAN,
    )


@app.command()
def info():
    """
    Display the current swarm configuration summary.
    """
    try:
        config = load_config()
    except (FileNotFoundError, ValueError) as e:
        typer.secho(f"CONFIG ERROR: {e}", fg=typer.colors.RED)
        raise typer.Exit(code=1)

    swarm = config["swarm"]
    model = config["model"]

    typer.secho(f"\n{'═' * 50}", fg=typer.colors.CYAN)
    typer.secho(f"  {swarm['name']}", fg=typer.colors.CYAN, bold=True)
    typer.secho(f"  {swarm.get('description', '')}", fg=typer.colors.WHITE)
    typer.secho(f"{'═' * 50}", fg=typer.colors.CYAN)

    typer.secho(f"\n📡 Model: {model['provider']}/{model['name']} (temp={model.get('temperature', 0.2)})")

    typer.secho(f"\n👥 Personas:")
    for p in config["personas"]:
        tools_str = ", ".join(p.get("tools", []))
        typer.secho(f"   {p.get('icon', '🤖')} {p['name']} — {p['role']} [{tools_str}]")

    typer.secho(f"\n🔧 Tools registered: {len(config['tools'])}")
    for name, spec in config["tools"].items():
        typer.secho(f"   • {name}: {spec.get('description', spec['function'])}")

    orch = config.get("orchestrator", {})
    typer.secho(f"\n🎯 Orchestrator: {orch.get('agent', 'Dr. Nexus')} "
                f"(journalist: {orch.get('journalist', 'Journalist')}, "
                f"max_agent_calls: {orch.get('max_agent_calls', 8)}, "
                f"max_tool_rounds: {orch.get('max_tool_rounds_per_agent', 5)})")

    typer.secho(f"\n📋 Report modes: {', '.join(REPORT_MODES)}")

    reviewer = config["reviewer"]
    r_status = "✅ Enabled" if reviewer.get("enabled", True) else "❌ Disabled"
    typer.secho(f"\n🔍 Reviewer-2: {r_status} (max {reviewer.get('max_revision_loops', 3)} loops)")
    typer.secho(f"   Banned words: {', '.join(reviewer.get('banned_words', []))}")
    typer.secho(f"   Tone: {reviewer.get('tone', 'neutral')}")

    typer.echo()


if __name__ == "__main__":
    app()
