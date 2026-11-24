# Copy the "master" version of the python modules in the app/src directory
# into the agent's src/{{agent_name}}/src directory.
#
# Usage: .\copy-master-src.ps1

$ErrorActionPreference = 'Stop'
Push-Location -LiteralPath $PSScriptRoot
try {
    $appSrc = '../../src'
    $agentSrc = 'src/{{agent_name}}/src'

    # Files to copy, relative to app/src.
    $files = @(
        '__init__.py'
        'ai/__init__.py'
        'ai/ai_search_util.py'
        'io/__init__.py'
        'io/fs.py'
        'io/storage_util.py'
        'os/__init__.py'
        'os/env.py'
        'os/system.py'
    )

    foreach ($f in $files) {
        $dest = Join-Path $agentSrc $f
        New-Item -ItemType Directory -Force -Path (Split-Path $dest -Parent) | Out-Null
        Copy-Item -LiteralPath (Join-Path $appSrc $f) -Destination $dest -Force
        Write-Host "copied $appSrc/$f -> $agentSrc/$f"
    }
}
finally {
    Pop-Location
}
