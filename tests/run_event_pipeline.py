import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import time
from pathlib import Path

from agents.deployment.deployment_agent import DeploymentManager
from agents.generation.generation_agent import GenerationAgent
from core.interception_layer import InterceptionLayer
from core.path_resolver import normalize_path

from collectors.file_collector import FileCollector


DEMO_ROOT = Path(__file__).resolve().parents[1] / "demo_shared"


def get_mock_strategy_output():
    log_path = str((DEMO_ROOT / "logs" / "sec_audit.log").resolve())
    return {
        "execution_plan": {
            "files_to_create": [
                {
                    "absolute_path": log_path,
                    "file_type": "log",
                    "content_profile": "logs",
                    "realism": "medium",
                    "size_bytes_target": 5000
                }
            ]
        }
    }


def get_mock_analysis():
    return {
        "intent": "data_exfiltration",
        "attack_stage": "collection",
        "confidence": 0.9
    }


def main():

    print("\nStarting Event-Driven Pipeline\n")

    # ------------------------
    # 1. Deployment
    # ------------------------
    deployment_manager = DeploymentManager()
    deployment_state = deployment_manager.deploy(get_mock_strategy_output())

    # ------------------------
    # 2. Setup agents
    # ------------------------
    generation_agent = GenerationAgent()
    interception = InterceptionLayer(generation_agent=generation_agent)

    # ------------------------
    # 3. Start collector
    # ------------------------
    os.makedirs(DEMO_ROOT, exist_ok=True)
    collector = FileCollector(path=str(DEMO_ROOT), recursive=True)
    print("Watching path:", collector.path)

    print("Watching for file events...\n")

    try:
        while True:
            events = collector.collect()

            for event in events:
           
                print("RAW EVENT:", event)

                raw_path = event["data"]["file_path"]

                print("\nEVENT DETECTED:", raw_path)

                input_data = {
                    "path": raw_path,
                    "analysis": get_mock_analysis(),
                    "deployment": deployment_state
                }

                result = interception.handle(input_data)

                print("INTERCEPTION RESULT:")
                print(result[:300])  # don’t spam logs

            time.sleep(1)

    except KeyboardInterrupt:
        print("\nStopping...")
        collector.stop()


if __name__ == "__main__":
    main()
