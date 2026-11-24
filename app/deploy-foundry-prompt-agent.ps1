# Deploy a Foundry prompt agent, defined in an azure.yaml file,
# to a Foundry project via the project data-plane REST API.
# Note: 'az cognitiveservices agent create' only supports hosted (container) agents,
# so this script uses 'az rest' for prompt agents.
#
# The yaml must contain name, definition, id, and version.  The request body is built from
# definition, description, version, id, and metadata (minus metadata.modified_at); other yaml
# fields (status, draft, etc.) are ignored.  The request body and response are written to tmp/.
#
# Usage:   .\deploy-foundry-prompt-agent.ps1 <foundry-name> <foundry-project-name> <api-version> <path-to-azure.yaml> [--dry-run]
# Example: .\deploy-foundry-prompt-agent.ps1 aif-cjoakimforge1102b epl 2025-11-15-preview agents/python-stdlib/azure.yaml
#
# The project URL is computed as
# https://<foundry-name>.services.ai.azure.com/api/projects/<foundry-project-name>
# <api-version> is the Foundry agents data-plane API version, e.g. 2025-11-15-preview.

param(
    [string]$FoundryName,
    [string]$ProjectName,
    [string]$ApiVersion,
    [string]$YamlFile,
    [string]$DryRun
)

if (-not $FoundryName -or -not $ProjectName -or -not $ApiVersion -or -not $YamlFile -or -not (Test-Path -LiteralPath $YamlFile -PathType Leaf)) {
    Write-Host "Usage: .\deploy-foundry-prompt-agent.ps1 <foundry-name> <foundry-project-name> <api-version> <path-to-azure.yaml> [--dry-run]"
    exit 1
}

$projectUrl = "https://$FoundryName.services.ai.azure.com/api/projects/$ProjectName"

New-Item -ItemType Directory -Force -Path tmp | Out-Null

# Convert the yaml to the JSON request body; pyyaml is provided ephemerally by uv.
# Single quotes only: Windows PowerShell 5.1 doesn't escape embedded double quotes in native args.
$pyCode = @'
import json, sys, yaml
with open(sys.argv[1]) as f:
    doc = yaml.safe_load(f)
if 'name' not in doc or 'definition' not in doc:
    sys.exit('yaml must contain name and definition')
metadata = {k: str(v) for k, v in (doc.get('metadata') or {}).items() if k != 'modified_at'}
body = {
    'definition': doc['definition'],
    'description': doc.get('description'),
    'version': doc['version'],
    'id': doc['id']
}
if metadata:
    body['metadata'] = metadata
name = doc['name']
with open(f'tmp/agent-{name}-body.json', 'w') as f:
    json.dump(body, f, indent=2)
print(doc['name'])
'@
$agentName = (uv run --quiet --no-project --with pyyaml python -I -c $pyCode $YamlFile)
if ($LASTEXITCODE -ne 0) { exit 1 }
$agentName = $agentName.Trim()

$bodyFile = "tmp/agent-$agentName-body.json"
$url = "$projectUrl/agents/$agentName/versions?api-version=$ApiVersion"

Write-Host "agent:   $agentName"
Write-Host "url:     $url"
Write-Host "body:    $bodyFile"

if ($DryRun -eq "--dry-run") {
    Get-Content $bodyFile
    Write-Host "dry run, not deployed"
    exit 0
}

az rest `
    --method POST `
    --url $url `
    --resource "https://ai.azure.com" `
    --headers "Content-Type=application/json" `
    --body "@$bodyFile" `
    | Out-File -Encoding utf8 "tmp/agent-$agentName-deployed.json"
if ($LASTEXITCODE -ne 0) { exit 1 }

Get-Content "tmp/agent-$agentName-deployed.json"
Write-Host "done"
