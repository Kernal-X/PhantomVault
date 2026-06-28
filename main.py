"""
Main Entry Point
Agentic Security System
"""

import yaml

from agents.system_agent import SystemAgent


def load_config(config_file):
    """Load configuration from YAML file"""
    with open(config_file, "r") as f:
        config = yaml.safe_load(f)
    return config


def main():
    """Main entry point"""
    system_config = load_config("configs/system_config.yaml")
    print("Agentic Security System Started")
    print(f"Version: {system_config['system']['version']}")
    agent = SystemAgent(config=system_config)
    agent.start()


if __name__ == "__main__":
    main()
from agents.system_agent import SystemAgent

def run():
    agent = SystemAgent()
    agent.start()

if __name__ == "__main__":
    run()
