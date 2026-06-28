"""
Lightweight LangGraph for the analysis -> strategy planning path.

The full operational graph lives in ``langgraph_pipeline.py`` and additionally
wraps monitoring, deployment, and interception.
"""

from __future__ import annotations

from typing import Any, Dict, List, TypedDict

from langgraph.graph import END, START, StateGraph

from agents.analysis.analysis_agent import analysis_agent
from agents.strategy.strategy_agent import strategy_agent


class DeceptionState(TypedDict, total=False):
    risk_score: float
    events: List[Dict[str, Any]]
    analysis: Dict[str, Any]
    strategy: Dict[str, Any]
    strategy_meta: Dict[str, Any]
    generation: Dict[str, Any]


def _queue_generation(state: DeceptionState) -> DeceptionState:
    state["generation"] = {
        "status": "queued",
        "reason": "Concrete artifact generation happens after deployment/interception input is available.",
    }
    return state


def build_deception_graph():
    graph = StateGraph(DeceptionState)
    graph.add_node("analysis", analysis_agent)
    graph.add_node("strategy", strategy_agent)
    graph.add_node("generation", _queue_generation)
    graph.add_edge(START, "analysis")
    graph.add_edge("analysis", "strategy")
    graph.add_edge("strategy", "generation")
    graph.add_edge("generation", END)
    return graph.compile()


deception_workflow = build_deception_graph()
