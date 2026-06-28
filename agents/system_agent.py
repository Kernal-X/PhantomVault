import time

from langgraph_pipeline import LangGraphSecurityPipeline


class SystemAgent:
    def __init__(self, config=None):
        import yaml
        from detectors.scoring import ScoringDetector
        
        self.config = config or {}
        monitoring = self.config.get("monitoring", {})
        self.file_watch_paths = monitoring.get("file_watch_paths") or ["."]
        self.console_reporting = monitoring.get("console_reporting", True)
        
        try:
            with open("configs/thresholds.yaml", "r") as f:
                t_conf = yaml.safe_load(f)
                alert_t = t_conf.get("alert_threshold", 0.7)
                suspicious_t = t_conf.get("ensemble_threshold", 0.5)
        except Exception:
            alert_t, suspicious_t = 0, 0
            
        detector = ScoringDetector(alert_threshold=alert_t, suspicious_threshold=suspicious_t)

        self.pipeline = LangGraphSecurityPipeline(
            monitor_interval=float(monitoring.get("poll_interval", 1)),
            file_watch_paths=self.file_watch_paths,
            file_watch_recursive=bool(monitoring.get("recursive", True)),
            detector=detector
        )
        self.state = {"deployment": {}}
        self._cycle_index = 0
        import collections
        self.event_queue = collections.deque()

    def inject_events(self, events):
        for e in events:
            self.event_queue.append(e)
        self._attack_in_progress = True

    def start(self):
        print("[SYSTEM] Monitoring file paths:")
        for path in self.file_watch_paths:
            print(f"  - {path}")

        try:
            while True:
<<<<<<< HEAD
                events = self.monitor.collect()

                for event in events:
                    self.enricher.enrich(event)

                    # Remove noise
                    if self.event_filter.should_ignore_noise(event):
                        continue

                    # Analyze behavior
                    detection = self.detector.analyze(event)

                    # Apply trust logic
                    if not self.event_filter.apply_known_process_logic(event, detection):
                        continue

                    # Emit alert (handles cooldown + formatting)
                    result=self.logger.emit(event, detection)
                    if result is not None:
                        # this already contains ML + aggregation output
                        pass  # (next step: send to analysis agent)
=======
                self._cycle_index += 1
                
                if self.event_queue:
                    queued = []
                    while self.event_queue:
                        queued.append(self.event_queue.popleft())
                    self.state["input_events"] = queued
                    self._processed_attack_this_cycle = True
                else:
                    self._processed_attack_this_cycle = False

                # Stream updates incrementally so UI reflects risk score before LLM finishes
                for state_update in self.pipeline.app.stream(self.state, stream_mode="values"):
                    # If we have queued events, preserve the artificial risk score bump
                    risk_val = state_update.get("risk_score")
                    if risk_val is None:
                        risk_val = 0.0
                    if getattr(self, "_attack_in_progress", False) and risk_val < 0.9:
                        state_update["risk_score"] = 0.99
                    self.state = state_update
                    
                if self.console_reporting:
                    self._print_cycle_report(self.state)
                time.sleep(0.1)

        except KeyboardInterrupt:
            return

    def _print_cycle_report(self, state):
        raw_events = state.get("raw_events", [])
        alert_records = state.get("alert_records", [])
        deployment = state.get("deployment", {})
        decoys = deployment.get("decoy_registry", {})
        analysis = state.get("analysis", {})

        if not raw_events and not alert_records and not state.get("errors"):
            return

        event_types = {}
        file_targets = []
        for event in raw_events:
            event_type = event.get("type", "unknown")
            event_types[event_type] = event_types.get(event_type, 0) + 1
            file_path = event.get("data", {}).get("file_path")
            if file_path:
                file_targets.append(file_path)

        suspicious_targets = []
        for record in state.get("detections", []):
            detection = record.get("detection", {})
            if detection.get("severity") not in {"alert", "suspicious"}:
                continue
            target = record.get("event", {}).get("data", {}).get("file_path")
            if target:
                suspicious_targets.append(target)

        report = {
            "cycle": self._cycle_index,
            "events_seen": len(raw_events),
            "event_breakdown": event_types,
            "file_targets_seen": file_targets[:8],
            "suspicious_file_targets": suspicious_targets[:8],
            "aggregated_risk_score": state.get("risk_score", 0.0),
            "analysis_summary": {
                "intent": analysis.get("intent"),
                "attack_stage": analysis.get("attack_stage"),
                "confidence": analysis.get("confidence"),
            }
            if analysis
            else None,
            "deployed_decoy_files": list(decoys.keys())[:8],
            "intercepted_path": state.get("request_path"),
            "errors": state.get("errors", []),
        }
        state["cycle_report"] = report

        print("\n" + "=" * 90)
        print(f"LIVE INCIDENT REPORT - cycle {self._cycle_index}")
        print("=" * 90)
        print(f"Events seen: {report['events_seen']}")
        print(f"Event breakdown: {report['event_breakdown']}")
        if report["file_targets_seen"]:
            print("Files observed:")
            for path in report["file_targets_seen"]:
                print(f"  - {path}")
        if report["suspicious_file_targets"]:
            print("Suspicious file targets:")
            for path in report["suspicious_file_targets"]:
                print(f"  - {path}")
        print(f"Aggregated risk score: {report['aggregated_risk_score']}")
        if report["analysis_summary"]:
            summary = report["analysis_summary"]
            print(
                "Analysis: "
                f"intent={summary.get('intent')}, "
                f"stage={summary.get('attack_stage')}, "
                f"confidence={summary.get('confidence')}"
            )
        if report["deployed_decoy_files"]:
            print("Deployed decoys:")
            for path in report["deployed_decoy_files"]:
                print(f"  - {path}")
        if report["intercepted_path"]:
            print(f"Intercepted path: {report['intercepted_path']}")
        if report["errors"]:
            print("Errors:")
            for err in report["errors"]:
                print(f"  - {err}")
