#!/bin/bash

# Companion script to invoke main-foundry.py.

echo "=== list_available_models ==="
uv run main-foundry.py list_available_models

echo "=== list_model_prices southcentralus --refresh ==="
uv run main-foundry.py list_model_prices southcentralus --refresh

echo "=== produce_models_report ==="
uv run main-foundry.py produce_models_report

echo "=== deploy_models config/model-deployments-config.json ==="
uv run main-foundry.py deploy_models config/model-deployments-config.json

echo "=== list_model_deployments ==="
uv run main-foundry.py list_model_deployments

echo "=== invoke_agent config/invoke-agents-config.json python-stdlib ==="
uv run main-foundry.py invoke_agent config/invoke-agents-config.json python-stdlib-uuid

echo "=== listing files in ../data/foundry ==="
ls -al ../data/foundry
