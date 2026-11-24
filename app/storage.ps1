# Blob storage operations against an Azure Storage account: list the account's containers,
# create or delete a container, list a container's blobs, and upload, download, or delete a blob.
# Authenticates with your Entra ID (--auth-mode login), since the storage account doesn't
# allow shared keys; you need a data-plane role such as Storage Blob Data Contributor
# (or Storage Blob Data Reader for list-containers, list-container, and download-blob) on the account, and your IP must be
# allowed through its firewall (see arm/ip_address.ps1 update_ip).
#
# The first arg is the function; the remaining args are always in the same order:
# <storage-account-name> <container-name> <blob-name> <local-file-path>
#
# create-container: creates the container (an existing one is left as is), then lists the account's containers
# list-containers:  lists the containers in the account
# list-container:   lists the blobs in the container
# upload-blob:      uploads the local file to the blob; an existing blob is overwritten
# download-blob:    downloads the blob to the local file; its directory is created if needed,
#                   and an existing local file is overwritten
# delete-blob:      deletes the blob
# delete-container: deletes the container and all of its blobs
# test:             smoke-tests the other functions against a container named test: deletes it
#                   (if it exists) and re-creates it, lists it, uploads uv.lock to it, lists it
#                   again, downloads the blob to ~\Downloads\uv.lock (overwriting that file), then
#                   deletes the container
#
# Usage:
#   .\storage.ps1 create-container <storage-account-name> <container-name>
#   .\storage.ps1 list-containers  <storage-account-name>
#   .\storage.ps1 list-container   <storage-account-name> <container-name>
#   .\storage.ps1 upload-blob      <storage-account-name> <container-name> <blob-name> <local-file-path>
#   .\storage.ps1 download-blob    <storage-account-name> <container-name> <blob-name> <local-file-path>
#   .\storage.ps1 delete-blob      <storage-account-name> <container-name> <blob-name>
#   .\storage.ps1 delete-container <storage-account-name> <container-name>
#   .\storage.ps1 test             <storage-account-name>
# Examples:
#   .\storage.ps1 create-container stcjoakimforge1022a agents
#   .\storage.ps1 list-containers  stcjoakimforge1022a
#   .\storage.ps1 list-container   stcjoakimforge1022a agents
#   .\storage.ps1 upload-blob      stcjoakimforge1022a agents c1.txt tmp\c1.txt
#   .\storage.ps1 download-blob    stcjoakimforge1022a agents c1.txt tmp\c1.txt
#   .\storage.ps1 delete-blob      stcjoakimforge1022a agents c1.txt
#   .\storage.ps1 delete-container stcjoakimforge1022a agents
#   .\storage.ps1 test             stcjoakimforge1022a

param(
    [string]$Function,
    [string]$AccountName,
    [string]$ContainerName,
    [string]$BlobName,
    [string]$LocalFilename
)

function Show-Usage {
    Write-Host "Usage:"
    Write-Host "  .\storage.ps1 create-container <storage-account-name> <container-name>"
    Write-Host "  .\storage.ps1 list-containers  <storage-account-name>"
    Write-Host "  .\storage.ps1 list-container   <storage-account-name> <container-name>"
    Write-Host "  .\storage.ps1 upload-blob      <storage-account-name> <container-name> <blob-name> <local-file-path>"
    Write-Host "  .\storage.ps1 download-blob    <storage-account-name> <container-name> <blob-name> <local-file-path>"
    Write-Host "  .\storage.ps1 delete-blob      <storage-account-name> <container-name> <blob-name>"
    Write-Host "  .\storage.ps1 delete-container <storage-account-name> <container-name>"
    Write-Host "  .\storage.ps1 test             <storage-account-name>"
    exit 1
}

# Exits with the usage message unless the first N of account, container, blob, and local file are given.
function Assert-Args([int]$Count) {
    $values = @($AccountName, $ContainerName, $BlobName, $LocalFilename)
    for ($i = 0; $i -lt $Count; $i++) {
        if ([string]::IsNullOrWhiteSpace($values[$i])) { Show-Usage }
    }
}

