"""
graph.py — True Multi-Agent LangGraph State Machine (Supervisor Pattern)

Architecture
------------
Each persona is a separate LangGraph node with its own system prompt and
scoped tool set. Dr. Nexus (orchestrator) routes between specialists using
structured output decisions. Token use is optimised by injecting only the
relevant context into each agent call rather than broadcasting the full
message history or all persona files to every node.

Graph topology
--------------
  START → orchestrator ─┬→ specialist_A ──────────────────────────┐
                         ├→ [specialist_B + specialist_C] (parallel)┤ → orchestrator
                         ├→ ...                                    ┘
                         └→ Journalist → reviewer ─→ END
                                  ↑              ↘ Journalist (on rejection)

Token strategy (per call)
--------------------------
  Orchestrator  : its persona prompt + compressed findings summary
  Specialist    : its persona prompt + task + orchestrator instructions
                  + peer findings capped at MAX_PEER_CHARS chars each
  Journalist    : its persona prompt + task + full uncompressed findings
  Reviewer      : reviewer prompt + journalist draft only (not full history)
"""

from typing import Annotated, TypedDict

from pydantic import BaseModel
from langgraph.graph import StateGraph, END, START
from langgraph.graph.message import add_messages
from langgraph.types import Send
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langgraph.prebuilt import ToolNode

from automation.config import (
    load_config,
    create_model,
    create_reviewer_model,
    build_reviewer_prompt,
    get_persona_config,
    load_tools_for_persona,
    build_agent_system_prompt,
)

# Characters retained from each peer agent's output when shown to another
# specialist. Keeps cross-agent context lean without losing key facts.
MAX_PEER_CHARS = 600


# ── State ──────────────────────────────────────────────────────────────────

def _merge_agent_outputs(existing: dict, update: dict) -> dict:
    """Reducer: merge agent-output dicts; newer values win on key collision."""
    return {**existing, **update}


class GraphState(TypedDict):
    """Shared state for the multi-agent supervisor swarm.

    task              Original user prompt — never mutated after initialisation.
    messages          Append-only audit log of all agent/reviewer messages.
    agent_outputs     {persona_name: latest findings text} — merged across nodes.
    next_agents       Routing targets set by the orchestrator. One name = sequential;
                      multiple names = parallel fan-out via Send.
    next_instructions Shared instruction context for the next agent batch.
    agent_call_count  Count of specialist invocations only (safety valve).
    reviewer_approved Set True once Reviewer-2 approves the Journalist draft.
    revision_count    Number of Journalist revision cycles completed.
    """
    task: str
    messages: Annotated[list, add_messages]
    agent_outputs: Annotated[dict, _merge_agent_outputs]
    next_agents: list          # list[str]: specialist names | ["Journalist"] | ["END"]
    next_instructions: str
    agent_call_count: int      # only incremented for specialist dispatches
    reviewer_approved: bool
    revision_count: int


# ── Orchestrator routing schema ────────────────────────────────────────────

class OrchestratorDecision(BaseModel):
    reasoning: str
    next_agents: list[str]  # one name (sequential) or multiple (parallel fan-out)
    instructions: str        # shared instruction context for the dispatched batch


# ── Shared helpers ─────────────────────────────────────────────────────────

def _format_findings(agent_outputs: dict, compress: bool = False,
                     exclude: str = None,
                     max_chars: int = MAX_PEER_CHARS) -> str:
    """Serialise agent_outputs into a prompt-ready string.

    compress=False  → full text (orchestrator, Journalist)
    compress=True   → each entry capped at max_chars (specialist peers)
    """
    if not agent_outputs:
        return "No findings collected yet."
    parts = []
    for agent, output in agent_outputs.items():
        if agent == exclude:
            continue
        body = (output[:max_chars] + "…") if compress and len(output) > max_chars else output
        parts.append(f"### [{agent}]\n{body}")
    return "\n\n".join(parts) if parts else "No findings from colleagues yet."


