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
# Usage:   .\set-azd-env.ps1 <agent-dir>
# Example: .\set-azd-env.ps1 agents/epl

param(
    [string]$AgentDir
)

if ([string]::IsNullOrWhiteSpace($AgentDir)) {
    Write-Host "Usage: .\set-azd-env.ps1 <agent-dir>"
    exit 1
}
if (-not (Test-Path (Join-Path $AgentDir 'azure.yaml'))) {
    Write-Host "$(Join-Path $AgentDir 'azure.yaml') not found"
    exit 1
}
$envName = Split-Path -Leaf (Resolve-Path $AgentDir).Path

$dotenvFile = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot '.env'))
if (-not (Test-Path $dotenvFile)) {
    Write-Host "$dotenvFile not found; see dotenv-example"
    exit 1
}

# The names and values of the entries in the .env file
$envVars = @()
foreach ($line in Get-Content $dotenvFile) {
    if ($line -match '^\s*(#.*)?$') { continue }
    if ($line -notmatch '^\s*(export\s+)?([^=]*?)\s*=(.*)$') { continue }
    $name = $Matches[2]
    $value = $Matches[3].Trim() -replace '^"(.*)"$', '$1' -replace "^'(.*)'$", '$1'
    if ($name -notmatch '^[A-Za-z_][A-Za-z0-9_]*$') {
        Write-Host "skipping invalid name: $name"
        continue
    }
    $envVars += [PSCustomObject]@{ Name = $name; Value = $value }
}
if ($envVars.Count -eq 0) {
    Write-Host "no environment variables found in $dotenvFile"
    exit 1
}

# The last entry wins if a name is repeated
$subscriptionId = ($envVars | Where-Object { $_.Name -eq 'AZURE_SUBSCRIPTION_ID' } | Select-Object -Last 1).Value
$region = ($envVars | Where-Object { $_.Name -eq 'AZURE_REGION' } | Select-Object -Last 1).Value

Push-Location $AgentDir
try {
    Write-Host "deleting azd environment $envName in $AgentDir ..."
    azd env remove $envName --force 2>$null
    if ($LASTEXITCODE -ne 0) { Write-Host "azd environment $envName not found" }

    Write-Host "creating azd environment $envName in $AgentDir ..."
    $newArgs = @()
    if ($subscriptionId) { $newArgs += @('--subscription', $subscriptionId) }
    if ($region) { $newArgs += @('--location', $region) }
    azd env new $envName @newArgs
    if ($LASTEXITCODE -ne 0) { exit 1 }

    Write-Host "setting $($envVars.Count) environment variables from $dotenvFile in azd environment $envName ..."
    foreach ($envVar in $envVars) {
        Write-Host "  $($envVar.Name)"
        # PowerShell before 7.3 (including Windows PowerShell 5.1) drops empty-string
        # arguments to native commands, so pass an empty value as "" instead
        $value = $envVar.Value
        if ($value -eq '' -and $PSVersionTable.PSVersion -lt [version]'7.3') { $value = '""' }
        azd env set --environment $envName $envVar.Name $value
        if ($LASTEXITCODE -ne 0) { exit 1 }
    }

    Write-Host "list of values in azd environment $envName in directory $AgentDir"
    azd env get-values --environment $envName | Sort-Object
}
finally {
    Pop-Location
}
