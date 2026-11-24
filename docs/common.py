"""
common.py - shared helpers for the AI-103 study guide summary examples.

Auth is keyless everywhere: Microsoft Entra ID via
DefaultAzureCredential (az login locally, managed identity in Azure)
plus Azure RBAC role assignments. No API keys are used. Each builder
names the least-privilege role its caller needs. SDK imports live
inside each builder, so install only the packages for the examples
you run.

PyPI packages (per example; always azure-identity):
  a2a-sdk
  agent-framework,
  azure-ai-contentsafety,
  azure-ai-contentunderstanding,
  azure-ai-documentintelligence,
  azure-ai-evaluation,
  azure-ai-projects,
  azure-ai-textanalytics,
  azure-ai-translation-text,
  azure-ai-voicelive,
  azure-identity,
  azure-cognitiveservices-speech,
  azure-mgmt-cognitiveservices,
  azure-mgmt-resource,
  azure-search-documents,
  mcp,
  openai,

Environment variables:
  AZURE_FOUNDRY_RESOURCE_URL
      Format:  https://<res>.services.ai.azure.com/
      Example: https://foundrycjf01135.services.ai.azure.com/
  AZURE_FOUNDRY_PROJECT_URL
      Format:  https://<res>.services.ai.azure.com/api/projects/<project>
      Example: https://foundrycjf01135.services.ai.azure.com/api/projects/fprojectcjf01135
  AZURE_OPENAI_V1_URL
      https://<res>.openai.azure.com/openai/v1/
  AZURE_FOUNDRY_MODEL_DEPLOYMENT  deployment name, default "gpt-4.1"
  AZURE_SEARCH_URL                https://<service>.search.windows.net
  AZURE_SUBSCRIPTION_ID,
  AZURE_RESOURCE_GROUP,
  AZURE_FOUNDRY_RESOURCE_NAME     control-plane examples
  TRAINING_CONTAINER_URL          Document Intelligence training data
  STORAGE_ACCOUNT_RESOURCE_ID     keyless Azure AI Search indexers

RBAC roles used by these helpers (assign to the user running the code
locally, or to the app's managed identity in Azure):
  Azure AI User                 Foundry project: models, agents,
                                evaluations, Agent Applications
  Azure AI Project Manager      publish agents (plus Azure AI User)
  Cognitive Services User       Foundry Tools data plane (Language,
                                Translator, Speech, Voice Live, Content
                                Understanding, Document Intelligence,
                                Content Safety)
  Cognitive Services OpenAI User / Contributor
                                inference / fine-tuning on the Azure
                                OpenAI v1 endpoint
  Cognitive Services Contributor
                                control plane: model deployments
  Search Index Data Reader / Contributor, Search Service Contributor
                                Azure AI Search query / load / manage
"""

import base64
import mimetypes
import os
from functools import lru_cache
from pathlib import Path

from azure.ai.projects import AIProjectClient
from azure.identity import (
    DefaultAzureCredential,
    get_bearer_token_provider,
)

FOUNDRY_SCOPE = "https://ai.azure.com/.default"  # Agent App Client
COGNITIVE_SCOPE = "https://cognitiveservices.azure.com/.default"  # OpenAI, AzureOpenAI

# Examples:
# AZURE_FOUNDRY_RESOURCE_URL = "https://aicjf0907ap7lkn.services.ai.azure.com/"
# AZURE_FOUNDRY_PROJECT_URL="https://aicjf0907ap7lkn.services.ai.azure.com/api/projects/proj-cjf0907ap7lkn"

# ---- configuration and credentials ---------------------------------


def env(name: str, default: str | None = None) -> str:
    """Return an environment variable; raise if unset and no default."""
    value = os.getenv(name, default)
    if value is None:
        raise RuntimeError(f"environment variable {name} is not set")
    return value


def model_deployment() -> str:
    """The deployment name; it goes in the 'model' parameter."""
    return env("AZURE_FOUNDRY_MODEL_DEPLOYMENT", "gpt-4.1")


