# Post-Deployment

The previous page on [Deployment](docs/deployment.md) deployed the 
Azure PaaS services into your Resource Group in your Azure Subscription.
The instructions on this page further configures and populates them.

Specifically, these steps are:

- User Role Assignments for RBAC
- Setup your localhost environment variables
- Create, Populate, and Test the Azure AI Search Indexes
- Check Access to your Azure Container Registry (ACR)
- Check Access to your Azure Blob Storage
- Create and Populate your Foundry Vector Store(s)
- See your Cosmos DB enterprise_memory database

--- 

## User Role Assignments 

This accelerator uses **Role Based Access Control (RBAC)**, rather than keys, as this
is an Azure best-practice.  The ARM deployment created the PaaS services, but they
didn't assign complete access to **you**.  Therefore, you need to execute the following
script to grant access to yourself, or someone else:

Format:
```
./rg.sh user_roles_assign [resource-group-name] [optional-user-upn-or-object-id]
```

Example:
```
cd app/
./rg.sh user_roles_assign cjoakimforge1102b
```

Output:
```
Subscription:     ... redacted ...
Resource Group:   cjoakimforge1102b
User:             ... redacted ...
Principal ID:     ... redacted ...

crcjoakimforge1102b (Microsoft.ContainerRegistry/registries)
  created  AcrPush on crcjoakimforge1102b
kv-cjoakimforge1102b (Microsoft.KeyVault/vaults)
  created  Key Vault Secrets Officer on kv-cjoakimforge1102b
stcjoakimforge1102b (Microsoft.Storage/storageAccounts)
  created  Storage Blob Data Contributor on stcjoakimforge1102b
log-cjoakimforge1102b (Microsoft.OperationalInsights/workspaces)
  created  Log Analytics Reader on log-cjoakimforge1102b
srch-cjoakimforge1102b (Microsoft.Search/searchServices)
  created  Search Service Contributor on srch-cjoakimforge1102b
  created  Search Index Data Contributor on srch-cjoakimforge1102b
aif-cjoakimforge1102b (Microsoft.CognitiveServices/accounts, AIServices)
  created  Azure AI User on aif-cjoakimforge1102b
  created  Azure AI Project Manager on aif-cjoakimforge1102b
  created  Cognitive Services User on aif-cjoakimforge1102b
appi-cjoakimforge1102b (Microsoft.Insights/components)
  created  Monitoring Metrics Publisher on appi-cjoakimforge1102b

10 role assignment(s) created, 0 already existed
New assignments can take several minutes to take effect.
```

The above example determines your identity in the script, so you don't need to provide it.
However, to assign RBAC to someone else, you can execute this version of the command:
```
./rg.sh user_roles_assign cjoakimforge1102b someone.else@somehost.com
```

Windows users: Execute the **rg.ps1** script instead.


---

## Setup your localhost environment variables

Note: If you're not yet familiar with **environment variables**, this [Wikipedia page](https://en.wikipedia.org/wiki/Environment_variable) describes them.

This accelerator uses environment variables in several places:
- Your workstation/laptop operating system (OS)
- azd environments running locally on your workstation/laptop
- azd deployments pushed to Azure Foundry

Since Forge uses Entra (aka - *keyless**) authentication, the nature of
the environment variables are mostly PaaS service URLs rather than secret keys.

### Create your app/.env file

This file is not present in the Git repo; it is intentionally [git ignored](https://docs.github.com/en/get-started/git-basics/ignoring-files) as it may contain values that should not be stored in a source-control system.

You can copy the **app/dotenv-example** to the **app/.env** file to get started.
This file must then be edited as described below.

#### Note: The importance of your .env file

**Consider the .env file to be the "master" set of environment variables for this accelerator**.
These same values are used in several ways:

1) The python scripts in the app/ directory
   - These scripts use the **python-dotenv** library to read the environment from the .env file
   - These scripts are in the filename pattern: main-xxx.py
2) Bash and PowerShell scripts in the app directory
   - These scripts use your operating system (OS) environment variables
   - The **set-os-env.xxx** scripts set your OS environment variables from the contents of your .env file
3) azd  
   - The azd CLI program has its own sets of environment variables
   - The **set-azd-env.xxx** scripts set your azd environment variables from the contents of your .env file

### Execute the provided scripts to get your deployed Names and URLs

