"""
Usage:
  uv run main-generator.py <function> <optional-args>
  uv run main-generator.py gen_generator_config
  uv run main-generator.py gen_code_agent <agent-name>
  uv run main-generator.py gen_prompt_agent <agent-name>
"""

import sys
import traceback

from dotenv import load_dotenv
from typing import Any

from src.io.fs import FS
from src.os.system import System
from src.util.agent_generator import AgentGenerator


def gen_code_agent(name: str) -> None:
    generator = AgentGenerator()
    generator.generate_agent("code", name)


def gen_prompt_agent(name: str) -> None:
    generator = AgentGenerator()
    generator.generate_agent("prompt", name)


def gen_generator_config() -> None:
    """
    Generate the generator_config.json file used by the code generator.
    """
    config = dict[str, Any]()
    config["agents"] = {
        "agent_name": "none",
        "agent_image": "TODO",
        "user": str(System.user()),
        "container_cpu": "2.0",
        "container_memory": "4Gi",
        "model_deployment_name": "gpt-4.1-mini",
        "docker_image_version": "1",
        "dockerfile_base_image": "python:3.12-slim",
        "agent_framework_foundry_hosting_version": "==1.0.0b261015",
        "agent_framework_foundry_version": ">=1.15.0",
        "azure_ai_agents_version": ">=1.0.0",
        "azure_ai_agentserver_responses_version": ">=2.3.0",
    }
    config["app"] = {
        "app_root_dir": ".",
        "agents_dir": "agents",
    }
    FS.write_json(config, "generator_config.json")


def print_options(msg: str | None = None) -> None:
    if msg is not None:
        print(msg)
    print(__doc__)


if __name__ == "__main__":
    try:
        load_dotenv(override=True)
        if len(sys.argv) < 2:
            print_options("Error: no function provided")
            sys.exit(1)
        func = sys.argv[1].lower()
        if func == "gen_generator_config":
            gen_generator_config()
        elif func == "gen_code_agent":
            name = sys.argv[2]
            gen_code_agent(name)
        elif func == "gen_prompt_agent":
            name = sys.argv[2]
            gen_prompt_agent(name)
        else:
            print_options("Error: invalid function: {}".format(func))
    except Exception as e:
        print(str(e))
        print(traceback.format_exc())
