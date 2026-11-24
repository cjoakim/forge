import time

import httpx

from azure.core.credentials import AccessToken

from src.ai.ai_search_util import SEARCH_SCOPE, AISearchUtil

# pytest -v tests/test_ai_search_util.py


class FakeCredential:
    """A TokenCredential stand-in, so the tests don't need az login or the network."""

    def __init__(self):
        self.scopes = []

    def get_token(self, *scopes, **kwargs):
        self.scopes.extend(scopes)
        return AccessToken("fake-token", int(time.time()) + 3600)


def test_headers_use_entra_bearer_token(monkeypatch):
    monkeypatch.setenv("AZURE_AI_SEARCH_URL", "https://srch-forge1023a.search.windows.net")
    credential = FakeCredential()
    util = AISearchUtil(credential=credential)
    headers = util.headers
    assert headers["Authorization"] == "Bearer fake-token"
    assert "api-key" not in headers
    assert credential.scopes == [SEARCH_SCOPE]
    assert util.base_url == "https://srch-forge1023a.search.windows.net"


def test_http_request_keeps_token_out_of_result(monkeypatch):
    monkeypatch.setenv("AZURE_AI_SEARCH_URL", "https://srch-forge1023a.search.windows.net")
    sent = {}

    def handler(request):
        sent["authorization"] = request.headers.get("Authorization")
        return httpx.Response(200, json={"value": []})

    real_client = httpx.Client
    monkeypatch.setattr(
        httpx, "Client", lambda *a, **kw: real_client(transport=httpx.MockTransport(handler))
    )
    util = AISearchUtil(credential=FakeCredential())
    result = util.list_indexes()
    assert sent["authorization"] == "Bearer fake-token"
    assert result["status_code"] == 200
    assert "Authorization" not in result["headers"]
