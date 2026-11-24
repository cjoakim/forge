# Using the Reference Application

In addition to the curated data that you've already loaded into Azure AI Search,
this accelerator contains two deployable Agents for your use.  These are:

- **Python Standard Library Agent**
  - A simple "Low-Code" YAML-based prompt agent
  - See directory **app/agents/python-stdlib/**, file **azure.yaml**
- **EPL Agent**
  - A "Pro-Code" Docker-containerized Agent implemented in Python
  - See directory **app/agents/epl/**

---

## Setup 

```
az login
```

---

## The YAML-based Python Standard Library Agent 

This Agent doesn't relate to the EPL reference application.
It's just intended as an example of a simple YAML-based prompt Agent.

### The YAML Code

The entire YAML code is shown here.  Note that it provides a description,
a model deployment name (gpt-4.1-mini), instructions, an example of
the desired response format, and a list of the built-in Foundry Tools
that the Agent may use (i.e. - web_search and code_interpreter).

```
id: python-stdlib:1
name: python-stdlib
version: "1"
description: "Provides solutions using the Python 3 standard library."
definition:
  kind: prompt
  model: gpt-4.1-mini
  instructions: |
    You are an expert on the python 3 standard library.

    You can:
    - Recommend a standard library to use for a given use-case and provide sample code

    Responses:
    - Respond in the following json list format
    [
      { "standard-library-name": "aaa", "sample-code": "bbb" }, 
      { "standard-library-name": "xxx", "sample-code": "yyy" }, 
    ]
    - Respond with an empty json list if there are no suitable standard libraries for the given use-case
    [
    ]
  tools:
    - type: web_search
    - type: code_interpreter
      container:
        type: auto
draft: false
status: active
```

### Deploying the python-stdlib YAML agent to your Foundry Project 

We'll deploy it with an **az rest** HTTP POST in the **deploy-foundry-prompt-agent.sh** or
**deploy-foundry-prompt-agent.ps1** script.

Command-line format:
```
./deploy-foundry-prompt-agent.sh <foundry-name> <foundry-project-name> <api-version> <path-to-azure.yaml> 
```

Example:
```
cd app/

./deploy-foundry-prompt-agent.sh aif-cjoakimforge1102b epl 2025-11-15-preview agents/python-stdlib/azure.yaml
```

Output:
```
agent:   python-stdlib
url:     https://aif-cjoakimforge1102b.services.ai.azure.com/api/projects/epl/agents/python-stdlib/versions?api-version=2025-11-15-preview
body:    tmp/agent-python-stdlib-body.json
{
  "agent_guid": "... redacted ...",
  "blueprint": {
    "client_id": "... redacted ...",
    "principal_id": "... redacted ..."
  },
  "blueprint_reference": {
    "blueprint_id": "python-stdlib-0915e",
    "type": "ManagedAgentIdentityBlueprint"
  },
  "created_at": 1793724142,
  "definition": {
    "instructions": "You are an expert on the python 3 standard library.\n\nYou can:\n- Recommend a standard library to use for a given use-case and provide sample code\n\nResponses:\n- Respond in the following json list format\n[\n  { \"standard-library-name\": \"aaa\", \"sample-code\": \"bbb\" }, \n  { \"standard-library-name\": \"xxx\", \"sample-code\": \"yyy\" }, \n]\n- Respond with an empty json list if there are no suitable standard libraries for the given use-case\n[\n]\n",
    "kind": "prompt",
    "model": "gpt-4.1-mini",
    "tools": [
      {
        "type": "web_search"
      },
      {
        "container": {
          "type": "auto"
        },
        "type": "code_interpreter"
      }
    ]
  },
  "description": "Provides solutions using the Python 3 standard library.",
  "draft": false,
  "id": "python-stdlib:1",
  "instance_identity": {
    "client_id": "... redacted ...",
    "principal_id": "... redacted ..."
  },
  "metadata": {},
  "name": "python-stdlib",
  "object": "agent.version",
  "status": "active",
  "version": "1"
}
done
```

The above output indicates success, version 1 of the agent was deployed.

### Using the python-stdlib YAML Agent in the Foundry Project Playground

In your browser, navigate to the **Agents tab** of your **Microsoft Foundry Project**.
This UI allows you to interact with your agent as shown in the screen-shot below:

![python-stdlib-playground](./docs/img/python-stdlib-playground.png)

Note that the JSON response data format is as specified in the YAML.

### Invoking the python-stdlib Agent with Python Code 

As with the Azure AI Search client, as discussed on the Post-Deployment page,
the app/ directory contains a main-xxx.py CLI program to invoke the Agents.
The name of the program is **main-foundry.py**.

It, too, uses a configuration file to simplify the CLI args used in invoking
an Agent by passing in a "named" Agent call such as "python-stdlib-uuid".
See file **app/config/invoke-agents-config.json**, it looks like this:
```
{
  "python-stdlib-uuid": {
    "agent_name": "python-stdlib",
    "agent_type": "prompt",
    "user_message": "How can I create a globally unique identifier?"
  },
  ...
```

Therefore, main-foundry.py can be invoked as follows to ask about how to
create a globally unique identifier with the python standard library.

CLI command:
```
cd app/
uv run main-foundry.py invoke_agent config/invoke-agents-config.json python-stdlib-uuid
```

Output:
```
agent config: {
    "agent_name": "python-stdlib",
    "agent_type": "prompt",
    "user_message": "How can I create a globally unique identifier?"
}
invoking prompt agent: python-stdlib
project_client: <azure.ai.projects._patch.AIProjectClient object at 0x10a948ec0>
user_message: How can I create a globally unique identifier?
response id: resp_0ad09170662b166c006aea3f49d1c48197b8b22d64149549b1, status: completed
usage: input_tokens: 588, output_tokens: 38
response text:
[
  {
    "standard-library-name": "uuid",
    "sample-code": "import uuid\nunique_id = uuid.uuid4()\nprint(unique_id)"
  }
]
```

---

## The Python-based EPL (English Premier League) Agent 

This is a more complex "pro-code" Agent implemented with Python and
deployed with the **azd** CLI tool as a **Docker** container.
The Agent uses several different **tools** that are built-in to Microsoft Foundry.

### azd and azd environments 

[azd is the Azure Developer CLI](https://learn.microsoft.com/en-us/azure/developer/azure-developer-cli/).
It can accelerate your path from a local development environment to Azure deployment.
It has excellent functionality for developing and deploying Foundry Agents, therefore
it is featured in this accelerator.

azd has its own concept of "environments" that are similar to, but not the same as,
OS environment variables.  You can have a named environment for each of your Agents.
See https://learn.microsoft.com/en-us/azure/developer/azure-developer-cli/environments-overview

This accelerator contains scripts that automate the creation and updating of these
named azd environments; these are **set-os-env.sh** and **set-os-env.ps1** as demonstrated below.

```
cd app/

source ./set-os-env.sh

./set-azd-env.sh agents/epl
```

The command above creates an azd environment named **epl**.

### Start the Python Agent locally 

The following starts the epl Agent with the environment also named epl.

```
cd agents/epl

azd ai agent run epl --environment epl
```

Output:
```
Detected python project. Start command: python main.py
Installing dependencies (requirements.txt)...
  ✓ Dependencies installed (requirements.txt)
Starting agent on http://localhost:8088 (Ctrl+C to stop)

epl agent main()...
...
```

The **azd ai agent run** command will start the Agent at **http://localhost:8088** 
and open your default browser to a web UI at **http://127.0.0.1:8087/**.
There, you can interact with the agent with your browser as shown below.

![localhost-agent-playground](./docs/img/localhost-agent-playground.png)

```
./set-azd-env.sh agents/epl
deleting azd environment epl in agents/epl ...

Remove an environment (azd env remove)
Azure resources are not deleted when running 'azd env remove'. To delete Azure resources, run 'azd down' instead.


SUCCESS: Environment 'epl' was removed.
creating azd environment epl in agents/epl ...
? Set new environment 'epl' as default environment? Yes

New environment 'epl' created and set as default
setting 26 environment variables from /Users/cjoakim/github/forge/app/.env in azd environment epl ...
  AZURE_AI_SEARCH_NAME
  AZURE_AI_SEARCH_REGION
  AZURE_AI_SEARCH_URL
  AZURE_AI_SEARCH_VERSION
  AZURE_CONTAINER_REGISTRY_ENDPOINT
  AZURE_FOUNDRY_NAME
  AZURE_FOUNDRY_PROJECT_NAME
  AZURE_FOUNDRY_PROJECT_URL
  AZURE_FOUNDRY_REGION
  AZURE_FOUNDRY_URL
  AZURE_REGION
  AZURE_RESOURCE_GROUP
  AZURE_STORAGE_ACCOUNT_NAME
  AZURE_STORAGE_ACCOUNT_URL
  AZURE_SUBSCRIPTION_ID
  FOUNDRY_PROJECT_ENDPOINT
  AZURE_AI_PROJECT_ID
  FORGE_AGENT_CPU
  FORGE_AGENT_MAX_REPLICAS
  FORGE_AGENT_MEMORY
  FORGE_AGENT_MIN_REPLICAS
  FORGE_AGENT_ROLE_SCOPE
  FORGE_AGENT_ROLE
  FORGE_AGENT_SEARCH_ROLE
  FORGE_AGENT_SHOW_LOGS
  FORGE_AGENT_STORAGE_ROLE
list of values in azd environment epl in directory agents/epl
```





---

## Next Steps

See the [AI Development and Deployment](ai-development.md) documentation.
