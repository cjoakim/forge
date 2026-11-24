import json
import os
import shutil
import traceback

from pathlib import Path

from src.io.fs import FS
from src.util.template import Template


class AgentGenerator:
    """
    This class is used to generate a complete set of artifacts
    for a given Foundry-Hosted Agent name.
    """

    def __init__(self):
        self.config = FS.read_json_dict("generator_config.json")
        self.ctxt = self.config["agents"]

    def generate_agent(self, agent_type: str, agent_name: str) -> bool:
        try:
            agent_name = agent_name.strip().lower().replace(" ", "_")
            print(f"generate_agent: {agent_type} -> {agent_name}")
            agent_dir = self.create_agent_directory_structure(agent_type, agent_name)
            template_configs = None

            if agent_dir is None:
                return False
            print(f"agent_dir created: {agent_dir}")

            if agent_type == "prompt":
                template_configs = self.prompt_agent_templates_file_map()
            elif agent_type == "code":
                template_configs = self.code_agent_templates_file_map(agent_name)
            else:
                print(f"generate_agent error: Invalid agent_type: {agent_type}")
                return False

            self.ctxt["agent_name"] = agent_name
            self.ctxt["agent_dir"] = agent_dir
            FS.write_json(self.ctxt, f"tmp/generate_agent_ctxt.json")
            print(json.dumps(self.ctxt, indent=4))

            for config in template_configs:
                template_name = config["in"]
                outpath = config["out"]
                t = Template.get_template(os.getcwd(), template_name)
                content = Template.render(t, self.ctxt)
                outfile = f"{agent_dir}/{outpath}"
                FS.write(content, outfile)
            return True
        except Exception as e:
            print(f"AgentGenerator#generate_prompt_agent error: {e}")
            print(traceback.format_exc())
            return False

    def create_agent_directory_structure(self, agent_type: str, agent_name: str) -> str | None:
        """
        Delete and recreate the agent directory structure.
        Return the agent directory path.
        """
        try:
            agent_dir = f"agents/{agent_name.strip()}".lower().replace(" ", "_")
            shutil.rmtree(agent_dir, ignore_errors=True)

            if agent_type == "prompt":
                shutil.rmtree(agent_dir, ignore_errors=True)
                agent_path = Path(agent_dir)
                agent_path.mkdir(parents=True, exist_ok=True)
                return agent_dir
            elif agent_type == "code":
                shutil.rmtree(agent_dir, ignore_errors=True)
                agent_path = Path(agent_dir)
                agent_path.mkdir(parents=True, exist_ok=True)

                src_path = Path(f"{agent_dir}/src/{agent_name}")
                src_path.mkdir(parents=True, exist_ok=True)

                src_src_path = Path(f"{agent_dir}/src/{agent_name}/src")
                src_src_path.mkdir(parents=True, exist_ok=True)

                return agent_dir
            else:
                print(
                    f"AgentGenerator#create_agent_directory_structure error: Invalid agent type: {agent_type}"
                )
                return None

        except Exception as e:
            print(f"AgentGenerator#create_agent_directory_structure error: {e}")
            print(traceback.format_exc())
            return None

    def context(self):
        return {}

    def code_agent_templates_file_map(self, agent_name: str):
        return [
            {"in": "code_agent_azure.yaml", "out": "azure.yaml"},
            {"in": "code_agent_deploy.sh", "out": "deploy.sh"},
            {"in": "code_agent_deploy.ps1", "out": "deploy.ps1"},
            {"in": "code_agent_copy-master-src.sh", "out": "copy-master-src.sh"},
            {"in": "code_agent_copy-master-src.ps1", "out": "copy-master-src.ps1"},
            {"in": "code_agent_readme.md", "out": "readme.md"},
            {"in": "code_agent_azdignore", "out": f"src/{agent_name}/.azdignore"},
            {"in": "code_agent_dockerignore", "out": f"src/{agent_name}/.dockerignore"},
            {"in": "code_agent_Dockerfile", "out": f"src/{agent_name}/Dockerfile"},
            {"in": "code_agent_main.py", "out": f"src/{agent_name}/main.py"},
            {"in": "code_agent_requirements.txt", "out": f"src/{agent_name}/requirements.txt"},
        ]

    def prompt_agent_templates_file_map(self):
        return [{"in": "prompt_agent_azure.yaml", "out": "azure.yaml"}]
