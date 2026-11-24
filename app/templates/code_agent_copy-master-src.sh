#!/bin/bash

# Copy the "master" version of the python modules in the app/src directory
# into the agent's src/{{agent_name}}/src directory.
#
# Usage: ./copy-src.sh

cd "$(dirname "$0")" || exit 1

app_src="../../src"
agent_src="src/{{agent_name}}/src"

# Files to copy, relative to app/src.
files=(
    __init__.py
    ai/__init__.py
    ai/ai_search_util.py
    io/__init__.py
    io/fs.py
    io/storage_util.py
    os/__init__.py
    os/env.py
    os/system.py
)

for f in "${files[@]}"; do
    mkdir -p "$(dirname "$agent_src/$f")"
    cp "$app_src/$f" "$agent_src/$f" || exit 1
    echo "copied $app_src/$f -> $agent_src/$f"
done
