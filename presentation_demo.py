from __future__ import annotations

import json
from textwrap import indent

from langgraph_pipeline import LangGraphSecurityPipeline


def hr(title: str) -> None:
    print("\n" + "=" * 100)
    print(title)
    print("=" * 100)


def pretty(data) -> str:
    return json.dumps(data, indent=2, default=str, ensure_ascii=False)


def summarize_event(event: dict) -> dict:
    data = event.get("data", {})
    return {
        "type": event.get("type"),
        "process_name": data.get("process_name"),
        "parent_process": data.get("parent_process"),
        "cmdline": data.get("cmdline"),
        "cpu_percent": data.get("cpu_percent"),
        "memory_mb": data.get("memory_mb"),
        "file_path": data.get("file_path"),
        "action": data.get("action"),
        "remote_ip": data.get("remote_ip"),
        "remote_port": data.get("remote_port"),
    }


def summarize_detection(record: dict) -> dict:
    return {
        "event_type": record.get("event", {}).get("type"),
        "accepted": record.get("accepted"),
        "score": record.get("detection", {}).get("score"),
        "severity": record.get("detection", {}).get("severity"),
        "reasons": record.get("detection", {}).get("reasons"),
        "rare_patterns": record.get("detection", {}).get("rare_patterns"),
    }


def summarize_strategy(strategy: dict) -> dict:
    execution = strategy.get("execution_plan", {})
    return {
        "strategy_type": strategy.get("strategy_type"),
        "intent": strategy.get("intent"),
        "attack_stage": strategy.get("attack_stage"),
        "confidence": strategy.get("confidence"),
        "files_to_create": len(execution.get("files_to_create", [])),
        "credentials_to_create": len(execution.get("credentials_to_create", [])),
        "monitoring_plan": strategy.get("monitoring_plan", {}),
        "reasoning_summary": strategy.get("reasoning_summary", []),
    }


