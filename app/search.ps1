# Azure AI Search index operations.
# These demonstrate the nice REST API for Azure AI Search, as well as
# directly populating (pushing) the search index data with the REST API.
# Authentication is Entra ID; you need the Search Service Contributor and
# Search Index Data Contributor roles, which deploy-arm.ps1 grants the deployer.
#
# The first arg is the function; none of the functions take further args.
#
# recreate-epl:    deletes, creates, and populates the "epl" index
# recreate-cities: deletes, creates, and populates the "cities" vector index
#
# Usage:
#   .\search.ps1 recreate-epl
#   .\search.ps1 recreate-cities
#
# See main-search.py to execute searches on these indexes.

param(
    [string]$Function
)

function Show-Usage {
    Write-Host "Usage:"
    Write-Host "  .\search.ps1 recreate-epl"
    Write-Host "  .\search.ps1 recreate-cities"
    exit 1
}

# Recreate-Index <index-name> <index-definition-file> <data-file>
function Recreate-Index {
    param([string]$Index, [string]$Definition, [string]$Data)

    Write-Host "=== SHELL delete index $Index ==="
    uv run main-search.py delete_index $Index

    Write-Host "=== SHELL create index $Index ==="
    uv run main-search.py create_index $Index $Definition
    if ($LASTEXITCODE -ne 0) { exit 1 }

    Write-Host "=== SHELL populate index $Index ==="
    uv run main-search.py direct_load_index $Index $Data --load
    if ($LASTEXITCODE -ne 0) { exit 1 }

    Write-Host "done"
}

switch ($Function) {
    "recreate-epl" {
        Recreate-Index "epl" (Join-Path "config" (Join-Path "search" "epl_index.json")) `
            (Join-Path ".." (Join-Path "data" (Join-Path "epl" "merged_documents_v2.json")))
    }
    "recreate-cities" {
        Recreate-Index "cities" (Join-Path "config" (Join-Path "search" "cities_vector_index.json")) `
            (Join-Path ".." (Join-Path "data" (Join-Path "epl" "cities_v2.json")))
    }
    default {
        Show-Usage
    }
}
