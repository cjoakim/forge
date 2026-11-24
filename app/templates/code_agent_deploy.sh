#!/bin/bash

# Build and deploy this hosted agent with azd, then check that the new version works.
# The steps are:
#   1. azd deploy: builds the container image, pushes it to ACR, and creates a new agent version;
#      the script stops here if the deploy fails, so the later steps never run against the
#      previous version
#   2. assigns the agent's Entra identity its roles (see below); existing assignments are left
#      as is, so this does nothing after the first deploy unless the roles were removed
#   3. waits <wait-seconds> (default 30) for the new version to start
#   4. azd ai agent show: displays the agent's status and version
#   5. azd ai agent invoke: sends the agent a test question
#   6. azd ai agent monitor: displays the last 100 lines of the agent's console logs
#
# Foundry creates an Entra agent identity (instance_identity) per agent, shared by all of its
# versions; the agent's container authenticates as this identity. azd deploy doesn't give it any
# data-plane roles, so step 2 assigns it 'Foundry User' (formerly 'Azure AI User') so the
# container can call the model deployment, plus data-plane roles on AI Search (default
# 'Search Index Data Contributor') and Storage (default 'Storage Blob Data Contributor') so it
# can read and write index documents and blobs. New role assignments can take a few minutes to
# take effect.
#
# The agent name and the azd environment name are both the name of this script's directory
# (e.g. epl for agents/epl). The script can be run from any directory; azd commands run in this
# script's directory, where azure.yaml is.
#
# Settings are read from the azd environment, which is created from the app/.env file.
# Required:
#   AZURE_SUBSCRIPTION_ID, AZURE_RESOURCE_GROUP, AZURE_FOUNDRY_NAME, AZURE_FOUNDRY_PROJECT_NAME
# Optional; a service gets no role when its name is empty or its FORGE_AGENT_*_ROLE setting
# is 'none':
#   AZURE_AI_SEARCH_NAME, AZURE_STORAGE_ACCOUNT_NAME
#   FORGE_AGENT_ROLE             default 'Foundry User'; role name or id for the agent identity
#   FORGE_AGENT_ROLE_SCOPE       default project; 'project' or 'account'
#   FORGE_AGENT_SEARCH_ROLE      default 'Search Index Data Contributor'; 'none' to skip
#   FORGE_AGENT_STORAGE_ROLE     default 'Storage Blob Data Contributor'; 'none' to skip
#
# Usage:   ./deploy.sh [wait-seconds]
# Examples:
#   ./deploy.sh
#   ./deploy.sh 60        (from the app directory)

wait_seconds="${1:-30}"
if ! [[ "$wait_seconds" =~ ^[0-9]+$ ]]; then
    echo "Usage: $0 [wait-seconds]"
    exit 1
fi

cd "$(dirname "$0")" || exit 1
agent_name="$(basename "$(pwd)")"
env_name="$agent_name"

# azd_env_or_default <name> <default>: the value of <name> in the azd environment, else the
# default.
azd_env_or_default() {
    local value
    value=$(azd env get-value "$1" --environment "$env_name" 2>/dev/null) || value=""
    echo "${value:-$2}"
}

# azd_env_required <name>: the value of <name> in the azd environment; exits if it's missing or
# empty.
azd_env_required() {
    local value
    value=$(azd_env_or_default "$1" "")
    if [ -z "$value" ]; then
        echo "$1 must be set in azd environment $env_name; see set-azd-env.sh" >&2
        exit 1
    fi
    echo "$value"
}

subscription_id=$(azd_env_required AZURE_SUBSCRIPTION_ID) || exit 1
resource_group=$(azd_env_required AZURE_RESOURCE_GROUP) || exit 1
foundry_name=$(azd_env_required AZURE_FOUNDRY_NAME) || exit 1
project_name=$(azd_env_required AZURE_FOUNDRY_PROJECT_NAME) || exit 1
search_name=$(azd_env_or_default AZURE_AI_SEARCH_NAME "")
storage_name=$(azd_env_or_default AZURE_STORAGE_ACCOUNT_NAME "")
role=$(azd_env_or_default FORGE_AGENT_ROLE "Foundry User")
role_scope=$(azd_env_or_default FORGE_AGENT_ROLE_SCOPE "project")
search_role=$(azd_env_or_default FORGE_AGENT_SEARCH_ROLE "Search Index Data Contributor")
storage_role=$(azd_env_or_default FORGE_AGENT_STORAGE_ROLE "Storage Blob Data Contributor")

