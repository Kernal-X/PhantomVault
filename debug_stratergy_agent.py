import os
import json
from copy import deepcopy
from pathlib import Path

from dotenv import load_dotenv

from agents.strategy.strategy_agent import strategy_agent


# -------------------------------
# Load .env properly (robust)
# -------------------------------
env_path = Path(__file__).resolve().parent / ".env"
if env_path.exists():
    load_dotenv(dotenv_path=env_path)
else:
    load_dotenv()

print("API KEY LOADED:", bool(os.getenv("OPENAI_API_KEY")))


# -------------------------------
# Build Generation Input
# -------------------------------
def build_generation_input(state, result):
    """
    This simulates EXACT payload passed to Generation Agent.
    """
    return {
        "analysis": state.get("analysis"),
        "strategy": result.get("strategy"),
        "strategy_meta": result.get("strategy_meta"),
    }


# -------------------------------
# Pretty Printer
# -------------------------------
def print_block(title, data):
    print("\n" + "-" * 80)
    print(f"[{title}]")
    print("-" * 80)
    print(json.dumps(data, indent=2))


# -------------------------------
# Run Single Case
# -------------------------------
def run_case(name: str, state: dict):
    print("\n" + "=" * 100)
    print(f"TEST CASE: {name}")
    print("=" * 100)

    result = strategy_agent(deepcopy(state))

    generation_input = build_generation_input(state, result)

    # --- Output Sections ---
    print_block("INPUT ANALYSIS", state["analysis"])
    print_block("STRATEGY OUTPUT", result.get("strategy", {}))
    print_block("STRATEGY META", result.get("strategy_meta", {}))

    # ⭐ THIS IS WHAT GENERATION AGENT GETS
    print_block("FINAL INPUT TO GENERATION AGENT", generation_input)


# -------------------------------
# Main
# -------------------------------
def main():
    USE_LLM = True   # 🔥 set True for real pipeline

    if not USE_LLM:
        os.environ.pop("OPENAI_API_KEY", None)
        print("\nRunning in FALLBACK mode\n")
    else:
        if not os.getenv("OPENAI_API_KEY"):
            raise RuntimeError("OPENAI_API_KEY not found. Fix your .env loading.")
        print("\nRunning in LLM mode (REAL PIPELINE)\n")

    cases = [
        (
            "High Confidence - Exfiltration",
            {
                "analysis": {
                    "intent": "data_exfiltration",
                    "attack_stage": "exfiltration",
                    "confidence": 0.92,
                    "reasoning": [
                        "large outbound transfer",
                        "archive creation detected"
                    ],
                }
            },
        ),
        (
            "Credential Access Scenario",
            {
                "analysis": {
                    "intent": "credential_access",
                    "attack_stage": "lateral_movement",
                    "confidence": 0.78,
                    "reasoning": [
                        "SMB login attempts",
                        "privilege escalation traces"
                    ],
                }
            },
        ),
        (
            "Low Confidence Noise",
            {
                "analysis": {
                    "intent": "unknown",
                    "attack_stage": "initial_access",
                    "confidence": 0.25,
                    "reasoning": ["weak anomaly"],
                }
            },
        ),
    ]

    for name, state in cases:
        run_case(name, state)


if __name__ == "__main__":
    main()