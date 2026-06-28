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
    File-focused attack narrative (variant 2):
    1. User opens a malicious attachment -> script engine starts PowerShell
    2. PowerShell connects to external C2
    3. Attacker touches sensitive files (encryption/collection behavior)
    4. Drops ransom note + staging archive
    """
    return [
        {
            "type": "process_sample",
            "timestamp": 0,
            "data": {
                "pid": 5128,
                "process_name": "powershell.exe",
                "parent_process": "wscript.exe",
                "cmdline": "powershell.exe -ExecutionPolicy Bypass -enc SQBFAFgA",
                "cpu_percent": 92,
                "memory_mb": 710,
                "exe_path": r"C:\Users\Public\powershell.exe",
            },
        },
        {
            "type": "network_connection",
            "timestamp": 0,
            "data": {
                "pid": 5128,
                "process_name": "powershell.exe",
                "remote_ip": "91.208.197.54",
                "remote_port": 8443,
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
                "parent_process": "wscript.exe",
                "cpu_percent": 86,
                "memory_mb": 640,
            },
        },
        {
            "type": "file_access",
            "timestamp": 0,
            "data": {
                "file_path": r"C:\shared\finance\salary_2025_backup.xlsx",
                "action": "modified",
                "process_name": "powershell.exe",
                "parent_process": "wscript.exe",
                "cpu_percent": 85,
                "memory_mb": 635,
            },
        },
        {
            "type": "file_access",
            "timestamp": 0,
            "data": {
                "file_path": r"C:\shared\admin\backup_credentials.txt",
                "action": "modified",
                "process_name": "powershell.exe",
                "parent_process": "wscript.exe",
                "cpu_percent": 88,
                "memory_mb": 655,
            },
        },
        {
            "type": "file_access",
            "timestamp": 0,
            "data": {
                "file_path": r"C:\shared\config\.env",
                "action": "modified",
                "process_name": "powershell.exe",
                "parent_process": "wscript.exe",
                "cpu_percent": 89,
                "memory_mb": 660,
            },
        },
        {
            "type": "file_access",
            "timestamp": 0,
            "data": {
                "file_path": r"C:\Users\Public\Desktop\READ_ME_RECOVER_FILES.txt",
                "action": "created",
                "process_name": "powershell.exe",
                "parent_process": "wscript.exe",
                "cpu_percent": 80,
                "memory_mb": 520,
            },
        },
        {
            "type": "file_access",
            "timestamp": 0,
            "data": {
                "file_path": r"C:\Users\Public\AppData\loot_finance_archive.zip",
                "action": "created",
                "process_name": "powershell.exe",
                "parent_process": "wscript.exe",
                "cpu_percent": 79,
                "memory_mb": 515,
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
    priority_terms = ("credential", "payroll", ".env", "secret", "finance", "admin", "recover")
    for path in registry:
        low = path.lower()
        if any(term in low for term in priority_terms):
            return path
    return next(iter(registry.keys()), None)


def _ensure_demo_analysis(state: dict) -> None:
    """
    Keep this demo usable even when an LLM key is not configured.
    If analysis is missing/low confidence, inject a deterministic high-confidence analysis.
    """
    analysis = state.get("analysis") if isinstance(state.get("analysis"), dict) else {}
    if float(analysis.get("confidence") or 0.0) >= 0.4:
        return
    state["analysis"] = {
        "intent": "data_exfiltration",
        "attack_stage": "exfiltration",
        "confidence": 0.86,
        "reasoning": [
            "External C2 connection from PowerShell spawned by script engine.",
            "Sensitive finance/credential/config files modified in short succession.",
            "Suspicious archive + ransom note creation indicates active attack progression.",
        ],
    }


def main() -> None:
    pipeline = LangGraphSecurityPipeline()
    state = {"mode": "monitor", "input_events": build_attack_story()}

    hr("REAL-WORLD FILE-CENTRIC ATTACK PRESENTATION (VARIANT 2 - RANSOMWARE/LOOT STAGING)")
    print(
        "Scenario: A script-launched PowerShell connects externally, modifies sensitive files, "
        "stages an archive, and drops a ransom note."
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

    state = pipeline.run_analysis(state)
    _ensure_demo_analysis(state)
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
    print("The deployment agent registers honeyfiles and interception rules.")
    deployment = state.get("deployment", {})
    registry = deployment.get("decoy_registry", {})
    rules = deployment.get("interception_rules", {})
    print("Honeyfile registry:")
    print(pretty(registry))
    print("\nInterception rules:")
    print(pretty(rules))

    chosen_path = choose_demo_path(registry)
    state["request_path"] = chosen_path
    state = pipeline.run_interception(state)
    hr("STEP 10 - INTERCEPTION + GENERATION AGENT")
    print(f"Simulated attacker request path: {chosen_path}")
    print("Interception returns the served content preview below:")
    print(preview(state.get("interception_result", "")))

    hr("FINAL INCIDENT REPORT")
    final_summary = {
        "storyline": "Script -> PowerShell -> external C2 -> sensitive file modifications -> archive + ransom note",
        "events_ingested": len(state.get("raw_events", [])),
        "events_after_filtering": len(state.get("filtered_events", [])),
        "detection_count": len(state.get("detections", [])),
        "alert_record_count": len(state.get("alert_records", [])),
        "aggregated_risk_score": state.get("risk_score"),
        "analysis_result": state.get("analysis", {}),
        "strategy_type": state.get("strategy", {}).get("strategy_type"),
        "deployed_honeyfiles": list(registry.keys()),
        "intercepted_file": chosen_path,
        "final_response_mode": "fake content served" if state.get("interception_result") else "no response",
    }
    print(pretty(final_summary))

    hr("PRESENTATION NARRATION")
    narration = [
        "We simulate a file-centric attack that includes encryption/loot staging behavior.",
        "Telemetry is ingested and enriched with behavioral features.",
        "Noise is filtered and suspicious events are scored.",
        "ML aggregation produces an incident-level risk signal.",
        "The analysis stage summarizes intent/stage/confidence (with a safe demo fallback if LLM is unavailable).",
        "The strategy stage produces a deception plan.",
        "Deployment registers honeyfiles and rules.",
        "Interception serves fake content for attacker-selected high-value paths.",
    ]
    print(indent("\n".join(f"- {line}" for line in narration), prefix=""))


if __name__ == "__main__":
    main()

