"""
Main Entry Point
Agentic Security System
"""

from pathlib import Path

import yaml

from agents.system_agent import SystemAgent


REPO_ROOT = Path(__file__).resolve().parent
CONFIG_PATH = REPO_ROOT / "configs" / "system_config.yaml"
REQUIRED_MODEL_ARTIFACTS = (
    REPO_ROOT / "ml" / "ml_models" / "file_model" / "file_hybrid_final.pkl",
    REPO_ROOT / "ml" / "ml_models" / "process_model" / "process_hybrid_final.pkl",
    REPO_ROOT / "ml" / "ml_models" / "network_model" / "network_hybrid_model.pkl",
)


def load_config(config_file):
    """Load configuration from YAML file"""
    config_path = Path(config_file)
    if not config_path.is_absolute():
        config_path = REPO_ROOT / config_path

    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f) or {}
    return config


def validate_config(config):
    """Validate the minimum runtime configuration contract."""
    if not isinstance(config, dict):
        raise ValueError("System configuration must be a YAML object.")

    system = config.get("system")
    if not isinstance(system, dict):
        raise ValueError("Missing required 'system' configuration section.")

    version = system.get("version")
    if not version:
        raise ValueError("Missing required system.version in configuration.")

    monitoring = config.get("monitoring", {})
    if monitoring and not isinstance(monitoring, dict):
        raise ValueError("monitoring configuration must be an object when provided.")

    file_watch_paths = monitoring.get("file_watch_paths")
    if file_watch_paths is not None and not isinstance(file_watch_paths, list):
        raise ValueError("monitoring.file_watch_paths must be a list when provided.")


def validate_runtime_prerequisites():
    """Fail fast when required local runtime assets are missing."""
    missing = [str(path.relative_to(REPO_ROOT)) for path in REQUIRED_MODEL_ARTIFACTS if not path.exists()]
    if missing:
        raise FileNotFoundError(
            "Missing required model artifacts: " + ", ".join(missing)
        )


def main():
    """Main entry point"""
    system_config = load_config(CONFIG_PATH)
    validate_config(system_config)
    validate_runtime_prerequisites()

    print("Agentic Security System Started")
    print(f"Version: {system_config['system']['version']}")
    agent = SystemAgent(config=system_config)
    agent.start()


if __name__ == "__main__":
    main()
