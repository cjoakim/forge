#!/bin/bash

# Azure resource group operations.
#
# The first arg is the function; the remaining args are always in the same order:
# <resource-group-name> <user-upn-or-object-id | foundry-account-name>
# except show-user and my-ip, which take no args, rg-ownership, whose only arg is an email, and
# get-ai-project-id and show-foundry-project, whose resource group defaults to $AZURE_RESOURCE_GROUP.
#
# show:      shows the resource group, writing its JSON to tmp/rg-show.json
# export:    exports the resource group as an ARM template, writing it to
#            tmp/rg-export-<resource-group-name>.json
# show-user: shows the signed-in Azure user, writing its JSON to tmp/user-show.json
#            and its object id to tmp/user-id-show.json
# user_roles_assign: post-deployment, grants a user the data-plane and management RBAC roles
#            needed to work with the resource group's Forge resources from a laptop
#            (az login / DefaultAzureCredential). The user defaults to the signed-in user.
#            You must have Owner, or User Access Administrator, on the resource group.
#            Cosmos DB for NoSQL accounts get the Cosmos DB Built-in Data Reader and Data
#            Contributor roles, which are Cosmos data-plane roles (az cosmosdb sql role assignment),
#            not Azure RBAC roles, assigned at the account scope.
#            New role assignments can take several minutes to propagate.
# update-firewall-ip: updates the Foundry firewall so that it allows your current public IP
#            address, or the IPs given with -a / --allowed-ips (comma or semicolon separated).
#            Foundry projects don't have their own firewall; they inherit the network rules of
#            their parent Foundry account (Microsoft.CognitiveServices/accounts, kind AIServices).
#            If the account name is omitted, every Foundry account in the resource group is
#            updated. Existing IP rules are kept unless --remove-others is given.
#            See also arm/ip_address.sh update_ip, which updates all of the sandbox's PaaS firewalls.
# rg-ownership: lists the resource groups in the current subscription whose Creator tag is the
#            given email (default: the signed-in user's mail address), with their location and
#            CreationDate / ExpirationDate tags, and counts the groups that have no Creator tag.
# export-rg-urls: lists the PaaS services in the resource group with all of their endpoints/URLs,
#            writing them to tmp/rg-urls-<resource-group-name>.json and .tsv (the full resource
#            JSON goes to tmp/rg-resources-<resource-group-name>.json). Endpoints are discovered
#            generically by walking each resource's properties for endpoint-like keys (endpoint,
#            endpoints.*, *Url, *Uri, hostName, fqdn, loginServer, ...) with URL/hostname values;
#            resources without endpoints (identities, workspaces, alerts, etc.) are omitted.
#            Requires jq.
# get-ai-project-id: displays the ARM resource ID of the Foundry project (AZURE_AI_PROJECT_ID).
#            Requires AZURE_FOUNDRY_NAME and AZURE_FOUNDRY_PROJECT_NAME, and AZURE_RESOURCE_GROUP
#            unless the resource group is given.
# my-ip:     displays your workstation's current public IP address, as seen by the Azure firewalls.
# show-foundry-project: shows the Foundry project, a child resource of the Foundry (AIServices)
#            account, writing its JSON to tmp/foundry-project-<project-name>.json.
#            Requires AZURE_FOUNDRY_NAME and AZURE_FOUNDRY_PROJECT_NAME, and AZURE_RESOURCE_GROUP
#            unless the resource group is given.
#
# Usage:
#   ./rg.sh show      <resource-group-name>
#   ./rg.sh export    <resource-group-name>
#   ./rg.sh show-user
#   ./rg.sh user_roles_assign <resource-group-name> [user-upn-or-object-id]
#   ./rg.sh update-firewall-ip <resource-group-name> [foundry-account-name] [-a <ip[,ip...]>] [--remove-others]
#   ./rg.sh rg-ownership [email]
#   ./rg.sh export-rg-urls <resource-group-name> > outfile
#   ./rg.sh get-ai-project-id [resource-group-name]
#   ./rg.sh my-ip
#   ./rg.sh show-foundry-project [resource-group-name]
# Examples:
#   ./rg.sh show      cjoakimforge1030x
#   ./rg.sh export    cjoakimforge1030x
#   ./rg.sh show-user
#   ./rg.sh user_roles_assign cjoakimforge1030x
#   ./rg.sh user_roles_assign cjoakimforge1030x someone.else@somehost.com
#   ./rg.sh update-firewall-ip cjoakimforge1030x
#   ./rg.sh update-firewall-ip cjoakimforge1030x forge-foundry-12345
#   ./rg.sh update-firewall-ip cjoakimforge1030x -a 203.0.113.10,198.51.100.20
#   ./rg.sh update-firewall-ip cjoakimforge1030x --remove-others
#   ./rg.sh rg-ownership
#   ./rg.sh rg-ownership someone.else@somehost.com
#   ./rg.sh export-rg-urls cjoakimforge1030x > tmp/rg-urls.json
#   ./rg.sh get-ai-project-id
#   ./rg.sh get-ai-project-id cjoakimforge1030x
#   ./rg.sh my-ip
#   ./rg.sh show-foundry-project
#   ./rg.sh show-foundry-project cjoakimforge1030x