The **rg.ps1** and **rg.sh** scripts in this accelerator execute several **CLI functions**
related to your resource group.  The list of these is shown here: 

```
./rg.sh show      <resource-group-name>
./rg.sh export    <resource-group-name>
./rg.sh show-user
./rg.sh user_roles_assign <resource-group-name> [user-upn-or-object-id]
./rg.sh update-firewall-ip <resource-group-name> [foundry-account-name] [-a <ip[,ip...]>] [--remove-others]
./rg.sh rg-ownership [email]
./rg.sh export-rg-urls <resource-group-name>
./rg.sh get-ai-project-id [resource-group-name]
./rg.sh my-ip
./rg.sh show-foundry-project [resource-group-name]
```

Excute the **./rg.sh export-rg-urls [your-resource-group-name]** script 
which will scan your resource group and create a file in your tmp/ directory
with a list of the many URLs in the deployment.  The output file has the 
filename pattern: "tmp/rg-resources-rrr.json** where rrr is your given resource
group name value.

Open both the rg-resources JSON file and the app/.env file in your editor.
Update all of the values above "FOUNDRY_PROJECT_ENDPOINT" in the .env file
per the output of the rg-resources JSON file.

### FOUNDRY_PROJECT_ENDPOINT

Obtaining this value can be done via scripts in this accelerator app/ directory.
However, you first have to set your initial OS environment variables
in your current Terminal with either of these scripts:

```
cd app

source ./set-os-env.sh           # macOS or Linux

.\set-os-env.ps1                 # Windows 11
```

Then run the following script to get your value for FOUNDRY_PROJECT_ENDPOINT.

```
./rg.sh get-ai-project-id        # macOS or Linux
.\rg.sh get-ai-project-id        # Windows 11
```

Then copy and paste the value into the FOUNDRY_PROJECT_ENDPOINT line in your .env file.

Remember that if you change an values in your .env file, then you should also
run the set-os-env.xxx script.  The set-azd-env.xxx scripts will be discussed later.

---

## Create, Populate, and Test the Azure AI Search Indexes

The ARM deployment process created your Azure AI Search instance, but
it did not create or populate any indexes in it.  That's what we'll do here.

See the **app/config/search/epl_index.json** and **app/config/search/cities_vector_index.json**
files which define the indexes.

Ensure that you're in the app/ directory, in the same terminal window where you just
ran the above set-os-env.sh or set-os-env.ps1 script.

The app/ directory contains two scripts related to Azure AI Search: **search.sh** and **search.ps1**.
Execute them as shown below:

### Bash
```
./search.sh recreate-epl
./search.sh recreate-cities
```

### Windows PowerShell
```
.\search.ps1 recreate-epl
.\search.ps1 recreate-cities
```

These commands delete, recreate, and populate the **epl** and **cities** indexes
in your Azure AI Search instance, per your .env file, using the curated and pre-vectorized
data in the data/ directory of this repository.

The **epl index** is recreated and loaded in batches of 100 documents each.
This data includes **teams, stadiums, matches (schedule), and players**.
Each document contains a **doctype** attribute that identifies it as one of these four types.
You should see output that ends like this:
```
1068 documents were in the list to load to index epl in account https://xxx.search.windows.net
done
```

The **cities index** is recreated and loaded similarly.
This data contains vectorized descriptions of cities in England for semantic search.
You should see output that ends like this:
```
99 documents were in the list to load to index cities in account https://xxx.search.windows.net
done
```

### Execute example searches to validate each index

File **app/config/search/named_searches.json** in this repository defines several **"named searches"**
that are intended for ease of use from the command line.

For example, two named searches are **all_documents** and **matches_at_arsenal**.  The JSON
object at each key is passed to Azure Search as the query parameter for these named searches.
```
{
  "all_documents": {
    "count": true,
    "search": "*",
    "orderby": "id"
  },
  "matches_at_arsenal": {
    "count": true,
    "search": "doctype:match AND lc_home_team:arsenal",
    "filter": "matchday gt 30",
    "select": "id,lc_home_team,lc_away_team,date,matchday",
    "orderby": "date",
    "queryType": "full"
  },
  ...
```

#### epl index matches_at_arsenal

CLI command:
```
cd app/

uv run main-search.py search_index epl matches_at_arsenal config/search/named_searches.json
```

