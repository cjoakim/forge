#!/bin/bash

# Azure Cosmos DB for NoSQL operations, using the az CLI.
#
# The first arg is the function; the second is the Cosmos DB account name
# (e.g. cosmos-cjoakimforge1030x). Some functions then take a database name and a container
# name. The last arg, optional, is the resource group, which defaults to $AZURE_RESOURCE_GROUP.
#
# show_account:         shows the account, writing its JSON to
#                       tmp/cosmos-account-<account-name>.json
# enable_vector_search: enables Vector Search for NoSQL API (the EnableNoSQLVectorSearch
#                       capability) on the account, keeping its other capabilities, since
#                       --capabilities replaces the whole list. The capability can't be
#                       disabled once enabled, and can take up to 15 minutes to take effect.
# list_databases:       lists the account's databases
# show_database:        shows a database, writing its JSON to
#                       tmp/cosmos-database-<account-name>-<database-name>.json
# list_containers:      lists a database's containers, with their partition key paths, whether
#                       they have a vector embedding policy, and their default TTL
# show_container:       shows a container, including its indexing and vector embedding
#                       policies, writing its JSON to
#                       tmp/cosmos-container-<account-name>-<database-name>-<container-name>.json
# load_reference_data:  deletes then reloads the Reference App data (the epl and cities
#                       containers of the forge database) using main-cosmos-nosql.py. It takes
#                       no other args; the account comes from AZURE_COSMOSDB_NOSQL_* in .env.
#
# Usage:
#   ./cosmos.sh show_account         <account-name> [resource-group-name]
#   ./cosmos.sh enable_vector_search <account-name> [resource-group-name]
#   ./cosmos.sh list_databases       <account-name> [resource-group-name]
#   ./cosmos.sh show_database        <account-name> <database-name> [resource-group-name]
#   ./cosmos.sh list_containers      <account-name> <database-name> [resource-group-name]
#   ./cosmos.sh show_container       <account-name> <database-name> <container-name> [resource-group-name]
#   ./cosmos.sh load_reference_data
# Examples:
#   ./cosmos.sh show_account         cosmos-cjoakimforge1030x
#   ./cosmos.sh show_account         cosmos-cjoakimforge1030x cjoakimforge1030x
#   ./cosmos.sh enable_vector_search cosmos-cjoakimforge1030x
#   ./cosmos.sh list_databases       cosmos-cjoakimforge1030x
#   ./cosmos.sh show_database        cosmos-cjoakimforge1030x enterprise_memory cjoakimforge1030x
#   ./cosmos.sh list_containers      cosmos-cjoakimforge1030x enterprise_memory cjoakimforge1030x
#   ./cosmos.sh show_container       cosmos-cjoakimforge1030x enterprise_memory d579365d-0a7e-473f-ae9a-b9d3c733663d-agent-entity-store cjoakimforge1030x
#   ./cosmos.sh load_reference_data

function_name="$1"
account_name="$2"

usage() {
    echo "Usage:"
    echo "  $0 show_account         <account-name> [resource-group-name]"
    echo "  $0 enable_vector_search <account-name> [resource-group-name]"
    echo "  $0 list_databases       <account-name> [resource-group-name]"
    echo "  $0 show_database        <account-name> <database-name> [resource-group-name]"
    echo "  $0 list_containers      <account-name> <database-name> [resource-group-name]"
    echo "  $0 show_container       <account-name> <database-name> <container-name> [resource-group-name]"
    echo "  $0 load_reference_data"
    exit 1
}

# set_rg_name [resource-group-name]: sets rg_name to the given resource group,
# or to $AZURE_RESOURCE_GROUP
set_rg_name() {
    rg_name="${1:-$AZURE_RESOURCE_GROUP}"
    if [ -z "$rg_name" ]; then
        echo "AZURE_RESOURCE_GROUP must be set unless the resource group is given"
        usage
    fi
}

[ -z "$account_name" ] && [ "$function_name" != "load_reference_data" ] && usage

case "$function_name" in
    show_account)
        set_rg_name "$3"
        mkdir -p tmp
        out_file="tmp/cosmos-account-$account_name.json"
        az cosmosdb show \
            --resource-group "$rg_name" \
            --name "$account_name" \
            --output json \
            > "$out_file" || exit 1

        cat "$out_file"
        echo "done"
        ;;
    enable_vector_search)
        set_rg_name "$3"
        capability="EnableNoSQLVectorSearch"
        capabilities=$(az cosmosdb show \
            --resource-group "$rg_name" \
            --name "$account_name" \
            --query "capabilities[].name" \
            --output tsv) || exit 1

        if echo "$capabilities" | grep -qx "$capability"; then
            echo "$capability is already enabled on $account_name"
            exit 0
        fi

        echo "enabling $capability on $account_name ..."
        # word splitting of $capabilities passes each existing capability as its own value
        # shellcheck disable=SC2086
        az cosmosdb update \
            --resource-group "$rg_name" \
            --name "$account_name" \
            --capabilities $capabilities "$capability" \
            --query "capabilities[].name" \
            --output tsv || exit 1

        echo "done"
        ;;
    list_databases)
        set_rg_name "$3"
        az cosmosdb sql database list \
            --resource-group "$rg_name" \
            --account-name "$account_name" \
            --query '[].{name: name}' \
            --output table
        ;;
    show_database)
        database_name="$3"
        [ -z "$database_name" ] && usage
        set_rg_name "$4"
        mkdir -p tmp
        out_file="tmp/cosmos-database-$account_name-$database_name.json"
        az cosmosdb sql database show \
            --resource-group "$rg_name" \
            --account-name "$account_name" \
            --name "$database_name" \
            --output json \
            > "$out_file" || exit 1

        cat "$out_file"
        echo "done"
        ;;
    list_containers)
        database_name="$3"
        [ -z "$database_name" ] && usage
        set_rg_name "$4"
        az cosmosdb sql container list \
            --resource-group "$rg_name" \
            --account-name "$account_name" \
            --database-name "$database_name" \
            --query '[].{name: name, partitionKey: join(`, `, resource.partitionKey.paths), vectorPolicy: resource.vectorEmbeddingPolicy != `null`, defaultTtl: resource.defaultTtl}' \
            --output table
        ;;
    show_container)
        database_name="$3"
        container_name="$4"
        { [ -z "$database_name" ] || [ -z "$container_name" ]; } && usage
        set_rg_name "$5"
        mkdir -p tmp
        out_file="tmp/cosmos-container-$account_name-$database_name-$container_name.json"
        az cosmosdb sql container show \
            --resource-group "$rg_name" \
            --account-name "$account_name" \
            --database-name "$database_name" \
            --name "$container_name" \
            --output json \
            > "$out_file" || exit 1

        cat "$out_file"
        echo "done"
        ;;
    load_reference_data)
        # epl container
        uv run main-cosmos-nosql.py delete_container forge epl
        uv run main-cosmos-nosql.py create_container forge epl /pk 5000 default_idx || exit 1
        uv run main-cosmos-nosql.py load_epl_bulk forge epl || exit 1

        # cities container
        uv run main-cosmos-nosql.py delete_container forge cities
        uv run main-cosmos-nosql.py create_container forge cities /pk 10000 config/cosmos/cosmosdb_nosql_vector_index_policy_diskann.json
        sleep 60
        uv run main-cosmos-nosql.py load_cities forge cities --load || exit 1

        echo "done"
        ;;
    *)
        usage
        ;;
esac
