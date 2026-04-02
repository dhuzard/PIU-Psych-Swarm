"""
graph.py — LangGraph State Machine for the Research Swarm

This module builds the core Agent → Tools → Reviewer loop.
ALL configuration (model, tools, reviewer constraints) is loaded
dynamically from swarm_config.yml via config.py.

Graph topology:
  START → agent → (tools | reviewer)
                    ↓          ↓
                  agent    (APPROVED → END)
                           (REJECTED → agent)  ← max N loops
"""

from typing import Annotated, Sequence, TypedDict

from langgraph.graph import StateGraph, END, START
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage, SystemMessage, HumanMessage
from langgraph.prebuilt import ToolNode

from automation.config import load_config, load_tools, create_model, build_reviewer_prompt


# ── State Definition ─────────────────────────────────
class GraphState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]
    reviewer_approved: bool
    revision_count: int


# ── Graph Builder ────────────────────────────────────
def build_graph(config: dict = None):
    """Build and compile the LangGraph state machine.

    Args:
        config: Optional pre-loaded config dict. If None, loads
                from swarm_config.yml automatically.

    Returns:
        A compiled LangGraph that can be invoked or streamed.
    """
    if config is None:
        config = load_config()

    # Load tools and reviewer settings from config
    tools = load_tools(config)
    max_revisions = config["reviewer"].get("max_revision_loops", 3)
    reviewer_enabled = config["reviewer"].get("enabled", True)
    reviewer_prompt_text = build_reviewer_prompt(config)

    # ── Node: Agent ──────────────────────────────────
    def call_model(state: GraphState):
        """Central agent node — invokes the LLM with all bound tools."""
        model = create_model(config)
        model_with_tools = model.bind_tools(tools)
        response = model_with_tools.invoke(state["messages"])
        return {"messages": [response]}

    # ── Node: Reviewer-2 ─────────────────────────────
    def call_reviewer(state: GraphState):
        """Adversarial checkpoint node.

        Reads the agent's latest text output and decides:
          - APPROVED → end the graph
          - REJECTED → loop back to agent with feedback

        Includes a safety valve: after max_revision_loops,
        the output is force-approved to prevent infinite loops
        and runaway API costs.
        """
        messages = state["messages"]
        last_message = messages[-1]

        # If the last message was a tool call, pass through
        if hasattr(last_message, "tool_calls") and last_message.tool_calls:
            return {"reviewer_approved": True}

        # Safety valve: force-approve after N revision loops
        revision_count = state.get("revision_count", 0)
        if revision_count >= max_revisions:
            return {
                "messages": [
                    HumanMessage(
                        content=(
                            f"[Reviewer-2 Safety Valve]: Maximum revision loops "
                            f"({max_revisions}) reached. Force-approving output."
                        )
                    )
                ],
                "reviewer_approved": True,
            }

        # Invoke the reviewer LLM
        model = create_model(config)
        reviewer_system = SystemMessage(content=reviewer_prompt_text)
        response = model.invoke(
            [reviewer_system, HumanMessage(content=str(last_message.content))]
        )

        if response.content.strip().startswith("APPROVED"):
            return {"reviewer_approved": True}
        else:
            return {
                "messages": [
                    HumanMessage(
                        content=f"Reviewer-2 Feedback: {response.content}"
                    )
                ],
                "reviewer_approved": False,
                "revision_count": revision_count + 1,
            }

    # ── Build the State Machine ──────────────────────
    workflow = StateGraph(GraphState)

    # Define nodes
    workflow.add_node("agent", call_model)
    workflow.add_node("tools", ToolNode(tools))

    if reviewer_enabled:
        workflow.add_node("reviewer", call_reviewer)

    # ── Routing Logic ────────────────────────────────
    def agent_router(state: GraphState):
        """Route after agent: tool calls → tools node, text → reviewer."""
        last_message = state["messages"][-1]
        if hasattr(last_message, "tool_calls") and last_message.tool_calls:
            return "tools"
        return "reviewer" if reviewer_enabled else END

    def reviewer_router(state: GraphState):
        """Route after reviewer: approved → END, rejected → agent."""
        if state.get("reviewer_approved", False):
            return END
        return "agent"

    # Wire edges
    workflow.add_edge(START, "agent")

    if reviewer_enabled:
        workflow.add_conditional_edges(
            "agent",
            agent_router,
            {"tools": "tools", "reviewer": "reviewer"},
        )
        workflow.add_conditional_edges(
            "reviewer",
            reviewer_router,
            {"agent": "agent", END: END},
        )
    else:
        workflow.add_conditional_edges(
            "agent",
            agent_router,
            {"tools": "tools", END: END},
        )

    workflow.add_edge("tools", "agent")

    return workflow.compile()
