"""
Usage:
  CLI app for Azure Storage.
  uv run main-storage.py <func>
  uv run main-storage.py check_env
  uv run main-storage.py create_container documents
  uv run main-storage.py upload_file ../data/documents/30-Years-of-the-EPL.pdf documents
  uv run main-storage.py download_blob_to_file documents 30-Years-of-the-EPL.pdf
  uv run main-storage.py execute_examples 5
"""

# This script demonstrates the use of the Azure Storage with
# custom class StorageUtil using the Microsoft Azure SDK for Python.

import os
import logging
import sys
import time
import tomllib
import traceback

from dotenv import load_dotenv

from src.io.fs import FS
from src.io.storage_util import StorageUtil
from src.os.env import Env


def check_env():
    account_url = Env.azure_storage_account_url()
    print(f"Env.azure_storage_account_url(): {account_url}")


def create_container(cname: str):
    print(f"Creating container: {cname}")
    storage_util = StorageUtil()
    created_container = storage_util.create_container(cname)
    if created_container:
        print(f"Container '{created_container}' created successfully.")
    else:
        print(f"Failed to create container '{cname}'.")


def upload_file(cname: str, filename: str):
    print(f"Uploading file: {filename} to container: {cname}")
    storage_util = StorageUtil()
    result = storage_util.upload_file_as(cname, os.path.basename(filename), filename, replace=True)
    print(f"Upload result: {result}")


def download_blob_to_file(cname: str, filename: str):
    outfile = f"tmp/{os.path.basename(filename)}"
    print(f"Downloading file: {filename} from container: {cname}")
    storage_util = StorageUtil()
    result = storage_util.download_blob_to_file(cname, filename, outfile)
    print(f"Download result: {result}")


def execute_examples(sleep_time: int = 3):
    print("\n===== StorageUtil constructor")
    storage_util = StorageUtil()
    time.sleep(sleep_time)

    print("\n===== initial listing, and deletion of execute_examples containers")
    containers = storage_util.list_containers()
    print(f"Current storage containers: {containers}")
    for container in containers:
        if container.startswith("execute-examples"):
            print(f"Deleting container: {container}")
            if storage_util.delete_container(container):
                print(f"Container '{container}' deleted successfully.")
            else:
                print(f"Container '{container}' does not exist or could not be deleted.")
        else:
            print(f"Retaining container: {container} (not a execute-examples container)")
    time.sleep(sleep_time)

    cname = "execute-examples-{}".format(int(Env.epoch()))

    print("\n===== creating a new container named: {}".format(cname))
    created_container = storage_util.create_container(cname)
    if created_container:
        print(f"Container '{created_container}' created successfully.")
    else:
        print(f"Failed to create container '{cname}'.")
    time.sleep(sleep_time)

    print("\n===== uploading pyproject.toml, with optional metadata attributes")
    lines = FS.read_lines("pyproject.toml")
    line_count = str(len(lines))
    print(f"pyproject.toml has {len(lines)} lines")
    metadata = {
        "description": "pyproject.toml file for the zero-to-AI project",
        "line_count": line_count,
    }
    result = storage_util.upload_file(cname, "pyproject.toml", metadata=metadata, replace=True)
    print(f"Upload result: {result}")
    time.sleep(sleep_time)

    print("\n===== uploading data/uk_football/teams_pl.json")
    result = storage_util.upload_file(cname, "data/uk_football/teams_pl.json", replace=True)
    print(f"Upload result: {result}")
    time.sleep(sleep_time)

    print("\n===== list containers again")
    containers = storage_util.list_containers()
    print(f"Containers: {containers}")
    FS.write_json(containers, "tmp/storage-containers.json", pretty=True, sort_keys=True)
    time.sleep(sleep_time)

    print("\n===== list container, blob names only")
    blobs = storage_util.list_container(cname, names_only=True)
    print(f"Blobs in '{cname}': {blobs}")
    FS.write_json(blobs, "tmp/storage-blobs.json", pretty=True, sort_keys=True)
    time.sleep(sleep_time)

    print("\n===== download_blob_to_file: pyproject.toml -> tmp/pyproject_downloaded.toml")
    result = storage_util.download_blob_to_file(
        cname, "pyproject.toml", "tmp/pyproject_downloaded.toml"
    )
    print(f"Download result: {result}")
    print(f"Download result metadata: {result[1]['metadata']}")
    time.sleep(sleep_time)

    print("\n===== download_blob_to_file: data/uk_football/teams_pl.json -> tmp/teams_pl.json")
    result = storage_util.download_blob_to_file(
        cname, "data/uk_football/teams_pl.json", "tmp/teams_pl.json"
    )
    print(f"Download result: {result}")
    time.sleep(sleep_time)

    print("\n===== parse the downloaded pyproject file with tomllib.load()")
    with open("tmp/pyproject_downloaded.toml", "rb") as f:
        data = tomllib.load(f)
    print(f"project name: {data['project']['name']}")
    print(f"project version: {data['project']['version']}")
    print(f"project description: {data['project']['description']}")
    print(f"project dependencies: {data['project']['dependencies']}")
    FS.write_json(data, "tmp/pyproject_downloaded.json", pretty=True, sort_keys=True)
    time.sleep(sleep_time)


def print_options(msg: str | None = None) -> None:
    if msg is not None:
        logging.info(msg)
    logging.info(__doc__)


if __name__ == "__main__":
    load_dotenv(override=True)
    logging.basicConfig(format="%(asctime)s - %(message)s", level=logging.INFO)
    try:
        if len(sys.argv) < 2:
            print_options("Error: invalid command-line")
            exit(1)
        else:
            func = sys.argv[1].lower()
            if func == "check_env":
                check_env()
            elif func == "create_container":
                cname = sys.argv[2]
                create_container(cname)
            elif func == "upload_file":
                filename = sys.argv[2]
                cname = sys.argv[3]
                upload_file(cname, filename)
            elif func == "download_blob_to_file":
                cname = sys.argv[2]
                filename = sys.argv[3]
                download_blob_to_file(cname, filename)
            elif func == "execute_examples":
                sleep_time = int(sys.argv[2])
                execute_examples(sleep_time)
            else:
                print_options("Error: invalid function: {}".format(func))
    except Exception as e:
        print(str(e))
        print(traceback.format_exc())
