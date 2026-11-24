import logging
import os
import traceback

from azure.identity import DefaultAzureCredential
from azure.mgmt.cognitiveservices import CognitiveServicesManagementClient


class FoundryModels:
    def __init__(self, opts={}):
        self.opts = opts

    def list_available_models(
        self,
        subscription_id: str | None = None,
        resource_group: str | None = None,
        foundry_project_name: str | None = None,
    ) -> list[dict]:
        """
        List all available models in the given Foundry project.
        Returns a list of dictionaries, each containing the model name, description, and other details.
        Implementation uses RBAC, not keys.
        """
        try:
            if subscription_id is None:
                subscription_id = os.getenv("AZURE_SUBSCRIPTION_ID")
            if resource_group is None:
                resource_group = os.getenv("AZURE_RESOURCE_GROUP")
            if foundry_project_name is None:
                foundry_project_name = os.getenv("AZURE_FOUNDRY_PROJECT_NAME")
            logging.info(
                "Models#list_available_models sub: {}, rg: {}, project: {}".format(
                    subscription_id, resource_group, foundry_project_name
                )
            )
            if not (subscription_id and resource_group and foundry_project_name):
                logging.error(
                    "Models#list_available_models - missing subscription, resource group, or project"
                )
                return []

            client = CognitiveServicesManagementClient(DefaultAzureCredential(), subscription_id)
            account_name = self.find_foundry_account_name(
                client, resource_group, foundry_project_name
            )
            if account_name is None:
                logging.error(
                    "Models#list_available_models - no Foundry account found for project: {}".format(
                        foundry_project_name
                    )
                )
                return []
            logging.info("Models#list_available_models account: {}".format(account_name))

            models = []
            for m in client.accounts.list_models(resource_group, account_name):
                d = m.as_dict()
                d["description"] = self.model_description(m)
                models.append(d)
            return sorted(models, key=lambda d: (d.get("name", ""), d.get("version", "")))
        except Exception as e:
            logging.error(f"Error in Models#list_available_models: {e}")
            logging.error(traceback.format_exc())
            return []

    def find_foundry_account_name(
        self,
        client: CognitiveServicesManagementClient,
        resource_group: str,
        foundry_project_name: str,
    ) -> str | None:
        """
        Return the name of the Foundry (Cognitive Services) account which contains the
        given project.  Models are available at the account level, and are shared by its projects.
        The given name may also be the account name itself.
        """
        for account in client.accounts.list_by_resource_group(resource_group):
            if account.name == foundry_project_name:
                return account.name
            try:
                for project in client.projects.list(resource_group, account.name):
                    # ARM returns project names in "<account>/<project>" format
                    if project.name.split("/")[-1] == foundry_project_name:
                        return account.name
            except Exception as e:
                # accounts of kinds other than AIServices do not support projects
                logging.debug(f"Models#find_foundry_account_name - skipping {account.name}: {e}")
        return None

    def model_description(self, m) -> str:
        parts = [m.format, m.name, m.version]
        if m.lifecycle_status:
            parts.append(f"({m.lifecycle_status})")
        if m.capabilities:
            parts.append("capabilities: " + ", ".join(sorted(m.capabilities.keys())))
        return " ".join(str(p) for p in parts if p)
