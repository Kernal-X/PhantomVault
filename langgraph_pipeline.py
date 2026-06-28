from __future__ import annotations

import copy
from typing import Any, Dict, List

from langgraph.graph import END, START, StateGraph

from agents.analysis.analysis_agent import analysis_agent
from agents.deployment.deployment_agent import DeploymentManager
from agents.event_enrichment import EventEnricher
from agents.generation.generation_agent import GenerationAgent
from agents.strategy.strategy_agent import strategy_agent
from core.interception_layer import InterceptionLayer
from core.monitor import Monitor
from detectors.scoring import ScoringDetector
from logs.logger import SOCLogger
from state_schema import DetectionRecord, SecuritySystemState
from utils.filters import EventFilter


def _copy_events(events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return copy.deepcopy(events or [])


class LangGraphSecurityPipeline:
    """
    LangGraph wrapper around the existing monitoring, scoring, analysis,
    strategy, deployment, and interception components.
    """

    def __init__(
        self,
        monitor: Monitor | None = None,
        detector: ScoringDetector | None = None,
        event_filter: EventFilter | None = None,
        logger: SOCLogger | None = None,
        enricher: EventEnricher | None = None,
        deployment_manager: DeploymentManager | None = None,
        generation_agent: GenerationAgent | None = None,
        monitor_interval: float = 1.0,
        file_watch_paths: List[str] | None = None,
        file_watch_recursive: bool = True,
    ) -> None:
        self.monitor = monitor or Monitor(
            interval=monitor_interval,
            file_watch_paths=file_watch_paths,
            file_watch_recursive=file_watch_recursive,
        )
        self.detector = detector or ScoringDetector(alert_threshold=0, suspicious_threshold=0)
        self.event_filter = event_filter or EventFilter()
        self.logger = logger or SOCLogger(rate_limit_seconds=30)
        self.enricher = enricher or EventEnricher()
        self.deployment_manager = deployment_manager or DeploymentManager()
        self.generation_agent = generation_agent or GenerationAgent()
        self.interception_layer = InterceptionLayer(generation_agent=self.generation_agent)
        self.app = self._build_graph()

    def _build_graph(self):
        graph = StateGraph(SecuritySystemState)

        graph.add_node("prepare_state", self.prepare_state)
        graph.add_node("collect_events", self.collect_events)
        graph.add_node("enrich_events", self.enrich_events)
        graph.add_node("filter_events", self.filter_events)
        graph.add_node("score_events", self.score_events)
        graph.add_node("emit_alerts", self.emit_alerts)
        graph.add_node("analysis", self.run_analysis)
        graph.add_node("strategy", self.run_strategy)
        graph.add_node("deployment", self.run_deployment)
        graph.add_node("interception", self.run_interception)

        graph.add_edge(START, "prepare_state")
        graph.add_conditional_edges(
            "prepare_state",
            self.route_after_prepare,
            {
                "collect_events": "collect_events",
                "analysis": "analysis",
                "strategy": "strategy",
                "deployment": "deployment",
                "interception": "interception",
                "end": END,
            },
        )

        graph.add_edge("collect_events", "enrich_events")
        graph.add_edge("enrich_events", "filter_events")
        graph.add_edge("filter_events", "score_events")
        graph.add_edge("score_events", "emit_alerts")
        graph.add_conditional_edges(
            "emit_alerts",
            self.route_after_alerting,
            {
                "analysis": "analysis",
                "end": END,
            },
        )

        graph.add_edge("analysis", "strategy")
        graph.add_conditional_edges(
            "strategy",
            self.route_after_strategy,
            {
                "deployment": "deployment",
                "end": END,
            },
        )
        graph.add_conditional_edges(
            "deployment",
            self.route_after_deployment,
            {
                "interception": "interception",
                "end": END,
            },
        )
        graph.add_edge("interception", END)

        return graph.compile()

    def prepare_state(self, state: SecuritySystemState) -> SecuritySystemState:
        prepared = dict(state)
        prepared.setdefault("mode", "monitor")
        prepared["input_events"] = list(prepared.get("input_events") or [])
        prepared["raw_events"] = []
        prepared["enriched_events"] = []
        prepared["filtered_events"] = []
        prepared["detections"] = []
        prepared["suspicious_events"] = []
        prepared["alert_records"] = []
        prepared["errors"] = []
        prepared["notes"] = []
        prepared["risk_score"] = 0.0
        return prepared

    def route_after_prepare(self, state: SecuritySystemState) -> str:
        if state.get("mode") != "intercept":
            return "collect_events"

        if state.get("deployment"):
            return "interception"
        if state.get("strategy"):
            return "deployment"
        if state.get("analysis"):
            return "strategy"
        if state.get("alert_records"):
            return "analysis"
        return "end"

    def collect_events(self, state: SecuritySystemState) -> SecuritySystemState:
        events = _copy_events(state.get("input_events") or [])
        if not events:
            events = self.monitor.collect()
        state["raw_events"] = events
        state["notes"] = [*state.get("notes", []), f"Collected {len(events)} events"]
        return state

    def enrich_events(self, state: SecuritySystemState) -> SecuritySystemState:
        enriched = _copy_events(state.get("raw_events") or [])
        for event in enriched:
            self.enricher.enrich(event)
        state["enriched_events"] = enriched
        return state

    def filter_events(self, state: SecuritySystemState) -> SecuritySystemState:
        filtered = [
            event
            for event in state.get("enriched_events", [])
            if not self.event_filter.should_ignore_noise(event)
        ]
        state["filtered_events"] = filtered
        return state

    def score_events(self, state: SecuritySystemState) -> SecuritySystemState:
        detection_records: List[DetectionRecord] = []
        suspicious_events: List[Dict[str, Any]] = []

        for event in state.get("filtered_events", []):
            detection = self.detector.analyze(event)
            accepted = self.event_filter.apply_known_process_logic(event, detection)
            record: DetectionRecord = {
                "event": event,
                "detection": detection,
                "accepted": accepted,
            }
            detection_records.append(record)

            if accepted and detection.get("severity") in {"alert", "suspicious"}:
                suspicious_events.append(event)

        state["detections"] = detection_records
        state["suspicious_events"] = suspicious_events
        return state

    def emit_alerts(self, state: SecuritySystemState) -> SecuritySystemState:
        alert_records: List[Dict[str, Any]] = []
        risk_score = 0.0

        for record in state.get("detections", []):
            if not record.get("accepted"):
                continue

            detection = record.get("detection", {})
            if detection.get("severity") not in {"alert", "suspicious"}:
                continue

            output = self.logger.emit(record["event"], detection)
            if not output:
                continue

            alert_records.append(output)
            aggregation = output.get("aggregation", {})
            if aggregation.get("alert"):
                risk_score = float(
                    aggregation.get("data", {}).get("risk_score", risk_score) or risk_score
                )

        state["alert_records"] = alert_records
        state["risk_score"] = risk_score
        return state

    def route_after_alerting(self, state: SecuritySystemState) -> str:
        for record in state.get("alert_records", []):
            if record.get("aggregation", {}).get("alert"):
                return "analysis"
        return "end"

    def run_analysis(self, state: SecuritySystemState) -> SecuritySystemState:
        dominant_alert = None
        for record in reversed(state.get("alert_records", [])):
            aggregation = record.get("aggregation", {})
            if aggregation.get("alert"):
                dominant_alert = aggregation.get("data", {})
                break

        analysis_input = {
            "risk_score": state.get("risk_score", 0.0),
            "events": (dominant_alert or {}).get("events", []),
        }
        analysis_output = analysis_agent(analysis_input)
        state["analysis"] = analysis_output.get("analysis", {})
        return state

    def run_strategy(self, state: SecuritySystemState) -> SecuritySystemState:
        strategy_output = strategy_agent(
            {
                "analysis": state.get("analysis", {}),
                "strategy": state.get("strategy"),
                "strategy_meta": state.get("strategy_meta"),
            }
        )
        state["strategy"] = strategy_output.get("strategy", {})
        state["strategy_meta"] = strategy_output.get("strategy_meta", {})
        return state

    def route_after_strategy(self, state: SecuritySystemState) -> str:
        return "deployment" if state.get("strategy") else "end"

    def run_deployment(self, state: SecuritySystemState) -> SecuritySystemState:
        deployment = self.deployment_manager.deploy(state.get("strategy", {}))
        state["deployment"] = deployment
        return state

    def route_after_deployment(self, state: SecuritySystemState) -> str:
        return "interception" if state.get("request_path") else "end"

    def run_interception(self, state: SecuritySystemState) -> SecuritySystemState:
        request_path = state.get("request_path")
        if not request_path:
            state["errors"] = [*state.get("errors", []), "Missing request_path for interception"]
            return state

        result = self.interception_layer.handle(
            {
                "path": request_path,
                "analysis": state.get("analysis", {}),
                "deployment": state.get("deployment", {}),
            }
        )
        state["interception_result"] = result
        return state

    def run_monitor_cycle(self, state: SecuritySystemState | None = None) -> SecuritySystemState:
        initial_state = dict(state or {})
        initial_state["mode"] = "monitor"
        return self.app.invoke(initial_state)

    def intercept_access(self, state: SecuritySystemState | None = None) -> SecuritySystemState:
        initial_state = dict(state or {})
        initial_state["mode"] = "intercept"
        return self.app.invoke(initial_state)


def build_security_workflow() -> LangGraphSecurityPipeline:
    return LangGraphSecurityPipeline()
