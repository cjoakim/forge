import pytest

from src.os.env import Env

from dotenv import load_dotenv

# Helper methods that can be reused in the tests.


def load_env_file():
    print("helpers.py#load_env_file")
    load_dotenv()


def set_testing_envvars(monkeypatch):
    monkeypatch.setenv("USER", "chris")
    monkeypatch.setenv("USERNAME", "joakim")
