import os
import json
from copy import deepcopy
from pathlib import Path

from dotenv import load_dotenv

from agents.strategy.strategy_agent import strategy_agent
from agents.strategy.schema import (
    compute_generation_limits,
    confidence_to_strategy_type,
    stage_to_depth,
)

# -------------------------------
# Load .env
# -------------------------------
env_path = Path(__file__).resolve().parent / ".env"
load_dotenv(dotenv_path=env_path)

print("API KEY LOADED:", bool(os.getenv("OPENAI_API_KEY")))


# -------------------------------
# INPUT (your real analysis)
# -------------------------------
analysis_input = {
    "intent": "data_exfiltration",
    "attack_stage": "collection",
    "confidence": 0.6,
    "reasoning": [
        "The successful login by an employee with access to 'confidential.docx' and 'admin_data.csv' suggests potential data_exfiltration intent, as these files are sensitive and their read actions align with data collection for exfiltration.",
        "The attack stage is 'collection' because the observed file reads represent the aggregation of sensitive data prior to exfiltration, consistent with the kill-chain progression from initial access to data exfiltration."
    ]
}


# -------------------------------
# Validation (lightweight)
# -------------------------------
def validate(strategy, analysis):
    errors = []

    expected_type = confidence_to_strategy_type(analysis["confidence"])
    expected_depth = stage_to_depth(analysis["attack_stage"])

    if strategy.get("strategy_type") != expected_type:
        errors.append(f"strategy_type mismatch (expected {expected_type})")

    if strategy.get("placement_plan", {}).get("depth") != expected_depth:
        errors.append(f"depth mismatch (expected {expected_depth})")

    max_files, max_creds = compute_generation_limits(expected_type, expected_depth)

    files = strategy.get("artifact_plan", {}).get("files", [])
    creds = strategy.get("artifact_plan", {}).get("credentials", [])

    if len(files) > max_files:
        errors.append("file limit exceeded")

    if len(creds) > max_creds:
        errors.append("credential limit exceeded")

    if not strategy.get("data_protection", {}).get("real_files_lock"):
        errors.append("real_files_lock missing")

    return errors


# -------------------------------
# Pretty print
# -------------------------------
def print_block(title, data):
    print("\n" + "-" * 80)
    print(f"[{title}]")
    print("-" * 80)
    print(json.dumps(data, indent=2))


# -------------------------------
# Main Execution
# -------------------------------
def main():
    USE_LLM = True

    if not USE_LLM:
        os.environ.pop("OPENAI_API_KEY", None)
        print("\nRunning in FALLBACK mode\n")
    else:
        if not os.getenv("OPENAI_API_KEY"):
            raise RuntimeError("OPENAI_API_KEY not found")
        print("\nRunning in LLM mode (REAL)\n")

    state = {"analysis": analysis_input}

    result = strategy_agent(deepcopy(state))

    strategy = result.get("strategy")
    meta = result.get("strategy_meta", {})

    if not strategy:
        print("\n[ERROR] Strategy missing (LLM failure)")
        return

    # -------------------------------
    # Output
    # -------------------------------
    print_block("ANALYSIS INPUT", analysis_input)
    print_block("STRATEGY OUTPUT", strategy)
    print_block("STRATEGY META", meta)

    generation_input = {
        "analysis": analysis_input,
        "strategy": strategy,
        "strategy_meta": meta,
    }

    # ⭐ FINAL PAYLOAD
    print_block("FINAL INPUT TO GENERATION AGENT", generation_input)

    # -------------------------------
    # Validation
    # -------------------------------
    errors = validate(strategy, analysis_input)

    if errors:
        print_block("VALIDATION FAILED", errors)
    else:
        print("\n[VALIDATION PASSED]")


if __name__ == "__main__":
    main()