"""
Usage:
  CLI app for zip-file functions - such as zipping the common codebase
  and unzipping it to your agent directories.
  uv run main-zip.py <func>
  uv run main-zip.py zip_src --verbose
  uv run main-zip.py unzip_src_in_agent <agent_name>
  uv run main-zip.py unzip_src_in_agent c1
"""

import logging
import os
import shutil
import sys
import traceback

from dotenv import load_dotenv

from src.io.zip_util import ZipUtil

COMMON_SRC_ZIPFILE = "src.zip"


def zip_codebase():
    zip_util = ZipUtil()
    exclude_dirs = zip_util.standard_dir_exclusions()
    exclude_dirs.append("data")
    result = zip_util.zip_directory(
        directory="..",
        outfile="../codebase.zip",
        exclude_hidden=True,
        include_dirs=[],
        exclude_dirs=exclude_dirs,
        exclude_files=None,
    )
    print(f"zip_codebase result: {result}")


def zip_src():
    zip_util = ZipUtil()
    result = zip_util.zip_directory(
        directory=".",
        outfile="src.zip",
        exclude_hidden=True,
        include_dirs=["src"],
        exclude_dirs=None,
        exclude_files=None,
    )
    print(f"zip_src result: {result}")


def unzip_src_in_agent(agent_name: str):
    """
    Use shutil to delete the computed src_path, then copy the src.zip to the src_path

    """

    if os.path.exists(COMMON_SRC_ZIPFILE):
        print(f"OK: {COMMON_SRC_ZIPFILE} exists")
    else:
        print(
            f"Error: {COMMON_SRC_ZIPFILE} file does not exist.  Create it with 'uv run main-zip.py zip_src'"
        )
        exit(1)

    agent_src_path = f"agents/{agent_name}/src/{agent_name}"
    print(f"agent_name: {agent_name}, agent_src_path: {agent_src_path}")

    if os.path.exists(agent_src_path):
        print(f"OK: {agent_src_path} exists")
        shutil.unpack_archive(COMMON_SRC_ZIPFILE, extract_dir=agent_src_path)
        print(f"OK: {COMMON_SRC_ZIPFILE} unpacked to {agent_src_path}")
    else:
        print(f"Error: agent_src_path {agent_src_path} does not exist")


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
            if func == "zip_codebase":
                zip_codebase()
            elif func == "zip_src":
                zip_src()
            elif func == "unzip_src_in_agent":
                agent_name = sys.argv[2]
                unzip_src_in_agent(agent_name)
            else:
                print_options("Error: invalid function: {}".format(func))
    except Exception as e:
        print(str(e))
        print(traceback.format_exc())
