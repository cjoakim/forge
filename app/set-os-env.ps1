# Set an OS environment variable in the current session for every entry in the app/.env file.
# Blank lines and # comments are skipped; an optional leading 'export' and surrounding
# single or double quotes on values are removed. Values are not expanded or evaluated.
# The names of the variables set are displayed, then all AZURE_ and FORGE_ variables in the
# environment are displayed with their values.
#
# PowerShell environment variables are process-scoped, so they persist in your session
# after the script exits; unlike set-os-env.sh, it does not need to be dot-sourced.
#
# Usage:   .\set-os-env.ps1

$dotenvFile = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot '.env'))
if (-not (Test-Path $dotenvFile)) {
    Write-Host "$dotenvFile not found; see dotenv-example"
    return
}

$count = 0
foreach ($line in Get-Content $dotenvFile) {
    if ($line -match '^\s*(#.*)?$') { continue }
    if ($line -notmatch '^\s*(export\s+)?([^=]*?)\s*=(.*)$') { continue }
    $name = $Matches[2]
    $value = $Matches[3].Trim() -replace '^"(.*)"$', '$1' -replace "^'(.*)'$", '$1'
    if ($name -notmatch '^[A-Za-z_][A-Za-z0-9_]*$') {
        Write-Host "skipping invalid name: $name"
        continue
    }
    [System.Environment]::SetEnvironmentVariable($name, $value, 'Process')
    Write-Host "set $name"
    $count++
}
Write-Host "$count environment variables set from $dotenvFile"

Write-Host ""
Write-Host "AZURE_ and FORGE_ environment variables:"
Get-ChildItem Env: | Where-Object { $_.Name -match '^(AZURE_|FORGE_)' } | Sort-Object Name |
    ForEach-Object { Write-Host "$($_.Name)=$($_.Value)" }