def _run_tool_loop(model, tools: list, messages: list, max_rounds: int):
    """Run the agent ↔ tools loop until the model stops calling tools.

    Correctly extends the message list on each round so that the full
    conversation context (system prompt, task, prior tool exchanges) is
    preserved across iterations.

    Returns the final AIMessage response.
    """
    tool_executor = ToolNode(tools)
    response = None
    for _ in range(max_rounds):
        response = model.invoke(messages)
        messages = list(messages) + [response]
        if not (hasattr(response, "tool_calls") and response.tool_calls):
            break
        # Extend — not replace — so prior context is preserved
        tool_result = tool_executor.invoke({"messages": messages})
        messages = messages + tool_result["messages"]
    return response


# ── Orchestrator node (Dr. Nexus) ──────────────────────────────────────────

def make_orchestrator_node(config: dict, specialist_names: list):
    """Build the orchestrator node that routes work between specialists."""
    nexus_cfg = get_persona_config(config, config["orchestrator"]["agent"])
    system_prompt = build_agent_system_prompt(nexus_cfg)
    max_calls = config["orchestrator"].get("max_agent_calls", 8)
    valid_targets = set(specialist_names) | {"Journalist", "END"}

    def orchestrator_node(state: GraphState):
        call_count = state.get("agent_call_count", 0)
        already_consulted = list(state.get("agent_outputs", {}).keys())

        # Safety valve — force to Journalist after too many specialist calls
        if call_count >= max_calls:
            return {
                "next_agents": ["Journalist"],
                "next_instructions": (
                    "Synthesise all collected findings into a final structured report. "
                    "The orchestrator has reached its maximum specialist call count."
                ),
                "messages": [AIMessage(content=(
                    f"[Orchestrator safety valve: {max_calls} specialist calls reached. "
                    "Routing directly to Journalist.]"
                ))],
            }

        findings = _format_findings(state.get("agent_outputs", {}))

        # Include already-consulted list so the orchestrator avoids redundant re-routing
        consulted_note = (
            f"SPECIALISTS ALREADY CONSULTED: {', '.join(already_consulted)}"
            if already_consulted else
            "No specialists consulted yet."
        )

        routing_prompt = (
            f"RESEARCH TASK:\n{state['task']}\n\n"
            f"{consulted_note}\n\n"
            f"FINDINGS COLLECTED SO FAR:\n{findings}\n\n"
            f"ALL AVAILABLE SPECIALISTS: {', '.join(specialist_names)}\n\n"
            "Decide the next step:\n"
            "  • Route to one specialist for sequential deep investigation.\n"
            "  • Route to TWO OR MORE specialists simultaneously if their sub-questions\n"
            "    are independent (e.g. prevalence + mechanisms can run in parallel).\n"
            "  • Route to ['Journalist'] when sufficient evidence is ready to write.\n"
            "  • Route to ['END'] only after the Journalist has already produced output.\n"
            "  • Do NOT re-route to a specialist already in ALREADY CONSULTED unless\n"
            "    a specific new sub-question requires it.\n"
            "Return structured output with: reasoning, next_agents (list), instructions."
        )

        model = create_model(config).with_structured_output(OrchestratorDecision)
        decision = model.invoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=routing_prompt),
        ])

        # Validate and filter routing targets
        valid_next = [t for t in decision.next_agents if t in valid_targets]
        if not valid_next:
            valid_next = ["Journalist"]

        # Only count specialist dispatches against the call limit
        specialist_dispatches = [t for t in valid_next if t in specialist_names]

        return {
            "next_agents": valid_next,
            "next_instructions": decision.instructions,
            "agent_call_count": call_count + len(specialist_dispatches),
            "messages": [AIMessage(content=(
                f"[Orchestrator → {valid_next}]: {decision.reasoning}"
            ))],
        }

    return orchestrator_node


# ── Specialist node factory ────────────────────────────────────────────────

