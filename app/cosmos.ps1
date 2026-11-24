# Azure Cosmos DB for NoSQL operations, using the az CLI.
#
# The first arg is the function; the second is the Cosmos DB account name
# (e.g. cosmos-cjoakimforge1030x). Some functions then take a database name and a container
# name. The last arg, optional, is the resource group, which defaults to $env:AZURE_RESOURCE_GROUP.
#
# show_account:         shows the account, writing its JSON to
#                       tmp\cosmos-account-<account-name>.json
# enable_vector_search: enables Vector Search for NoSQL API (the EnableNoSQLVectorSearch
#                       capability) on the account, keeping its other capabilities, since
#                       --capabilities replaces the whole list. The capability can't be
#                       disabled once enabled, and can take up to 15 minutes to take effect.
# list_databases:       lists the account's databases
# show_database:        shows a database, writing its JSON to
#                       tmp\cosmos-database-<account-name>-<database-name>.json
# list_containers:      lists a database's containers, with their partition key paths, whether
#                       they have a vector embedding policy, and their default TTL
# show_container:       shows a container, including its indexing and vector embedding
#                       policies, writing its JSON to
#                       tmp\cosmos-container-<account-name>-<database-name>-<container-name>.json
# load_reference_data:  deletes then reloads the Reference App data (the epl and cities
#                       containers of the forge database) using main-cosmos-nosql.py. It takes
#                       no other args; the account comes from AZURE_COSMOSDB_NOSQL_* in .env.
#
# Usage:
#   .\cosmos.ps1 show_account         <account-name> [resource-group-name]
#   .\cosmos.ps1 enable_vector_search <account-name> [resource-group-name]
#   .\cosmos.ps1 list_databases       <account-name> [resource-group-name]
#   .\cosmos.ps1 show_database        <account-name> <database-name> [resource-group-name]
#   .\cosmos.ps1 list_containers      <account-name> <database-name> [resource-group-name]
#   .\cosmos.ps1 show_container       <account-name> <database-name> <container-name> [resource-group-name]
#   .\cosmos.ps1 load_reference_data
# Examples:
#   .\cosmos.ps1 show_account         cosmos-cjoakimforge1030x
#   .\cosmos.ps1 show_account         cosmos-cjoakimforge1030x cjoakimforge1030x
#   .\cosmos.ps1 enable_vector_search cosmos-cjoakimforge1030x
#   .\cosmos.ps1 list_databases       cosmos-cjoakimforge1030x
#   .\cosmos.ps1 show_database        cosmos-cjoakimforge1030x enterprise_memory cjoakimforge1030x
#   .\cosmos.ps1 list_containers      cosmos-cjoakimforge1030x enterprise_memory cjoakimforge1030x
#   .\cosmos.ps1 show_container       cosmos-cjoakimforge1030x enterprise_memory d579365d-0a7e-473f-ae9a-b9d3c733663d-agent-entity-store cjoakimforge1030x
#   .\cosmos.ps1 load_reference_data

param(
    [string]$Function,
    [string]$AccountName,
    [string]$Arg3,
    [string]$Arg4,
    [string]$Arg5
)

function Show-Usage {
    Write-Host "Usage:"
    Write-Host "  .\cosmos.ps1 show_account         <account-name> [resource-group-name]"
    Write-Host "  .\cosmos.ps1 enable_vector_search <account-name> [resource-group-name]"
    Write-Host "  .\cosmos.ps1 list_databases       <account-name> [resource-group-name]"
    Write-Host "  .\cosmos.ps1 show_database        <account-name> <database-name> [resource-group-name]"
    Write-Host "  .\cosmos.ps1 list_containers      <account-name> <database-name> [resource-group-name]"
    Write-Host "  .\cosmos.ps1 show_container       <account-name> <database-name> <container-name> [resource-group-name]"
    Write-Host "  .\cosmos.ps1 load_reference_data"
    exit 1
}

# Get-ResourceGroupName [resource-group-name]: the given resource group,
# or $env:AZURE_RESOURCE_GROUP
function Get-ResourceGroupName {
    param([string]$Name)

    if ([string]::IsNullOrWhiteSpace($Name)) { $Name = $env:AZURE_RESOURCE_GROUP }
    if ([string]::IsNullOrWhiteSpace($Name)) {
        Write-Host "AZURE_RESOURCE_GROUP must be set unless the resource group is given"
        Show-Usage
    }
    return $Name
}

if ([string]::IsNullOrWhiteSpace($AccountName) -and $Function -ne "load_reference_data") { Show-Usage }

