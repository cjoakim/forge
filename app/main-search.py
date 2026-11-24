"""
Usage:
    CLI app for Azure AI Search.
    -
    uv run main-search.py <func>
    uv run main-search.py check_env
    -
    uv run main-search.py list_indexes
    uv run main-search.py list_indexers
    uv run main-search.py list_datasources
    -
    uv run main-search.py lookup_index epl
    uv run main-search.py lookup_indexer <indexer_name>
    uv run main-search.py get_indexer_status <indexer_name>
    uv run main-search.py lookup_datasource <datasource_name>
    -
    uv run main-search.py create_index <index_name> <schema_file>
    uv run main-search.py create_index epl config/search/epl_index.json
    uv run main-search.py delete_index epl
    uv run main-search.py epl_index_field_names
    uv run main-search.py cities_index_field_names
    -
    uv run main-search.py create_indexer <indexer_name> <schema_file>
    uv run main-search.py delete_indexer <indexer_name>
    uv run main-search.py run_indexer <indexer_name>
    uv run main-search.py delete_datasource <datasource_name>
    -
    uv run main-search.py search_index epl top_1000_documents config/search/named_searches.json
    uv run main-search.py search_index epl matches config/search/named_searches.json
    uv run main-search.py search_index epl matches_at_arsenal config/search/named_searches.json
    uv run main-search.py search_index epl players config/search/named_searches.json
    uv run main-search.py search_index epl team config/search/named_searches.json
    uv run main-search.py search_index epl teams config/search/named_searches.json
    uv run main-search.py search_index cities vector_search_bristol config/search/named_searches.json
    -
    uv run main-search.py direct_load_index epl ../data/epl/merged_documents_v2.json --load
    uv run main-search.py direct_load_index cities ../data/epl/cities_v2.json --load
    -
    Note 1: The 'indexer' and 'datasource' functionality is not used in this project
            but the relevant code is retained here for reference.
    Note 2: Authentication is Entra ID (DefaultAzureCredential) rather than with keys.
"""

# This script demonstrates the use of the Azure AI Search with
# custom class AISearchUtil using the Microsoft Azure SDK for Python.

import json
import logging
import os
import sys
import time
import traceback
import uuid

from dotenv import load_dotenv

from src.ai.ai_search_util import AISearchUtil
from src.io.fs import FS


def check_env():
    for name in sorted(os.environ.keys()):
        if name.startswith("AZURE_AI_SEARCH"):
            print("{}: {}".format(name, os.environ[name]))


def direct_load_index(index_name, input_json_file_or_dir):
    docs = list()
    if input_json_file_or_dir.endswith(".json"):
        # it's a file, assumed to be a JSON array of documents
        docs = FS.read_json(input_json_file_or_dir)
        print("Read {} documents from file {}".format(len(docs), input_json_file_or_dir))
    else:
        # it's a directory, assumed to have one JSON file per document
        files = FS.list_files_in_dir(input_json_file_or_dir)
        print("Found {} files in directory {}".format(len(files), input_json_file_or_dir))
        for file in files:
            if file.endswith(".json"):
                fq_filename = "{}/{}".format(input_json_file_or_dir, file)
                doc = FS.read_json(fq_filename)
                if isinstance(doc, dict):
                    docs.append(doc)
        print("Read {} documents from directory {}".format(len(docs), input_json_file_or_dir))
    for doc in docs:
        doc["id"] = str(uuid.uuid4())

    # trannsform attribute datattypes to match the index schema
    for doc in docs:
        if "population" in doc.keys():
            doc["population"] = int(doc["population"])

    # Remove any attributes that are not in the AI Search index schema!
    if index_name == "epl":
        allowed_attributes = epl_index_field_names()
    elif index_name == "cities":
        allowed_attributes = cities_index_field_names()
    else:
        allowed_attributes = "id,doctype".split(",")
    for doc in docs:
        keys, keys_to_remove = doc.keys(), list()
        for key in keys:
            if key not in allowed_attributes:
                keys_to_remove.append(key)
        for key in keys_to_remove:
            del doc[key]

    if "--load" in sys.argv:
        client = AISearchUtil()
        batch, batch_size, batch_num = list(), 100, 0
        # Azure AI Search has a limit of 1000 documents per batch;
        # see https://learn.microsoft.com/en-us/azure/search/search-what-is-data-import
        for idx, doc in enumerate(docs):
            if idx < 100000:
                if "location" in doc.keys():
                    del doc["location"]  # remove the 'location' nested object for now
                print("Document idx {}: id: {}".format(idx, doc["id"]))
                if idx == 0:
                    print(json.dumps(doc, sort_keys=False, indent=2))
                batch.append(doc)
                if len(batch) >= batch_size:
                    batch_num = batch_num + 1
                    print("Adding batch {} of {} documents".format(batch_num, len(batch)))
                    try:
                        result = client.add_documents_to_index(index_name, batch)
                        print(json.dumps(result, sort_keys=False, indent=2))
                    except Exception as e:
                        print("Error adding batch: {}".format(str(e)))
                        print(traceback.format_exc())
                    batch = list()
                    time.sleep(1.0)  # sleep to avoid possible throttling

        if len(batch) > 0:
            batch_num = batch_num + 1
            print("Adding last batch {} of {} documents".format(batch_num, len(batch)))
            result = client.add_documents_to_index(index_name, batch)
            print(json.dumps(result, sort_keys=False, indent=2))

        print(
            "{} documents were in the list to load to index {} in account {}".format(
                len(docs), index_name, client.base_url
            )
        )


