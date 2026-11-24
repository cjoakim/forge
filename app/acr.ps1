# Azure Container Registry (ACR) operations: list the registry's contents, delete an image,
# or open its firewall to public traffic.
# The registry is given as its name (e.g. crcjoakimforge1022a) or its URL (login server),
# e.g. crcjoakimforge1022a.azurecr.io, the same form as AZURE_CONTAINER_REGISTRY_ENDPOINT
# in .env; a leading https:// is allowed.
#
# The first arg is the function; the second is the registry; the third, for delete, is the image.
#
# list:         lists each repository's images (manifests), newest first, including untagged
#               ones: their tags, last update time, and image as <repository>@<digest>, which
#               can be passed to delete as is. Your IP must be allowed through the registry's
#               firewall (see arm/ip_address.ps1 update_ip).
# delete:       deletes an image without prompting. The image is given in one of two forms:
#                 by tag:    <repository>:<tag>, e.g. c1:azd-deploy-1793051434; the repository
#                            is the name on list's "repository:" line, and the tag is one of
#                            the values in that row's Tags column
#                 by digest: <repository>@<digest>, e.g. c1@sha256:3f2a...; this is list's
#                            Image column, which can be copied as is, and is the only way to
#                            delete an untagged image
#               Either form deletes the whole image (manifest), including every other tag on it,
#               not just the one tag; an agent version that uses the image can no longer pull it.
#               Your IP must be allowed through the registry's firewall.
# allow_public: sets the registry's default network action to Allow, so that Foundry hosted
#               agents can pull their container images. Existing IP rules are kept; they have
#               no effect while the default action is Allow. This opens the registry to all
#               public traffic. It's a fallback for when Foundry can't pull through the
#               registry's private endpoint in the agent VNet (see arm/template.json); check
#               ContainerRegistryLoginEvents in Log Analytics to see where the pulls come from.
#
# Usage:
#   .\acr.ps1 list         <acr-name-or-url>
#   .\acr.ps1 delete       <acr-name-or-url> <repository>:<tag>|<repository>@<digest>
#   .\acr.ps1 allow_public <acr-name-or-url>
# Examples:
#   .\acr.ps1 list         crcjoakimforge1022a.azurecr.io
#   .\acr.ps1 delete       crcjoakimforge1022a.azurecr.io c1:azd-deploy-1793051434
#   .\acr.ps1 delete       crcjoakimforge1022a.azurecr.io c1@sha256:3f2a...
#   .\acr.ps1 allow_public crcjoakimforge1022a

param(
    [string]$Function,
    [string]$Acr,
    [string]$Image
)

function Show-Usage {
    Write-Host "Usage:"
    Write-Host "  .\acr.ps1 list         <acr-name-or-url>"
    Write-Host "  .\acr.ps1 delete       <acr-name-or-url> <repository>:<tag>|<repository>@<digest>"
    Write-Host "  .\acr.ps1 allow_public <acr-name-or-url>"
    exit 1
}

if ([string]::IsNullOrWhiteSpace($Acr)) { Show-Usage }

# https://myacr.azurecr.io/ -> myacr.azurecr.io -> myacr; a bare name is used as is
$acrName = ($Acr -replace '^https://', '').Split('/')[0].Split('.')[0]
$acrHost = "$acrName.azurecr.io"

switch ($Function) {
    "list" {
        $repositories = @(az acr repository list --name $acrName -o tsv)
        if ($LASTEXITCODE -ne 0) { exit 1 }

        if ($repositories.Count -eq 0) {
            Write-Host "ACR $acrHost has no repositories"
            exit 0
        }

        foreach ($repository in $repositories) {
            Write-Host ''
            Write-Host "repository: $repository"
            az acr manifest list-metadata `
                --registry $acrName `
                --name $repository `
                --orderby time_desc `
                --query "[].{tags: tags && join(', ', tags) || '', lastUpdated: lastUpdateTime, image: join('@', ['$repository', digest])}" `
                --only-show-errors `
                -o table
        }
    }
    "delete" {
        if ([string]::IsNullOrWhiteSpace($Image)) { Show-Usage }
        Write-Host "deleting image $acrHost/$Image ..."
        az acr repository delete --name $acrName --image $Image --yes
        if ($LASTEXITCODE -ne 0) { exit 1 }

        Write-Host "deleted"
    }
    "allow_public" {
        az acr update -n $acrName --default-action Allow
    }
    default {
        Show-Usage
    }
}
