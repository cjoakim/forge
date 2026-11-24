import os
import pytest

from src.os.env import Env
from src.os.system import System

# pytest -v tests/test_system.py


# This method runs once at the beginning of this test module.
@pytest.fixture(scope="session", autouse=True)
def setup_before_all_tests():
    Env.set_unit_testing_environment()


def test_platform():
    platform = System.platform()
    print("platform is: {}".format(platform))

    if platform.startswith("win"):
        assert System.is_windows() is True
        assert System.is_mac() is False
    elif "darwin" in platform:
        assert System.is_windows() is False
        assert System.is_mac() is True
    elif "linux" in platform:
        assert System.is_windows() is False
        assert System.is_mac() is False
    else:
        assert False, "Unknown platform: {}".format(platform)


def test_pwd():
    assert System.pwd() == os.getcwd()


def test_epoch_int():
    n = System.epoch_int()
    assert isinstance(n, int)
    assert n > 1767225600  # 2026-01-01


def test_user():
    user = System.user()
    assert isinstance(user, str)
    assert len(user) > 0
