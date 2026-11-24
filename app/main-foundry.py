"""
Usage:
  CLI app for Azure AI Foundry functionality.
  uv run main-foundry.py <func> <other-args...>
  uv run main-foundry.py list_available_models
  uv run main-foundry.py list_available_models <subscription_id> <resource_group> <foundry_project_name>
  uv run main-foundry.py list_model_prices
  uv run main-foundry.py list_model_prices <region> --refresh
  uv run main-foundry.py list_model_prices southcentralus --refresh
  uv run main-foundry.py produce_models_report
  uv run main-foundry.py deploy_models config/model-deployments-config.json
  ---
  uv run main-foundry.py list_model_deployments
  uv run main-foundry.py get_model_deployment <deployment_name>
  uv run main-foundry.py get_model_deployment test-text-embedding-ada-002
  ---
  uv run main-foundry.py list_agents
  uv run main-foundry.py get_agent <agent_name>
  uv run main-foundry.py get_agent c1
  ---
  uv run main-foundry.py invoke_agent <config_file> <key>
  uv run main-foundry.py invoke_agent config/invoke-agents-config.json epl
  ---
  uv run main-foundry.py create_vector_store <vector_store_name>
  uv run main-foundry.py create_vector_store epl
  uv run main-foundry.py list_vector_stores
  uv run main-foundry.py delete_vector_store <vector_store_id>
  uv run main-foundry.py delete_vector_store vs_0hAfIm5gnuVZOFYUUPBdqciE
  uv run main-foundry.py upload_file_to_vector_store <vector_store_id> <file_path>
  uv run main-foundry.py upload_file_to_vector_store vs_0hAfIm5gnuVZOFYUUPBdqciE ../data/documents/FIFA-Laws-of-the-Game-2004.pdf
  uv run main-foundry.py list_files_in_vector_store <vector_store_id>
  uv run main-foundry.py list_files_in_vector_store vs_0hAfIm5gnuVZOFYUUPBdqciE
  uv run main-foundry.py delete_file_from_vector_store <vector_store_id> <file_id>
  uv run main-foundry.py delete_file_from_vector_store vs_0hAfIm5gnuVZOFYUUPBdqciE assistant-HUUXvnBjMCL7DjHyHCXeF8


"""

# This script demonstrates the use of Azure AI Foundry with RBAC authentication.
# Logic is generally delegated to reusable classes in the src/ai/ directory.

import json
import logging
import sys
import traceback

from dotenv import load_dotenv

from azure.ai.projects import AIProjectClient

from src.ai.foundry_model_pricing import FoundryModelPricing
from src.ai.foundry_models import FoundryModels
from src.ai.foundry_util import FoundryUtil
from src.io.fs import FS

AVAILABLE_MODELS_FILE = "../data/foundry/foundry_available_models.json"
MODEL_PRICES_FILE = "../data/foundry/foundry_model_prices.json"
MODELS_REPORT_FILE = "../data/foundry/models_report.md"


def list_available_models(
    subscription_id: str | None = None,
    resource_group: str | None = None,
    foundry_project_name: str | None = None,
):
    models = FoundryModels().list_available_models(
        subscription_id, resource_group, foundry_project_name
    )
    for m in models:
        logging.info(f"Model: {m.get('description')}")
    logging.info(f"{len(models)} models")
    outfile = "../data/foundry/foundry_available_models.json"
    FS.write_json(models, outfile, pretty=True, verbose=True)


def list_model_prices(region: str | None = None, refresh: bool = False):
    """
    Price the models in foundry_available_models.json (see list_available_models)
    using the Azure Retail Prices API; list prices are in USD per 1M tokens.
    """
    models = FS.read_json_list(AVAILABLE_MODELS_FILE)
    if not models:
        logging.info(f"No models in {AVAILABLE_MODELS_FILE}; run list_available_models first")
        return
    pricing = FoundryModelPricing(region)
    results = pricing.price_models(models, refresh)
    for r in results:
        for sku, p in r["prices"].items():
            logging.info(
                "{:40} {:11} {:18} input: {:>9} cached: {:>9} output: {:>9}".format(
                    r["name"],
                    r["version"],
                    sku,
                    str(p.get("input", "-")),
                    str(p.get("cached_input", "-")),
                    str(p.get("output", "-")),
                )
            )
    unmatched = sorted({f"{r['format']}/{r['name']}" for r in results if not r["matched"]})
    matched_count = len([r for r in results if r["matched"]])
    logging.info(
        f"{matched_count} of {len(results)} model versions priced in region {pricing.region}"
    )
    logging.info(f"unpriced models: {unmatched}")
    FS.write_json(results, MODEL_PRICES_FILE, pretty=True, verbose=True)