switch ($Function) {
    "create-container" {
        Assert-Args 2
        az storage container create `
            --account-name $AccountName `
            --name $ContainerName `
            --auth-mode login
        if ($LASTEXITCODE -ne 0) { exit 1 }

        Write-Host "containers in storage account ${AccountName}:"
        az storage container list `
            --account-name $AccountName `
            --auth-mode login `
            --query "[].{name: name, lastModified: properties.lastModified}" `
            -o table
    }
    "list-containers" {
        Assert-Args 1
        Write-Host "containers in storage account ${AccountName}:"
        az storage container list `
            --account-name $AccountName `
            --auth-mode login `
            --query "[].{name: name, lastModified: properties.lastModified}" `
            -o table
    }
    "list-container" {
        Assert-Args 2
        Write-Host "blobs in container $ContainerName of storage account ${AccountName}:"
        az storage blob list `
            --account-name $AccountName `
            --container-name $ContainerName `
            --auth-mode login `
            --num-results '*' `
            --query "[].{name: name, size: properties.contentLength, lastModified: properties.lastModified}" `
            -o table
    }
    "upload-blob" {
        Assert-Args 4
        if (-not (Test-Path -LiteralPath $LocalFilename -PathType Leaf)) {
            Write-Host "file not found: $LocalFilename"
            exit 1
        }

        Write-Host "uploading $LocalFilename to $AccountName/$ContainerName/$BlobName ..."
        az storage blob upload `
            --account-name $AccountName `
            --container-name $ContainerName `
            --name $BlobName `
            --file $LocalFilename `
            --overwrite true `
            --auth-mode login `
            -o table
    }
    "download-blob" {
        Assert-Args 4
        $localDir = Split-Path -Parent $LocalFilename
        if ($localDir) { New-Item -ItemType Directory -Force -Path $localDir | Out-Null }

        Write-Host "downloading $AccountName/$ContainerName/$BlobName to $LocalFilename ..."
        az storage blob download `
            --account-name $AccountName `
            --container-name $ContainerName `
            --name $BlobName `
            --file $LocalFilename `
            --overwrite true `
            --auth-mode login `
            -o none
        if ($LASTEXITCODE -ne 0) { exit 1 }

        Get-Item -LiteralPath $LocalFilename
    }
    "delete-blob" {
        Assert-Args 3
        Write-Host "deleting $AccountName/$ContainerName/$BlobName ..."
        az storage blob delete `
            --account-name $AccountName `
            --container-name $ContainerName `
            --name $BlobName `
            --auth-mode login `
            -o none
        if ($LASTEXITCODE -ne 0) { exit 1 }

        Write-Host "deleted"
    }
    "delete-container" {
        Assert-Args 2
        Write-Host "deleting container $AccountName/$ContainerName ..."
        az storage container delete `
            --account-name $AccountName `
            --name $ContainerName `
            --auth-mode login `
            -o none
        if ($LASTEXITCODE -ne 0) { exit 1 }

        Write-Host "deleted"
    }
    "test" {
        Assert-Args 1
        $testContainer = "test"
        $testFile = "uv.lock"

        $exists = az storage container exists `
            --account-name $AccountName `
            --name $testContainer `
            --auth-mode login `
            --query exists `
            -o tsv
        if ($LASTEXITCODE -ne 0) { exit 1 }
        if ($exists -eq "true") {
            & $PSCommandPath delete-container $AccountName $testContainer
            if ($LASTEXITCODE -ne 0) { exit 1 }
        }

        # A deleted container's name can't be reused until Azure finishes deleting it, which can
        # take a minute or more; until then create reports created=false, so retry.
        Write-Host "creating container $AccountName/$testContainer ..."
        for ($attempt = 1; $attempt -le 18; $attempt++) {
            $created = az storage container create `
                --account-name $AccountName `
                --name $testContainer `
                --auth-mode login `
                --query created `
                -o tsv
            if ($created -eq "true") { break }
            Write-Host "container not created yet (attempt $attempt), retrying in 10 seconds ..."
            Start-Sleep -Seconds 10
        }
        if ($created -ne "true") {
            Write-Host "container $testContainer could not be created"
            exit 1
        }

        & $PSCommandPath list-container $AccountName $testContainer
        if ($LASTEXITCODE -ne 0) { exit 1 }
        & $PSCommandPath upload-blob $AccountName $testContainer $testFile $testFile
        if ($LASTEXITCODE -ne 0) { exit 1 }
        & $PSCommandPath list-container $AccountName $testContainer
        if ($LASTEXITCODE -ne 0) { exit 1 }
        & $PSCommandPath download-blob $AccountName $testContainer $testFile (Join-Path (Join-Path $HOME "Downloads") $testFile)
        if ($LASTEXITCODE -ne 0) { exit 1 }
        & $PSCommandPath delete-container $AccountName $testContainer
        if ($LASTEXITCODE -ne 0) { exit 1 }
    }
    default {
        Show-Usage
    }
}