def make_specialist_node(persona_name: str, config: dict):
    """Return a LangGraph node function for a specialist persona.

    Each specialist:
      - Gets its own system prompt (not the full swarm prompt).
      - Has access only to its tools listed in swarm_config.yml.
      - Runs its own tool-use loop internally (no shared ToolNode).
      - Stores findings in agent_outputs[persona_name].
    """
    persona_cfg = get_persona_config(config, persona_name)
    tools = load_tools_for_persona(config, persona_cfg)
    system_prompt = build_agent_system_prompt(
        persona_cfg,
        epistemic_tags=config.get("epistemic_tags"),
    )
    max_rounds = config["orchestrator"].get("max_tool_rounds_per_agent", 5)

    def specialist_node(state: GraphState):
        model = create_model(config).bind_tools(tools) if tools else create_model(config)

        # Token-optimised peer context: each peer capped at MAX_PEER_CHARS
        peer_findings = _format_findings(
            state.get("agent_outputs", {}),
            compress=True,
            exclude=persona_name,
        )

        context = HumanMessage(content=(
            f"RESEARCH TASK:\n{state['task']}\n\n"
            f"YOUR SPECIFIC INSTRUCTIONS:\n"
            f"{state.get('next_instructions', 'Provide your expert analysis.')}\n\n"
            f"RELEVANT FINDINGS FROM COLLEAGUES:\n{peer_findings}"
        ))

        response = _run_tool_loop(
            model, tools,
            [SystemMessage(content=system_prompt), context],
            max_rounds,
        )

        final_text = response.content if hasattr(response, "content") else str(response)
        brief = final_text[:150] + "…" if len(final_text) > 150 else final_text

        return {
            "messages": [AIMessage(content=f"[{persona_name}]: {brief}")],
            "agent_outputs": {persona_name: final_text},
        }

    return specialist_node


# ── Journalist node ────────────────────────────────────────────────────────

def make_journalist_node(config: dict):
    """Journalist receives full findings and writes the structured final output."""
    journalist_name = config["orchestrator"]["journalist"]
    journalist_cfg = get_persona_config(config, journalist_name)
    tools = load_tools_for_persona(config, journalist_cfg)
    system_prompt = build_agent_system_prompt(journalist_cfg)
    max_rounds = config["orchestrator"].get("max_tool_rounds_per_agent", 5)

    def journalist_node(state: GraphState):
        model = create_model(config).bind_tools(tools) if tools else create_model(config)

        # Journalist gets full uncompressed findings from all specialists
        full_findings = _format_findings(state.get("agent_outputs", {}))

        revision_note = ""
        if state.get("revision_count", 0) > 0:
            revision_note = (
                f"\n\nREVISION INSTRUCTIONS FROM REVIEWER-2:\n"
                f"{state.get('next_instructions', '')}\n"
                "Address all reviewer feedback in this revised version."
            )

        context = HumanMessage(content=(
            f"RESEARCH TASK:\n{state['task']}\n\n"
            f"ALL SPECIALIST FINDINGS:\n{full_findings}"
            f"{revision_note}\n\n"
            "Write a complete structured output. You MUST include:\n"
            "  • Formal in-text citations [1], [2]…\n"
            "  • A section explicitly distinguishing high engagement from clinical impairment\n"
            "  • A limitations section\n"
            "  • A complete formal References section at the end\n"
            "Save the output to disk using write_manuscript_section, "
            "then call git_commit_snapshot."
        ))

        response = _run_tool_loop(
            model, tools,
            [SystemMessage(content=system_prompt), context],
            max_rounds,
        )

        final_text = response.content if hasattr(response, "content") else str(response)

        return {
            "messages": [AIMessage(content=f"[Journalist draft — {len(final_text)} chars]")],
            "agent_outputs": {journalist_name: final_text},
        }

    return journalist_node


# ── Reviewer node ──────────────────────────────────────────────────────────

