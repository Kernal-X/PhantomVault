from __future__ import annotations

import json
import mimetypes
import os
import time
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict, List
from urllib.parse import parse_qs, urlparse

import yaml
from dotenv import load_dotenv

from langgraph_pipeline import LangGraphSecurityPipeline


REPO_ROOT = Path(__file__).resolve().parent
load_dotenv(REPO_ROOT / ".env")
FRONTEND_DIST = REPO_ROOT / "frontend" / "dist"
CONFIG_PATH = REPO_ROOT / "configs" / "system_config.yaml"
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8765
MODEL_ARTIFACTS = [
    REPO_ROOT / "ml" / "ml_models" / "file_model" / "file_hybrid_final.pkl",
    REPO_ROOT / "ml" / "ml_models" / "process_model" / "process_hybrid_final.pkl",
    REPO_ROOT / "ml" / "ml_models" / "network_model" / "network_hybrid_model.pkl",
]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def load_yaml(path: Path) -> Dict[str, Any]:
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except Exception:
        return {}


def load_registry() -> Dict[str, Any]:
    path = REPO_ROOT / "registry.json"
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def summarize_event(event: Dict[str, Any]) -> Dict[str, Any]:
    data = event.get("data", {}) if isinstance(event, dict) else {}
    return {
        "type": event.get("type", "unknown"),
        "timestamp": event.get("timestamp"),
        "process_name": data.get("process_name"),
        "pid": data.get("pid"),
        "parent_process": data.get("parent_process"),
        "cmdline": data.get("cmdline"),
        "file_path": data.get("file_path"),
        "action": data.get("action"),
        "remote_ip": data.get("remote_ip"),
        "remote_port": data.get("remote_port"),
        "status": data.get("status"),
        "score_features": {
            "cpu_percent": data.get("cpu_percent"),
            "memory_mb": data.get("memory_mb"),
            "cmd_entropy": data.get("cmd_entropy"),
            "file_freq_1min": data.get("file_freq_1min"),
            "connection_freq_1min": data.get("connection_freq_1min"),
        },
    }


def summarize_detection(record: Dict[str, Any]) -> Dict[str, Any]:
    detection = record.get("detection", {}) if isinstance(record, dict) else {}
    return {
        "accepted": bool(record.get("accepted")),
        "event": summarize_event(record.get("event", {})),
        "score": safe_int(detection.get("score")),
        "severity": detection.get("severity", "none"),
        "reasons": detection.get("reasons", []) or [],
        "rare_patterns": detection.get("rare_patterns", []) or [],
    }


class DashboardRuntime:
    def __init__(self) -> None:
        self.pipeline: LangGraphSecurityPipeline | None = None
        self.state: Dict[str, Any] = {"deployment": {"decoy_registry": load_registry()}}
        self.config = load_yaml(CONFIG_PATH)
        self.started_at = utc_now()
        self.cycle_count = 0
        self.last_cycle_at: str | None = None
        self.last_cycle_duration_ms = 0
        self.last_interception: Dict[str, Any] | None = None
        self.errors: List[str] = []

    def _ensure_pipeline(self) -> LangGraphSecurityPipeline:
        if self.pipeline is not None:
            return self.pipeline

        monitoring = self.config.get("monitoring", {}) if isinstance(self.config, dict) else {}
        self.pipeline = LangGraphSecurityPipeline(
            monitor_interval=safe_float(monitoring.get("poll_interval"), 1.0),
            file_watch_paths=monitoring.get("file_watch_paths") or ["."],
            file_watch_recursive=bool(monitoring.get("recursive", True)),
        )
        return self.pipeline

    def stop(self) -> None:
        try:
            if self.pipeline and getattr(self.pipeline.monitor, "file_collector", None):
                self.pipeline.monitor.file_collector.stop()
        except Exception:
            pass

    def run_cycle(self) -> Dict[str, Any]:
        start = time.perf_counter()
        try:
            self.state = dict(self._ensure_pipeline().run_monitor_cycle(self.state))
            self.cycle_count += 1
            self.last_cycle_at = utc_now()
            self.last_cycle_duration_ms = int((time.perf_counter() - start) * 1000)
        except Exception as exc:
            self.errors.append(str(exc))
        return self.snapshot()

    def intercept(self, request_path: str) -> Dict[str, Any]:
        if not request_path:
            raise ValueError("path is required")
        state = dict(self.state)
        state["request_path"] = request_path
        try:
            self.state = dict(self._ensure_pipeline().intercept_access(state))
            self.last_interception = {
                "path": request_path,
                "timestamp": utc_now(),
                "result": self.state.get("interception_result"),
            }
        except Exception as exc:
            self.errors.append(str(exc))
            raise
        return self.snapshot()

    def snapshot(self) -> Dict[str, Any]:
        state = self.state or {}
        raw_events = state.get("raw_events", []) or []
        detections = state.get("detections", []) or []
        alert_records = state.get("alert_records", []) or []
        deployment = state.get("deployment", {}) or {}
        registry = deployment.get("decoy_registry") or load_registry()
        rules = deployment.get("interception_rules") or {}
        risk_score = safe_float(state.get("risk_score"))
        active_incidents = len([item for item in detections if item.get("accepted")])

        return {
            "generated_at": utc_now(),
            "backend": {
                "connected": True,
                "entrypoint": "dashboard_server.py",
                "mode": "manual_api",
                "auto_cycles": False,
                "started_at": self.started_at,
            },
            "runtime": {
                "pipeline_initialized": self.pipeline is not None,
                "cycle_count": self.cycle_count,
                "last_cycle_at": self.last_cycle_at,
                "last_cycle_duration_ms": self.last_cycle_duration_ms,
            },
            "status": {
                "threat_level": self._threat_level(risk_score, active_incidents),
                "risk_score": risk_score,
                "active_incidents": active_incidents,
                "events_processed": len(raw_events),
            },
            "telemetry": {
                "counts": self._event_counts(raw_events),
                "recent_events": [summarize_event(event) for event in raw_events[-30:]],
            },
            "detections": [summarize_detection(record) for record in detections[-40:]],
            "alerts": alert_records[-20:],
            "analysis": state.get("analysis", {}) or {},
            "strategy": state.get("strategy", {}) or {},
            "strategy_meta": state.get("strategy_meta", {}) or {},
            "deployment": {
                "decoys": [{"path": path, **meta} for path, meta in registry.items()],
                "rules": [{"path": path, **rule} for path, rule in rules.items()],
            },
            "interception": self.last_interception,
            "models": self._models(),
            "config": self._config_summary(),
            "errors": list(dict.fromkeys([*self.errors, *state.get("errors", [])]))[-20:],
            "notes": state.get("notes", [])[-20:],
        }

    def _event_counts(self, events: List[Dict[str, Any]]) -> Dict[str, int]:
        counts: Dict[str, int] = {}
        for event in events:
            key = event.get("type", "unknown")
            counts[key] = counts.get(key, 0) + 1
        return counts

    def _models(self) -> List[Dict[str, Any]]:
        output = []
        for model in MODEL_ARTIFACTS:
            output.append(
                {
                    "name": model.stem,
                    "path": str(model.relative_to(REPO_ROOT)),
                    "exists": model.exists(),
                    "size": model.stat().st_size if model.exists() else 0,
                }
            )
        return output

    def _config_summary(self) -> Dict[str, Any]:
        monitoring = self.config.get("monitoring", {}) if isinstance(self.config, dict) else {}
        system = self.config.get("system", {}) if isinstance(self.config, dict) else {}
        return {
            "name": system.get("name", "Agentic Security System"),
            "version": system.get("version", "unknown"),
            "environment": system.get("environment", "unknown"),
            "poll_interval": monitoring.get("poll_interval"),
            "recursive": monitoring.get("recursive"),
            "watch_paths": monitoring.get("file_watch_paths", []),
        }

    def _threat_level(self, risk_score: float, active_incidents: int) -> str:
        if risk_score >= 1.5:
            return "critical"
        if risk_score >= 0.8:
            return "high"
        if active_incidents > 0 or risk_score > 0:
            return "elevated"
        return "quiet"


