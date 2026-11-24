# AI Development and Deployment

---

## Developing and Deploying Agents

In the app directory - set the OS and AZD environment variables.

```
source ./set-os-env.sh

./set-azd-env.sh agents/c1
```


```
cd agents/c1

azd ai agent run c1 --environment c1

in c1 dir:
azd ai agent invoke c1 'what is the capital of NC?' --local --environment c1
```

Ask the code interpreter what libs it has.
```
Use the code interpreter tool to run exactly this Python code,
then return its complete printed output verbatim in a code block.
Do not summarize, truncate, or omit any lines.

import importlib.metadata as m, sys
print(sys.version)
for name, ver in sorted({(d.metadata["Name"], d.version) for d in m.distributions()}, key=lambda x: x[0].lower()):
  print(f"{name}=={ver}")
```

```
3.10.12 (main, Sep  7 2023, 16:52:42) [GCC 11.3.0]
aiohttp==3.8.4
aiosignal==1.3.1
attrs==23.1.0
Brotli==1.0.9
cachetools==5.3.1
charset-normalizer==3.2.0
colorama==0.4.6
comm==0.1.4
contourpy==1.1.1
cycler==0.11.0
filelock==3.12.0
fonttools==4.41.0
idna==3.4
kiwisolver==1.4.4
MarkupSafe==2.1.2
matplotlib==3.7.1
multidict==6.0.4
numpy==1.26.4
packaging==23.1
pandas==2.1.1
Pillow==10.0.0
pyparsing==3.1.1
python-dateutil==2.8.2
pytz==2023.3
requests==2.31.0
scipy==1.11.1
six==1.16.0
soupsieve==2.4
sympy==1.12
typing_extensions==4.7.1
urllib3==2.0.4
yarl==1.9.2
zipp==3.16.2
```

- https://learn.microsoft.com/en-us/azure/foundry/agents/how-to/tools/file-search?pivots=python
- https://learn.microsoft.com/en-us/azure/foundry/agents/concepts/capability-hosts#configure-capability-hosts

```
$ ./deploy-arm.sh -g cjoakimforge1030x -l southcentralus -a 113.213.116.0/24
Subscription:     ...
Resource Group:   cjoakimforge1030x
Location:         southcentralus
Name:             cjoakimforge1030x
Foundry:          aif-cjoakimforge1030x
AI Search:        srch-cjoakimforge1030x
Storage:          stcjoakimforge1030x
Project:          epl
Allowed IPs:      113.213.116.0/24
Agent VNet:       vnet-cjoakimforge1030x
Cosmos DB:        cosmos-cjoakimforge1030x
Registry:         crcjoakimforge1030x
Deployer ID:      b7ac24c8-1b9b-4210-a696-cf6f8111777b
API Management:   (not deployed; use --with-apim)
Key Vault:        kv-cjoakimforge1030x
Deployment Name:  forge-arm-20261030-140054
Parameters File:  tmp/parameters-cjoakimforge1030x.json
Fri Oct 30 14:00:54 EDT 2026
Ensuring the resource group exists...
Ensuring the Microsoft.App, Microsoft.ContainerService, and Microsoft.DocumentDB providers are registered...
Validating the deployment...
Validation succeeded; see tmp/validate.json
Do you want to deploy? (y/n): y
Proceeding...
Creating the deployment (this typically takes 15-30 minutes)...
Fri Oct 30 14:03:07 EDT 2026
Deployment Succeeded; see tmp/deployment.json
azurE_AGENT_VNET_NAME=vnet-cjoakimforge1030x
azurE_AI_SEARCH_NAME=srch-cjoakimforge1030x
azurE_AI_SEARCH_URL=https://srch-cjoakimforge1030x.search.windows.net
azurE_API_MANAGEMENT_GATEWAY_URL=
azurE_APPLICATION_INSIGHTS_NAME=appi-cjoakimforge1030x
azurE_CONTAINER_REGISTRY_ENDPOINT=crcjoakimforge1030x.azurecr.io
azurE_COSMOSDB_NAME=cosmos-cjoakimforge1030x
azurE_FOUNDRY_NAME=aif-cjoakimforge1030x
azurE_FOUNDRY_PROJECT_URL=https://aif-cjoakimforge1030x.services.ai.azure.com/api/projects/epl
azurE_KEY_VAULT_URI=https://kv-cjoakimforge1030x.vault.azure.net/
azurE_LOG_ANALYTICS_WORKSPACE_NAME=log-cjoakimforge1030x
azurE_STORAGE_ACCOUNT_NAME=stcjoakimforge1030x
azurE_STORAGE_ACCOUNT_URL=https://stcjoakimforge1030x.blob.core.windows.net/
Fri Oct 30 14:25:09 EDT 2026
```