function_name="$1"
rg_name="$2"
user_id="$3"

usage() {
    echo "Usage:"
    echo "  $0 show      <resource-group-name>"
    echo "  $0 export    <resource-group-name>"
    echo "  $0 show-user"
    echo "  $0 user_roles_assign <resource-group-name> [user-upn-or-object-id]"
    echo "  $0 update-firewall-ip <resource-group-name> [foundry-account-name] [-a <ip[,ip...]>] [--remove-others]"
    echo "  $0 rg-ownership [email]"
    echo "  $0 export-rg-urls <resource-group-name>"
    echo "  $0 get-ai-project-id [resource-group-name]"
    echo "  $0 my-ip"
    echo "  $0 show-foundry-project [resource-group-name]"
    exit 1
}

# Exits with the usage message unless the first N of the resource group args are given.
require_args() {
    local count="$1"
    local args=("$rg_name")
    for ((i = 0; i < count; i++)); do
        [ -z "${args[$i]}" ] && usage
    done
}

# Built-in Azure role definition IDs, used by user_roles_assign
AZURE_AI_USER="53ca6127-db72-4b80-b1b0-d745d6d5456d"
AZURE_AI_PROJECT_MANAGER="eadc314b-1a2d-4efa-be10-5d325db5065e"
COGNITIVE_SERVICES_USER="a97b65f3-24c7-4388-baec-2e87135dc908"
STORAGE_BLOB_DATA_CONTRIBUTOR="ba92f5b4-2d11-453d-a403-e96b0029c9fe"
KEY_VAULT_SECRETS_OFFICER="b86a8fe4-44ce-4948-aee5-eccb2c155cd7"
ACR_PUSH="8311e382-0749-4cb8-b61a-304f252e45ec"
SEARCH_SERVICE_CONTRIBUTOR="7ca78c08-252a-4471-8644-bb5ff32d4ba0"
SEARCH_INDEX_DATA_CONTRIBUTOR="8ebe5a00-799e-43f5-93ac-243d3dce84a7"
MONITORING_METRICS_PUBLISHER="3913510d-42f4-4e42-8a64-420c390055eb"
LOG_ANALYTICS_READER="73c42c96-874c-492b-b04d-ab87d138a893"

# Built-in Cosmos DB for NoSQL data-plane role definition IDs, used by user_roles_assign
COSMOS_DB_BUILT_IN_DATA_READER="00000000-0000-0000-0000-000000000001"
COSMOS_DB_BUILT_IN_DATA_CONTRIBUTOR="00000000-0000-0000-0000-000000000002"

# assign_role <scope-resource-id> <resource-name> <role-id> <role-label>
# Assigns the role to $principal_id at the scope unless it's already assigned there.
assign_role() {
    local scope="$1" name="$2" role="$3" label="$4"
    local count
    count="$(az role assignment list --assignee "$principal_id" --role "$role" --scope "$scope" \
        --query "length([?scope=='$scope'])" -o tsv)" || exit 1
    if [ "$count" != "0" ]; then
        echo "  exists   $label on $name"
        existing=$((existing + 1))
    else
        az role assignment create \
            --assignee-object-id "$principal_id" \
            --assignee-principal-type User \
            --role "$role" \
            --scope "$scope" \
            --only-show-errors --output none || exit 1
        echo "  created  $label on $name"
        created=$((created + 1))
    fi
}

