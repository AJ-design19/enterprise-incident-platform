"""
LangGraph orchestration for the full incident-response pipeline.

Flow (matches the Week 4 plan):
    User Query
        -> Incident Classifier
        -> Parallel: [Log Agent, Graph Agent]
        -> Knowledge Retrieval
        -> Root Cause Agent
        -> Recommendation Agent
        -> Response

State is shared across nodes via IncidentState (TypedDict). Each node is
wrapped with basic error handling/retry logic so one agent's failure
doesn't crash the whole run — it records the error in state and the
downstream nodes work with whatever evidence is available.
"""
from __future__ import annotations

import operator
from typing import Annotated, Any, Optional, TypedDict

from langgraph.graph import END, StateGraph

from agents.graph_query_agent import GraphQueryAgent
from agents.incident_classifier import IncidentClassifierAgent
from agents.log_analyzer import LogAnalysisAgent
from agents.rca_agent import RootCauseAgent
from agents.recommendation_agent import RecommendationAgent
from agents.retrieval_agent import KnowledgeRetrievalAgent
from logging_setup import logger


class IncidentState(TypedDict, total=False):
    incident_text: str
    log_path: Optional[str]
    graph_question: Optional[str]

    classification: dict
    log_findings: dict
    graph_findings: dict
    sop_findings: dict
    rca: dict
    recommendation: dict

    errors: Annotated[list[str], operator.add]


def _safe(node_name: str, fn, state: IncidentState) -> dict:
    try:
        return fn(state)
    except Exception as exc:  # noqa: BLE001
        logger.error(f"[workflow:{node_name}] failed: {exc}")
        return {"errors": [f"{node_name}: {exc}"]}


class IncidentWorkflow:
    """Builds and runs the compiled LangGraph state machine."""

    def __init__(self):
        self.classifier = IncidentClassifierAgent()
        self.log_agent = LogAnalysisAgent()
        self.graph_agent = GraphQueryAgent()
        self.retrieval_agent = KnowledgeRetrievalAgent()
        self.rca_agent = RootCauseAgent()
        self.recommendation_agent = RecommendationAgent()
        self.graph = self._build_graph()

    # ---- Nodes -----------------------------------------------------
    def _classify(self, state: IncidentState) -> dict:
        def _fn(s):
            result = self.classifier.run(s["incident_text"])
            return {"classification": result.model_dump()}

        return _safe("classify", _fn, state)

    def _analyze_logs(self, state: IncidentState) -> dict:
        def _fn(s):
            if not s.get("log_path"):
                return {"log_findings": {"summary": "No log file provided for this incident."}}
            result = self.log_agent.run(s["log_path"])
            return {"log_findings": result.model_dump()}

        return _safe("log_analysis", _fn, state)

    def _query_graph(self, state: IncidentState) -> dict:
        def _fn(s):
            question = s.get("graph_question") or (
                f"What services, dependencies, and past incidents relate to "
                f"{s.get('classification', {}).get('affected_service', 'the affected service')}?"
            )
            result = self.graph_agent.run(question)
            return {"graph_findings": result.model_dump()}

        return _safe("graph_query", _fn, state)

    def _retrieve_knowledge(self, state: IncidentState) -> dict:
        def _fn(s):
            result = self.retrieval_agent.run(s["incident_text"])
            return {"sop_findings": result.model_dump()}

        return _safe("knowledge_retrieval", _fn, state)

    def _root_cause(self, state: IncidentState) -> dict:
        def _fn(s):
            result = self.rca_agent.run(
                classification=s.get("classification", {}),
                log_findings=s.get("log_findings", {}),
                graph_findings=s.get("graph_findings", {}),
                sop_findings=s.get("sop_findings", {}),
            )
            return {"rca": result.model_dump()}

        return _safe("root_cause", _fn, state)

    def _recommend(self, state: IncidentState) -> dict:
        def _fn(s):
            priority = s.get("classification", {}).get("priority", "P3-Medium")
            result = self.recommendation_agent.run(rca_summary=s.get("rca", {}), priority=priority)
            return {"recommendation": result.model_dump()}

        return _safe("recommendation", _fn, state)

    # ---- Graph construction -----------------------------------------
    def _build_graph(self):
        builder = StateGraph(IncidentState)

        builder.add_node("classify", self._classify)
        builder.add_node("analyze_logs", self._analyze_logs)
        builder.add_node("query_graph", self._query_graph)
        builder.add_node("retrieve_knowledge", self._retrieve_knowledge)
        builder.add_node("root_cause", self._root_cause)
        builder.add_node("recommend", self._recommend)

        builder.set_entry_point("classify")

        # Fan-out: classify -> {analyze_logs, query_graph} run in parallel
        builder.add_edge("classify", "analyze_logs")
        builder.add_edge("classify", "query_graph")

        # Fan-in: both parallel branches must complete before retrieval proceeds
        builder.add_edge("analyze_logs", "retrieve_knowledge")
        builder.add_edge("query_graph", "retrieve_knowledge")

        builder.add_edge("retrieve_knowledge", "root_cause")
        builder.add_edge("root_cause", "recommend")
        builder.add_edge("recommend", END)

        return builder.compile()

    def run(self, incident_text: str, log_path: str | None = None, graph_question: str | None = None) -> IncidentState:
        initial_state: IncidentState = {
            "incident_text": incident_text,
            "log_path": log_path,
            "graph_question": graph_question,
            "errors": [],
        }
        logger.info(f"Starting incident workflow for: {incident_text[:80]}...")
        final_state = self.graph.invoke(initial_state)
        logger.info(f"Workflow complete. Errors encountered: {final_state.get('errors', [])}")
        return final_state


if __name__ == "__main__":
    workflow = IncidentWorkflow()
    output = workflow.run(
        incident_text="Payment API is timing out for ~15% of checkout requests since 10:42 UTC.",
        log_path="sample_data/logs/app.log",
    )
    import json

    print(json.dumps(output, indent=2, default=str))
