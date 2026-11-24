import asyncio
import json
import os

from datetime import datetime, timezone
from typing import Annotated

from agent_framework import Agent, AgentContext, Message, agent_middleware, tool
from agent_framework.foundry import FoundryChatClient
from agent_framework_foundry_hosting import ResponsesHostServer
from azure.identity import DefaultAzureCredential
from pydantic import Field

from src.ai.ai_search_util import AISearchUtil
from src.io.fs import FS
from src.io.storage_util import StorageUtil
from src.os.env import Env

BLOB_CONTAINER = "agents"
BLOB_NAME = "epl-middleware.txt"
SEARCH_INDEX = "epl"


def read_and_write_blob(storage_util: StorageUtil) -> tuple[str, str]:
    """
    Read the blob's current value ('absent' if there is none), then overwrite it with the
    current UTC timestamp. Returns (previous_value, written_timestamp).
    """
    previous_value = storage_util.download_blob_as_string(BLOB_CONTAINER, BLOB_NAME)
    if previous_value is None:
        previous_value = "absent"
    timestamp = datetime.now(timezone.utc).isoformat()
    if not storage_util.upload_string_as(BLOB_CONTAINER, BLOB_NAME, timestamp):
        timestamp = f"{timestamp} (write failed)"
    return previous_value, timestamp


def blob_middleware(storage_util: StorageUtil):
    """
    Return agent middleware that, on every invocation, reads and writes to a
    specific blob in Azure Blob Storage.  This is just for middleware demonstration purposes.
    """

    @agent_middleware
    async def middleware(context: AgentContext, call_next):
        previous_value, timestamp = await asyncio.to_thread(read_and_write_blob, storage_util)
        print(f"{BLOB_CONTAINER}/{BLOB_NAME}: previous value: {previous_value}, wrote: {timestamp}")
        context.messages.append(
            Message(
                "system",
                [
                    f"Blob {BLOB_CONTAINER}/{BLOB_NAME} previous value: {previous_value}\n"
                    f"Blob {BLOB_CONTAINER}/{BLOB_NAME} new value written: {timestamp}\n"
                    "Include both of these values, verbatim, at the end of your response."
                ],
            )
        )
        await call_next()

    return middleware


def get_teams_search_tool(search_util: AISearchUtil):
    """
    Return the team_info_tool function tool, bound to the given AISearchUtil.
    """

    @tool(approval_mode="never_require")
    async def teams_search_tool() -> str:
        """
        Get the list of all teams in the EPL.

        Returns a JSON string that looks like this:
        {
            "value": [
                {
                    "@search.score": 4.1271343,
                    "id": "8add66ae-e93f-4a22-9742-bc9e22efeff7",
                    "lc_team": "crystal palace",
                    "venue": "Selhurst Park",
                    "address": "Whitehorse Lane London SE25 6PU"
                },
                {
                    "@search.score": 4.1053944,
                    "id": "30ce7915-aee2-4f25-98b2-788c2fa0327b",
                    "lc_team": "tottenham",
                    "venue": "Tottenham Hotspur Stadium",
                    "address": "Bill Nicholson Way, 748 High Road London N17 0AP"
                },
            ...
            ]
        }

        The 'lc_team' attribute contains the lowercased team name.
        The 'venue' attribute contains the name of the stadium the team plays at.
        The 'address' attribute includes the city.
        """
        search_params = {
            "count": False,
            "search": "doctype eq 'team'",
            "select": "id,lc_team,venue,address",
            "queryType": "full",
            "top": 1000
        }
        result = await asyncio.to_thread(search_util.search_index, SEARCH_INDEX, "*", search_params)
        if result is None or result.get("status_code") != 200:
            # Return only the status and service message; the full result has the endpoint URL.
            content = (result or {}).get("content") or {}
            return json.dumps(
                {
                    "error": "search failed",
                    "status_code": (result or {}).get("status_code"),
                    "message": content.get("error", {}).get("message"),
                }
            )
        content = result["content"] or {}
        # Drop @search.score and similar; with a "*" search they carry no information.
        matches = [
            {k: v for k, v in doc.items() if not k.startswith("@")}
            for doc in content.get("value", [])
        ]
        return json.dumps({"count": content.get("@odata.count"), "matches": matches})

    return teams_search_tool


def get_schedule_search_tool(search_util: AISearchUtil):
    """
    Return the schedule_tool function tool, bound to the given AISearchUtil.
    """

    @tool(approval_mode="never_require")
    async def schedule_search_tool() -> str:
        """
        Get the list of all matches in the current EPL season.

        Returns a JSON string that looks like this:
        {
            "value": [
                {
                "@search.score": 1.0498221,
                    "id": "b6abfe86-7193-4fce-a21a-ca1355f286e0",
                    "doctype": "match",
                    "lc_home_team": "arsenal",
                    "lc_away_team": "coventry city",
                    "date": "2026-08-21",
                    "matchday": 1
                },
                {
                "@search.score": 0.93637747,
                    "id": "c50121e2-da6a-4aa1-8fec-af25a6f93cba",
                    "doctype": "match",
                    "lc_home_team": "brentford",
                    "lc_away_team": "tottenham",
                    "date": "2026-08-22",
                    "matchday": 1
                },
                ...
            ]
        }
        """

        search_params = {
            "count": False,
            "search": "doctype:match",
            "select": "id,doctype,lc_home_team,lc_away_team,date,matchday",
            "orderby": "date,lc_home_team",
            "queryType": "full",
            "top": 1000
        }
        result = await asyncio.to_thread(search_util.search_index, SEARCH_INDEX, "*", search_params)
        if result is None or result.get("status_code") != 200:
            # Return only the status and service message; the full result has the endpoint URL.
            content = (result or {}).get("content") or {}
            return json.dumps(
                {
                    "error": "search failed",
                    "status_code": (result or {}).get("status_code"),
                    "message": content.get("error", {}).get("message"),
                }
            )
        content = result["content"] or {}
        # Drop @search.score and similar; with a "*" search they carry no information.
        matches = [
            {k: v for k, v in doc.items() if not k.startswith("@")}
            for doc in content.get("value", [])
        ]
        return json.dumps({"count": content.get("@odata.count"), "matches": matches})

    return schedule_search_tool


