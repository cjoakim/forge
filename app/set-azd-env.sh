#!/bin/bash

# Recreate an agent's azd environment, named after the agent directory, from the
# entries in the app/.env file.
# Deletes the environment (if present), creates it again with the subscription and
# location from the AZURE_SUBSCRIPTION_ID and AZURE_REGION entries, then sets every
# entry in it with 'azd env set'.
# Blank lines and # comments are skipped; an optional leading 'export' and surrounding
# single or double quotes on values are removed. Values are not expanded or evaluated.
# azd commands run in the given agent directory (where azure.yaml is), so the environment
# is stored in <agent-dir>/.azure/<env-name>/.
# The environment name is the basename of <agent-dir>; e.g. c1 for agents/c1.
#
# Usage:   ./set-azd-env.sh <agent-dir>
# Example: ./set-azd-env.sh agents/epl

agent_dir="$1"
if [ -z "$agent_dir" ]; then
    echo "Usage: $0 <agent-dir>"
    exit 1
fi
if [ ! -f "$agent_dir/azure.yaml" ]; then
    echo "$agent_dir/azure.yaml not found"
    exit 1
fi
env_name="$(basename "$(cd "$agent_dir" && pwd)")"

dotenv_file="$(cd "$(dirname "$0")" && pwd)/.env"
if [ ! -f "$dotenv_file" ]; then
    echo "$dotenv_file not found; see dotenv-example"
    exit 1
fi

# names and values of the entries in the .env file
var_names=()
var_values=()
while IFS= read -r line || [ -n "$line" ]; do
    line="${line%$'\r'}"
    # skip blank lines, comments, and lines without '='
    case "$line" in
        ''|[[:space:]]*'#'*|'#'*) continue ;;
        *=*) ;;
        *) continue ;;
    esac
    name="${line%%=*}"
    value="${line#*=}"
    name="$(echo "$name" | sed -E 's/^[[:space:]]*(export[[:space:]]+)?//; s/[[:space:]]+$//')"
    value="$(printf '%s' "$value" | sed -E 's/^[[:space:]]+//; s/[[:space:]]+$//; s/^"(.*)"$/\1/; s/^'\''(.*)'\''$/\1/')"
    if ! echo "$name" | grep -Eq '^[A-Za-z_][A-Za-z0-9_]*$'; then
        echo "skipping invalid name: $name"
        continue
    fi
    var_names+=("$name")
    var_values+=("$value")
done < "$dotenv_file"
if [ ${#var_names[@]} -eq 0 ]; then
    echo "no environment variables found in $dotenv_file"
    exit 1
fi

# the value of the named entry in the .env file; the last one wins if repeated
dotenv_value() {
    local i result=""
    for i in "${!var_names[@]}"; do
        if [ "${var_names[$i]}" = "$1" ]; then
            result="${var_values[$i]}"
        fi
    done
    printf '%s' "$result"
}
subscription_id="$(dotenv_value AZURE_SUBSCRIPTION_ID)"
region="$(dotenv_value AZURE_REGION)"

original_dir="$(pwd)"
cd "$agent_dir" || exit 1

echo "deleting azd environment $env_name in $agent_dir ..."
azd env remove "$env_name" --force 2>/dev/null || echo "azd environment $env_name not found"

echo "creating azd environment $env_name in $agent_dir ..."
new_args=()
if [ -n "$subscription_id" ]; then
    new_args+=(--subscription "$subscription_id")
fi
if [ -n "$region" ]; then
    new_args+=(--location "$region")
fi
if ! azd env new "$env_name" "${new_args[@]}"; then
    cd "$original_dir"
    exit 1
fi

echo "setting ${#var_names[@]} environment variables from $dotenv_file in azd environment $env_name ..."
for i in "${!var_names[@]}"; do
    echo "  ${var_names[$i]}"
    if ! azd env set --environment "$env_name" "${var_names[$i]}" "${var_values[$i]}"; then
        cd "$original_dir"
        exit 1
    fi
done

echo "list of values in azd environment $env_name in directory $agent_dir"
azd env get-values --environment "$env_name" | sort

cd "$original_dir"
