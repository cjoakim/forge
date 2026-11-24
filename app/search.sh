#!/bin/bash

# Azure AI Search index operations.
# These demonstrate the nice REST API for Azure AI Search, as well as
# directly populating (pushing) the search index data with the REST API.
# Authentication is Entra ID; you need the Search Service Contributor and
# Search Index Data Contributor roles, which deploy-arm.sh grants the deployer.
#
# The first arg is the function; none of the functions take further args.
#
# recreate-epl:    deletes, creates, and populates the "epl" index
# recreate-cities: deletes, creates, and populates the "cities" vector index
#
# Usage:
#   ./search.sh recreate-epl
#   ./search.sh recreate-cities
#
# See main-search.py to execute searches on these indexes.

function_name="$1"

usage() {
    echo "Usage:"
    echo "  $0 recreate-epl"
    echo "  $0 recreate-cities"
    exit 1
}

# recreate_index <index-name> <index-definition-file> <data-file>
recreate_index() {
    local index="$1" definition="$2" data="$3"

    echo "=== SHELL delete index $index ==="
    uv run main-search.py delete_index "$index"

    echo "=== SHELL create index $index ==="
    uv run main-search.py create_index "$index" "$definition" || exit 1

    echo "=== SHELL populate index $index ==="
    uv run main-search.py direct_load_index "$index" "$data" --load || exit 1

    echo "done"
}

case "$function_name" in
    recreate-epl)
        recreate_index epl config/search/epl_index.json ../data/epl/merged_documents_v2.json
        ;;
    recreate-cities)
        recreate_index cities config/search/cities_vector_index.json ../data/epl/cities_v2.json
        ;;
    *)
        usage
        ;;
esac