def get_players_search_tool(search_util: AISearchUtil):
    """
    Return the players_search_tool function tool, bound to the given AISearchUtil.
    """

    @tool(approval_mode="never_require")
    async def players_search_tool(
        team: Annotated[
            str,
            Field(
                description="Lowercased team name, or '*' for all teams, as stored in the index, "
                "e.g. 'arsenal', 'man city', 'nottingham', '*'."
            ),
        ] = "*",
    ) -> str:
        """
        Get a list of players on an a given EPL team, or all teams if no team ('*') is specified.

        Returns a JSON string that looks like this:
        {
            "value": [
                {
                "@search.score": 0.42972973,
                    "id": "fbe4218a-c94e-4fcf-b703-51be14b0f4f1",
                    "lc_team": "arsenal",
                    "firstName": "Riccardo",
                    "lastName": "Calafiori",
                    "position": "Defence",
                    "nationality": "Italy",
                    "dateOfBirth": "2002-05-19"
                },
                {
                "@search.score": 0.535755,
                    "id": "7d9ec83e-1388-49d2-a691-eb648d47b807",
                    "lc_team": "arsenal",
                    "firstName": "",
                    "lastName": "Cristhian Mosquera",
                    "position": "Defence",
                    "nationality": "Spain",
                    "dateOfBirth": "2004-06-27"
                },
                ...
            ]
        }
        """

        filter = f"search.ismatch('{team}', 'lc_team')"
        search_params = {
            "count": False,
            "search": "doctype:player",
            "select": "id,lc_team,firstName,lastName,nationality,position,dateOfBirth",
            "top": 1000,
            "filter": filter,
            "orderby": "lastName",
            "queryType": "full",
        }
        result = await asyncio.to_thread(search_util.search_index, SEARCH_INDEX, "*", search_params)
        if result is None or result.get("status_code") != 200:
            # Return only the status and service message; the full result has the endpoint URL.
            content = (result or {}).get("content") or {}
            return json.dumps(
                {
                    "error": "search failed",
                    "status_code": (result or {}).get("status_code"),
                    "message": content.get("error", {}).get("message"),
                }
            )
        content = result["content"] or {}
        # Drop @search.score and similar; with a "*" search they carry no information.
        matches = [
            {k: v for k, v in doc.items() if not k.startswith("@")}
            for doc in content.get("value", [])
        ]
        return json.dumps({"count": content.get("@odata.count"), "matches": matches})

    return players_search_tool


def main():
    print("epl agent main()...")
    Env.log_env_vars()
    project_endpoint = os.getenv("AZURE_FOUNDRY_PROJECT_URL")
    model_name = os.getenv("AZURE_AI_MODEL_DEPLOYMENT_NAME")
    vector_store_id = os.getenv("AZURE_FOUNDRY_VECTOR_STORE_ID")

    if not project_endpoint:
        raise RuntimeError("AZURE_FOUNDRY_PROJECT_URL is not configured.")
    if not model_name:
        raise RuntimeError("AZURE_AI_MODEL_DEPLOYMENT_NAME is not configured.")
    if not os.getenv("AZURE_STORAGE_ACCOUNT_URL"):
        raise RuntimeError("AZURE_STORAGE_ACCOUNT_URL is not configured.")

    credential = DefaultAzureCredential()


    client = FoundryChatClient(
        project_endpoint=project_endpoint,
        model=model_name,
        credential=credential,
    )
    print("FoundryChatClient created")

    storage_util = StorageUtil(credential=credential)
    search_util = AISearchUtil(verbose=True, credential=credential)

    agent = Agent(
        client=client,
        instructions=(
            "You are a friendly assistant for English Premier League (EPL) questions. "
            "Keep your answers brief and to the point. "
            "Prefer to use the custom search tools first, then the file search tool, and finally the web search tool. "
            "Prefer to use tools over LLM calls."
        ),
        # middleware=[blob_middleware(storage_util)],
        # The Agent uses these built-in and custom tools:
        tools=[
            FoundryChatClient.get_web_search_tool(),
            FoundryChatClient.get_code_interpreter_tool(),
            FoundryChatClient.get_file_search_tool(vector_store_ids=[vector_store_id]),
            # matches_at_team_tool(search_util),
            get_teams_search_tool(search_util),
            get_schedule_search_tool(search_util),
            get_players_search_tool(search_util),
        ],
        # History will be managed by the hosting infrastructure, thus there
        # is no need to store history by the service. Learn more at:
        # https://developers.openai.com/api/reference/resources/responses/methods/create
        default_options={"store": False},
    )
    print("Agent created")

    server = ResponsesHostServer(agent)
    server.run()


if __name__ == "__main__":
    main()