def main() -> None:
    pipeline = LangGraphSecurityPipeline()

    suspicious_events = [
        {
            "type": "process_sample",
            "timestamp": 0,
            "data": {
                "pid": 1111,
                "process_name": "powershell.exe",
                "parent_process": "winword.exe",
                "cmdline": "powershell.exe -enc SQBFAFgA",
                "cpu_percent": 91,
                "memory_mb": 650,
            },
        },
        {
            "type": "process_sample",
            "timestamp": 0,
            "data": {
                "pid": 2222,
                "process_name": "powershell.exe",
                "parent_process": "winword.exe",
                "cmdline": "powershell.exe -enc SQBFAFkA",
                "cpu_percent": 92,
                "memory_mb": 670,
            },
        },
    ]

    state = {"mode": "monitor", "input_events": suspicious_events}

    hr("ENTRY POINT")
    print("Starting from the same orchestration class used by the runtime:")
    print("LangGraphSecurityPipeline")
    print("\nInput events injected for demo:")
    print(pretty([summarize_event(e) for e in suspicious_events]))

    state = pipeline.prepare_state(state)
    hr("NODE 1: prepare_state")
    print("Purpose: initialize/reset shared state for this cycle.")
    print("State keys prepared:")
    print(sorted(state.keys()))

    state = pipeline.collect_events(state)
    hr("NODE 2: collect_events")
    print("Purpose: collect telemetry into shared state.")
    print(f"Collected events: {len(state.get('raw_events', []))}")
    print(pretty([summarize_event(e) for e in state.get("raw_events", [])]))

    state = pipeline.enrich_events(state)
    hr("NODE 3: enrich_events")
    print("Purpose: add ML and behavioral features to each event.")
    enriched_preview = []
    for event in state.get("enriched_events", []):
        data = event.get("data", {})
        enriched_preview.append(
            {
                "type": event.get("type"),
                "process_name": data.get("process_name"),
                "cpu_zscore": data.get("cpu_zscore"),
                "memory_zscore": data.get("memory_zscore"),
                "parent_child_rarity": data.get("parent_child_rarity"),
                "process_freq_5min": data.get("process_freq_5min"),
                "is_known_binary": data.get("is_known_binary"),
            }
        )
    print(pretty(enriched_preview))

    state = pipeline.filter_events(state)
    hr("NODE 4: filter_events")
    print("Purpose: remove trusted/noisy events before scoring.")
    print(f"Events after filtering: {len(state.get('filtered_events', []))}")
    print(pretty([summarize_event(e) for e in state.get("filtered_events", [])]))

    state = pipeline.score_events(state)
    hr("NODE 5: score_events")
    print("Purpose: apply rule-based suspiciousness scoring.")
    print(pretty([summarize_detection(d) for d in state.get("detections", [])]))

    state = pipeline.emit_alerts(state)
    hr("NODE 6: emit_alerts")
    print("Purpose: convert suspicious detections into ML payloads and aggregate risk.")
    print(f"Alert records emitted: {len(state.get('alert_records', []))}")
    print(f"Aggregated risk score: {state.get('risk_score')}")
    alert_preview = []
    for record in state.get("alert_records", []):
        alert_preview.append(
            {
                "model_risk_score": record.get("model", {}).get("risk_score"),
                "aggregator_alert": record.get("aggregation", {}).get("alert"),
                "aggregator_risk": record.get("aggregation", {}).get("data", {}).get("risk_score"),
            }
        )
    print(pretty(alert_preview))

    state = pipeline.run_analysis(state)
    hr("NODE 7: analysis")
    print("Purpose: analysis agent infers attacker intent and attack stage.")
    print(pretty(state.get("analysis", {})))

    state = pipeline.run_strategy(state)
    hr("NODE 8: strategy")
    print("Purpose: strategy agent converts analysis into deception plan.")
    print(pretty(summarize_strategy(state.get("strategy", {}))))

    state = pipeline.run_deployment(state)
    hr("NODE 9: deployment")
    print("Purpose: build decoy registry, context, and interception rules.")
    deployment = state.get("deployment", {})
    registry = deployment.get("decoy_registry", {})
    rules = deployment.get("interception_rules", {})
    print("Decoy registry:")
    print(pretty(registry))
    print("\nInterception rules:")
    print(pretty(rules))

    decoy_path = next(iter(registry.keys()), "/shared/admin/backup_credentials.txt")
    state["request_path"] = decoy_path
    state = pipeline.run_interception(state)
    hr("NODE 10: interception")
    print("Purpose: decide real/partial/fake response and return decoy content.")
    print(f"Requested path: {decoy_path}")
    print("\nReturned content preview:")
    print(state.get("interception_result", "")[:1200])

    hr("FINAL SUMMARY")
    summary = {
        "entry_point": "LangGraphSecurityPipeline",
        "events_processed": len(state.get("raw_events", [])),
        "events_after_filtering": len(state.get("filtered_events", [])),
        "detections_generated": len(state.get("detections", [])),
        "aggregated_risk_score": state.get("risk_score"),
        "analysis_result": state.get("analysis", {}),
        "strategy_type": state.get("strategy", {}).get("strategy_type"),
        "deployed_decoy_files": list(registry.keys()),
        "final_intercepted_path": decoy_path,
        "final_action": "fake content returned" if state.get("interception_result") else "no result",
    }
    print(pretty(summary))

    print("\nPresentation narration:")
    narration = [
        "Telemetry is collected and placed into shared state.",
        "Events are enriched with behavioral and ML features.",
        "Trusted noise is removed.",
        "The scoring detector marks the events as suspicious.",
        "The ML router and aggregator compute overall risk.",
        "The analysis agent explains attacker intent and stage.",
        "The strategy agent generates a deception plan.",
        "The deployment manager registers decoy assets and rules.",
        "The interception layer serves fake content for the selected decoy path.",
    ]
    print(indent("\n".join(f"- {line}" for line in narration), prefix=""))


if __name__ == "__main__":
    main()
