"""
main.py — CLI Entry Point for the Research Swarm

Usage:
    python -m automation.main execute "Your research prompt here"
    python -m automation.main scaffold "Climate Science"

All behavior is driven by swarm_config.yml. Edit that file to
customize personas, tools, reviewer constraints, and LLM backend.
"""

import os
import shutil
from pathlib import Path

import typer
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, SystemMessage

from automation.config import (
    load_config,
    build_system_prompt,
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


@app.command()
def execute(prompt: str):
    """
    Execute an autonomous research task with the swarm.

    Pass a natural-language prompt describing what you want the agents to do.
    The swarm will search, reason, validate, and write outputs to the Drafts/ folder.

    Example:
        python -m automation.main execute "Search for the latest FDA guidance on NAMs and summarize."
    """
    # Load configuration
    try:
        config = load_config()
    except (FileNotFoundError, ValueError) as e:
        typer.secho(f"CONFIG ERROR: {e}", fg=typer.colors.RED)
        raise typer.Exit(code=1)

    # Validate environment variables
    try:
        warnings = validate_env(config)
        for w in warnings:
            typer.secho(f"⚠️  {w}", fg=typer.colors.YELLOW)
    except EnvironmentError as e:
        typer.secho(f"ENV ERROR: {e}", fg=typer.colors.RED)
        raise typer.Exit(code=1)

    swarm_name = config["swarm"]["name"]
    typer.secho(f"🚀 Initializing {swarm_name}...", fg=typer.colors.CYAN)

    # Build the graph from config
    graph = build_graph(config)

    # Assemble the system prompt dynamically from config + persona files
    system_prompt_text = build_system_prompt(config)
    system_persona = SystemMessage(content=system_prompt_text)
    user_request = HumanMessage(content=prompt)

    try:
        typer.secho(f"\n🧠 [THINKING] Executing graph state...", fg=typer.colors.BLUE)

        for event in graph.stream(
            {"messages": [system_persona, user_request]},
            stream_mode="values",
        ):
            latest_msg = event["messages"][-1]

            # Print Tool Invocations
            if hasattr(latest_msg, "tool_calls") and latest_msg.tool_calls:
                for target_tool in latest_msg.tool_calls:
                    typer.secho(
                        f"🔧 [TOOL INVOKED]: {target_tool['name']} -> {target_tool['args']}",
                        fg=typer.colors.YELLOW,
                    )
            # Print Agent Output text
            elif hasattr(latest_msg, "content") and latest_msg.content:
                if isinstance(latest_msg, (HumanMessage, SystemMessage)):
                    continue
                typer.echo(f"\n🤖 [AGENT OUTPUT]:\n{latest_msg.content}\n")

        typer.secho("✅ Task Execution Complete.", fg=typer.colors.GREEN)

        # Remind the user where to find outputs
        output_dir = config["swarm"].get("output_dir", "./Drafts")
        typer.secho(
            f"📂 Check '{output_dir}/' for generated files.",
            fg=typer.colors.CYAN,
        )

    except Exception as e:
        typer.secho(f"Execution Error: {e}", fg=typer.colors.RED)
        raise typer.Exit(code=1)


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

    # Create a domain-specific config if one doesn't exist
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

    reviewer = config["reviewer"]
    r_status = "✅ Enabled" if reviewer.get("enabled", True) else "❌ Disabled"
    typer.secho(f"\n🔍 Reviewer-2: {r_status} (max {reviewer.get('max_revision_loops', 3)} loops)")
    typer.secho(f"   Banned words: {', '.join(reviewer.get('banned_words', []))}")
    typer.secho(f"   Tone: {reviewer.get('tone', 'neutral')}")

    typer.echo()


if __name__ == "__main__":
    app()
