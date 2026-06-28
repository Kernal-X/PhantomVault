from __future__ import annotations

from typing import Any, Dict, List, Literal, TypedDict


class DetectionRecord(TypedDict, total=False):
    event: Dict[str, Any]
    detection: Dict[str, Any]
    accepted: bool


class SecuritySystemState(TypedDict, total=False):
    mode: Literal["monitor", "intercept"]
    input_events: List[Dict[str, Any]]
    raw_events: List[Dict[str, Any]]
    enriched_events: List[Dict[str, Any]]
    filtered_events: List[Dict[str, Any]]
    detections: List[DetectionRecord]
    suspicious_events: List[Dict[str, Any]]
    alert_records: List[Dict[str, Any]]
    risk_score: float
    analysis: Dict[str, Any]
    strategy: Dict[str, Any]
    strategy_meta: Dict[str, Any]
    deployment: Dict[str, Any]
    request_path: str
    interception_result: str
    errors: List[str]
    notes: List[str]
    cycle_report: Dict[str, Any]