def epl_index_field_names():
    infile = "config/search/epl_index.json"
    fields = FS.read_json(infile)["fields"]
    names = list()
    for field in fields:
        names.append(field["name"])
    return names


def cities_index_field_names():
    infile = "config/search/cities_vector_index.json"
    fields = FS.read_json(infile)["fields"]
    names = list()
    for field in fields:
        names.append(field["name"])
    return names


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
            load_dotenv(override=True)
            logging.basicConfig(format="%(asctime)s - %(message)s", level=logging.INFO)

            func = sys.argv[1].lower()
            print("=== CLI function: {}".format(func))
            client = AISearchUtil()
            time.sleep(1)

            if func == "check_env":
                check_env()
            elif func == "list_indexes":
                result = client.list_indexes()
                print(json.dumps(result, sort_keys=False, indent=2))
            elif func == "list_indexers":
                result = client.list_indexers()
                print(json.dumps(result, sort_keys=False, indent=2))
            elif func == "list_datasources":
                result = client.list_datasources()
                print(json.dumps(result, sort_keys=False, indent=2))

            elif func == "delete_indexer":
                name = sys.argv[2]
                result = client.delete_indexer(name)
                print(json.dumps(result, sort_keys=False, indent=2))
            elif func == "delete_index":
                name = sys.argv[2]
                result = client.delete_index(name)
                print(json.dumps(result, sort_keys=False, indent=2))
            elif func == "delete_datasource":
                name = sys.argv[2]
                result = client.delete_datasource(name)
                print(json.dumps(result, sort_keys=False, indent=2))

            elif func == "create_index":
                name, schema_json_filename = sys.argv[2], sys.argv[3]
                result = client.create_index(name, schema_json_filename)
                print(json.dumps(result, sort_keys=False, indent=2))
            elif func == "create_indexer":
                name, schema_json_filename = sys.argv[2], sys.argv[3]
                result = client.create_indexer(name, schema_json_filename)
                print(json.dumps(result, sort_keys=False, indent=2))

            elif func == "lookup_datasource":
                name = sys.argv[2]
                result = client.lookup_datasource(name)
                print(json.dumps(result, sort_keys=False, indent=2))
            elif func == "lookup_index":
                name = sys.argv[2]
                result = client.lookup_index(name)
                print(json.dumps(result, sort_keys=False, indent=2))
            elif func == "lookup_indexer":
                name = sys.argv[2]
                result = client.lookup_indexer(name)
                print(json.dumps(result, sort_keys=False, indent=2))
            elif func == "lookup_indexer_schema":
                indexer_name = sys.argv[2]
                index_name = sys.argv[3]
                datasource_name = sys.argv[4]
                result = client.lookup_indexer_schema(indexer_name, index_name, datasource_name)
                print(json.dumps(result, sort_keys=False, indent=2))

            elif func == "run_indexer":
                name = sys.argv[2]
                result = client.run_indexer(name)
                print(json.dumps(result, sort_keys=False, indent=2))
            elif func == "reset_indexer":
                name = sys.argv[2]
                result = client.reset_indexer(name)
                print(json.dumps(result, sort_keys=False, indent=2))
            elif func == "get_indexer_status":
                name = sys.argv[2]
                result = client.get_indexer_status(name)
                print(json.dumps(result, sort_keys=False, indent=2))

            elif func == "search_index":
                index_name = sys.argv[2]
                search_name = sys.argv[3]
                searches_json_filename = sys.argv[4]
                search_params = FS.read_json(searches_json_filename)[search_name]
                print("Index name:  {}".format(index_name))
                print("Search name: {}".format(search_name))
                print(
                    "Search params:\n{}".format(
                        json.dumps(search_params, sort_keys=False, indent=2)
                    )
                )
                result = client.search_index(index_name, search_name, search_params)
                print(json.dumps(result, sort_keys=False, indent=2))
                FS.write_json(result, "tmp/search_result.json", pretty=True, sort_keys=False)

            elif func == "direct_load_index":
                index_name = sys.argv[2]
                input_json_file_or_dir = sys.argv[3]
                direct_load_index(index_name, input_json_file_or_dir)
            elif func == "epl_index_field_names":
                names = epl_index_field_names()
                print(json.dumps(names, sort_keys=False, indent=2))
            elif func == "cities_index_field_names":
                names = cities_index_field_names()
                print(json.dumps(names, sort_keys=False, indent=2))
            else:
                print_options("Error: invalid function: {}".format(func))
    except Exception as e:
        print(str(e))
        print(traceback.format_exc())
