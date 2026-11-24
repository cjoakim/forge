# This script demonstrates the Agent generation and deployment process.
# The generated agents are git-ignored.
#
# Usage:   .\demo.ps1

# remove any existing example agents
Remove-Item -Recurse -Force agents\xpa -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force agents\xca -ErrorAction SilentlyContinue

New-Item -ItemType Directory -Force -Path tmp | Out-Null
. .\.venv\Scripts\Activate.ps1

Write-Host ""
Write-Host "==== Updating azd extensions ===="
azd extension update --all
Start-Sleep -Seconds 8

Write-Host ""
Write-Host "==== Setting OS environment variables ===="
.\set-os-env.ps1
Start-Sleep -Seconds 8

Write-Host ""
Write-Host "==== Generating the generator configuration file ===="
uv run main-generator.py gen_generator_config
Start-Sleep -Seconds 8

Write-Host ""
Write-Host "==== Displaying the generator configuration file ===="
Get-Content generator_config.json
Start-Sleep -Seconds 12

Write-Host ""
Write-Host "==== Generating example prompt agent ===="
uv run main-generator.py gen_prompt_agent xpA   # xpa = Example Prompt Agent
Start-Sleep -Seconds 8

Write-Host ""
Write-Host "==== Generating example code agent ===="
uv run main-generator.py gen_code_agent xcA     # xca = Example Code Agent
Start-Sleep -Seconds 8

Write-Host "==== Deploying example prompt agent ===="
.\deploy-foundry-prompt-agent.ps1 aif-cjoakimforge1102b epl 2025-11-15-preview agents/xpa/azure.yaml
Start-Sleep -Seconds 8

Write-Host ""
Write-Host "==== Setting azd environment variables for the xca code agent ===="
.\set-azd-env.ps1 agents/xca
Start-Sleep -Seconds 8

Write-Host ""
Write-Host "==== Changing to the xca code agent directory ===="
# Push-Location so that the caller's directory is restored when the script ends,
# since a Set-Location in a PowerShell script persists in the session
Push-Location agents\xca
try {
    Get-Location
    Start-Sleep -Seconds 8

    Write-Host ""
    Write-Host "==== Executing the generated script to copy the core python src/ files ===="
    .\copy-master-src.ps1
    Start-Sleep -Seconds 8

    Write-Host ""
    Write-Host "==== Displaying the generated agent-specific readme.md ===="
    Get-Content readme.md
    Start-Sleep -Seconds 12

    Write-Host ""
    Write-Host "==== Running the python xca agent locally.  ===="
    Write-Host "Enter the prompt: What teams are in the EPL?"
    Write-Host "CTRL-C when done. "
    Write-Host "Then run the generated .\deploy.ps1 script to deploy the xca code agent."
    Start-Sleep -Seconds 8

    azd ai agent run xca --environment xca
}
finally {
    Pop-Location
}

# What teams are in the epl, where are they located, and who are their goalkeepers?
