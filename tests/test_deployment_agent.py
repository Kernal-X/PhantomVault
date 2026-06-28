# tests/test_deployment_agent.py
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from agents.deployment.deployment_agent import DeploymentManager


def get_mock_strategy():
    return {
        "execution_plan": {
            "files_to_create": [
                {
                    "path": "/finance/accounts.csv",
                    "file_type": "csv",
                    "columns": ["name", "account_no", "balance"],
                    "realism": "high"
                },
                {
                    "path": "/public/readme.txt",
                    "file_type": "txt",
                    "columns": [],
                    "realism": "low"
                }
            ]
        },
        "generation_constraints": {
            "max_files": 5
        }
    }


def test_deployment_output_structure():
    manager = DeploymentManager()
    strategy = get_mock_strategy()

    state = manager.deploy(strategy)

    print("\n=== DEPLOYMENT STATE ===")
    for key, value in state.items():
        print(f"{key}: {value}")

    # ✅ structure checks
    assert "decoy_registry" in state
    assert "global_context" in state
    assert "interception_rules" in state

    print("\n✔ Deployment structure valid")


def test_decoy_registry_population():
    manager = DeploymentManager()
    strategy = get_mock_strategy()

    state = manager.deploy(strategy)
    registry = state["decoy_registry"]

    print("\n=== DECOY REGISTRY ===")
    for path, meta in registry.items():
        print(path, "→", meta)

    # ✅ check paths exist
    assert "/finance/accounts.csv" in registry
    assert "/public/readme.txt" in registry

    # ✅ check metadata fields
    for meta in registry.values():
        assert "file_type" in meta
        assert "columns" in meta
        assert "realism" in meta
        # assert "sensitivity" in meta

    print("\n✔ Decoy registry valid")


def test_interception_rules_generation():
    manager = DeploymentManager()
    strategy = get_mock_strategy()

    state = manager.deploy(strategy)
    rules = state["interception_rules"]

    print("\n=== INTERCEPTION RULES ===")
    for path, rule in rules.items():
        print(path, "→", rule)

    for rule in rules.values():
        assert "risk_threshold" in rule
        assert "deception_mode" in rule

    print("\n✔ Rules generated correctly")


def test_global_context_presence():
    manager = DeploymentManager()
    strategy = get_mock_strategy()

    state = manager.deploy(strategy)
    context = state["global_context"]

    print("\n=== GLOBAL CONTEXT ===")
    for k, v in context.items():
        print(k, ":", v)

    # basic checks
    assert "employee_names" in context
    assert "email_domain" in context
    assert "projects" in context

    print("\n✔ Global context valid")


def test_sensitivity_assignment():
    manager = DeploymentManager()
    strategy = get_mock_strategy()

    state = manager.deploy(strategy)
    registry = state["decoy_registry"]

    print("\n=== SENSITIVITY CHECK ===")

    assert registry["/finance/accounts.csv"]["sensitivity"] == "high"
    assert registry["/public/readme.txt"]["sensitivity"] == "medium"

    print("\n✔ Sensitivity logic works")


if __name__ == "__main__":
    print("\nRunning Deployment Agent Tests...\n")

    test_deployment_output_structure()
    test_decoy_registry_population()
    test_interception_rules_generation()
    test_global_context_presence()
    test_sensitivity_assignment()

    print("\n🎉 Deployment Agent tests passed (your fake world is structurally sound)")