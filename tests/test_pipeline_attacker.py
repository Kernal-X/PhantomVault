import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from agents.deployment.deployment_agent import DeploymentManager
from core.interception_layer import InterceptionLayer
from agents.generation.generation_agent import GenerationAgent
from core.path_resolver import normalize_path


def get_mock_strategy_output():
    return {
        "execution_plan": {
            "files_to_create": [
                {
                    "absolute_path": "C:\\shared\\finance\\payroll_march.csv",
                    "file_type": "csv",
                    "columns": ["employee_id", "name", "salary", "department", "email"],
                    "content_profile": "salary_data",
                    "realism": "high",
                    "size_bytes_target": 3000
                },
                {
                    "absolute_path": "/shared/admin/backup_credentials.txt",
                    "file_type": "txt",
                    "columns": [],
                    "content_profile": "credentials",
                    "realism": "medium",
                    "size_bytes_target": 800
                },
                {
                    "absolute_path": "D:\\shared\\logs\\security_audit.log",
                    "file_type": "log",
                    "columns": [],
                    "content_profile": "logs",
                    "realism": "high",
                    "size_bytes_target": 5000
                }
            ]
        }
    }


def get_mock_analysis(intent, stage, confidence):
    return {
        "intent": intent,
        "attack_stage": stage,
        "confidence": confidence
    }


def simulate_attacker_access(interception, deployment_state):

    print("\nSimulating Attacker Behavior\n")

    # Simulated attacker actions (mixed paths)
    attacker_requests = [
        "D:\\shared\\logs\\security_audit.log",   # suspicious target
        "C:\\shared\\finance\\payroll_march.csv", # sensitive data
        "/shared/admin/backup_credentials.txt",   # credentials
        "D:\\shared\\public\\readme.txt"          # non-decoy (real)
    ]

    analysis = get_mock_analysis("data_exfiltration", "collection", 0.9)

    for path in attacker_requests:

        print("\n" + "=" * 80)
        print(f"ATTACKER REQUEST: {path}")
        print("NORMALIZED PATH:", normalize_path(path))

        input_data = {
            "path": path,
            "analysis": analysis,
            "deployment": deployment_state
        }

        result = interception.handle(input_data)

        print("\nOUTPUT:\n")
        print(result)

        print("\n--- DEBUG ---")
        if "[REAL" in result:
            print("SOURCE: REAL FILE")
        else:
            print("SOURCE: DECOY / GENERATED")

        print("=" * 80)


def run_test():

    print("\nRunning ATTACKER-SIMULATION PIPELINE\n")

    # 1. Deployment (setup environment)
    deployment_manager = DeploymentManager()
    strategy_output = get_mock_strategy_output()
    deployment_state = deployment_manager.deploy(strategy_output)

    # 2. Setup interception + generation
    generation_agent = GenerationAgent()
    interception = InterceptionLayer(generation_agent=generation_agent)

    # 3. Simulate attacker
    simulate_attacker_access(interception, deployment_state)


if __name__ == "__main__":
    run_test()