# assign_cosmos_role <account-resource-id> <account-name> <role-definition-guid> <role-label>
# Assigns the Cosmos DB data-plane role to $principal_id at the account scope unless it's
# already assigned there.
assign_cosmos_role() {
    local scope="$1" name="$2" role="$3" label="$4"
    local count
    count="$(az cosmosdb sql role assignment list --account-name "$name" --resource-group "$rg_name" \
        --query "length([?principalId=='$principal_id' && ends_with(roleDefinitionId, '/$role') && ends_with(scope, '/$name')])" \
        -o tsv)" || exit 1
    if [ "$count" != "0" ]; then
        echo "  exists   $label on $name"
        existing=$((existing + 1))
    else
        az cosmosdb sql role assignment create \
            --account-name "$name" \
            --resource-group "$rg_name" \
            --principal-id "$principal_id" \
            --role-definition-id "$role" \
            --scope "/" \
            --only-show-errors --output none || exit 1
        echo "  created  $label on $name"
        created=$((created + 1))
    fi
}

# graph_query <kusto-query> <jmespath-query>
# Runs an Azure Resource Graph query against $sub_id and returns the JMESPath selection as tsv.
graph_query() {
    az rest --method post \
        --url "https://management.azure.com/providers/Microsoft.ResourceGraph/resources?api-version=2022-10-01" \
        --body "{\"subscriptions\":[\"$sub_id\"],\"query\":\"$1\"}" \
        --query "$2" -o tsv
}

# show_resources <type> <id>...
# Writes the JSON array of the given resources, all of the given type, to stdout; used by
# export-rg-urls. az uses the provider's newest API version, which may not be available yet in
# the resources' region ("No registered resource provider found for location ... and API
# version ..."), so on failure the provider's older non-preview API versions are tried in turn.
show_resources() {
    local type="$1"
    shift
    local out versions version
    if out="$(az resource show --ids "$@" --output json 2>/dev/null)"; then
        echo "$out" | jq 'if type == "array" then . else [.] end'
        return 0
    fi

    versions="$(az provider show --namespace "${type%%/*}" --output json | jq -r --arg t "${type#*/}" '
        .resourceTypes[] | select((.resourceType | ascii_downcase) == ($t | ascii_downcase))
        | .apiVersions[] | select(test("preview") | not)')" || return 1
    for version in $versions; do
        if out="$(az resource show --ids "$@" --api-version "$version" --output json 2>/dev/null)"; then
            echo "  $type: using API version $version" >&2
            echo "$out" | jq 'if type == "array" then . else [.] end'
            return 0
        fi
    done

    # No version worked; run the default once more so that its error is displayed
    echo "Unable to show resources of type $type" >&2
    az resource show --ids "$@" --output none
    return 1
}

