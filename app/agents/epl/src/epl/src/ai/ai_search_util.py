import json
import logging
import traceback

import httpx

from azure.identity import DefaultAzureCredential, get_bearer_token_provider

from src.os.env import Env

# This class is used to invoke Azure AI Search via HTTP.
# Authentication is Entra ID (DefaultAzureCredential); the search service doesn't
# allow API keys. Roles: Search Service Contributor (indexes, indexers, data sources)
# and Search Index Data Contributor (documents) on the search service.

SEARCH_SCOPE = "https://search.azure.com/.default"


class AISearchUtil:
    def __init__(self, verbose: bool = False, credential=None):
        self.api_version = Env.azure_ai_search_version()
        self.base_url = Env.azure_ai_search_url()
        if credential is None:
            credential = DefaultAzureCredential()
        # Returns a cached bearer token, refreshed before it expires.
        self.token_provider = get_bearer_token_provider(credential, SEARCH_SCOPE)
        # One client for the life of this object, so requests reuse pooled connections
        # instead of paying a new TLS handshake each time. httpx.Client is thread-safe.
        self.client = httpx.Client()
        if verbose:
            print(f"AISearchUtil initialized; api_version:  {self.api_version}")
            print(f"AISearchUtil initialized; base_url:     {self.base_url}")

    @property
    def headers(self) -> dict:
        return {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.token_provider()}",
        }

    def add_document_to_index(self, index_name: str, document: dict) -> dict | None:
        try:
            url = f"{self.base_url}/indexes/{index_name}/docs/index?api-version={self.api_version}"
            body = {"value": [document]}
            return self._http_request("add_document_to_index", "POST", url, json_body=body)
        except Exception as e:
            logging.error(f"Error in add_document_to_index: {str(e)}")
            traceback.print_stack()
            return None

    def add_documents_to_index(self, index_name: str, documents: list) -> dict | None:
        try:
            url = f"{self.base_url}/indexes/{index_name}/docs/index?api-version={self.api_version}"
            body = {"value": documents}
            return self._http_request("add_document_to_index", "POST", url, json_body=body)
        except Exception as e:
            logging.error(f"Error in add_document_to_index: {str(e)}")
            traceback.print_stack()
            return None

    def create_index(self, name, schema_json_filename: str) -> dict | None:
        try:
            with open(schema_json_filename, "r") as file:
                schema = json.load(file)
            schema["name"] = name  # override the name in the schema file
            url = f"{self.base_url}/indexes/{name}?api-version={self.api_version}"
            return self._http_request("create_index", "PUT", url, json_body=schema)
        except Exception as e:
            logging.error(f"Error in create_index: {str(e)}")
            traceback.print_stack()
            return False

    def create_indexer(self, name, schema_json_filename: str) -> dict | None:
        try:
            with open(schema_json_filename, "r") as file:
                schema = json.load(file)
            schema["name"] = name  # override the name in the schema file
            url = f"{self.base_url}/indexers/{name}?api-version={self.api_version}"
            return self._http_request("create_indexer", "PUT", url, json_body=schema)
        except Exception as e:
            logging.error(f"Error in create_indexer: {str(e)}")
            traceback.print_stack()
            return False

    def get_indexer_status(self, name: str) -> dict | None:
        try:
            url = f"{self.base_url}/indexers/{name}/status?api-version={self.api_version}"
            return self._http_request("get_indexer_status", "GET", url, headers=self.headers)
        except Exception as e:
            logging.error(f"Error in get_indexer_status: {str(e)}")
            traceback.print_stack()
            return False

    def delete_datasource(self, name: str) -> bool:
        try:
            url = f"{self.base_url}/datasources/{name}?api-version={self.api_version}"
            return self._http_request("delete_datasource", "DELETE", url)
        except Exception as e:
            logging.error(f"Error in delete_datasource: {str(e)}")
            traceback.print_stack()
            return False

    def delete_index(self, name: str) -> bool:
        try:
            url = f"{self.base_url}/indexes/{name}?api-version={self.api_version}"
            return self._http_request("delete_index", "DELETE", url)
        except Exception as e:
            logging.error(f"Error in delete_index: {str(e)}")
            traceback.print_stack()
            return False

    def delete_indexer(self, name: str) -> dict | None:
        try:
            url = f"{self.base_url}/indexers/{name}?api-version={self.api_version}"
            return self._http_request("delete_indexer", "DELETE", url)
        except Exception as e:
            logging.error(f"Error in delete_indexer: {str(e)}")
            traceback.print_stack()
            return None

    def list_datasources(self) -> dict | None:
        try:
            url = f"{self.base_url}/datasources?api-version={self.api_version}"
            return self._http_request("list_datasources", "GET", url)
        except Exception as e:
            logging.error(f"Error in list_datasources: {str(e)}")
            traceback.print_stack()
            return None

    def list_indexers(self) -> dict | None:
        try:
            url = f"{self.base_url}/indexers?api-version={self.api_version}"
            return self._http_request("list_indexers", "GET", url)
        except Exception as e:
            logging.error(f"Error in list_indexers: {str(e)}")
            traceback.print_stack()
            return

    def list_indexes(self) -> dict | None:
        try:
            url = f"{self.base_url}/indexes?api-version={self.api_version}"
            return self._http_request("list_indexes", "GET", url)
        except Exception as e:
            logging.error(f"Error in list_indexes: {str(e)}")
            traceback.print_stack()
            return []

    def lookup_datasource(self, name: str) -> dict | None:
        try:
            url = f"{self.base_url}/datasources/{name}?api-version={self.api_version}"
            return self._http_request("lookup_datasource", "GET", url)
        except Exception as e:
            logging.error(f"Error in lookup_datasource: {str(e)}")
            traceback.print_stack()
            return None

    def lookup_doc(self, index_name: str, doc_key: str) -> dict | None:
        try:
            url = f"{self.base_url}/indexes/{index_name}/docs/{doc_key}?api-version={self.api_version}"
            return self._http_request("lookup_doc", "GET", url)
        except Exception as e:
            logging.error(f"Error in lookup_doc: {str(e)}")
            traceback.print_stack()
            return None

    def lookup_index(self, name: str) -> dict | None:
        try:
            url = f"{self.base_url}/indexes/{name}?api-version={self.api_version}"
            return self._http_request("lookup_index", "GET", url)
        except Exception as e:
            logging.error(f"Error in lookup_index: {str(e)}")
            traceback.print_stack()
            return None

    def lookup_indexer_schema(
        self, indexer_name: str, index_name: str, datasource_name: str
    ) -> dict | None:
        try:
            indexer = self.lookup_indexer(indexer_name)
            index = self.lookup_index(index_name)
            datasource = self.lookup_datasource(datasource_name)
            return {"indexer": indexer, "index": index, "datasource": datasource}
        except Exception as e:
            logging.error(f"Error in lookup_indexer_schema: {str(e)}")
            traceback.print_stack()
            return None

    def lookup_indexer(self, name: str) -> dict | None:
        try:
            url = f"{self.base_url}/indexers/{name}?api-version={self.api_version}"
            return self._http_request("lookup_indexer", "GET", url)
        except Exception as e:
            logging.error(f"Error in lookup_indexer: {str(e)}")
            traceback.print_stack()
            return None

    def modify_index(self, action, name: str, schema_json_filename: str):
        try:
            with open(schema_json_filename, "r") as file:
                schema = json.load(file)
            url = f"{self.base_url}/indexes/{name}?api-version={self.api_version}"
            return self._http_request("modify_index", action, url, json_body=schema)
        except Exception as e:
            logging.error(f"Error in modify_index: {str(e)}")
            traceback.print_stack()
            return None

    def modify_indexer(self, action: str, name: str, schema_json_filename: str):
        try:
            with open(schema_json_filename, "r") as file:
                schema = json.load(file)
            url = f"{self.base_url}/indexers/{name}?api-version={self.api_version}"
            return self._http_request("modify_indexer", action, url, json_body=schema)
        except Exception as e:
            logging.error(f"Error in modify_indexer: {str(e)}")
            traceback.print_stack()
            return None

    def reset_indexer(self, name: str) -> dict | None:
        try:
            url = f"{self.base_url}/indexers/{name}/reset?api-version={self.api_version}"
            return self._http_request("reset_indexer", "POST", url)
        except Exception as e:
            logging.error(f"Error in reset_indexer: {str(e)}")
            traceback.print_stack()
            return None

    def run_indexer(self, name: str) -> dict | None:
        try:
            url = f"{self.base_url}/indexers/{name}/run?api-version={self.api_version}"
            return self._http_request("run_indexer", "POST", url)
        except Exception as e:
            logging.error(f"Error in run_indexer: {str(e)}")
            traceback.print_stack()
            return None

    def search_index(self, idx_name: str, search_name: str, search_params: object) -> dict | None:
        try:
            url = f"{self.base_url}/indexes/{idx_name}/docs/search?api-version={self.api_version}"
            search_body = {"search": search_name, **search_params}
            return self._http_request("search_index", "POST", url, json_body=search_body)
        except Exception as e:
            logging.error(f"Error in search_index: {str(e)}")
            traceback.print_stack()
            return None

    def update_index(self, name, schema_json_filename: str) -> dict | None:
        return self.modify_index("PUT", name, schema_json_filename)

    def update_indexer(self, name, schema_json_filename: str) -> dict | None:
        return self.modify_indexer("PUT", name, schema_json_filename)

    def _http_request(self, function_name: str, method: str, url: str, headers={}, json_body={}):
        try:
            if headers is None:
                headers = self.headers
            if headers == {}:
                headers = self.headers
            response = self.client.request(method, url, headers=headers, json=json_body)
            print(f"response.status_code: {response.status_code}")
            data = dict()
            data["url"] = url
            data["method"] = method
            # The bearer token is a credential; keep it out of the returned (and printed) data.
            data["headers"] = {k: v for k, v in headers.items() if k != "Authorization"}
            data["status_code"] = response.status_code
            data["content"] = None
            if response.content is not None:
                if len(response.content) > 0:
                    data["content"] = response.json()
            return data
        except Exception as e:
            logging.error(f"Exception in {function_name}: {str(e)}")
            traceback.print_stack()
            return None
