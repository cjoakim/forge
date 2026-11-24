#!/bin/bash

# Deploy a Foundry prompt agent, defined in an azure.yaml file,
# to a Foundry project via the project data-plane REST API.
# Note: 'az cognitiveservices agent create' only supports hosted (container) agents,
# so this script uses 'az rest' for prompt agents.
#
# The yaml must contain name, definition, id, and version.  The request body is built from
# definition, description, version, id, and metadata (minus metadata.modified_at); other yaml
# fields (status, draft, etc.) are ignored.  The request body and response are written to tmp/.
#
# Usage:   ./deploy-foundry-prompt-agent.sh <foundry-name> <foundry-project-name> <api-version> <path-to-azure.yaml> [--dry-run]
# Example: ./deploy-foundry-prompt-agent.sh aif-cjoakimforge1102b epl 2025-11-15-preview agents/python-stdlib/azure.yaml
#
# The project URL is computed as
# https://<foundry-name>.services.ai.azure.com/api/projects/<foundry-project-name>
# <api-version> is the Foundry agents data-plane API version, e.g. 2025-11-15-preview.

foundry_name="$1"
project_name="$2"
api_version="$3"
yaml_file="$4"
dry_run="$5"

if [ -z "$foundry_name" ] || [ -z "$project_name" ] || [ -z "$api_version" ] || [ -z "$yaml_file" ] || [ ! -f "$yaml_file" ]; then
    echo "Usage: $0 <foundry-name> <foundry-project-name> <api-version> <path-to-azure.yaml> [--dry-run]"
    exit 1
fi

project_url="https://$foundry_name.services.ai.azure.com/api/projects/$project_name"

mkdir -p tmp

# Convert the yaml to the JSON request body; pyyaml is provided ephemerally by uv.
agent_name=$(uv run --quiet --no-project --with pyyaml python -I -c '
import json, sys, yaml
with open(sys.argv[1]) as f:
    doc = yaml.safe_load(f)
if "name" not in doc or "definition" not in doc:
    sys.exit("yaml must contain name and definition")
metadata = {k: str(v) for k, v in (doc.get("metadata") or {}).items() if k != "modified_at"}
body = {
    "definition": doc["definition"],
    "description": doc.get("description"),
    "version": doc["version"],
    "id": doc["id"]
}
if metadata:
    body["metadata"] = metadata
name = doc["name"]
with open(f"tmp/agent-{name}-body.json", "w") as f:
    json.dump(body, f, indent=2)
print(doc["name"])
' "$yaml_file") || exit 1

body_file="tmp/agent-$agent_name-body.json"
url="$project_url/agents/$agent_name/versions?api-version=$api_version"

echo "agent:   $agent_name"
echo "url:     $url"
echo "body:    $body_file"

if [ "$dry_run" == "--dry-run" ]; then
    cat "$body_file"; echo
    echo "dry run, not deployed"
    exit 0
fi

az rest \
    --method POST \
    --url "$url" \
    --resource "https://ai.azure.com" \
    --headers "Content-Type=application/json" \
    --body "@$body_file" \
    > "tmp/agent-$agent_name-deployed.json" || exit 1

cat "tmp/agent-$agent_name-deployed.json"
echo "done"
