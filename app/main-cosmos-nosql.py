"""
Usage:
  Example use of the Cosmos NoSQL API.
  uv run main-cosmos-nosql.py list_databases
  uv run main-cosmos-nosql.py create_database forge 0
  uv run main-cosmos-nosql.py create_container forge epl /pk 1000 default_idx
  uv run main-cosmos-nosql.py create_container forge cities /pk 10000 config/cosmos/cosmosdb_nosql_vector_index_policy_diskann.json
  uv run main-cosmos-nosql.py delete_database forge
  uv run main-cosmos-nosql.py delete_container forge epl
  uv run main-cosmos-nosql.py list_containers enterprise_memory
  uv run main-cosmos-nosql.py load_epl_sequential forge epl --load
  uv run main-cosmos-nosql.py load_epl_bulk forge epl --load
  uv run main-cosmos-nosql.py load_cities forge cities --load
  uv run main-cosmos-nosql.py vector_search_similar_cities forge cities Accrington
"""

import asyncio
import json
import sys
import time
import logging
import traceback
import uuid

from dotenv import load_dotenv

from src.db.cosmos_nosql_util import CosmosNoSqlUtil
from src.io.fs import FS


def print_options(msg: str | None = None) -> None:
    if msg is not None:
        logging.info(msg)
    logging.info(__doc__)


async def list_databases():
    try:
        cosmos = CosmosNoSqlUtil()
        await cosmos.initialize()
        db_list = await cosmos.list_databases()
        for db in db_list:
            logging.info(f"Database: {db}")
    except Exception as e:
        logging.info(str(e))
        logging.info(traceback.format_exc())
    await cosmos.close()


async def create_database(dbname: str, db_ru: int):
    try:
        cosmos = CosmosNoSqlUtil()
        await cosmos.initialize()
        result = await cosmos.create_database(dbname, db_ru)
        logging.info(f"create_database result: {result}")
    except Exception as e:
        logging.info(str(e))
        logging.info(traceback.format_exc())
    await cosmos.close()


async def delete_database(dbname: str):
    try:
        cosmos = CosmosNoSqlUtil()
        await cosmos.initialize()
        result = await cosmos.delete_database(dbname)
        logging.info(f"delete_database result: {result}")
    except Exception as e:
        logging.info(str(e))
        logging.info(traceback.format_exc())
    await cosmos.close()


async def create_container(dbname, cname, pkpath, c_ru, idx_policy_filename="default_idx"):
    try:
        cosmos = CosmosNoSqlUtil()
        await cosmos.initialize()
        await cosmos.set_db(dbname)
        if idx_policy_filename == "default_idx":
            idx_policy_filename = "cosmos/cosmosdb_nosql_default_index_policy.json"
        await cosmos.create_container(cname, pkpath, c_ru, idx_policy_filename)
    except Exception as e:
        logging.info(str(e))
        logging.info(traceback.format_exc())
    await cosmos.close()


async def delete_container(dbname, cname):
    try:
        cosmos = CosmosNoSqlUtil()
        await cosmos.initialize()
        await cosmos.set_db(dbname)
        await cosmos.delete_container(cname)
    except Exception as e:
        logging.info(str(e))
        logging.info(traceback.format_exc())
    await cosmos.close()


async def list_containers(dbname: str):
    try:
        cosmos = CosmosNoSqlUtil()
        await cosmos.initialize()
        await cosmos.set_db(dbname)
        containers = await cosmos.list_containers()
        for container in containers:
            logging.info(f"Container: {container}")
    except Exception as e:
        logging.info(str(e))
        logging.info(traceback.format_exc())
    await cosmos.close()