def foundry_resource_url() -> str:
    """
    Foundry resource endpoint used by the Foundry Tools.
    Example: https://foundrycjf01135.services.ai.azure.com/
    """
    return env("AZURE_FOUNDRY_RESOURCE_URL")


@lru_cache(maxsize=1)
def credential() -> DefaultAzureCredential:
    """
    One shared Entra ID credential for all sync clients.
    From library azure-identity.
    Class azure.identity.DefaultAzureCredential.
    """
    return DefaultAzureCredential()


def async_credential():
    """Async Entra ID credential (Voice Live, Agent Framework)."""
    from azure.identity.aio import DefaultAzureCredential as AsyncCred

    return AsyncCred()


def token_provider(scope: str = FOUNDRY_SCOPE):
    """
    Callable returning Entra bearer tokens, for the OpenAI SDK.
    'azure.identity.get_bearer_token_provider' is a callable
    that returns a bearer token provider (which is callable)
    """
    return get_bearer_token_provider(credential(), scope)

    # Note: FOUNDRY_SCOPE = "https://ai.azure.com/.default"


# ---- Foundry project and OpenAI-compatible clients -----------------
# Role: Azure AI User on the Foundry project (or resource).


def build_project_client() -> AIProjectClient:
    """
    Return a azure.ai.projects.AIProjectClient, from lib azure-ai-projects
    """
    return AIProjectClient(
        endpoint=os.getenv("AZURE_FOUNDRY_PROJECT_URL"),
        credential=DefaultAzureCredential(),
    )


def build_openai_client():
    """Return an OpenAI client from a AIProjectClient."""
    return build_project_client().get_openai_client()


def build_openai_v1_client():
    """OpenAI SDK client on the Azure OpenAI v1 endpoint (Entra).

    Role: Cognitive Services OpenAI User (inference) or
    Cognitive Services OpenAI Contributor (files, fine-tuning).
    """
    from openai import OpenAI

    return OpenAI(base_url=env("AZURE_OPENAI_V1_URL"), api_key=token_provider(COGNITIVE_SCOPE))

    # Note:
    # AZURE_OPENAI_V1_URL: https://<res>.openai.azure.com/openai/v1/
    # COGNITIVE_SCOPE = "https://cognitiveservices.azure.com/.default"


def build_azure_openai_client(api_version="2025-03-01-preview"):
    """AzureOpenAI client, for when an API version is required.

    Role: Cognitive Services OpenAI User.
    """
    from openai import AzureOpenAI

    return AzureOpenAI(
        azure_endpoint=foundry_resource_url(),
        azure_ad_token_provider=token_provider(COGNITIVE_SCOPE),
        api_version=api_version,
    )
    # Note: COGNITIVE_SCOPE = "https://cognitiveservices.azure.com/.default"


def build_agent_application_client(app_name: str):
    """Client for a published Agent Application (Entra ID only).

    Role: Azure AI User on the Agent Application; else 403 Forbidden.
    """
    from openai import OpenAI

    base_url = f"{env('AZURE_FOUNDRY_PROJECT_URL')}/applications/{app_name}/protocols/openai"
    return OpenAI(base_url=base_url, api_key=token_provider())


# ---- Foundry Agent Service -----------------------------------------
# Role: Azure AI User on the project to create and run agents.


def create_prompt_agent(
    name: str,
    instructions: str,
    tools: list | None = None,
    model: str | None = None,
    metadata: dict | None = None,
):
    """Create a prompt agent, or add a new version of it."""
    from azure.ai.projects.models import PromptAgentDefinition

    definition = PromptAgentDefinition(
        model=model or model_deployment(),
        instructions=instructions,
        tools=tools or [],
    )
    extra = {"metadata": metadata} if metadata else {}
    return build_project_client().agents.create_version(
        agent_name=name, definition=definition, **extra
    )


def agent_reference(agent_name: str) -> dict:
    """extra_body that routes a Responses call to an agent/workflow."""
    return {"agent": {"name": agent_name, "type": "agent_reference"}}