def produce_models_report():
    models = FS.read_json_list(AVAILABLE_MODELS_FILE)
    prices = FS.read_json_list(MODEL_PRICES_FILE)
    lines = list()
    lines.append("# Foundry Models Report")
    lines.append("")
    lines.append(
        f"Source data file: **{AVAILABLE_MODELS_FILE}** produced by the azure.mgmt.cognitiveservices SDK."
    )
    lines.append("")
    lines.append(f"Also see file: {MODEL_PRICES_FILE}")
    lines.append("")
    lines.append("## Models")
    lines.append("")
    lines.append("| Name | Version | Format | Description and Capabilities |")
    lines.append("|------|---------|--------|------------------------------|")
    for model in models:
        name = model["name"]
        vers = model["version"]
        format = model["format"]
        desc = model["description"]

        lines.append(f"| {name} | {vers} | {format} |{desc} |")
    lines.append("")
    lines.append(f"Model count in this report: {len(models)}")
    lines.append("")

    FS.write_lines(lines, MODELS_REPORT_FILE, verbose=True)


def deploy_models(json_list_config_file):
    try:
        futil = FoundryUtil()
        models_config = FS.read_json_list(json_list_config_file)
        print(f"models_config: {json.dumps(models_config, indent=4)}")
        deployments = futil.deploy_models(models_config)
        for deployment in deployments:
            logging.info(f"deployment: {json.dumps(deployment, indent=4)}")

    except Exception as e:
        print(traceback.format_exc())


def list_model_deployments() -> None:
    try:
        futil = FoundryUtil()
        results = list()
        for idx, deployment in enumerate(futil.get_model_deployments_list()):
            # deployment is an instance of <class 'azure.ai.projects.models._models.ModelDeployment'>
            obj = deployment.as_dict()
            obj["_type"] = str(type(deployment))
            print(f"model deployment {idx + 1}:\n{json.dumps(obj, indent=4)}")
            results.append(obj)
        FS.write_json(results, "tmp/model_deployments_list.json", verbose=True)
    except Exception as e:
        print(traceback.format_exc())


def get_model_deployment(deployment_name: str) -> None:
    try:
        futil = FoundryUtil()
        deployment = futil.get_model_deployment(deployment_name)
        if deployment is not None:
            print(f"model deployment: {json.dumps(deployment.as_dict(), indent=4)}")
        else:
            print(f"Deployment {deployment_name} not found.")
    except Exception as e:
        print(traceback.format_exc())


def list_agents() -> None:
    try:
        futil = FoundryUtil()
        results = list()
        for idx, agent in enumerate(futil.get_agents_list()):
            # deployment is an instance of <class 'azure.ai.projects.models._models.AgentDetails'>
            obj = agent.as_dict()
            obj["_type"] = str(type(agent))
            print(f"agent {idx + 1}:\n{json.dumps(obj, indent=4)}")
            results.append(obj)
        FS.write_json(results, "tmp/agents_list.json", verbose=True)
    except Exception as e:
        print(traceback.format_exc())


def get_agent(agent_name: str) -> None:
    try:
        futil = FoundryUtil()
        agent = futil.get_agent(agent_name)
        if agent is not None:
            print(f"agent: {json.dumps(agent.as_dict(), indent=4)}")
        else:
            print(f"Agent {agent_name} not found.")
    except Exception as e:
        print(traceback.format_exc())


def get_agent_deployment(agent_name: str) -> None:
    try:
        futil = FoundryUtil()
        agent = futil.get_agent(agent_name)
        if agent is not None:
            print(f"Agent deployment: {json.dumps(agent.as_dict(), indent=4)}")
        else:
            print(f"Agent {agent_name} not found.")
    except Exception as e:
        print(traceback.format_exc())


def invoke_agent(config_file, key):
    """
    Invoke an agent by using a AIProjectClient and the responses API.
    The agent_name, agent_type, and user_message are specified in the config file.
    A "code" agent_type is a hosted (container) agent, which is called through
    its own agent endpoint; other agent types, such as "prompt", are called through
    the project's responses API with an agent_reference.
    """
    try:
        config_dict = FS.read_json(config_file)
        if key in config_dict:
            agent_config = config_dict[key]
            print(f"agent config: {json.dumps(agent_config, indent=4)}")
            agent_name = agent_config.get("agent_name")
            agent_type = agent_config.get("agent_type")
            user_message = agent_config.get("user_message")
            futil = FoundryUtil()
            print(f"invoking {agent_type} agent: {agent_name}")
            if agent_type == "code":
                # Hosted agents can only be called through their own agent endpoint
                openai_client = futil.get_hosted_agent_openai_client(agent_name)
                print(f"agent endpoint: {openai_client.base_url}")
                response = openai_client.responses.create(input=user_message)
            else:
                project_client: AIProjectClient = futil.get_project_client()
                print(f"project_client: {project_client}")
                openai_client = project_client.get_openai_client()
                # The agent_reference routes the Responses call to the named agent
                response = openai_client.responses.create(
                    input=user_message,
                    extra_body={"agent_reference": {"name": agent_name, "type": "agent_reference"}},
                )
            print(f"user_message: {user_message}")
            print(f"response id: {response.id}, status: {response.status}")
            if response.usage is not None:
                print(
                    f"usage: input_tokens: {response.usage.input_tokens}, "
                    + f"output_tokens: {response.usage.output_tokens}"
                )
            print(f"response text:\n{response.output_text}")
        else:
            logging.info(f"Error: agent config not found for key: {key}")
            return
    except Exception as e:
        print(traceback.format_exc())