async def load_epl_sequential(dbname: str, cname: str) -> None:
    try:
        all_docs = collect_epl_documents_for_loading()

        opts = dict()
        opts["enable_diagnostics_logging"] = True
        nosql_util = CosmosNoSqlUtil(opts)
        await nosql_util.initialize()
        dbproxy = await nosql_util.set_db(dbname)
        logging.info(f"dbproxy: {dbname} {dbproxy}")
        ctrproxy = await nosql_util.set_container(cname)
        logging.info(f"ctrproxy: {cname} {ctrproxy}")

        if "--load" in sys.argv:
            for doc in all_docs:
                try:
                    cdb_doc = await nosql_util.upsert_item(doc)
                    logging.info("upserted doc: {}".format(json.dumps(cdb_doc, indent=2)))
                    time.sleep(0.05)
                except Exception as e:
                    logging.info("Error upserting doc: {}".format(str(e)))
                    logging.info(traceback.format_exc())
                    time.sleep(1.0)
    except Exception as e:
        logging.info(str(e))
        logging.info(traceback.format_exc())
    if nosql_util is not None:
        await nosql_util.close()
    logging.info("load_epl_sequential completed")


async def load_epl_bulk(dbname: str, cname: str) -> None:
    try:
        # Initialize the CosmosNoSqlUtil, pointing to the database and container
        opts = dict()
        opts["enable_diagnostics_logging"] = True
        nosql_util = CosmosNoSqlUtil(opts)
        await nosql_util.initialize()
        dbproxy = await nosql_util.set_db(dbname)
        logging.info(f"dbproxy: {dbname} {dbproxy}")
        ctrproxy = await nosql_util.set_container(cname)
        logging.info(f"ctrproxy: {cname} {ctrproxy}")

        # Do a file-based load because each file has its own pk value
        # and bulk-loading must be done with a single partition key.
        for infile in epl_data_files():
            docs = FS.read_json(infile)
            for doc in docs:
                doc["id"] = str(uuid.uuid4())
            await bulk_load_documents(docs, nosql_util, docs[0]["pk"], 20, 1.0)
    except Exception as e:
        logging.info(str(e))
        logging.info(traceback.format_exc())
    if nosql_util is not None:
        await nosql_util.close()
    logging.info("load_epl_bulk completed")


async def bulk_load_documents(
    documents: list,
    nosql_util: CosmosNoSqlUtil,
    pk: str,
    batch_size: int = 50,
    batch_sleep_seconds: float = 0.05,
) -> None:
    try:
        operations = list()
        for doc in documents:
            op = ("create", (doc,))
            operations.append(op)

            # execute several batches of up to 100 operations each
            if len(operations) >= batch_size:
                logging.info("===== executing batch of {} operations ...".format(len(operations)))
                results = await nosql_util.execute_item_batch(operations, pk)
                for idx, result in enumerate(results):
                    logging.info("batch result {}: {}".format(idx, result))
                operations.clear()
                time.sleep(batch_sleep_seconds)

        if len(operations) > 0:
            logging.info("===== executing last batch of {} operations ...".format(len(operations)))
            results = await nosql_util.execute_item_batch(operations, pk)
            for idx, result in enumerate(results):
                logging.info("batch result {}: {}".format(idx, result))
    except Exception as e:
        logging.info(str(e))
        logging.info(traceback.format_exc())


def collect_epl_documents_for_loading():
    """
    Collect the EPL documents from several files into a single list for loading,
    and assign a uuid id value to each document.
    """
    all_docs = list()
    try:
        infiles = epl_data_files()
        for infile in infiles:
            docs = FS.read_json(infile)
            for doc in docs:
                doc["id"] = str(uuid.uuid4())
                all_docs.append(doc)
        logging.info("collected {} epl documents from {} files".format(len(all_docs), len(infiles)))
    except Exception as e:
        logging.info(str(e))
        logging.info(traceback.format_exc())
    return all_docs


def epl_data_files() -> list:
    return [
        "data/cosmos/teams.json",
        "data/cosmos/stadiums.json",
        "data/cosmos/matches.json",
        "data/cosmos/players.json",
    ]


async def load_cities(dbname: str, cname: str):
    try:
        logging.info(f"load_cities, dbname: {dbname}, cname: {cname}")
        infile = "data/cosmos/cities.json"
        cities = FS.read_json(infile)
        logging.info(f"read {len(cities)} cities from file {infile}")
        if "--load" in sys.argv:
            cosmos = CosmosNoSqlUtil()
            await cosmos.initialize()
            await cosmos.set_db(dbname)
            await cosmos.set_container(cname)
            for doc in cities:
                await cosmos.upsert_item(doc)
                time.sleep(0.05)
            await cosmos.close()
    except Exception as e:
        logging.info(str(e))
        logging.info(traceback.format_exc())


