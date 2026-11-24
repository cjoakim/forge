# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

A Foundry-centric deployable reference AI application on Azure
(Microsoft Foundry, AI Search, Storage, Cosmos DB, ACR, Key Vault,
App Insights, private endpoints, IP firewalls).
The reference app is about the English Premier League (EPL).
It is meant to be copied or forked, not edited in place.
It favors the Microsoft stack (Agent Framework, not LangChain), pro-code Python,
Entra auth instead of keys, and Docker-hosted agents deployed with `azd`.
Every `.sh` script has a matching `.ps1` for Windows, so keep the pair in sync when you change one.

## Commands

All Python work happens in `app/` with **uv** (Python >= 3.14; deps in `app/pyproject.toml`). CLI programs are run from `app/`, because paths such as `config/...`, `templates/`, `generator_config.json` and `../data/...` are relative to it.

```bash
cd app
uv sync                                   # create .venv, install deps + dev group
./tests.sh                                # all pytest tests with coverage (htmlcov/), then pylint
uv run pytest tests/test_fs.py -v         # one test file
uv run pytest tests/test_fs.py::test_name # one test
uv run pylint *.py src                    # lint: errors + unused/re-imports only (see pyproject)
uv run ruff format                        # formatter, line length 100
```

`pytest-randomly` is installed, so test order is shuffled. Some tests (for example `test_ai_search_util.py`, `test_storage_util.py`) need a populated `app/.env` and live Azure resources.

CLI entry points are `app/main-*.py` and are dispatched by function name; each file's docstring lists its usage (for example `uv run main-search.py list_indexes`, `uv run main-foundry.py list_agents`, `uv run main-cosmos-nosql.py ...`, `uv run main-storage.py ...`). The `*.sh` wrappers (`search.sh`, `storage.sh`, `cosmos.sh`, `acr.sh`, `rg.sh`, `models-report.sh`) chain these together.

## Configuration flow

- `app/.env` (git-ignored; template in `app/dotenv-example`) is the single source of settings. Python loads it with `load_dotenv()` and reads it through `src/os/env.py` (`Env`). `Env` masks values whose names contain KEY, SECRET, TOKEN, and similar, because container logs go to Log Analytics.
- `source ./set-os-env.sh` exports `.env` into the current shell. It must be sourced.
- `./set-azd-env.sh agents/<name>` recreates an azd environment named after the agent directory, from `.env`. It is stored in `agents/<name>/.azure/`. Run it before deploying an agent.

## Architecture

**Infrastructure**: `app/arm/template.json` plus `parameters.json`, deployed with `app/arm/deploy-arm.sh -g <rg> -l <region> [-a <allowed-ips>]`. Resource names come from one base name with CAF prefixes (`aif-`, `srch-`, `st`, `cr`, `kv-`, `cosmos-`, ...). Service firewalls default to the deployer's public IP (`arm/ip_address.sh`).

**Shared library `app/src/`**: reusable classes grouped by area: `ai/` (`AISearchUtil`, `FoundryUtil`, model listing and pricing), `db/` (`CosmosNoSqlUtil`), `io/` (`FS`, `StorageUtil`, `ZipUtil`), `os/` (`Env`, `System`), and `util/` (`AgentGenerator`, `Template`, `PyprojectParser`). Imports use the `src.` prefix (`from src.io.fs import FS`).

**Agents `app/agents/<name>/`**: each agent is its own azd project (`azure.yaml`).
- `epl`: a code agent. Python Agent Framework, hosted in Foundry as a Docker container (`host: azure.ai.agent`, responses protocol). Code is in `agents/epl/src/epl/` (`main.py`, `Dockerfile`, `requirements.txt`). Its tools use AI Search (index `epl`), Storage, a Foundry vector store, and web search.
- The agent container does **not** import `app/src` directly. `agents/<name>/copy-master-src.sh` copies a chosen subset of `app/src` modules into `agents/<name>/src/<name>/src/`, which is not committed. Edit the master copy in `app/src`, then re-copy. If an agent needs a new module, add it to that script's file list.
- `agents/<name>/deploy.sh` runs `azd deploy`, then gives the agent's Entra identity Foundry User, Search Index Data Contributor and Storage Blob Data Contributor, then runs `azd ai agent show` and `azd ai agent monitor`.
- `python-stdlib`: a YAML-only prompt agent, deployed with `deploy-foundry-prompt-agent.sh`.

**Code generator**: `uv run main-generator.py gen_code_agent <name>` or `gen_prompt_agent <name>`. `AgentGenerator` renders the Jinja2 templates in `app/templates/` (`code_agent_*`, `prompt_agent_*`), using the context from `generator_config.json` (package versions, base image, CPU/memory, model deployment), into `agents/<name>/`. Generating deletes and recreates that agent directory. `gen.sh` builds the example agents `xpa` and `xca`, which are git-ignored. To change generated output, edit the templates or `generator_config.json`, not the generated files.

**Data and search config**: curated EPL data lives in `data/` (`uk_football/`, pre-vectorized `epl/`, PDFs in `documents/`). Search index schemas and named queries are in `app/config/search/`, and Cosmos indexing policies in `app/config/cosmos/`. Cosmos is optional and on the roadmap; AI Search is the primary datastore for the agent.

**Other top-level directories**: `docs/` holds the user-facing guides (getting started → deployment → post-deployment → reference app → AI development). `wrangling/` is a separate uv project used to obtain and shape the curated data. `prompts/` holds prompt and reference notes for AI tools.
