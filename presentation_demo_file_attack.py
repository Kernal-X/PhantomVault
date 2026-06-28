from __future__ import annotations

import json
from textwrap import indent

from langgraph_pipeline import LangGraphSecurityPipeline


def hr(title: str) -> None:
    print("\n" + "=" * 110)
    print(title)
    print("=" * 110)


def pretty(data) -> str:
    return json.dumps(data, indent=2, ensure_ascii=False, default=str)


def preview(text: str, limit: int = 900) -> str:
    text = text or ""
    return text if len(text) <= limit else text[:limit] + "\n...truncated..."


def build_attack_story():
    """
    File-focused attack narrative:
    1. Office document launches PowerShell
    2. PowerShell reaches external infra
    3. Attacker reads sensitive finance and credential files
    4. Attacker stages loot into suspicious archive locations
    """
    return [
        {
            "type": "process_sample",
            "timestamp": 0,
            "data": {
                "pid": 4012,
                "process_name": "powershell.exe",
                "parent_process": "winword.exe",
                "cmdline": "powershell.exe -ExecutionPolicy Bypass -EncodedCommand SQBFAFgA",
                "cpu_percent": 88,
                "memory_mb": 612,
                "exe_path": r"C:\Users\Public\powershell.exe",
            },
        },
        {
            "type": "network_connection",
            "timestamp": 0,
            "data": {
                "pid": 4012,
                "process_name": "powershell.exe",
                "remote_ip": "185.199.110.153",
                "remote_port": 4444,
                "status": "ESTABLISHED",
            },
        },
        {
            "type": "file_access",
            "timestamp": 0,
            "data": {
                "file_path": r"C:\shared\finance\payroll_march.csv",
                "action": "modified",
                "process_name": "powershell.exe",
                "parent_process": "winword.exe",
                "cpu_percent": 82,
                "memory_mb": 540,
            },
        },
        {
            "type": "file_access",
            "timestamp": 0,
            "data": {
                "file_path": r"C:\shared\admin\backup_credentials.txt",
                "action": "modified",
                "process_name": "powershell.exe",
                "parent_process": "winword.exe",
                "cpu_percent": 84,
                "memory_mb": 548,
            },
        },
        {
            "type": "file_access",
            "timestamp": 0,
            "data": {
                "file_path": r"C:\shared\config\.env",
                "action": "modified",
                "process_name": "powershell.exe",
                "parent_process": "winword.exe",
                "cpu_percent": 85,
                "memory_mb": 550,
            },
        },
        {
            "type": "file_access",
            "timestamp": 0,
            "data": {
                "file_path": r"C:\Users\Public\AppData\archive_passwords.zip",
                "action": "created",
                "process_name": "powershell.exe",
                "parent_process": "winword.exe",
                "cpu_percent": 80,
                "memory_mb": 525,
            },
        },
        {
            "type": "file_access",
            "timestamp": 0,
            "data": {
                "file_path": r"C:\Users\Public\AppData\finance_secret_dump.log",
                "action": "created",
                "process_name": "powershell.exe",
                "parent_process": "winword.exe",
                "cpu_percent": 79,
                "memory_mb": 520,
            },
        },
    ]


def summarize_events(events: list[dict]) -> list[dict]:
    out = []
    for event in events:
        data = event.get("data", {})
        out.append(
            {
                "type": event.get("type"),
                "process_name": data.get("process_name"),
                "parent_process": data.get("parent_process"),
                "cmdline": data.get("cmdline"),
                "file_path": data.get("file_path"),
                "action": data.get("action"),
                "remote_ip": data.get("remote_ip"),
                "remote_port": data.get("remote_port"),
            }
        )
    return out


def summarize_detections(records: list[dict]) -> list[dict]:
    out = []
    for record in records:
        detection = record.get("detection", {})
        event = record.get("event", {})
        out.append(
            {
                "event_type": event.get("type"),
                "target": event.get("data", {}).get("file_path") or event.get("data", {}).get("process_name"),
                "accepted": record.get("accepted"),
                "score": detection.get("score"),
                "severity": detection.get("severity"),
                "reasons": detection.get("reasons"),
                "rare_patterns": detection.get("rare_patterns"),
            }
        )
    return out


def choose_demo_path(registry: dict) -> str | None:
    priority_terms = ("credential", "payroll", ".env", "secret", "finance", "admin")
    for path in registry:
        low = path.lower()
        if any(term in low for term in priority_terms):
            return path
    return next(iter(registry.keys()), None)