def make_reviewer_node(config: dict):
    """Adversarial reviewer — uses a separate model config for genuine diversity."""
    reviewer_prompt = build_reviewer_prompt(config)
    max_revisions = config["reviewer"].get("max_revision_loops", 3)
    journalist_name = config["orchestrator"]["journalist"]

    def reviewer_node(state: GraphState):
        revision_count = state.get("revision_count", 0)

        if revision_count >= max_revisions:
            return {
                "reviewer_approved": True,
                "messages": [AIMessage(content=(
                    f"[Reviewer-2 safety valve: {max_revisions} revision loops reached. "
                    "Force-approved.]"
                ))],
            }

        draft = state.get("agent_outputs", {}).get(journalist_name, "")
        if not draft:
            return {"reviewer_approved": True}

        # Use reviewer-specific model (higher temperature, optionally different model)
        # for genuine adversarial diversity rather than the same model as the agents.
        model = create_reviewer_model(config)
        response = model.invoke([
            SystemMessage(content=reviewer_prompt),
            HumanMessage(content=draft),
        ])

        if response.content.strip().startswith("APPROVED"):
            return {
                "reviewer_approved": True,
                "messages": [AIMessage(content="[Reviewer-2]: APPROVED")],
            }

        return {
            "reviewer_approved": False,
            "revision_count": revision_count + 1,
            "next_instructions": response.content,
            "messages": [AIMessage(content=(
                f"[Reviewer-2 REJECTED]: {response.content[:200]}…"
            ))],
        }

    return reviewer_node


# ── Graph builder ──────────────────────────────────────────────────────────

def build_graph(config: dict = None):
    """Build and compile the multi-agent supervisor LangGraph.

    Node registration is fully dynamic — derived from the personas listed in
    swarm_config.yml. Adding or removing specialist agents requires only config
    changes, not Python code changes.

    Parallel fan-out: when the orchestrator sets next_agents to multiple
    specialist names, they are dispatched concurrently via LangGraph Send.
    """
    if config is None:
        config = load_config()

    reviewer_enabled = config["reviewer"].get("enabled", True)
    orchestrator_name = config["orchestrator"]["agent"]
    journalist_name = config["orchestrator"]["journalist"]

    specialist_names = [
        p["name"] for p in config["personas"]
        if p["name"] not in (orchestrator_name, journalist_name)
    ]

    workflow = StateGraph(GraphState)

    # ── Register nodes ──────────────────────────────────────────────────
    workflow.add_node(
        "orchestrator",
        make_orchestrator_node(config, specialist_names),
    )

    for name in specialist_names:
        workflow.add_node(name, make_specialist_node(name, config))

    workflow.add_node("Journalist", make_journalist_node(config))

    if reviewer_enabled:
        workflow.add_node("reviewer", make_reviewer_node(config))

    # ── Wire edges ──────────────────────────────────────────────────────
    workflow.add_edge(START, "orchestrator")

    # Every specialist returns to orchestrator (both sequential and parallel paths)
    for name in specialist_names:
        workflow.add_edge(name, "orchestrator")

    # Orchestrator routing: sequential | parallel fan-out via Send | Journalist | END
    specialist_set = set(specialist_names)

    def orchestrator_router(state: GraphState):
        targets = state.get("next_agents", ["END"])
        specialist_targets = [t for t in targets if t in specialist_set]

        if len(specialist_targets) > 1:
            # Parallel fan-out: dispatch multiple specialists simultaneously
            return [Send(name, state) for name in specialist_targets]
        elif len(specialist_targets) == 1:
            return specialist_targets[0]
        elif "Journalist" in targets:
            return "Journalist"
        return "reviewer" if reviewer_enabled else END

    routing_map = {name: name for name in specialist_names}
    routing_map["Journalist"] = "Journalist"
    routing_map["END"] = "reviewer" if reviewer_enabled else END

    workflow.add_conditional_edges("orchestrator", orchestrator_router, routing_map)

    if reviewer_enabled:
        workflow.add_edge("Journalist", "reviewer")

        def reviewer_router(state: GraphState) -> str:
            return END if state.get("reviewer_approved", False) else "Journalist"

        workflow.add_conditional_edges(
            "reviewer",
            reviewer_router,
            {END: END, "Journalist": "Journalist"},
        )
    else:
        workflow.add_edge("Journalist", END)

    return workflow.compile()