class DashboardHandler(BaseHTTPRequestHandler):
    runtime: DashboardRuntime

    def log_message(self, format: str, *args: Any) -> None:
        return

    def _send_json(self, payload: Dict[str, Any], status: int = 200) -> None:
        raw = json.dumps(payload, default=str).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET,POST,OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
        try:
            self.wfile.write(raw)
        except (BrokenPipeError, ConnectionAbortedError, ConnectionResetError):
            pass

    def do_OPTIONS(self) -> None:
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET,POST,OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/api/health":
            self._send_json({"ok": True, "generated_at": utc_now(), "auto_cycles": False})
            return
        if parsed.path == "/api/state":
            self._send_json(self.runtime.snapshot())
            return
        if parsed.path == "/api/cycle":
            self._send_json(self.runtime.run_cycle())
            return
        self._serve_static(parsed.path)

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        length = safe_int(self.headers.get("Content-Length"), 0)
        raw = self.rfile.read(length).decode("utf-8") if length else "{}"
        try:
            payload = json.loads(raw or "{}")
        except json.JSONDecodeError:
            payload = {}

        if parsed.path == "/api/cycle":
            self._send_json(self.runtime.run_cycle())
            return

        if parsed.path == "/api/intercept":
            query = parse_qs(parsed.query)
            request_path = payload.get("path") or query.get("path", [""])[0]
            try:
                self._send_json(self.runtime.intercept(str(request_path)))
            except Exception as exc:
                self._send_json({"error": str(exc)}, status=400)
            return

        self._send_json({"error": "Unknown endpoint"}, status=404)

    def _serve_static(self, request_path: str) -> None:
        if request_path == "/":
            request_path = "/index.html"
        if not FRONTEND_DIST.exists():
            self._send_json(
                {
                    "message": "Frontend build not found. Run `cd frontend && npm run build`.",
                    "api": ["/api/health", "/api/state", "/api/cycle", "/api/intercept"],
                }
            )
            return

        requested = (FRONTEND_DIST / request_path.lstrip("/")).resolve()
        root = FRONTEND_DIST.resolve()
        if not str(requested).startswith(str(root)) or not requested.exists():
            requested = root / "index.html"

        data = requested.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", mimetypes.guess_type(str(requested))[0] or "application/octet-stream")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        try:
            self.wfile.write(data)
        except (BrokenPipeError, ConnectionAbortedError, ConnectionResetError):
            pass


def run_server(host: str = DEFAULT_HOST, port: int = DEFAULT_PORT) -> None:
    runtime = DashboardRuntime()
    DashboardHandler.runtime = runtime
    server = ThreadingHTTPServer((host, port), DashboardHandler)
    print(f"Dashboard API running at http://{host}:{port}")
    print("Manual mode: no monitor cycle runs until /api/cycle is called.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        runtime.stop()
        server.server_close()


if __name__ == "__main__":
    run_server(
        host=os.environ.get("DASHBOARD_HOST", DEFAULT_HOST),
        port=safe_int(os.environ.get("DASHBOARD_PORT"), DEFAULT_PORT),
    )