def main() -> None:
    pipeline = LangGraphSecurityPipeline()
    state = {"mode": "monitor", "input_events": build_attack_story()}

    hr("REAL-WORLD FILE-CENTRIC ATTACK PRESENTATION")
    print(
        "Scenario: A malicious Office document spawns PowerShell, reaches an external host, "
        "touches payroll/credential/config files, and stages suspicious archives for exfiltration."
    )

    hr("ENTRY INPUT")
    print("Injected demo events:")
    print(pretty(summarize_events(state["input_events"])))

    state = pipeline.prepare_state(state)
    hr("STEP 1 - PREPARE STATE")
    print("LangGraph initializes a shared state object for this cycle.")
    print("Prepared keys:")
    print(sorted(state.keys()))

    state = pipeline.collect_events(state)
    hr("STEP 2 - COLLECT EVENTS")
    print("Monitor/collector stage output:")
    print(pretty(summarize_events(state.get("raw_events", []))))

    state = pipeline.enrich_events(state)
    hr("STEP 3 - EVENT ENRICHMENT AGENT")
    print("This stage adds behavioral and ML features like z-scores, rarity, process frequency, and trust flags.")
    enriched = []
    for event in state.get("enriched_events", []):
        data = event.get("data", {})
        enriched.append(
            {
                "type": event.get("type"),
                "target": data.get("file_path") or data.get("process_name"),
                "cpu_zscore": data.get("cpu_zscore"),
                "memory_zscore": data.get("memory_zscore"),
                "parent_child_rarity": data.get("parent_child_rarity"),
                "process_freq_5min": data.get("process_freq_5min"),
                "is_known_binary": data.get("is_known_binary"),
                "connection_freq_1min": data.get("connection_freq_1min"),
                "file_freq_1min": data.get("file_freq_1min"),
                "file_rarity": data.get("file_rarity"),
            }
        )
    print(pretty(enriched))

    state = pipeline.filter_events(state)
    hr("STEP 4 - FILTER AGENT")
    print("Noise removal stage. Suspicious file/process/network events remain after filtering.")
    print(f"Events after filtering: {len(state.get('filtered_events', []))}")
    print(pretty(summarize_events(state.get("filtered_events", []))))

    state = pipeline.score_events(state)
    hr("STEP 5 - DETECTOR / SCORING AGENT")
    print("Rule-based detector output:")
    print(pretty(summarize_detections(state.get("detections", []))))

    state = pipeline.emit_alerts(state)
    hr("STEP 6 - LOGGER + ML ROUTER + STREAMING AGGREGATOR")
    print("Suspicious events are transformed into ML payloads, routed to models, and aggregated into a global risk score.")
    print(f"Alert records emitted: {len(state.get('alert_records', []))}")
    print(f"Aggregated risk score: {state.get('risk_score')}")
    ml_summary = []
    for record in state.get("alert_records", []):
        ml_summary.append(
            {
                "event_type": record.get("log", {}).get("event_type"),
                "system_score": record.get("log", {}).get("system_score"),
                "severity": record.get("log", {}).get("severity_label"),
                "model_risk_score": record.get("model", {}).get("risk_score"),
                "aggregator_alert": record.get("aggregation", {}).get("alert"),
                "aggregator_risk": record.get("aggregation", {}).get("data", {}).get("risk_score"),
            }
        )
    print(pretty(ml_summary))

    state = pipeline.run_analysis(state)
    hr("STEP 7 - ANALYSIS AGENT")
    print("The analysis agent interprets attacker intent and attack stage.")
    print(pretty(state.get("analysis", {})))

    state = pipeline.run_strategy(state)
    hr("STEP 8 - STRATEGY AGENT")
    print("The strategy agent converts the analysis into a deception response plan.")
    strategy = state.get("strategy", {})
    strategy_summary = {
        "strategy_type": strategy.get("strategy_type"),
        "intent": strategy.get("intent"),
        "attack_stage": strategy.get("attack_stage"),
        "confidence": strategy.get("confidence"),
        "files_to_create": strategy.get("execution_plan", {}).get("files_to_create", []),
        "credentials_to_create": strategy.get("execution_plan", {}).get("credentials_to_create", []),
        "monitoring_plan": strategy.get("monitoring_plan", {}),
    }
    print(pretty(strategy_summary))

    state = pipeline.run_deployment(state)
    hr("STEP 9 - DEPLOYMENT AGENT")
    print("The deployment agent registers decoy files and interception rules.")
    deployment = state.get("deployment", {})
    registry = deployment.get("decoy_registry", {})
    rules = deployment.get("interception_rules", {})
    print("Decoy registry:")
    print(pretty(registry))
    print("\nInterception rules:")
    print(pretty(rules))

    chosen_path = choose_demo_path(registry)
    state["request_path"] = chosen_path
    state = pipeline.run_interception(state)
    hr("STEP 10 - INTERCEPTION + GENERATION AGENT")
    print(f"Simulated attacker request path: {chosen_path}")
    print("Interception returns the decoy content preview below:")
    print(preview(state.get("interception_result", "")))

    hr("FINAL INCIDENT REPORT")
    final_summary = {
        "storyline": "Office -> PowerShell -> external network -> sensitive file access -> staged exfiltration",
        "events_ingested": len(state.get("raw_events", [])),
        "events_after_filtering": len(state.get("filtered_events", [])),
        "detection_count": len(state.get("detections", [])),
        "alert_record_count": len(state.get("alert_records", [])),
        "aggregated_risk_score": state.get("risk_score"),
        "analysis_result": state.get("analysis", {}),
        "strategy_type": state.get("strategy", {}).get("strategy_type"),
        "deployed_decoy_files": list(registry.keys()),
        "intercepted_file": chosen_path,
        "final_response_mode": "fake content served" if state.get("interception_result") else "no response",
    }
    print(pretty(final_summary))

    hr("PRESENTATION NARRATION")
    narration = [
        "We start with a realistic intrusion sequence dominated by file activity.",
        "The monitor ingests process, file, and network events into shared state.",
        "The enrichment agent adds behavior-aware features required by downstream scoring and ML stages.",
        "The filter agent removes routine noise so only meaningful attack evidence remains.",
        "The detector marks the suspicious process chain and sensitive file operations as high risk.",
        "The ML router and streaming aggregator combine those events into a global incident score.",
        "The analysis agent interprets the behavior as a likely attacker campaign stage and intent.",
        "The strategy agent creates a deception response plan focused on fake files and believable attacker-facing content.",
        "The deployment agent registers the decoy files and interception policy.",
        "Finally, the interception/generation stage serves fake data for the attacker-selected file path.",
    ]
    print(indent("\n".join(f"- {line}" for line in narration), prefix=""))


if __name__ == "__main__":
    main()