def ask_agent(agent_name: str, prompt, conversation_id=None, openai_client=None, **kwargs):
    """Send a prompt to a Foundry agent or portal workflow."""
    openai_client = openai_client or build_openai_client()
    if conversation_id:
        kwargs["conversation"] = conversation_id
    return openai_client.responses.create(
        input=prompt, extra_body=agent_reference(agent_name), **kwargs
    )


def build_agent_framework_client():
    """Agent Framework chat client on Foundry Agent Service."""
    from agent_framework.azure import AzureAIAgentClient

    return AzureAIAgentClient(
        project_endpoint=env("AZURE_FOUNDRY_PROJECT_URL"),
        model_deployment_name=model_deployment(),
        async_credential=async_credential(),
    )


# ---- Foundry Tools -------------------------------------------------
# Role: Cognitive Services User on the Foundry resource. Entra ID
# needs the resource's custom-subdomain endpoint, not a regional one.


def build_text_analytics_client():
    from azure.ai.textanalytics import TextAnalyticsClient

    return TextAnalyticsClient(foundry_resource_url(), credential())


def build_translator_client():
    from azure.ai.translation.text import TextTranslationClient

    return TextTranslationClient(endpoint=foundry_resource_url(), credential=credential())


def build_speech_config():
    import azure.cognitiveservices.speech as speech_sdk

    return speech_sdk.SpeechConfig(token_credential=credential(), endpoint=foundry_resource_url())


def build_speech_translation_config():
    import azure.cognitiveservices.speech as speech_sdk

    return speech_sdk.translation.SpeechTranslationConfig(
        token_credential=credential(), endpoint=foundry_resource_url()
    )


def build_content_understanding_client():
    from azure.ai.contentunderstanding import ContentUnderstandingClient

    return ContentUnderstandingClient(
        endpoint=foundry_resource_url(), credential=credential(), api_version="2025-11-01"
    )


def build_document_intelligence_client():
    from azure.ai.documentintelligence import DocumentIntelligenceClient

    return DocumentIntelligenceClient(foundry_resource_url(), credential())


def build_document_intelligence_admin_client():
    from azure.ai.documentintelligence import (
        DocumentIntelligenceAdministrationClient as AdminClient,
    )

    return AdminClient(foundry_resource_url(), credential())


def build_content_safety_client():
    from azure.ai.contentsafety import ContentSafetyClient

    return ContentSafetyClient(foundry_resource_url(), credential())


# ---- Azure AI Search -----------------------------------------------
# Enable RBAC on the search service (API access control: "Role-based
# access control" or "Both"). Roles: Search Index Data Reader (query),
# Search Index Data Contributor (load docs), Search Service
# Contributor (indexes, indexers, data sources, skillsets).


def build_search_client(index_name: str):
    from azure.search.documents import SearchClient

    return SearchClient(env("AZURE_SEARCH_URL"), index_name, credential())


def build_search_index_client():
    from azure.search.documents.indexes import SearchIndexClient

    return SearchIndexClient(env("AZURE_SEARCH_URL"), credential())


def build_search_indexer_client():
    from azure.search.documents.indexes import SearchIndexerClient

    return SearchIndexerClient(env("AZURE_SEARCH_URL"), credential())


# ---- control plane (Azure Resource Manager) ------------------------
# Role: Cognitive Services Contributor (or Contributor) on the
# resource group; data-plane roles don't grant these actions.


def build_cognitive_mgmt_client():
    from azure.mgmt.cognitiveservices import (
        CognitiveServicesManagementClient,
    )

    return CognitiveServicesManagementClient(credential(), env("AZURE_SUBSCRIPTION_ID"))


def build_resource_mgmt_client():
    """Resource provider registration needs Contributor on the sub."""
    from azure.mgmt.resource import ResourceManagementClient

    return ResourceManagementClient(credential(), env("AZURE_SUBSCRIPTION_ID"))


# ---- utilities -----------------------------------------------------


def image_to_data_url(path: str) -> str:
    """Encode a local image as a base64 data URL."""
    mime = mimetypes.guess_type(path)[0] or "image/jpeg"
    data = base64.b64encode(Path(path).read_bytes()).decode()
    return f"data:{mime};base64,{data}"


def read_bytes(path: str) -> bytes:
    return Path(path).read_bytes()
