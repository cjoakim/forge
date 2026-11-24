# Deployment

Since the customer environment, and thus their requirements, are unknown
this accelerator strives to create a **"Sandbox Deployment"** containing the
Azure resources that are typical of a **Foundry-centric AI Application**.
This Sandbox environment provides a good "starter environment" for your AI project.

The deployment is "opinionated" as it contains the following Azure PaaS Services:

- Microsoft Foundry
- Microsoft Foundry Project named "epl", with the English Premier League Reference application
- Two LLM deployments in the Foundry Project for vectorization and completions
- Azure Container Registry (ACR) for the Docker-containerized Agents
- Azure Key Vault (AKV)
- Azure Data Services per standard Foundry deployment
  - Azure Storage 
  - Azure AI Search for both general-search and vector/semantic search
  - Azure Cosmos DB for tememetry and memory, optionally for application data and vectors
- Azure App Insights for Telemetry
- Azure Monitor for Telemetry collection, reporting, and alerts
- Azure firewall for IP-based Network Security
- Azure private endpoints for service-to-service communication

### Resource Names

This accelerator strives to implement the naming conventions used in the 
[Azure Cloud Adoption Framework (CAF)](https://learn.microsoft.com/en-us/azure/cloud-adoption-framework/ready/azure-best-practices/resource-naming).

Thus, every resource name derives from the **resource group name** as well
as a CAF prefix.  For example, given a resource group name of "cjoakimforge1030x"
the deployed Azure Foundry is named "aif-cjoakimforge1030x".

You choose your own resource group name, as described below.

## Deployment with ARM - Azure Resource Manager

### The ARM files

See the **app/arm** directory in this repo, and these ARM files.

```
parameters.json      <-- parameters passed to the ARM template; you edit this file
template.json        <-- the ARM template; parameterized provisioning of Azure resources
```

[ARM (Azure Resource Manager)](https://learn.microsoft.com/en-us/azure/azure-resource-manager/management/overview)
was determined to be the simplest and most reliable deployment mechanism
during the development of this accelerator.

### Firewall Rules

This deployment process generally creates the Azure PaaS services
that are available to any network, but have an IP address firewall
rules that are configured to use **your IP address**.
This lets you work with the services from your workstation.

Your IP address can be determined by running this script:
```
$ cd app/arm

./ip_address.sh my_ip
... your IP address is shown here
```

The following ARM deployment process dynamically determines your workstation
IP address and configures the PaaS service filewall rules appropriately.

### Private Endpoints

By default (`deployAgentVnet` is `true` in **parameters.json**) the deployment creates
an agent virtual network named **vnet-&lt;name&gt;** (address space 192.168.0.0/16) with two subnets:

| Subnet | Address Range | Purpose |
|---|---|---|
| snet-agents | 192.168.0.0/24 | Delegated to `Microsoft.App/environments`; the Foundry hosted agents run here (network injection) |
| snet-private-endpoints | 192.168.1.0/24 | Holds the private endpoints listed below |

Hosted agents use these private endpoints to reach the PaaS services, so that traffic stays on the
Azure backbone network instead of the public internet:

| Private Endpoint | Service | Private DNS Zone(s) |
|---|---|---|
| pe-&lt;name&gt;-foundry | Microsoft Foundry account | privatelink.cognitiveservices.azure.com, privatelink.openai.azure.com, privatelink.services.ai.azure.com |
| pe-&lt;name&gt;-search | Azure AI Search | privatelink.search.windows.net |
| pe-&lt;name&gt;-blob | Azure Storage (blob) | privatelink.blob.core.windows.net |
| pe-&lt;name&gt;-acr | Azure Container Registry | privatelink.azurecr.io |
| pe-&lt;name&gt;-cosmos | Azure Cosmos DB (NoSQL) | privatelink.documents.azure.com |

Each private DNS zone is linked to the VNet, so the services' regular hostnames
(for example `srch-<name>.search.windows.net`) resolve to private IP addresses
from inside the VNet.

The VNet also enables the Foundry project **capability host** (the Agent Service "standard setup"),
which stores agent files and vector stores in Azure Storage and AI Search, and conversation threads
in Cosmos DB, all reached privately.

The public endpoints of these services are **not** disabled. They keep the IP address firewall
rules described above, so you can still work with the services from your workstation.

To deploy without the VNet and the private endpoints, pass `--no-agent-vnet` (`-x`) to
the deployment script.  Cosmos DB and the capability host are then not created either;
hosted agents use the public endpoints, and Foundry file uploads to vector stores fail.
The VNet deployment is recommended.

### RBAC Roles and Assignments

All authentication uses Entra ID and RBAC (role-based access control); no keys are used.
AI Search and Storage are configured to be Entra-only.

The **deployer** is the Entra ID user who runs the deployment script, by default.
Use `--deployer-id <object-id>` to grant the roles to another user, or `--deployer-id none` to skip them.

The deployment grants these Entra ID roles:

| Principal | Scope | Roles |
|---|---|---|
| Foundry account managed identity | Key Vault | Key Vault Secrets Officer, Key Vault Contributor |
| Foundry project (epl) managed identity | Container Registry | AcrPull, to pull the hosted agent Docker images |
| Foundry project (epl) managed identity | Key Vault | Key Vault Secrets User |
| Foundry project (epl) managed identity | App Insights | Monitoring Metrics Publisher |
| Foundry project (epl) managed identity | Cosmos DB | Cosmos DB Operator; Cosmos DB Built-in Data Contributor on the `enterprise_memory` database (VNet deployments only) |
| Deployer | Container Registry | AcrPush, to push the hosted agent Docker images |
| Deployer | AI Search | Search Service Contributor, Search Index Data Contributor |
| Deployer | Storage | Storage Blob Data Contributor |
| Deployer | Key Vault | Key Vault Secrets Officer |
| Deployer | App Insights | Monitoring Metrics Publisher |
| Deployer | Log Analytics | Log Analytics Reader |

Other roles are granted after the deployment:

- **Other users:** `./rg.sh user_roles_assign <resource-group> [user-upn-or-object-id]`, run from
  **app/**, grants a user the data-plane and management roles needed to work with the
  Forge resources from a laptop (`az login` / `DefaultAzureCredential`). You need Owner, or User
  Access Administrator, on the resource group to run it.
- **Hosted agents:** each hosted agent has its own Entra ID identity.  The agent's **deploy.sh**
  (for example **app/agents/epl/deploy.sh**) grants that identity **Foundry User** on the project,
  **Search Index Data Contributor** on AI Search, and **Storage Blob Data Contributor** on Storage.
  These can be changed with the `FORGE_AGENT_ROLE`, `FORGE_AGENT_ROLE_SCOPE`,
  `FORGE_AGENT_SEARCH_ROLE`, and `FORGE_AGENT_STORAGE_ROLE` settings.

New role assignments can take several minutes to propagate.

### Edit the ARM parameters.json file for your deployment

The deployment scripts set the resource group, base name, location, and firewall IPs
in a copy of **parameters.json**, so you don't need to edit these values.

**NOTE: Please remove all references to the following values in parameters.json.  Change them to email address and name.**
- christopher.joakim@gmail.com
- Chris Joakim
- cjoakim

Also edit the **embeddingModelDeployment** and **chatModelDeployment** model names and configuration
as necessary.  However, be aware that the pre-vectorized dataset in this repository uses
the **text-embedding-ada-002** model.  Thus, you will have to re-vectorize the data if you 
choose another vectorization model.


### The Deployment Scripts

```
deploy-arm.ps1       <-- For Windows
deploy-arm.sh        <-- For macOS
```

### Get your IP Address

```
$ cd app/arm

$ mkdir tmp

$ ./ip_address.sh my_ip

222.219.116.10
```

This will display your workstation/laptop IP address.  This is used in the next step.

For Windows 11 users, execute the corresponding PowerShell (*.ps1) scripts in these instructions.

### Execute the ARM deployment

The following output shows a deployment to resource group **cjoakimforge1030x**
to region **southcentralus** with a firewall rule on a CIDR block of IP addresses
corresponding to IP address **222.219.116.10** obtained above.

**Please change the command-line argument value 'cjoakimforge1030x' to YOUR resource group name.**

You should also check the availability of Foundry LLM models in your prefferred **region**.
In this example "southcentralus" was chosen because it is both near my location
and has sufficient model availability.

```
$ ./deploy-arm.sh -g cjoakimforge1102b -l southcentralus -a 222.219.116.0/24
```

You should see output like the following.  The deployment typically takes 15-30 minutes to execute.

The script will validate the ARM files, then prompt you to ask if you'd
like to execute the deployment.  The deployment start and finish times
will be displayed.

```
Subscription:     ... redacted ...
Resource Group:   cjoakimforge1102b
Location:         southcentralus
Name:             cjoakimforge1102b
Foundry:          aif-cjoakimforge1102b
AI Search:        srch-cjoakimforge1102b
Storage:          stcjoakimforge1102b
Project:          epl
Allowed IPs:      222.219.116.0/24
Agent VNet:       vnet-cjoakimforge1102b
Cosmos DB:        cosmos-cjoakimforge1102b
Registry:         crcjoakimforge1102b
Deployer ID:     ... redacted ...
API Management:   (not deployed; use --with-apim)
Key Vault:        kv-cjoakimforge1102b
Deployment Name:  forge-arm-20261102-154215
Parameters File:  tmp/parameters-cjoakimforge1102b.json
Mon Nov  2 15:42:15 EST 2026
Ensuring the resource group exists...
Ensuring the Microsoft.App, Microsoft.ContainerService, and Microsoft.DocumentDB providers are registered...
Validating the deployment...
Validation succeeded; see tmp/validate.json

Do you want to deploy? (y/n): y
Proceeding...
Creating the deployment (this typically takes 15-30 minutes)...
Mon Nov  2 15:42:49 EST 2026
Deployment Succeeded; see tmp/deployment.json
azurE_AGENT_VNET_NAME=vnet-cjoakimforge1102b
azurE_AI_SEARCH_NAME=srch-cjoakimforge1102b
azurE_AI_SEARCH_URL=https://srch-cjoakimforge1102b.search.windows.net
azurE_API_MANAGEMENT_GATEWAY_URL=
azurE_APPLICATION_INSIGHTS_NAME=appi-cjoakimforge1102b
azurE_CONTAINER_REGISTRY_ENDPOINT=crcjoakimforge1102b.azurecr.io
azurE_COSMOSDB_NAME=cosmos-cjoakimforge1102b
azurE_FOUNDRY_NAME=aif-cjoakimforge1102b
azurE_FOUNDRY_PROJECT_URL=https://aif-cjoakimforge1102b.services.ai.azure.com/api/projects/epl
azurE_KEY_VAULT_URI=https://kv-cjoakimforge1102b.vault.azure.net/
azurE_LOG_ANALYTICS_WORKSPACE_NAME=log-cjoakimforge1102b
azurE_STORAGE_ACCOUNT_NAME=stcjoakimforge1102b
azurE_STORAGE_ACCOUNT_URL=https://stcjoakimforge1102b.blob.core.windows.net/
Mon Nov  2 16:05:10 EST 2026
```

In the event of a transient deployment error, you can re-execute the same deployment
since ARM deployments are **idempotent**.
See https://learn.microsoft.com/en-us/answers/questions/5680704/how-does-arm-handle-idempotency

Security Auditor Notes: The above IP address is a fictitious value, and the cjoakimforge1102b
resource group no longer exists. There are no keys displayed in this output, as all 
authentication used by these PaaS services is based on RBAC with Entra.

### Visit Azure Portal

Visually validate the deployment in Azure Portal; confirm that the expected PaaS services
are present in the resource group.

---

## Next Steps

See the [Post-Deployment](post-deployment.md) documentation.