Tail of Output:
```
...
      {
        "@search.score": 4.5776196,
        "id": "894f0c4e-6d73-4a72-87a7-633524c5caf7",
        "lc_home_team": "arsenal",
        "lc_away_team": "brighton hove",
        "date": "2027-05-30",
        "matchday": 38
      }
    ]
  }
}
file written: tmp/search_result.json
```

#### cities index 

This executes a semantic search to find the cities most similar to Bristol, England
per their vectorized descriptions.

CLI command:
```
cd app/

uv run main-search.py search_index cities vector_search_bristol config/search/named_searches.json
```

Tail of Output:
```
...
      {
        "@search.score": 0.015625,
        "id": "1fb70357-dc50-49f1-a9b8-6ed253aa84a8",
        "city_name": "Liverpool",
        "country": "England",
        "population": 508961,
        "notes": "Liverpool is a major port city in Merseyside founded as a borough in 1207 on the River Mersey. It became one of the world's busiest ports in the 18th and 19th centuries, heavily involved in Atlantic trade including the transatlantic slave trade, and was the departure point for millions of emigrants to the Americas. Its maritime waterfront, including the Pier Head's 'Three Graces', is a UNESCO-recognised heritage area. Liverpool is world-famous as the birthplace of the Beatles and has produced more UK number-one hit singles than any other city. Post-industrial decline was followed by major regeneration, cemented by its role as European Capital of Culture in 2008. The city is home to two Premier League clubs, Liverpool F.C. and Everton F.C., among England's most successful and storied football institutions."
      }
    ]
  }
}
file written: tmp/search_result.json
```

---

## Check Access to your Azure Container Registry (ACR)

The Python Agents will be deployed to Microsoft Foundry, via ACR.

You can test your access to your ACR as follows, where xxx is the name of your ACR.
```
./acr.sh list         xxx.azurecr.io
.\acr.ps1 list        xxx.azurecr.io
```

Output:
```
ACR xxx.azurecr.io has no repositories
```

This output confirms that you have access to your ACR, but there are no Docker containers there yet.

--- 

## Check Access to your Azure Blob Storage

Create a container, upload a file, and download it.
Commands and abbreviated output shown below.

```
cd app/

uv run main-storage.py check_env
Env.azure_storage_account_url(): https://xxx.blob.core.windows.net/

uv run main-storage.py create_container agents
...
Container 'agents' created successfully.

uv run main-storage.py upload_file ../data/documents/FIFA-Laws-of-the-Game-2004.pdf agents
...
Upload result: True


uv run main-storage.py download_blob_to_file agents FIFA-Laws-of-the-Game-2004.pdf
...
Download result: (True, ....
```

---

## Create and Populate your Foundry Vector Store(s)

Foundry **Vector Stores** use the built-in **File Search Tool** and provide
the ability to search your uploaded files in a semantic way.

You can read about this functionality here: 
_ https://learn.microsoft.com/en-us/azure/foundry/agents/concepts/vector-stores 
- https://learn.microsoft.com/en-us/azure/foundry/agents/how-to/tools/file-search?pivots=python

### List the Vector Store in your Foundry Project

First, confirm that you can access your Foundry Project and list the current vector stores.
It should return an empty JSON list.

CLI Command:
```
cd app/
uv run main-foundry.py list_vector_stores
```

Output:
```
vector stores: []
```

### Create the epl Vector Store

CLI Command:
```
uv run main-foundry.py create_vector_store epl
```

Output:
```
vector store: {
    "id": "vs_0hAfIm5gnuVZOFYUUPBdqciE",
    "created_at": 1793802212,
    "file_counts": {
        "cancelled": 0,
        "completed": 0,
        "failed": 0,
        "in_progress": 0,
        "total": 0
    },
    "last_active_at": 1793802212,
    "metadata": {},
    "name": "epl",
    "object": "vector_store",
    "status": "completed",
    "usage_bytes": 0,
    "expires_after": null,
    "expires_at": null
}
```

List your Vector Stores again:
```
uv run main-foundry.py list_vector_stores
```

