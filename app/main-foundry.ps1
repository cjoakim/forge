# Companion script to invoke main-foundry.py.

Write-Host "=== list_available_models ==="
uv run main-foundry.py list_available_models

Write-Host "=== list_model_prices southcentralus --refresh ==="
uv run main-foundry.py list_model_prices southcentralus --refresh

Write-Host "=== produce_models_report ==="
uv run main-foundry.py produce_models_report

Write-Host "=== deploy_models config/model-deployments-config.json ==="
uv run main-foundry.py deploy_models config/model-deployments-config.json

Write-Host "=== list_model_deployments ==="
uv run main-foundry.py list_model_deployments

Write-Host "=== invoke_agent config/invoke-agents-config.json python-stdlib ==="
uv run main-foundry.py invoke_agent config/invoke-agents-config.json python-stdlib-uuid

Write-Host "=== listing files in ..\data\foundry ==="
Get-ChildItem -Force ..\data\foundry