case "$function_name" in
    show)
        require_args 1
        echo "Showing resource group: $rg_name"
        az group show --name "$rg_name" --output json > tmp/rg-show.json
        ;;
    export)
        require_args 1
        mkdir -p tmp
        export_file="tmp/rg-export-$rg_name.json"
        echo "Exporting resource group: $rg_name -> $export_file"
        az group export --name "$rg_name" --output json > "$export_file" || exit 1
        echo "done"
        ;;
    show-user)
        mkdir -p tmp
        echo "Showing signed-in user -> tmp/user-show.json, tmp/user-id-show.json"
        az ad signed-in-user show --output json > tmp/user-show.json || exit 1
        az ad signed-in-user show --query id --output json > tmp/user-id-show.json || exit 1
        ;;
    user_roles_assign)
        require_args 1
        if [ -z "$user_id" ]; then
            principal_id="$(az ad signed-in-user show --query id -o tsv)" || exit 1
            user_name="$(az ad signed-in-user show --query userPrincipalName -o tsv)" || exit 1
        else
            principal_id="$(az ad user show --id "$user_id" --query id -o tsv)" || exit 1
            user_name="$(az ad user show --id "$user_id" --query userPrincipalName -o tsv)" || exit 1
        fi

        echo "Subscription:     $(az account show --query name -o tsv)"
        echo "Resource Group:   $rg_name"
        echo "User:             $user_name"
        echo "Principal ID:     $principal_id"
        echo ""

        created=0
        existing=0

        resources="$(az resource list --resource-group "$rg_name" \
            --query "[].[id, name, type, kind]" -o tsv)" || exit 1
        if [ -z "$resources" ]; then
            echo "No resources found in resource group $rg_name"
            exit 1
        fi

        while IFS=$'\t' read -r id name type kind; do
            type_lc="$(echo "$type" | tr '[:upper:]' '[:lower:]')"
            kind_lc="$(echo "$kind" | tr '[:upper:]' '[:lower:]')"
            case "$type_lc" in
                microsoft.cognitiveservices/accounts)
                    echo "$name ($type, $kind)"
                    if [ "$kind_lc" = "aiservices" ]; then
                        assign_role "$id" "$name" "$AZURE_AI_USER" "Azure AI User"
                        assign_role "$id" "$name" "$AZURE_AI_PROJECT_MANAGER" "Azure AI Project Manager"
                    fi
                    assign_role "$id" "$name" "$COGNITIVE_SERVICES_USER" "Cognitive Services User"
                    ;;
                microsoft.storage/storageaccounts)
                    echo "$name ($type)"
                    assign_role "$id" "$name" "$STORAGE_BLOB_DATA_CONTRIBUTOR" "Storage Blob Data Contributor"
                    ;;
                microsoft.keyvault/vaults)
                    echo "$name ($type)"
                    assign_role "$id" "$name" "$KEY_VAULT_SECRETS_OFFICER" "Key Vault Secrets Officer"
                    ;;
                microsoft.containerregistry/registries)
                    echo "$name ($type)"
                    assign_role "$id" "$name" "$ACR_PUSH" "AcrPush"
                    ;;
                microsoft.search/searchservices)
                    echo "$name ($type)"
                    assign_role "$id" "$name" "$SEARCH_SERVICE_CONTRIBUTOR" "Search Service Contributor"
                    assign_role "$id" "$name" "$SEARCH_INDEX_DATA_CONTRIBUTOR" "Search Index Data Contributor"
                    ;;
                microsoft.insights/components)
                    echo "$name ($type)"
                    assign_role "$id" "$name" "$MONITORING_METRICS_PUBLISHER" "Monitoring Metrics Publisher"
                    ;;
                microsoft.operationalinsights/workspaces)
                    echo "$name ($type)"
                    assign_role "$id" "$name" "$LOG_ANALYTICS_READER" "Log Analytics Reader"
                    ;;
                microsoft.documentdb/databaseaccounts)
                    if [ "$kind_lc" = "globaldocumentdb" ]; then
                        echo "$name ($type, $kind)"
                        assign_cosmos_role "$id" "$name" "$COSMOS_DB_BUILT_IN_DATA_READER" \
                            "Cosmos DB Built-in Data Reader"
                        assign_cosmos_role "$id" "$name" "$COSMOS_DB_BUILT_IN_DATA_CONTRIBUTOR" \
                            "Cosmos DB Built-in Data Contributor"
                    fi
                    ;;
            esac
        done <<< "$resources"

        echo ""
        echo "$created role assignment(s) created, $existing already existed"
        echo "New assignments can take several minutes to take effect."
        ;;
    update-firewall-ip)
        require_args 1
        account_name=""
        ips=""
        remove_others="false"
        set -- "${@:3}"
        while [ $# -gt 0 ]; do
            case "$1" in
                -a|--allowed-ips) ips="${2:-}"; shift; [ $# -gt 0 ] && shift ;;
                --remove-others)  remove_others="true"; shift ;;
                *)                account_name="$1"; shift ;;
            esac
        done

        if [ -z "$ips" ]; then
            ips="$(curl -fsS --max-time 10 https://api.ipify.org)"
        fi
        # One IP per line, without any /32 suffix
        ips="$(echo "$ips" | tr ',; ' '\n\n\n' | tr -d '\r' | sed -e 's|/32$||' -e '/^$/d' | sort -u)"
        if [ -z "$ips" ]; then
            echo "Error: unable to determine public IP address" >&2
            exit 1
        fi

        if [ -n "$account_name" ]; then
            accounts="$account_name"
        else
            accounts="$(az cognitiveservices account list -g "$rg_name" \
                --query "[?kind=='AIServices'].name" -o tsv)" || exit 1
        fi
        if [ -z "$accounts" ]; then
            echo "No Foundry (AIServices) accounts found in resource group $rg_name"
            exit 1
        fi

        echo "Resource Group:  $rg_name"
        echo "Allowed IPs:     $(echo $ips)"
        echo "Remove others:   $remove_others"

        for name in $accounts; do
            echo
            echo "Foundry account: $name"

            # Rules may be stored as either '1.2.3.4' or '1.2.3.4/32'.
            current="$(az cognitiveservices account network-rule list -g "$rg_name" -n "$name" \
                --query "ipRules[].value" -o tsv)" || exit 1

            for ip in $ips; do
                if echo "$current" | sed 's|/32$||' | grep -qx "$ip"; then
                    echo "    $ip is already allowed"
                else
                    echo "    adding $ip"
                    az cognitiveservices account network-rule add -g "$rg_name" -n "$name" \
                        --ip-address "$ip" --only-show-errors -o none || exit 1
                fi
            done

            if [ "$remove_others" = "true" ]; then
                for old in $current; do
                    if ! echo "$ips" | grep -qx "${old%/32}"; then
                        echo "    removing $old"
                        az cognitiveservices account network-rule remove -g "$rg_name" -n "$name" \
                            --ip-address "$old" --only-show-errors -o none || exit 1
                    fi
                done
            fi

            # IP rules only take effect when public access is enabled and the default action is Deny.
            az cognitiveservices account show -g "$rg_name" -n "$name" \
                --query "{publicNetworkAccess: properties.publicNetworkAccess, defaultAction: properties.networkAcls.defaultAction, ipRules: properties.networkAcls.ipRules[].value}" \
                -o json | sed 's/^/    /'
        done

        echo
        echo "Done. Firewall changes can take a few minutes to take effect."
        ;;
    rg-ownership)
        sub_id="$(az account show --query id -o tsv)" || exit 1
        sub_name="$(az account show --query name -o tsv)" || exit 1
        email="${2:-$(az ad signed-in-user show --query mail -o tsv)}"
        email="$(echo "$email" | tr 'A-Z' 'a-z')"
        if [ -z "$email" ]; then
            echo "Unable to determine your email address; pass it as an argument: $0 rg-ownership <email>"
            exit 1
        fi

        echo "Subscription: $sub_name ($sub_id)"
        echo "Creator:      $email"
        echo

        rgs="resourcecontainers | where type == 'microsoft.resources/subscriptions/resourcegroups'"
        rows="$(graph_query \
            "$rgs | where tolower(tostring(tags.Creator)) == '$email' | project name, location, created=tostring(tags.CreationDate), expires=tostring(tags.ExpirationDate) | order by name asc" \
            "data[].[name, location, created, expires]")" || exit 1

        printf "%-45s %-15s %-12s %-12s\n" "Resource Group" "Location" "Created" "Expires"
        printf "%-45s %-15s %-12s %-12s\n" "--------------" "--------" "-------" "-------"
        count=0
        while IFS=$'\t' read -r name loc created expires; do
            [ -z "$name" ] && continue
            printf "%-45s %-15s %-12s %-12s\n" "$name" "$loc" "$created" "$expires"
            count=$((count + 1))
        done <<< "$rows"

        untagged="$(graph_query "$rgs | where isempty(tags.Creator) | count" "data[0].Count")" || exit 1

        echo
        echo "$count resource group(s) created by $email"
        echo "$untagged resource group(s) in the subscription have no Creator tag and were not checked"
        ;;
    export-rg-urls)
        # This function is useful for getting values for your .env file.
        require_args 1
        if ! command -v jq > /dev/null 2>&1; then
            echo "jq is required; see https://jqlang.org/download/"
            exit 1
        fi

        mkdir -p tmp
        show_file="tmp/rg-resources-$rg_name.json"
        json_file="tmp/rg-urls-$rg_name.json"
        tsv_file="tmp/rg-urls-$rg_name.tsv"

        echo "Listing resources in resource group: $rg_name"
        resources="$(az resource list --resource-group "$rg_name" --query "[].[type, id]" --output tsv)" || exit 1
        if [ -z "$resources" ]; then
            echo "No resources found in resource group: $rg_name"
            exit 1
        fi

        # Show the resources one type at a time, so that each type can fall back to an older
        # API version (see show_resources) without affecting the others
        echo "Showing $(echo "$resources" | wc -l | tr -d ' ') resources -> $show_file"
        parts_file="tmp/rg-resources-$rg_name.parts.json"
        : > "$parts_file"
        while IFS= read -r type; do
            # Read ids one per line; some resource ids contain spaces
            ids=()
            while IFS= read -r id; do
                [ -n "$id" ] && ids+=("$id")
            done < <(echo "$resources" | awk -F'\t' -v t="$type" '$1 == t { print $2 }')
            show_resources "$type" "${ids[@]}" >> "$parts_file" || exit 1
        done < <(echo "$resources" | cut -f1 | sort -u)
        jq -s 'add' "$parts_file" > "$show_file" || exit 1
        rm -f "$parts_file"

        echo "Extracting endpoints -> $json_file"
        jq '
          [ (if type == "array" then .[] else . end)
            | . as $r
            | [ ($r.properties // {}) | paths(strings) as $p
                | { key: ($p | map(tostring) | join(".")), url: ($r.properties | getpath($p)) }
                | select(.key | test("(?i)(endpoint|url|uri|hostname|fqdn|loginserver|domainname)"))
                | select(.key | test("(?i)(privateendpoint|networkacls)") | not)
                | select(.url | test("^(https?|wss?)://|^[A-Za-z0-9-]+(\\.[A-Za-z0-9-]+)+(:[0-9]+)?$"))
                | .url |= (if test("^[a-z]+://") then . else "https://" + . end) ]
            | unique | sort_by(.key)
            | .[] | { name: $r.name, type: $r.type, key: .key, url: .url } ]
        ' "$show_file" > "$json_file" || exit 1

        jq -r '(["name", "type", "key", "url"] | @tsv), (.[] | [.name, .type, .key, .url] | @tsv)' \
            "$json_file" > "$tsv_file"
        echo "Writing tsv -> $tsv_file"

        echo ""
        jq . "$json_file"
        echo ""
        echo "$(jq length "$json_file") endpoints"
        echo "done"
        ;;
    get-ai-project-id)
        rg_name="${rg_name:-$AZURE_RESOURCE_GROUP}"
        if [ -z "$rg_name" ] || [ -z "$AZURE_FOUNDRY_NAME" ] || [ -z "$AZURE_FOUNDRY_PROJECT_NAME" ]; then
            echo "AZURE_FOUNDRY_NAME and AZURE_FOUNDRY_PROJECT_NAME must be set, and AZURE_RESOURCE_GROUP"
            echo "unless the resource group is given"
            usage
        fi
        az resource show \
            --resource-group "$rg_name" \
            --namespace Microsoft.CognitiveServices \
            --parent "accounts/$AZURE_FOUNDRY_NAME" \
            --resource-type projects \
            --name "$AZURE_FOUNDRY_PROJECT_NAME" \
            --query id -o tsv || exit 1
        ;;
    my-ip)
        curl -fsS --max-time 10 https://api.ipify.org || exit 1
        echo
        ;;
    show-foundry-project)
        rg_name="${rg_name:-$AZURE_RESOURCE_GROUP}"
        if [ -z "$rg_name" ] || [ -z "$AZURE_FOUNDRY_NAME" ] || [ -z "$AZURE_FOUNDRY_PROJECT_NAME" ]; then
            echo "AZURE_FOUNDRY_NAME and AZURE_FOUNDRY_PROJECT_NAME must be set, and AZURE_RESOURCE_GROUP"
            echo "unless the resource group is given"
            usage
        fi
        mkdir -p tmp
        out_file="tmp/foundry-project-$AZURE_FOUNDRY_PROJECT_NAME.json"
        az cognitiveservices account project show \
            --resource-group "$rg_name" \
            --name "$AZURE_FOUNDRY_NAME" \
            --project-name "$AZURE_FOUNDRY_PROJECT_NAME" \
            > "$out_file" || exit 1

        cat "$out_file"
        echo "done"
        ;;
    *)
        usage
        ;;
esac