# Out-File -Encoding utf8 avoids the UTF-16 output of '>' in Windows PowerShell 5.1
switch ($Function) {
    "show_account" {
        $rgName = Get-ResourceGroupName $Arg3
        New-Item -ItemType Directory -Force -Path tmp | Out-Null
        $outFile = Join-Path "tmp" "cosmos-account-$AccountName.json"
        az cosmosdb show `
            --resource-group $rgName `
            --name $AccountName `
            --output json | Out-File -FilePath $outFile -Encoding utf8
        if ($LASTEXITCODE -ne 0) { exit 1 }

        Get-Content $outFile
        Write-Host "done"
    }
    "enable_vector_search" {
        $rgName = Get-ResourceGroupName $Arg3
        $capability = "EnableNoSQLVectorSearch"
        $capabilities = @(az cosmosdb show `
            --resource-group $rgName `
            --name $AccountName `
            --query "capabilities[].name" `
            --output tsv)
        if ($LASTEXITCODE -ne 0) { exit 1 }

        if ($capabilities -contains $capability) {
            Write-Host "$capability is already enabled on $AccountName"
            exit 0
        }

        Write-Host "enabling $capability on $AccountName ..."
        az cosmosdb update `
            --resource-group $rgName `
            --name $AccountName `
            --capabilities @($capabilities + $capability) `
            --query "capabilities[].name" `
            --output tsv
        if ($LASTEXITCODE -ne 0) { exit 1 }

        Write-Host "done"
    }
    "list_databases" {
        $rgName = Get-ResourceGroupName $Arg3
        az cosmosdb sql database list `
            --resource-group $rgName `
            --account-name $AccountName `
            --query '[].{name: name}' `
            --output table
    }
    "show_database" {
        $databaseName = $Arg3
        if ([string]::IsNullOrWhiteSpace($databaseName)) { Show-Usage }
        $rgName = Get-ResourceGroupName $Arg4
        New-Item -ItemType Directory -Force -Path tmp | Out-Null
        $outFile = Join-Path "tmp" "cosmos-database-$AccountName-$databaseName.json"
        az cosmosdb sql database show `
            --resource-group $rgName `
            --account-name $AccountName `
            --name $databaseName `
            --output json | Out-File -FilePath $outFile -Encoding utf8
        if ($LASTEXITCODE -ne 0) { exit 1 }

        Get-Content $outFile
        Write-Host "done"
    }
    "list_containers" {
        $databaseName = $Arg3
        if ([string]::IsNullOrWhiteSpace($databaseName)) { Show-Usage }
        $rgName = Get-ResourceGroupName $Arg4
        az cosmosdb sql container list `
            --resource-group $rgName `
            --account-name $AccountName `
            --database-name $databaseName `
            --query '[].{name: name, partitionKey: join(`, `, resource.partitionKey.paths), vectorPolicy: resource.vectorEmbeddingPolicy != `null`, defaultTtl: resource.defaultTtl}' `
            --output table
    }
    "show_container" {
        $databaseName = $Arg3
        $containerName = $Arg4
        if ([string]::IsNullOrWhiteSpace($databaseName) -or
            [string]::IsNullOrWhiteSpace($containerName)) { Show-Usage }
        $rgName = Get-ResourceGroupName $Arg5
        New-Item -ItemType Directory -Force -Path tmp | Out-Null
        $outFile = Join-Path "tmp" "cosmos-container-$AccountName-$databaseName-$containerName.json"
        az cosmosdb sql container show `
            --resource-group $rgName `
            --account-name $AccountName `
            --database-name $databaseName `
            --name $containerName `
            --output json | Out-File -FilePath $outFile -Encoding utf8
        if ($LASTEXITCODE -ne 0) { exit 1 }

        Get-Content $outFile
        Write-Host "done"
    }
    "load_reference_data" {
        # epl container
        uv run main-cosmos-nosql.py delete_container forge epl
        uv run main-cosmos-nosql.py create_container forge epl /pk 5000 default_idx
        if ($LASTEXITCODE -ne 0) { exit 1 }
        uv run main-cosmos-nosql.py load_epl_bulk forge epl
        if ($LASTEXITCODE -ne 0) { exit 1 }

        # cities container
        uv run main-cosmos-nosql.py delete_container forge cities
        uv run main-cosmos-nosql.py create_container forge cities /pk 10000 config/cosmos/cosmosdb_nosql_vector_index_policy_diskann.json
        Start-Sleep -Seconds 60
        uv run main-cosmos-nosql.py load_cities forge cities --load
        if ($LASTEXITCODE -ne 0) { exit 1 }

        Write-Host "done"
    }
    default {
        Show-Usage
    }
}