async def vector_search_similar_cities(dbname: str, cname: str, libname: str):
    nosql_util = await initialize_cosmos_nosql_util(dbname, cname)
    try:
        sql = (
            "SELECT c.id, c.pk, c.name, c.embedding FROM c where c.city_name = '{}' offset 0 limit 1"
        ).format(libname)
        docs = await nosql_util.query_items(sql, cross_partition=False, pk="/pk", max_items=1)
        if len(docs) == 0:
            logging.info("No document found with id: {}".format(id))
        else:
            embedding = docs[0]["embedding"]
            logging.info("embedding length: {}".format(len(embedding)))
            sql = vector_search_sql(5, embedding)
            FS.write(sql, "tmp/vector_search_sql.txt")
            results = await nosql_util.query_items(sql, True)
            for idx, result in enumerate(results):
                logging.info(result)
    except Exception as e:
        logging.info(str(e))
        logging.info(traceback.format_exc())
    await nosql_util.close()


def vector_search_sql(top_n: int, embedding: list):
    return """
SELECT TOP {} c.id, c.pk, c.name, VectorDistance(c.embedding, {}) AS SimilarityScore
 FROM c
 ORDER BY VectorDistance(c.embedding, {})
""".format(top_n, embedding, embedding).lstrip()


async def initialize_cosmos_nosql_util(dbname: str, cname: str):
    opts = dict()
    opts["enable_diagnostics_logging"] = True
    nosql_util = CosmosNoSqlUtil(opts)
    await nosql_util.initialize()
    await nosql_util.set_db(dbname)
    await nosql_util.set_container(cname)
    return nosql_util


def throw_exception_here():
    # intentionally throw an exception
    intentional_exception = 1 / 0
    logging.info("{}".format(intentional_exception))


if __name__ == "__main__":
    # standard initialization of env and logger
    load_dotenv(override=True)
    logging.basicConfig(format="%(asctime)s - %(message)s", level=logging.INFO)
    if len(sys.argv) < 2:
        print_options("Error: invalid command-line")
        exit(1)
    else:
        try:
            func = sys.argv[1].lower()
            if func == "list_databases":
                asyncio.run(list_databases())
            elif func == "create_database":
                dbname, db_ru = sys.argv[2], int(sys.argv[3])
                asyncio.run(create_database(dbname, db_ru))
            elif func == "create_container":
                dbname, cname = sys.argv[2], sys.argv[3]
                pkpath, c_ru = sys.argv[4], int(sys.argv[5])
                idx_policy_filename = sys.argv[6]
                asyncio.run(create_container(dbname, cname, pkpath, c_ru, idx_policy_filename))
            elif func == "delete_database":
                dbname = sys.argv[2]
                asyncio.run(delete_database(dbname))
            elif func == "delete_container":
                dbname, cname = sys.argv[2], sys.argv[3]
                asyncio.run(delete_container(dbname, cname))
            elif func == "list_containers":
                dbname = sys.argv[2]
                asyncio.run(list_containers(dbname))
            elif func == "load_epl_sequential":
                dbname, cname = sys.argv[2], sys.argv[3]
                asyncio.run(load_epl_sequential(dbname, cname))
            elif func == "load_epl_bulk":
                dbname, cname = sys.argv[2], sys.argv[3]
                asyncio.run(load_epl_bulk(dbname, cname))
            elif func == "load_cities":
                dbname, cname = sys.argv[2], sys.argv[3]
                asyncio.run(load_cities(dbname, cname))
            elif func == "vector_search_similar_cities":
                dbname = sys.argv[2]
                cname = sys.argv[3]
                city_name = sys.argv[4]
                asyncio.run(vector_search_similar_cities(dbname, cname, city_name))
            else:
                print_options("Error: invalid function: {}".format(func))
        except Exception as e:
            logging.info(str(e))
            logging.info(traceback.format_exc())
