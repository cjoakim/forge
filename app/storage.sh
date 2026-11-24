#!/bin/bash

# Blob storage operations against an Azure Storage account: list the account's containers,
# create or delete a container, list a container's blobs, and upload, download, or delete a blob.
# Authenticates with your Entra ID (--auth-mode login), since the storage account doesn't
# allow shared keys; you need a data-plane role such as Storage Blob Data Contributor
# (or Storage Blob Data Reader for list-containers, list-container, and download-blob) on the account, and your IP must be
# allowed through its firewall (see arm/ip_address.sh update_ip).
#
# The first arg is the function; the remaining args are always in the same order:
# <storage-account-name> <container-name> <blob-name> <local-file-path>
#
# create-container: creates the container (an existing one is left as is), then lists the account's containers
# list-containers:  lists the containers in the account
# list-container:   lists the blobs in the container
# upload-blob:      uploads the local file to the blob; an existing blob is overwritten
# download-blob:    downloads the blob to the local file; its directory is created if needed,
#                   and an existing local file is overwritten
# delete-blob:      deletes the blob
# delete-container: deletes the container and all of its blobs
# test:             smoke-tests the other functions against a container named test: deletes it
#                   (if it exists) and re-creates it, lists it, uploads uv.lock to it, lists it
#                   again, downloads the blob to ~/Downloads/uv.lock (overwriting that file), then
#                   deletes the container
#
# Usage:
#   ./storage.sh create-container <storage-account-name> <container-name>
#   ./storage.sh list-containers  <storage-account-name>
#   ./storage.sh list-container   <storage-account-name> <container-name>
#   ./storage.sh upload-blob      <storage-account-name> <container-name> <blob-name> <local-file-path>
#   ./storage.sh download-blob    <storage-account-name> <container-name> <blob-name> <local-file-path>
#   ./storage.sh delete-blob      <storage-account-name> <container-name> <blob-name>
#   ./storage.sh delete-container <storage-account-name> <container-name>
#   ./storage.sh test             <storage-account-name>
# Examples:
#   ./storage.sh create-container stcjoakimforge1022a agents
#   ./storage.sh list-containers  stcjoakimforge1022a
#   ./storage.sh list-container   stcjoakimforge1022a agents
#   ./storage.sh upload-blob      stcjoakimforge1022a agents c1.txt tmp/c1.txt
#   ./storage.sh download-blob    stcjoakimforge1022a agents c1.txt tmp/c1.txt
#   ./storage.sh delete-blob      stcjoakimforge1022a agents c1.txt
#   ./storage.sh delete-container stcjoakimforge1022a agents
#   ./storage.sh test             stcjoakimforge1022a

function_name="$1"
account_name="$2"
container_name="$3"
blob_name="$4"
local_filename="$5"

usage() {
    echo "Usage:"
    echo "  $0 create-container <storage-account-name> <container-name>"
    echo "  $0 list-containers  <storage-account-name>"
    echo "  $0 list-container   <storage-account-name> <container-name>"
    echo "  $0 upload-blob      <storage-account-name> <container-name> <blob-name> <local-file-path>"
    echo "  $0 download-blob    <storage-account-name> <container-name> <blob-name> <local-file-path>"
    echo "  $0 delete-blob      <storage-account-name> <container-name> <blob-name>"
    echo "  $0 delete-container <storage-account-name> <container-name>"
    echo "  $0 test             <storage-account-name>"
    exit 1
}

# Exits with the usage message unless the first N of account, container, blob, and local file are given.
require_args() {
    local count="$1"
    local args=("$account_name" "$container_name" "$blob_name" "$local_filename")
    for ((i = 0; i < count; i++)); do
        [ -z "${args[$i]}" ] && usage
    done
}

case "$function_name" in
    create-container)
        require_args 2
        az storage container create \
            --account-name "$account_name" \
            --name "$container_name" \
            --auth-mode login || exit 1

        echo "containers in storage account $account_name:"
        az storage container list \
            --account-name "$account_name" \
            --auth-mode login \
            --query "[].{name: name, lastModified: properties.lastModified}" \
            -o table
        ;;
    list-containers)
        require_args 1
        echo "containers in storage account $account_name:"
        az storage container list \
            --account-name "$account_name" \
            --auth-mode login \
            --query "[].{name: name, lastModified: properties.lastModified}" \
            -o table
        ;;
    list-container)
        require_args 2
        echo "blobs in container $container_name of storage account $account_name:"
        az storage blob list \
            --account-name "$account_name" \
            --container-name "$container_name" \
            --auth-mode login \
            --num-results "*" \
            --query "[].{name: name, size: properties.contentLength, lastModified: properties.lastModified}" \
            -o table
        ;;
    upload-blob)
        require_args 4
        if [ ! -f "$local_filename" ]; then
            echo "file not found: $local_filename"
            exit 1
        fi

        echo "uploading $local_filename to $account_name/$container_name/$blob_name ..."
        az storage blob upload \
            --account-name "$account_name" \
            --container-name "$container_name" \
            --name "$blob_name" \
            --file "$local_filename" \
            --overwrite true \
            --auth-mode login \
            -o table
        ;;
    download-blob)
        require_args 4
        mkdir -p "$(dirname "$local_filename")" || exit 1

        echo "downloading $account_name/$container_name/$blob_name to $local_filename ..."
        az storage blob download \
            --account-name "$account_name" \
            --container-name "$container_name" \
            --name "$blob_name" \
            --file "$local_filename" \
            --overwrite true \
            --auth-mode login \
            -o none || exit 1

        ls -l "$local_filename"
        ;;
    delete-blob)
        require_args 3
        echo "deleting $account_name/$container_name/$blob_name ..."
        az storage blob delete \
            --account-name "$account_name" \
            --container-name "$container_name" \
            --name "$blob_name" \
            --auth-mode login \
            -o none || exit 1

        echo "deleted"
        ;;
    delete-container)
        require_args 2
        echo "deleting container $account_name/$container_name ..."
        az storage container delete \
            --account-name "$account_name" \
            --name "$container_name" \
            --auth-mode login \
            -o none || exit 1

        echo "deleted"
        ;;
    test)
        require_args 1
        test_container="test"
        test_file="uv.lock"

        exists=$(az storage container exists \
            --account-name "$account_name" \
            --name "$test_container" \
            --auth-mode login \
            --query exists \
            -o tsv) || exit 1
        if [ "$exists" = "true" ]; then
            "$0" delete-container "$account_name" "$test_container" || exit 1
        fi

        # A deleted container's name can't be reused until Azure finishes deleting it, which can
        # take a minute or more; until then create reports created=false, so retry.
        echo "creating container $account_name/$test_container ..."
        for ((attempt = 1; attempt <= 18; attempt++)); do
            created=$(az storage container create \
                --account-name "$account_name" \
                --name "$test_container" \
                --auth-mode login \
                --query created \
                -o tsv)
            [ "$created" = "true" ] && break
            echo "container not created yet (attempt $attempt), retrying in 10 seconds ..."
            sleep 10
        done
        if [ "$created" != "true" ]; then
            echo "container $test_container could not be created"
            exit 1
        fi

        "$0" list-container "$account_name" "$test_container" || exit 1
        "$0" upload-blob "$account_name" "$test_container" "$test_file" "$test_file" || exit 1
        "$0" list-container "$account_name" "$test_container" || exit 1
        "$0" download-blob "$account_name" "$test_container" "$test_file" "$HOME/Downloads/$test_file" || exit 1
        "$0" delete-container "$account_name" "$test_container" || exit 1
        ;;
    *)
        usage
        ;;
esac
