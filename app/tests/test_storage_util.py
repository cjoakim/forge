import time

from azure.core.credentials import AccessToken

from src.io.storage_util import StorageUtil

# pytest -v tests/test_storage_util.py


class FakeCredential:
    """A TokenCredential stand-in, so the tests don't need az login or the network."""

    def get_token(self, *scopes, **kwargs):
        return AccessToken("fake-token", int(time.time()) + 3600)


def test_uses_account_url_and_credential():
    url = "https://stforge1023a.blob.core.windows.net/"
    credential = FakeCredential()
    util = StorageUtil(account_url=url, credential=credential)
    assert util.blob_service_client.url == url
    assert util.blob_service_client.credential is credential


def test_account_url_from_env(monkeypatch):
    monkeypatch.setenv("AZURE_STORAGE_ACCOUNT_URL", "https://stfromenv.blob.core.windows.net/")
    util = StorageUtil(credential=FakeCredential())
    assert util.blob_service_client.account_name == "stfromenv"