if [ "$search_role" == "none" ]; then
    search_name=""
fi
if [ "$storage_role" == "none" ]; then
    storage_name=""
fi
if [ "$role_scope" != "project" ] && [ "$role_scope" != "account" ]; then
    echo "FORGE_AGENT_ROLE_SCOPE must be 'project' or 'account'"
    exit 1
fi

echo "Building and deploying agent $agent_name to azd environment $env_name ..."
azd deploy "$agent_name" --environment "$env_name" --no-prompt || exit 1

echo "Getting the resource ids for the role assignment scopes ..."
account_id=$(az cognitiveservices account show --subscription "$subscription_id" \
    --resource-group "$resource_group" --name "$foundry_name" --query id -o tsv) || exit 1
if [ "$role_scope" == "account" ]; then
    scope="$account_id"
else
    scope="$account_id/projects/$project_name"
fi
search_id=""
if [ -n "$search_name" ]; then
    search_id=$(az search service show --subscription "$subscription_id" \
        --resource-group "$resource_group" --name "$search_name" --query id -o tsv) || exit 1
fi
storage_id=""
if [ -n "$storage_name" ]; then
    storage_id=$(az storage account show --subscription "$subscription_id" \
        --resource-group "$resource_group" --name "$storage_name" --query id -o tsv) || exit 1
fi

echo "Getting the $agent_name agent identity ..."
principal_id=$(az cognitiveservices agent show \
    --subscription "$subscription_id" \
    --account-name "$foundry_name" \
    --project-name "$project_name" \
    --name "$agent_name" \
    --only-show-errors \
    --query instance_identity.principal_id \
    -o tsv) || exit 1
if [ -z "$principal_id" ]; then
    echo "agent identity not found for agent $agent_name"
    exit 1
fi
echo "agent identity principal id: $principal_id"

# assign_role <role> <scope>: assign the role to the agent identity unless it already has it.
assign_role() {
    # List by scope and filter on principalId, rather than using --assignee, which looks up the
    # principal in Microsoft Graph and can fail for agent identities.
    local existing
    existing=$(az role assignment list --subscription "$subscription_id" --scope "$2" --role "$1" \
        --query "[?principalId=='$principal_id'] | length(@)" -o tsv)
    if [ "$existing" != "0" ]; then
        echo "role '$1' is already assigned to the agent identity"
        return
    fi
    # A new agent identity can take a little while to replicate in Entra, so retry.
    for attempt in 1 2 3 4 5; do
        echo "assigning role '$1' to the agent identity (attempt $attempt) ..."
        if az role assignment create \
            --subscription "$subscription_id" \
            --assignee-object-id "$principal_id" \
            --assignee-principal-type ServicePrincipal \
            --role "$1" \
            --scope "$2" \
            --only-show-errors \
            -o none; then
            echo "role assigned"
            return
        fi
        if [ $attempt -eq 5 ]; then
            echo "ERROR: role assignment failed"
            exit 1
        fi
        sleep 15
    done
}

assign_role "$role" "$scope"
if [ -n "$search_id" ]; then
    assign_role "$search_role" "$search_id"
fi
if [ -n "$storage_id" ]; then
    assign_role "$storage_role" "$storage_id"
fi

echo "Waiting $wait_seconds seconds for the new version to start ..."
sleep "$wait_seconds"

echo "Showing $agent_name agent ..."
azd ai agent show "$agent_name" --environment "$env_name" || exit 1

# See https://aka.ms/azd-agents-invoke
# echo "Invoking $agent_name agent ..."
# azd ai agent invoke "$agent_name" 'what teams are in the EPL?' --environment "$env_name" || exit 1

# echo "Monitoring $agent_name agent, tail 100 ..."
# azd ai agent monitor "$agent_name" --tail 100 --environment "$env_name"
