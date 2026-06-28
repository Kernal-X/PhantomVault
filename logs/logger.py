import json
import time
from typing import Any, Dict, Optional, Tuple

from ml.ml_models.aggregator_model.aggregator import StreamingAggregator
from ml.ml_models.aggregator_model.router import ModelRouter


class SOCLogger:
    def __init__(self, rate_limit_seconds: int = 30, ml_threshold: float = 1.5, ml_decay: float = 0.9):
        self.rate_limit_seconds = rate_limit_seconds
        self._last_emit_by_key = {}
        self.router = ModelRouter()
        self.aggregator = StreamingAggregator(threshold=ml_threshold, decay=ml_decay)

    def emit(self, event: Dict, detection: Dict) -> Optional[Dict[str, Any]]:
        severity = detection.get("severity", "none")
        if severity not in {"alert", "suspicious"}:
            return None

        raw_type = event.get("type")
        if raw_type == "file_access":
            payload = self._build_file_ml_payload(event, detection)
        elif raw_type == "network_connection":
            payload = self._build_network_ml_payload(event, detection)
        else:
            payload = self._build_process_ml_payload(event, detection)

        if payload is None:
            return None

        output = self._run_ml(payload)
        print(json.dumps(output))
        return output

    def _run_ml(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        model_input = dict(payload)
        model_input["type"] = payload["event_type"]

        model_output = self.router.route(model_input)
        aggregation = self.aggregator.add_event(
            {
                "type": payload["event_type"],
                "risk_score": model_output["risk_score"],
                "data": payload,
            }
        )

        return {
            "log": payload,
            "model": model_output,
            "aggregation": aggregation,
        }

    def _build_process_ml_payload(self, event: Dict, detection: Dict) -> Optional[Dict[str, Any]]:
        data = event.get("data", {})
        ts = event.get("timestamp") or time.time()
        pid = data.get("pid")
        reasons = detection.get("reasons") or detection.get("rare_patterns") or ["behavioral anomaly"]
        primary_reason = reasons[0]
        key = f"process:{primary_reason}:{pid}"

        if not self._check_rate_limit(key):
            return None

        process_name = data.get("process_name")
        process_name_str = (
            str(process_name) if process_name is not None and str(process_name).strip() != "" else "unknown"
        )
        parent_raw = data.get("parent_process")
        parent_str: Optional[str]
        if parent_raw is None or str(parent_raw).strip() == "":
            parent_str = None
        else:
            parent_str = str(parent_raw)

        cpu_percent = float(data.get("cpu_percent") or 0.0)
        memory_mb = float(data.get("memory_mb") or 0.0)
        score = int(detection.get("score", 0))

        payload = self._base_ml_record(
            "process",
            ts,
            score,
            detection,
            process_name_str,
            parent_str,
            cpu_percent,
            memory_mb,
            remote_ip=None,
            remote_port=0,
            file_path=None,
            file_action=None,
        )
        self._apply_enriched_overrides(data, payload)
        return payload

    def _build_file_ml_payload(self, event: Dict, detection: Dict) -> Optional[Dict[str, Any]]:
        data = event.get("data", {})
        ts = event.get("timestamp") or time.time()
        file_path = data.get("file_path")
        action = data.get("action")
        reasons = detection.get("reasons") or ["suspicious file behavior"]
        primary_reason = reasons[0]
        fp_key = file_path if isinstance(file_path, str) else ""
        act_key = action if isinstance(action, str) else ""
        key = f"file:{primary_reason}:{fp_key}:{act_key}"

        if not self._check_rate_limit(key):
            return None

        score = int(detection.get("score", 0))
        path_str = str(file_path) if file_path is not None else None

        pn = data.get("process_name")
        if pn is not None and str(pn).strip() != "":
            process_name_str = str(pn)
        else:
            process_name_str = None
        pr = data.get("parent_process")
        if pr is not None and str(pr).strip() != "":
            parent_str: Optional[str] = str(pr)
        else:
            parent_str = None
        f_cpu = float(data.get("cpu_percent") or 0.0)
        f_mem = float(data.get("memory_mb") or 0.0)

        payload = self._base_ml_record(
            "file",
            ts,
            score,
            detection,
            process_name_str,
            parent_str,
            f_cpu,
            f_mem,
            remote_ip=None,
            remote_port=0,
            file_path=path_str,
            file_action=str(action) if action is not None else None,
        )
        self._apply_enriched_overrides(data, payload)
        return payload

    def _build_network_ml_payload(self, event: Dict, detection: Dict) -> Optional[Dict[str, Any]]:
        data = event.get("data", {})
        ts = event.get("timestamp") or time.time()
        process_name = data.get("process_name")
        process_name_str = (
            str(process_name) if process_name is not None and str(process_name).strip() != "" else "unknown"
        )
        remote_ip = data.get("remote_ip")
        remote_port = int(data.get("remote_port") or 0)
        reasons = detection.get("reasons") or ["suspicious network behavior"]
        primary_reason = reasons[0]
        rip = str(remote_ip).strip() if remote_ip is not None and str(remote_ip).strip() != "" else ""
        key = f"network:{primary_reason}:{process_name_str}:{rip}:{remote_port}"

        if not self._check_rate_limit(key):
            return None

        score = int(detection.get("score", 0))
        remote_ip_out: Optional[str] = rip if rip else None

        n_cpu = float(data.get("cpu_percent") or 0.0)
        n_mem = float(data.get("memory_mb") or 0.0)
        n_parent = data.get("parent_process")
        parent_net: Optional[str]
        if n_parent is not None and str(n_parent).strip() != "":
            parent_net = str(n_parent)
        else:
            parent_net = None

        payload = self._base_ml_record(
            "network",
            ts,
            score,
            detection,
            process_name_str,
            parent_net,
            n_cpu,
            n_mem,
            remote_ip=remote_ip_out,
            remote_port=remote_port,
            file_path=None,
            file_action=None,
        )
        self._apply_enriched_overrides(data, payload)
        return payload

    def _apply_enriched_overrides(self, data: Dict, payload: Dict[str, Any]) -> None:
        for key in (
            "cpu_zscore",
            "memory_zscore",
            "parent_child_rarity",
            "process_freq_5min",
            "is_known_binary",
            "connection_freq_1min",
            "unique_ip_5min",
            "port_risk",
            "is_known_ip",
            "is_private_ip",
            "file_freq_1min",
            "file_rarity",
        ):
            if key in data:
                payload[key] = data[key]

    def _ml_severity(self, score: int) -> int:
        if score <= 1:
            return 0
        if score <= 3:
            return 1
        return 2

    def _reason_blob(self, detection: Dict) -> str:
        parts = []
        parts.extend(detection.get("reasons") or [])
        parts.extend(detection.get("rare_patterns") or [])
        return " ".join(str(p) for p in parts).lower()

    def _sensitive_flags(self, file_path: Optional[str]) -> Tuple[int, int]:
        if not file_path or not isinstance(file_path, str):
            return 0, 0
        low = file_path.lower()
        terms = ("password", "secret", "key", "config")
        hit = int(any(t in low for t in terms))
        return hit, hit

    def _file_extension(self, file_path: Optional[str]) -> Optional[str]:
        if not file_path or not isinstance(file_path, str):
            return None
        base = file_path.rsplit("\\", 1)[-1].rsplit("/", 1)[-1]
        if "." in base:
            return "." + base.rsplit(".", 1)[-1].lower()
        return None

    def _is_executable_ext(self, ext: Optional[str]) -> int:
        if not ext:
            return 0
        return 1 if ext.lower() in {".exe", ".bat", ".dll"} else 0

    def _is_private_ip_basic(self, remote_ip: Optional[str]) -> int:
        if not remote_ip or not isinstance(remote_ip, str):
            return 0
        s = remote_ip.strip().lower()
        if s.startswith("10."):
            return 1
        if s.startswith("192."):
            return 1
        if s.startswith("172."):
            return 1
        return 0

    def _base_ml_record(
        self,
        ml_kind: str,
        ts: Any,
        score: int,
        detection: Dict,
        process_name: Optional[str],
        parent_process: Optional[str],
        cpu_percent: float,
        memory_mb: float,
        remote_ip: Optional[str],
        remote_port: int,
        file_path: Optional[str],
        file_action: Optional[str],
    ) -> Dict[str, Any]:
        ts_f = float(ts) if ts is not None else time.time()
        ts_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(ts_f))
        event_type = ml_kind
        reason_blob = self._reason_blob(detection)
        behavioral_anomaly_flag = 1 if "behavioral anomaly" in reason_blob else 0
        external_connection_flag = 1 if event_type == "network" else 0
        unknown_process_flag = 1 if process_name == "unknown" else 0
        sensitive_access_flag, is_sensitive_path = self._sensitive_flags(file_path)

        file_ext = self._file_extension(file_path)
        is_executable = self._is_executable_ext(file_ext)

        is_private_ip = self._is_private_ip_basic(remote_ip)

        connection_freq_1min = 1 if event_type == "network" else 0
        unique_ip_5min = 1 if event_type == "network" else 0
        file_freq_1min = 1 if event_type == "file" else 0

        return {
            "event_type": event_type,
            "timestamp": ts_str,
            "system_score": score,
            "severity": self._ml_severity(score),
            "severity_label": detection.get("severity", "none"),
            "behavioral_anomaly_flag": behavioral_anomaly_flag,
            "external_connection_flag": external_connection_flag,
            "unknown_process_flag": unknown_process_flag,
            "sensitive_access_flag": sensitive_access_flag,
            "label": None,
            "process_name": process_name,
            "parent_process": parent_process,
            "cpu_percent": cpu_percent,
            "memory_mb": memory_mb,
            "cpu_zscore": 0,
            "memory_zscore": 0,
            "parent_child_rarity": 0,
            "process_freq_5min": 1,
            "is_known_binary": 1,
            "remote_ip": remote_ip,
            "remote_port": remote_port,
            "is_private_ip": is_private_ip,
            "is_known_ip": 1,
            "connection_freq_1min": connection_freq_1min,
            "unique_ip_5min": unique_ip_5min,
            "port_risk": 0,
            "file_path": file_path,
            "file_action": file_action,
            "file_extension": file_ext,
            "is_sensitive_path": is_sensitive_path,
            "is_executable": is_executable,
            "file_freq_1min": file_freq_1min,
            "file_rarity": 0,
        }
        


    def _check_rate_limit(self, key: str) -> bool:
        now = time.time()
        last = self._last_emit_by_key.get(key, 0)
        if now - last < self.rate_limit_seconds:
            return False
        self._last_emit_by_key[key] = now
        return True
