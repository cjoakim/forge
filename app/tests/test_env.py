import sys

import pytest

from src.os.env import Env

from .helpers import set_testing_envvars

# pytest -v tests/test_env.py


# This method runs once at the beginning of this test module.
@pytest.fixture(scope="session", autouse=True)
def setup_before_all_tests():
    Env.set_unit_testing_environment()


def test_boolean_arg():
    print(sys.argv)
    assert Env.boolean_arg("--some-flag") is True
    assert Env.boolean_arg("--some-other-flag") is False


# def test_envvar():
#     assert "jdk" in Env.envvar("JAVA_HOME")
#     assert "21" in Env.envvar("JAVA_HOME")
#     assert Env.envvar("MISSING", "42") == "42"
#     assert Env.envvar("PI", 3.1415926) == 3.1415926


# def test_epoch():
#     e1 = Env.epoch()
#     assert str(type(e1)) == "<class 'float'>"
#     assert e1 > 1700000000.0
#     assert e1 < 1750000000.0


# def test_log_standard_env_vars():
#     assert Env.log_standard_env_vars() is True


# def test_redis_host():
#     expected = "127.0.0.1"
#     assert Env.redis_host() == expected


# def test_redis_port():
#     expected = "6379"
#     assert Env.redis_port() == expected


def test_standard_env_vars():
    keys = sorted(Env.standard_env_vars().keys())
    assert keys == ["AZURE_AI_SEARCH_URL", "AZURE_STORAGE_ACCOUNT_URL", "LOG_LEVEL"]


def test_azure_storage_account(monkeypatch):
    monkeypatch.setenv("AZURE_STORAGE_ACCOUNT_NAME", "stforge1023a")
    monkeypatch.setenv("AZURE_STORAGE_ACCOUNT_URL", "https://stforge1023a.blob.core.windows.net/")
    assert Env.azure_storage_account_name() == "stforge1023a"
    assert Env.azure_storage_account_url() == "https://stforge1023a.blob.core.windows.net/"


# def test_username():
#     assert Env.username() in ["chris", "cjoakim"]


# def test_verbose():
#     assert Env.verbose() is True