Output:
```
vector stores: [
    {
        "id": "vs_0hAfIm5gnuVZOFYUUPBdqciE",
        "created_at": 1793802212,
        "file_counts": {
            "cancelled": 0,
            "completed": 0,
            "failed": 0,
            "in_progress": 0,
            "total": 0
        },
        "last_active_at": 1793802212,
        "metadata": {},
        "name": "epl",
        "object": "vector_store",
        "status": "completed",
        "usage_bytes": 0,
        "expires_after": null,
        "expires_at": null
    }
]
```

The Vector Store **id** ("vs_0hAfIm5gnuVZOFYUUPBdqciE") will be used in the next step.

### Upload Files to the Vector Store

CLI Command:
```
uv run main-foundry.py upload_file_to_vector_store vs_0hAfIm5gnuVZOFYUUPBdqciE ../data/documents/FIFA-Laws-of-the-Game-2004.pdf
```

Output:
```
abs_path: ...redacted.../data/documents/FIFA-Laws-of-the-Game-2004.pdf
vector_store_file type: <class 'openai.types.vector_stores.vector_store_file.VectorStoreFile'>
result: {
    "id": "assistant-NRG376DmaCbLufrwqQb8bf",
    "created_at": 1793803069,
    "last_error": null,
    "object": "vector_store.file",
    "status": "completed",
    "usage_bytes": 133079,
    "vector_store_id": "vs_0hAfIm5gnuVZOFYUUPBdqciE",
    "chunking_strategy": {
        "static": {
            "chunk_overlap_tokens": 400,
            "max_chunk_size_tokens": 800
        },
        "type": "static"
    }
}
```

Also upload the TM2040-PL-Handbook-and-Collateral-2026-27.pdf file, as shown below:

```
uv run main-foundry.py upload_file_to_vector_store vs_0hAfIm5gnuVZOFYUUPBdqciE ../data/documents/
TM2040-PL-Handbook-and-Collateral-2026-27.pdf

abs_path: ...redacted.../data/documents/TM2040-PL-Handbook-and-Collateral-2026-27.pdf
vector_store_file type: <class 'openai.types.vector_stores.vector_store_file.VectorStoreFile'>
result: {
    "id": "assistant-HUUXvnBjMCL7DjHyHCXeF8",
    "created_at": 1793803415,
    "last_error": null,
    "object": "vector_store.file",
    "status": "completed",
    "usage_bytes": 3284309,
    "vector_store_id": "vs_0hAfIm5gnuVZOFYUUPBdqciE",
    "chunking_strategy": {
        "static": {
            "chunk_overlap_tokens": 400,
            "max_chunk_size_tokens": 800
        },
        "type": "static"
    }
}
```

### Visit your Azure Portal Foundry Project UI to see Knowledge (Foundry IQ)

In the **Knowledge --> Indexes** page you should see the **epl** index.

![foundry-knowledge-epl-vector-store](./docs/img/foundry-knowledge-epl-vector-store.png)

And when you click into epl, you should see the two files you uploaded.

![foundry-knowledge-epl-vector-store-files](./docs/img/foundry-knowledge-epl-vector-store-files.png)

### Add the AZURE_FOUNDRY_VECTOR_STORE_ID to your app/.env file

```
AZURE_FOUNDRY_VECTOR_STORE_ID="vs_0hAfIm5gnuVZOFYUUPBdqciE"
```

---

## See your Cosmos DB enterprise_memory database

Your Cosmos DB account should already contain an **enterprise_memory** database with
several containers as shown below.
These were created by the ARM deployment process, and will be used by your Agents.

![cosmosdb-enterprise-memory-db](./docs/img/cosmosdb-enterprise-memory-db.png)

### Future enhancement to the Forge Accelerator for Cosmos DB

This initial version of this accelerator doesn't further demonstrate Cosmos DB.
However, this is planned for version 2 as Cosmos DB has excellent vector search
functionality with the DiskANN algorithm.  In the meantime, you can read about 
DiskANN here: https://devblogs.microsoft.com/cosmosdb/azure-cosmos-db-vector-search-with-diskann-part-1-full-space-search/

The repository already contains these Cosmos DB files/classes that you may wish to use:
```
app/config/cosmos/cosmosdb_nosql_default_index_policy.json
app/config/cosmos/cosmosdb_nosql_vector_index_policy_diskann.json
app/cosmos.ps1
app/cosmos.sh
app/main-cosmos-nosql.py
app/src/db/cosmos_nosql_util.py
```

---

## Next Steps

See the [Using the Reference Application](reference-app.md) documentation.