def create_vector_store(vector_store_name: str) -> None:
    try:
        futil = FoundryUtil()
        vector_store = futil.create_vector_store(vector_store_name)
        print(f"vector store: {json.dumps(vector_store, indent=4)}")
    except Exception as e:
        print(traceback.format_exc())


def list_vector_stores() -> None:
    try:
        futil = FoundryUtil()
        vector_stores = futil.list_vector_stores()
        print(f"vector stores: {json.dumps(vector_stores, indent=4)}")
    except Exception as e:
        print(traceback.format_exc())


def delete_vector_store(vector_store_id: str) -> None:
    try:
        futil = FoundryUtil()
        result = futil.delete_vector_store(vector_store_id)
        print(f"result: {json.dumps(result, indent=4)}")
    except Exception as e:
        print(traceback.format_exc())


def upload_file_to_vector_store(vector_store_id, file_path) -> None:
    try:
        futil = FoundryUtil()
        result = futil.upload_file_to_vector_store(vector_store_id, file_path)
        print(f"result: {json.dumps(result, indent=4)}")
    except Exception as e:
        print(traceback.format_exc())


def list_files_in_vector_store(vector_store_id: str) -> None:
    try:
        futil = FoundryUtil()
        files = futil.list_files_in_vector_store(vector_store_id)
        print(f"files: {json.dumps(files, indent=4)}")
    except Exception as e:
        print(traceback.format_exc())


def delete_file_from_vector_store(vector_store_id: str, file_id: str) -> None:
    try:
        futil = FoundryUtil()
        result = futil.delete_file_from_vector_store(vector_store_id, file_id)
        print(f"result: {json.dumps(result, indent=4)}")
    except Exception as e:
        print(traceback.format_exc())


def print_options(msg: str | None = None) -> None:
    if msg is not None:
        logging.info(msg)
    logging.info(__doc__)


if __name__ == "__main__":
    load_dotenv(override=True)
    logging.basicConfig(format="%(asctime)s - %(message)s", level=logging.WARNING)
    try:
        if len(sys.argv) < 2:
            print_options("Error: invalid command-line")
            exit(1)
        else:
            func = sys.argv[1].lower()
            if func == "list_available_models":
                if len(sys.argv) > 4:
                    list_available_models(sys.argv[2], sys.argv[3], sys.argv[4])
                else:
                    list_available_models()
            elif func == "list_model_prices":
                region = (
                    sys.argv[2] if len(sys.argv) > 2 and not sys.argv[2].startswith("--") else None
                )
                list_model_prices(region, "--refresh" in sys.argv)
            elif func == "produce_models_report":
                produce_models_report()
            elif func == "deploy_models":
                json_list_config_file = sys.argv[2]
                deploy_models(json_list_config_file)
            elif func == "list_model_deployments":
                list_model_deployments()
            elif func == "get_model_deployment":
                deployment_name = sys.argv[2]
                get_model_deployment(deployment_name)
            elif func == "list_agents":
                list_agents()
            elif func == "get_agent":
                agent_name = sys.argv[2]
                get_agent(agent_name)
            elif func == "invoke_agent":
                config_file, key = sys.argv[2], sys.argv[3]
                invoke_agent(config_file, key)
            elif func == "create_vector_store":
                vector_store_name = sys.argv[2]
                create_vector_store(vector_store_name)
            elif func == "list_vector_stores":
                list_vector_stores()
            elif func == "delete_vector_store":
                vector_store_id = sys.argv[2]
                delete_vector_store(vector_store_id)
            elif func == "upload_file_to_vector_store":
                vector_store_id = sys.argv[2]
                file_path = sys.argv[3]
                upload_file_to_vector_store(vector_store_id, file_path)
            elif func == "list_files_in_vector_store":
                vector_store_id = sys.argv[2]
                list_files_in_vector_store(vector_store_id)
            elif func == "delete_file_from_vector_store":
                vector_store_id = sys.argv[2]
                file_id = sys.argv[3]
                delete_file_from_vector_store(vector_store_id, file_id)
            else:
                print_options("Error: invalid function: {}".format(func))
    except Exception as e:
        print(str(e))
        print(traceback.format_exc())
