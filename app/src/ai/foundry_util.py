import os
import traceback

from pathlib import Path
from typing import Any

from azure.ai.projects import AIProjectClient

from azure.identity.aio import DefaultAzureCredential as AsyncDefaultAzureCredential

from azure.identity import (
    DefaultAzureCredential,
    get_bearer_token_provider,
)
from openai import OpenAI

from azure.core.paging import ItemPaged

from azure.mgmt.cognitiveservices import CognitiveServicesManagementClient
from azure.mgmt.cognitiveservices.models import (
    Deployment,
    DeploymentModel,
    DeploymentProperties,
    Sku,
)


class FoundryUtil:
    @classmethod
    def foundry_scope(self) -> str:
        return "https://ai.azure.com/.default"

    @classmethod
    def cognitive_scope(self) -> str:
        return "https://cognitiveservices.azure.com/.default"

    def __init__(self, params: dict = {}):
        self.foundry_name = self.env("AZURE_FOUNDRY_NAME", None)
        self.foundry_url = self.env("AZURE_FOUNDRY_URL", None)
        self.foundry_project_name = self.env("AZURE_FOUNDRY_PROJECT_NAME", None)
        self.foundry_project_url = self.env("AZURE_FOUNDRY_PROJECT_URL", None)
        self.project_client = None
        self.openai_client = None
        self.mgmt_client = None

        if self.foundry_url is None:
            if self.foundry_name is None:
                raise RuntimeError("AZURE_FOUNDRY_NAME or AZURE_FOUNDRY_URL are not set")
            else:
                self.foundry_url = f"https://{self.foundry_name}.services.ai.azure.com"

        if self.foundry_project_url is None:
            if self.foundry_project_name is None:
                raise RuntimeError(
                    "AZURE_FOUNDRY_PROJECT_NAME or AZURE_FOUNDRY_PROJECT_URL is not set"
                )
            else:
                url = f"https://{self.foundry_name}.services.ai.azure.com/api/projects/{self.foundry_project_name}"
                self.foundry_project_url = url

    def env(self, name: str, default: str | None = None) -> str:
        """Return an environment variable; raise if unset and no default."""
        value = os.getenv(name, default)
        if value is None:
            return default
        return value

    def credential(self) -> DefaultAzureCredential:
        """
        One shared Entra ID credential for all sync clients.
        From library azure-identity.
        Class azure.identity.DefaultAzureCredential.
        """
        return DefaultAzureCredential()

    def async_credential(self):
        """
        For Entra authentication, return an async credential.
        An instance of DefaultAzureCredential from azure.identity.aio
        """
        return AsyncDefaultAzureCredential()

    def token_provider(self, scope: str | None = None):
        """
        Callable returning Entra bearer tokens, for the OpenAI SDK.
        'azure.identity.get_bearer_token_provider' is a callable
        that returns a bearer token provider (which is callable)
        """
        if scope is None:
            scope = self.foundry_scope()
        return get_bearer_token_provider(self.credential(), scope)

    # ---- Foundry project and OpenAI-compatible clients -----------------
    # Role: Azure AI User on the Foundry project (or resource).

    def get_project_client(self) -> AIProjectClient:
        """
        Return an azure.ai.projects.AIProjectClient,
        from library azure-ai-projects
        """
        if self.project_client is None:
            self.project_client = AIProjectClient(
                endpoint=self.foundry_project_url,
                credential=DefaultAzureCredential(),
            )
        return self.project_client

    def get_openai_client(self) -> OpenAI:
        """Return an OpenAI client, from library openai."""
        if self.openai_client is None:
            self.openai_client = self.get_project_client().get_openai_client()
        return self.openai_client

    def get_hosted_agent_openai_client(self, agent_name: str) -> OpenAI:
        """
        Return an OpenAI client for a Foundry hosted (container) agent.
        Hosted agents can only be called through their own endpoint,
        {project_url}/agents/{agent_name}/endpoint/protocols/openai, not through
        the project's Responses API with an agent_reference (that's for prompt agents).
        The agent endpoint is a preview feature, so it needs allow_preview=True.
        """
        project_client = AIProjectClient(
            endpoint=self.foundry_project_url,
            credential=DefaultAzureCredential(),
            allow_preview=True,
        )
        return project_client.get_openai_client(agent_name=agent_name)

    def get_mgmt_client(self) -> CognitiveServicesManagementClient:
        """
        Return an azure.mgmt.cognitiveservices.CognitiveServicesManagementClient,
        from library azure-mgmt-cognitiveservices
        """
        if self.mgmt_client is None:
            subscription_id = self.env("AZURE_SUBSCRIPTION_ID", None)
            if subscription_id is None:
                raise RuntimeError("AZURE_SUBSCRIPTION_ID is not set")
            self.mgmt_client = CognitiveServicesManagementClient(
                credential=self.credential(),
                subscription_id=subscription_id,
            )
        return self.mgmt_client

    def get_model_deployments_list(self) -> ItemPaged:
        return self.get_project_client().deployments.list()

    def get_model_deployment(self, deployment_name: str) -> Any:
        try:
            return self.get_project_client().deployments.get(deployment_name)
        except Exception as e:
            print(f"Error getting deployment {deployment_name}: {e}")
            print(traceback.format_exc())
            return None

    def deploy_model(
        self,
        model_name: str,
        model_version: str,
        deployment_name: str | None = None,
        sku_name: str = "GlobalStandard",
        capacity: int = 10,
        model_format: str = "OpenAI",
    ) -> Deployment:
        """
        Create or update a model deployment on the Foundry (AIServices) resource.
        capacity is in units of 1K tokens-per-minute (TPM).
        """
        resource_group = self.env("AZURE_RESOURCE_GROUP", None)
        if resource_group is None:
            raise RuntimeError("AZURE_RESOURCE_GROUP is not set")
        if deployment_name is None:
            deployment_name = model_name

        deployment = Deployment(
            sku=Sku(name=sku_name, capacity=capacity),
            properties=DeploymentProperties(
                model=DeploymentModel(
                    format=model_format,
                    name=model_name,
                    version=model_version,
                ),
                version_upgrade_option="OnceNewDefaultVersionAvailable",
            ),
        )
        poller = self.get_mgmt_client().deployments.begin_create_or_update(
            resource_group_name=resource_group,
            account_name=self.foundry_name,
            deployment_name=deployment_name,
            deployment=deployment,
        )
        return poller.result()  # blocks until provisioning completes

    def deploy_models(self, model_deployments_config: list[dict]) -> list[dict]:
        deployments = []
        for model_config in model_deployments_config:
            deployment = self.deploy_model(
                model_name=model_config["model_name"],
                model_version=model_config["model_version"],
                deployment_name=model_config["deployment_name"],
                capacity=model_config["capacity"],
            )
            deployments.append(deployment.as_dict())
        return deployments

    def sample_model_deployments_config(self) -> list[dict]:
        return [
            {
                "model_name": "text-embedding-ada-002",
                "model_version": "2",
                "deployment_name": "text-embedding-ada-002",
                "capacity": 100,
            },
            {
                "model_name": "gpt-4.1-mini",
                "model_version": "2025-04-14",
                "deployment_name": "gpt-4.1-mini",
                "capacity": 100,
            },
        ]

    def get_agents_list(self) -> ItemPaged:
        return self.get_project_client().agents.list()

    def get_agent(self, agent_name: str) -> Any:
        try:
            return self.get_project_client().agents.get(agent_name)
        except Exception as e:
            print(f"Error getting agent {agent_name}: {e}")
            print(traceback.format_exc())
            return None

    def create_vector_store(self, vector_store_name: str) -> dict | None:
        # See https://learn.microsoft.com/en-us/azure/foundry/agents/how-to/tools/file-search?pivots=python
        try:
            openai_client: OpenAI = self.get_openai_client()
            vector_store = openai_client.vector_stores.create(name=str(vector_store_name).strip())
            return vector_store.to_dict()
        except Exception as e:
            print(f"Error in create_vector_store: {e}")
            print(traceback.format_exc())
            return None

    def list_vector_stores(
        self,
    ) -> list[dict] | None:
        """
        Return a list of the vector stores in the Foundry Project.
        """
        try:
            openai_client: OpenAI = self.get_openai_client()
            # iterating the returned page auto-paginates through all vector stores
            return [vs.to_dict() for vs in openai_client.vector_stores.list()]
        except Exception as e:
            print(f"Error in list_vector_stores: {e}")
            print(traceback.format_exc())
            return None

    def delete_vector_store(self, vector_store_id: str) -> Any:
        """
        Delete the given vector store.
        """
        try:
            openai_client: OpenAI = self.get_openai_client()
            # returns a dict like {"id": "vs_...", "deleted": true, "object": "vector_store.deleted"}
            return openai_client.vector_stores.delete(vector_store_id=vector_store_id).to_dict()
        except Exception as e:
            print(f"Error in delete_vector_store on {vector_store_id}: {e}")
            print(traceback.format_exc())
            return None

    def upload_file_to_vector_store(self, vector_store_id: str, file_path: str) -> dict | None:
        # See https://learn.microsoft.com/en-us/azure/foundry/agents/how-to/tools/file-search?pivots=python
        try:
            openai_client: OpenAI = self.get_openai_client()
            vector_store_file = None
            abs_path = Path(os.path.abspath(file_path))
            print(f"abs_path: {abs_path}")
            with abs_path.open("rb") as file_handle:
                vector_store_file = openai_client.vector_stores.files.upload_and_poll(
                    vector_store_id=vector_store_id,
                    file=file_handle,
                )
                print(f"vector_store_file type: {str(type(vector_store_file))}")
            return vector_store_file.to_dict()
        except Exception as e:
            print(f"Error in upload_file_to_vector_store: {e}")
            print(traceback.format_exc())
            return None

    def list_files_in_vector_store(self, vector_store_id: str) -> list[dict] | None:
        try:
            openai_client: OpenAI = self.get_openai_client()
            return [
                file.to_dict()
                for file in openai_client.vector_stores.files.list(vector_store_id=vector_store_id)
            ]
        except Exception as e:
            print(f"Error in list_files_in_vector_store: {e}")
            print(traceback.format_exc())
            return None

    def delete_file_from_vector_store(self, vector_store_id: str, file_id: str) -> dict | None:
        try:
            openai_client: OpenAI = self.get_openai_client()
            return openai_client.vector_stores.files.delete(
                vector_store_id=vector_store_id, file_id=file_id
            ).to_dict()
        except Exception as e:
            print(f"Error in delete_file_from_vector_store: {e}")
            print(traceback.format_exc())
            return None


"""
vector store: {
    "id": "vs_CCxaq8JlHqpEDHYpFEbsnPCY",
    "created_at": 1793374815,
    "file_counts": {
        "cancelled": 0,
        "completed": 0,
        "failed": 0,
        "in_progress": 0,
        "total": 0
    },
    "last_active_at": 1793374815,
    "metadata": {},
    "name": "epl",
    "object": "vector_store",
    "status": "completed",
    "usage_bytes": 0,
    "expires_after": null,
    "expires_at": null
}
"""
