# Azure resource group operations.
#
# The first arg is the function; the remaining args are always in the same order:
# <resource-group-name> <user-upn-or-object-id | foundry-account-name>
# except show-user and my-ip, which take no args, rg-ownership, whose only arg is an email, and
# get-ai-project-id and show-foundry-project, whose resource group defaults to $env:AZURE_RESOURCE_GROUP.
#
# show:      shows the resource group, writing its JSON to tmp\rg-show.json
# export:    exports the resource group as an ARM template, writing it to
#            tmp\rg-export-<resource-group-name>.json
# show-user: shows the signed-in Azure user, writing its JSON to tmp\user-show.json
#            and its object id to tmp\user-id-show.json
# user_roles_assign: post-deployment, grants a user the data-plane and management RBAC roles
#            needed to work with the resource group's Forge resources from a laptop
#            (az login / DefaultAzureCredential). The user defaults to the signed-in user.
#            You must have Owner, or User Access Administrator, on the resource group.
#            Cosmos DB for NoSQL accounts get the Cosmos DB Built-in Data Reader and Data
#            Contributor roles, which are Cosmos data-plane roles (az cosmosdb sql role assignment),
#            not Azure RBAC roles, assigned at the account scope.
#            New role assignments can take several minutes to propagate.
# update-firewall-ip: updates the Foundry firewall so that it allows your current public IP
#            address, or the IPs given with -AllowedIps (comma or semicolon separated).
#            Foundry projects don't have their own firewall; they inherit the network rules of
#            their parent Foundry account (Microsoft.CognitiveServices/accounts, kind AIServices).
#            If the account name is omitted, every Foundry account in the resource group is
#            updated. Existing IP rules are kept unless -RemoveOthers is given.
#            See also arm\ip_address.ps1 update_ip, which updates all of the sandbox's PaaS firewalls.
# rg-ownership: lists the resource groups in the current subscription whose Creator tag is the
#            given email (default: the signed-in user's mail address), with their location and
#            CreationDate / ExpirationDate tags, and counts the groups that have no Creator tag.
# export-rg-urls: lists the PaaS services in the resource group with all of their endpoints/URLs,
#            writing them to tmp\rg-urls-<resource-group-name>.json and .tsv (the full resource
#            JSON goes to tmp\rg-resources-<resource-group-name>.json). Endpoints are discovered
#            generically by walking each resource's properties for endpoint-like keys (endpoint,
#            endpoints.*, *Url, *Uri, hostName, fqdn, loginServer, ...) with URL/hostname values;
#            resources without endpoints (identities, workspaces, alerts, etc.) are omitted.
# get-ai-project-id: displays the ARM resource ID of the Foundry project (AZURE_AI_PROJECT_ID).
#            Requires AZURE_FOUNDRY_NAME and AZURE_FOUNDRY_PROJECT_NAME, and AZURE_RESOURCE_GROUP
#            unless the resource group is given.
# my-ip:     displays your workstation's current public IP address, as seen by the Azure firewalls.
# show-foundry-project: shows the Foundry project, a child resource of the Foundry (AIServices)
#            account, writing its JSON to tmp\foundry-project-<project-name>.json.
#            Requires AZURE_FOUNDRY_NAME and AZURE_FOUNDRY_PROJECT_NAME, and AZURE_RESOURCE_GROUP
#            unless the resource group is given.
#
# Usage:
#   .\rg.ps1 show      <resource-group-name>
#   .\rg.ps1 export    <resource-group-name>
#   .\rg.ps1 show-user
#   .\rg.ps1 user_roles_assign <resource-group-name> [user-upn-or-object-id]
#   .\rg.ps1 update-firewall-ip <resource-group-name> [foundry-account-name] [-AllowedIps <ip[,ip...]>] [-RemoveOthers]
#   .\rg.ps1 rg-ownership [email]
#   .\rg.ps1 export-rg-urls <resource-group-name> > outfile
#   .\rg.ps1 get-ai-project-id [resource-group-name]
#   .\rg.ps1 my-ip
#   .\rg.ps1 show-foundry-project [resource-group-name]
# Examples:
#   .\rg.ps1 show      cjoakimforge1030x
#   .\rg.ps1 export    cjoakimforge1030x
#   .\rg.ps1 show-user
#   .\rg.ps1 user_roles_assign cjoakimforge1030x
#   .\rg.ps1 user_roles_assign cjoakimforge1030x someone.else@somehost.com
#   .\rg.ps1 update-firewall-ip cjoakimforge1030x
#   .\rg.ps1 update-firewall-ip cjoakimforge1030x forge-foundry-12345
#   .\rg.ps1 update-firewall-ip cjoakimforge1030x -AllowedIps "203.0.113.10,198.51.100.20"
#   .\rg.ps1 update-firewall-ip cjoakimforge1030x -RemoveOthers
#   .\rg.ps1 rg-ownership
#   .\rg.ps1 rg-ownership someone.else@somehost.com
#   .\rg.ps1 export-rg-urls cjoakimforge1030x > tmp\rg-urls.json
#   .\rg.ps1 get-ai-project-id
#   .\rg.ps1 get-ai-project-id cjoakimforge1030x
#   .\rg.ps1 my-ip
#   .\rg.ps1 show-foundry-project
#   .\rg.ps1 show-foundry-project cjoakimforge1030x

param(
    [string]$Function,
    [string]$ResourceGroupName,
    [string]$Name,
    [string]$AllowedIps,
    [switch]$RemoveOthers
)

function Show-Usage {
    Write-Host "Usage:"
    Write-Host "  .\rg.ps1 show      <resource-group-name>"
    Write-Host "  .\rg.ps1 export    <resource-group-name>"
    Write-Host "  .\rg.ps1 show-user"
    Write-Host "  .\rg.ps1 user_roles_assign <resource-group-name> [user-upn-or-object-id]"
    Write-Host "  .\rg.ps1 update-firewall-ip <resource-group-name> [foundry-account-name] [-AllowedIps <ip[,ip...]>] [-RemoveOthers]"
    Write-Host "  .\rg.ps1 rg-ownership [email]"
    Write-Host "  .\rg.ps1 export-rg-urls <resource-group-name>"
    Write-Host "  .\rg.ps1 get-ai-project-id [resource-group-name]"
    Write-Host "  .\rg.ps1 my-ip"
    Write-Host "  .\rg.ps1 show-foundry-project [resource-group-name]"
    exit 1
}

# Exits with the usage message unless the first N of the resource group args are given.
function Assert-Args([int]$Count) {
    $values = @($ResourceGroupName)
    for ($i = 0; $i -lt $Count; $i++) {
        if ([string]::IsNullOrWhiteSpace($values[$i])) { Show-Usage }
    }
}

# Built-in Azure role definition IDs, used by user_roles_assign
$AzureAiUser = "53ca6127-db72-4b80-b1b0-d745d6d5456d"
$AzureAiProjectManager = "eadc314b-1a2d-4efa-be10-5d325db5065e"
$CognitiveServicesUser = "a97b65f3-24c7-4388-baec-2e87135dc908"
$StorageBlobDataContributor = "ba92f5b4-2d11-453d-a403-e96b0029c9fe"
$KeyVaultSecretsOfficer = "b86a8fe4-44ce-4948-aee5-eccb2c155cd7"
$AcrPush = "8311e382-0749-4cb8-b61a-304f252e45ec"
$SearchServiceContributor = "7ca78c08-252a-4471-8644-bb5ff32d4ba0"
$SearchIndexDataContributor = "8ebe5a00-799e-43f5-93ac-243d3dce84a7"
$MonitoringMetricsPublisher = "3913510d-42f4-4e42-8a64-420c390055eb"
$LogAnalyticsReader = "73c42c96-874c-492b-b04d-ab87d138a893"

# Built-in Cosmos DB for NoSQL data-plane role definition IDs, used by user_roles_assign
$CosmosDbBuiltInDataReader = "00000000-0000-0000-0000-000000000001"
$CosmosDbBuiltInDataContributor = "00000000-0000-0000-0000-000000000002"

# Assigns the role to $script:principalId at the scope unless it's already assigned there.
function Set-RoleAssignment([string]$Scope, [string]$Name, [string]$Role, [string]$Label) {
    $count = az role assignment list --assignee $script:principalId --role $Role --scope $Scope `
        --query "length([?scope=='$Scope'])" -o tsv
    if ($LASTEXITCODE -ne 0) { exit 1 }
    if ($count -ne "0") {
        Write-Host "  exists   $Label on $Name"
        $script:existing++
    }
    else {
        az role assignment create `
            --assignee-object-id $script:principalId `
            --assignee-principal-type User `
            --role $Role `
            --scope $Scope `
            --only-show-errors --output none
        if ($LASTEXITCODE -ne 0) { exit 1 }
        Write-Host "  created  $Label on $Name"
        $script:created++
    }
}

# Assigns the Cosmos DB data-plane role to $script:principalId at the account scope unless it's
# already assigned there.
function Set-CosmosRoleAssignment([string]$Scope, [string]$Name, [string]$Role, [string]$Label) {
    $count = az cosmosdb sql role assignment list --account-name $Name --resource-group $ResourceGroupName `
        --query "length([?principalId=='$script:principalId' && ends_with(roleDefinitionId, '/$Role') && ends_with(scope, '/$Name')])" `
        -o tsv
    if ($LASTEXITCODE -ne 0) { exit 1 }
    if ($count -ne "0") {
        Write-Host "  exists   $Label on $Name"
        $script:existing++
    }
    else {
        az cosmosdb sql role assignment create `
            --account-name $Name `
            --resource-group $ResourceGroupName `
            --principal-id $script:principalId `
            --role-definition-id $Role `
            --scope "/" `
            --only-show-errors --output none
        if ($LASTEXITCODE -ne 0) { exit 1 }
        Write-Host "  created  $Label on $Name"
        $script:created++
    }
}

# Runs an Azure Resource Graph query against $script:subId and returns the response's data rows.
# The request body goes through a file, since quoting JSON for a native command differs between
# Windows PowerShell 5.1 and PowerShell 7.
function Invoke-GraphQuery([string]$Query) {
    $bodyFile = New-TemporaryFile
    @{ subscriptions = @($script:subId); query = $Query } | ConvertTo-Json -Compress |
        Out-File -FilePath $bodyFile -Encoding ascii
    $result = az rest --method post `
        --url "https://management.azure.com/providers/Microsoft.ResourceGraph/resources?api-version=2022-10-01" `
        --body "@$bodyFile" `
        -o json
    $code = $LASTEXITCODE
    Remove-Item -LiteralPath $bodyFile
    if ($code -ne 0) { exit 1 }
    return ($result -join "`n" | ConvertFrom-Json).data
}

# Join path segments as 'a.b.0.c'; used by export-rg-urls
function Join-KeyPath([string]$path, [string]$segment) {
    if ($path -eq '') { $segment } else { "$path.$segment" }
}

# Recursively yield every string leaf under $node as @{ Key = 'a.b.0.c'; Value = '...' };
# used by export-rg-urls
function Get-StringLeaves($node, [string]$path) {
    if ($null -eq $node) { return }
    if ($node -is [string]) {
        @{ Key = $path; Value = $node }
    }
    elseif ($node -is [System.Collections.IList]) {
        for ($i = 0; $i -lt $node.Count; $i++) {
            Get-StringLeaves $node[$i] (Join-KeyPath $path $i)
        }
    }
    elseif ($node -is [System.Management.Automation.PSCustomObject]) {
        foreach ($prop in $node.PSObject.Properties) {
            Get-StringLeaves $prop.Value (Join-KeyPath $path $prop.Name)
        }
    }
}

# Show-Resources <type> <ids>: returns the given resources, all of the given type, as objects;
# used by export-rg-urls. az uses the provider's newest API version, which may not be available
# yet in the resources' region ("No registered resource provider found for location ... and API
# version ..."), so on failure the provider's older non-preview API versions are tried in turn.
function Show-Resources([string]$type, [string[]]$ids) {
    $out = az resource show --ids @ids --output json 2>$null
    if ($LASTEXITCODE -eq 0) { return @(($out -join "`n") | ConvertFrom-Json) }

    $namespace, $resourceType = $type -split '/', 2
    $provider = (az provider show --namespace $namespace --output json) -join "`n" | ConvertFrom-Json
    if ($LASTEXITCODE -ne 0) { exit 1 }
    $versions = @($provider.resourceTypes |
        Where-Object { $_.resourceType -eq $resourceType } |
        ForEach-Object { $_.apiVersions } |
        Where-Object { $_ -notmatch 'preview' })

    foreach ($version in $versions) {
        $out = az resource show --ids @ids --api-version $version --output json 2>$null
        if ($LASTEXITCODE -eq 0) {
            Write-Host "  ${type}: using API version $version"
            return @(($out -join "`n") | ConvertFrom-Json)
        }
    }

    # No version worked; run the default once more so that its error is displayed
    Write-Host "Unable to show resources of type $type"
    az resource show --ids @ids --output none
    exit 1
}

switch ($Function) {
    "show" {
        Assert-Args 1
        Write-Host "Showing resource group: $ResourceGroupName"
        az group show --name $ResourceGroupName --output json | Out-File -FilePath (Join-Path "tmp" "rg-show.json") -Encoding utf8
        if ($LASTEXITCODE -ne 0) { exit 1 }
    }
    "export" {
        Assert-Args 1
        New-Item -ItemType Directory -Force -Path tmp | Out-Null
        $exportFile = Join-Path "tmp" "rg-export-$ResourceGroupName.json"

        # Out-File -Encoding utf8 avoids the UTF-16 output of '>' in Windows PowerShell 5.1
        Write-Host "Exporting resource group: $ResourceGroupName -> $exportFile"
        az group export --name $ResourceGroupName --output json | Out-File -FilePath $exportFile -Encoding utf8
        if ($LASTEXITCODE -ne 0) { exit 1 }

        Write-Host "done"
    }
    "show-user" {
        New-Item -ItemType Directory -Force -Path tmp | Out-Null
        $userFile = Join-Path "tmp" "user-show.json"
        $userIdFile = Join-Path "tmp" "user-id-show.json"

        Write-Host "Showing signed-in user -> $userFile, $userIdFile"
        az ad signed-in-user show --output json | Out-File -FilePath $userFile -Encoding utf8
        if ($LASTEXITCODE -ne 0) { exit 1 }
        az ad signed-in-user show --query id --output json | Out-File -FilePath $userIdFile -Encoding utf8
        if ($LASTEXITCODE -ne 0) { exit 1 }
    }
    "user_roles_assign" {
        Assert-Args 1
        if ([string]::IsNullOrWhiteSpace($Name)) {
            $script:principalId = az ad signed-in-user show --query id -o tsv
            if ($LASTEXITCODE -ne 0) { exit 1 }
            $userName = az ad signed-in-user show --query userPrincipalName -o tsv
            if ($LASTEXITCODE -ne 0) { exit 1 }
        }
        else {
            $script:principalId = az ad user show --id $Name --query id -o tsv
            if ($LASTEXITCODE -ne 0) { exit 1 }
            $userName = az ad user show --id $Name --query userPrincipalName -o tsv
            if ($LASTEXITCODE -ne 0) { exit 1 }
        }

        Write-Host "Subscription:     $(az account show --query name -o tsv)"
        Write-Host "Resource Group:   $ResourceGroupName"
        Write-Host "User:             $userName"
        Write-Host "Principal ID:     $script:principalId"
        Write-Host ""

        $script:created = 0
        $script:existing = 0

        $resources = az resource list --resource-group $ResourceGroupName `
            --query "[].{id: id, name: name, type: type, kind: kind}" -o json | ConvertFrom-Json
        if ($LASTEXITCODE -ne 0) { exit 1 }
        if (-not $resources) {
            Write-Host "No resources found in resource group $ResourceGroupName"
            exit 1
        }

        foreach ($r in $resources) {
            $resourceId = $r.id
            $resourceName = $r.name
            $kindLc = "$($r.kind)".ToLower()
            switch ("$($r.type)".ToLower()) {
                "microsoft.cognitiveservices/accounts" {
                    Write-Host "$resourceName ($($r.type), $($r.kind))"
                    if ($kindLc -eq "aiservices") {
                        Set-RoleAssignment $resourceId $resourceName $AzureAiUser "Azure AI User"
                        Set-RoleAssignment $resourceId $resourceName $AzureAiProjectManager "Azure AI Project Manager"
                    }
                    Set-RoleAssignment $resourceId $resourceName $CognitiveServicesUser "Cognitive Services User"
                }
                "microsoft.storage/storageaccounts" {
                    Write-Host "$resourceName ($($r.type))"
                    Set-RoleAssignment $resourceId $resourceName $StorageBlobDataContributor "Storage Blob Data Contributor"
                }
                "microsoft.keyvault/vaults" {
                    Write-Host "$resourceName ($($r.type))"
                    Set-RoleAssignment $resourceId $resourceName $KeyVaultSecretsOfficer "Key Vault Secrets Officer"
                }
                "microsoft.containerregistry/registries" {
                    Write-Host "$resourceName ($($r.type))"
                    Set-RoleAssignment $resourceId $resourceName $AcrPush "AcrPush"
                }
                "microsoft.search/searchservices" {
                    Write-Host "$resourceName ($($r.type))"
                    Set-RoleAssignment $resourceId $resourceName $SearchServiceContributor "Search Service Contributor"
                    Set-RoleAssignment $resourceId $resourceName $SearchIndexDataContributor "Search Index Data Contributor"
                }
                "microsoft.insights/components" {
                    Write-Host "$resourceName ($($r.type))"
                    Set-RoleAssignment $resourceId $resourceName $MonitoringMetricsPublisher "Monitoring Metrics Publisher"
                }
                "microsoft.operationalinsights/workspaces" {
                    Write-Host "$resourceName ($($r.type))"
                    Set-RoleAssignment $resourceId $resourceName $LogAnalyticsReader "Log Analytics Reader"
                }
                "microsoft.documentdb/databaseaccounts" {
                    if ($kindLc -eq "globaldocumentdb") {
                        Write-Host "$resourceName ($($r.type), $($r.kind))"
                        Set-CosmosRoleAssignment $resourceId $resourceName $CosmosDbBuiltInDataReader `
                            "Cosmos DB Built-in Data Reader"
                        Set-CosmosRoleAssignment $resourceId $resourceName $CosmosDbBuiltInDataContributor `
                            "Cosmos DB Built-in Data Contributor"
                    }
                }
            }
        }

        Write-Host ""
        Write-Host "$script:created role assignment(s) created, $script:existing already existed"
        Write-Host "New assignments can take several minutes to take effect."
    }
    "update-firewall-ip" {
        Assert-Args 1
        if ([string]::IsNullOrWhiteSpace($AllowedIps)) {
            try { $AllowedIps = Invoke-RestMethod -Uri "https://api.ipify.org" -TimeoutSec 10 }
            catch { $AllowedIps = "" }
        }
        # One entry per IP, without any /32 suffix
        $ips = @($AllowedIps -split '[,; ]' |
            ForEach-Object { $_.Trim() -replace '/32$', '' } |
            Where-Object { $_ } |
            Sort-Object -Unique)
        if ($ips.Count -eq 0) {
            Write-Host "Error: unable to determine public IP address"
            exit 1
        }

        if (-not [string]::IsNullOrWhiteSpace($Name)) {
            $accounts = @($Name)
        }
        else {
            $accounts = @(az cognitiveservices account list -g $ResourceGroupName `
                --query "[?kind=='AIServices'].name" -o tsv)
            if ($LASTEXITCODE -ne 0) { exit 1 }
        }
        if ($accounts.Count -eq 0) {
            Write-Host "No Foundry (AIServices) accounts found in resource group $ResourceGroupName"
            exit 1
        }

        Write-Host "Resource Group:  $ResourceGroupName"
        Write-Host "Allowed IPs:     $($ips -join ' ')"
        Write-Host "Remove others:   $($RemoveOthers.IsPresent.ToString().ToLower())"

        foreach ($accountName in $accounts) {
            Write-Host ""
            Write-Host "Foundry account: $accountName"

            # Rules may be stored as either '1.2.3.4' or '1.2.3.4/32'.
            $current = @(az cognitiveservices account network-rule list -g $ResourceGroupName -n $accountName `
                --query "ipRules[].value" -o tsv)
            if ($LASTEXITCODE -ne 0) { exit 1 }
            $currentIps = @($current | ForEach-Object { $_ -replace '/32$', '' })

            foreach ($ip in $ips) {
                if ($currentIps -contains $ip) {
                    Write-Host "    $ip is already allowed"
                }
                else {
                    Write-Host "    adding $ip"
                    az cognitiveservices account network-rule add -g $ResourceGroupName -n $accountName `
                        --ip-address $ip --only-show-errors -o none
                    if ($LASTEXITCODE -ne 0) { exit 1 }
                }
            }

            if ($RemoveOthers) {
                foreach ($old in $current) {
                    if ($ips -notcontains ($old -replace '/32$', '')) {
                        Write-Host "    removing $old"
                        az cognitiveservices account network-rule remove -g $ResourceGroupName -n $accountName `
                            --ip-address $old --only-show-errors -o none
                        if ($LASTEXITCODE -ne 0) { exit 1 }
                    }
                }
            }

            # IP rules only take effect when public access is enabled and the default action is Deny.
            az cognitiveservices account show -g $ResourceGroupName -n $accountName `
                --query "{publicNetworkAccess: properties.publicNetworkAccess, defaultAction: properties.networkAcls.defaultAction, ipRules: properties.networkAcls.ipRules[].value}" `
                -o json | ForEach-Object { Write-Host "    $_" }
        }

        Write-Host ""
        Write-Host "Done. Firewall changes can take a few minutes to take effect."
    }
    "rg-ownership" {
        # The email, if given, is the first arg after the function.
        $email = $ResourceGroupName
        $script:subId = az account show --query id -o tsv
        if ($LASTEXITCODE -ne 0) { exit 1 }
        $subName = az account show --query name -o tsv
        if ($LASTEXITCODE -ne 0) { exit 1 }
        if ([string]::IsNullOrWhiteSpace($email)) {
            $email = az ad signed-in-user show --query mail -o tsv
        }
        if ([string]::IsNullOrWhiteSpace($email)) {
            Write-Host "Unable to determine your email address; pass it as an argument: .\rg.ps1 rg-ownership <email>"
            exit 1
        }
        $email = $email.Trim().ToLower()

        Write-Host "Subscription: $subName ($script:subId)"
        Write-Host "Creator:      $email"
        Write-Host ""

        $rgs = "resourcecontainers | where type == 'microsoft.resources/subscriptions/resourcegroups'"
        $rows = @(Invoke-GraphQuery "$rgs | where tolower(tostring(tags.Creator)) == '$email' | project name, location, created=tostring(tags.CreationDate), expires=tostring(tags.ExpirationDate) | order by name asc")

        $format = "{0,-45} {1,-15} {2,-12} {3,-12}"
        Write-Host ($format -f "Resource Group", "Location", "Created", "Expires")
        Write-Host ($format -f "--------------", "--------", "-------", "-------")
        $count = 0
        foreach ($row in $rows) {
            if (-not $row.name) { continue }
            Write-Host ($format -f $row.name, $row.location, $row.created, $row.expires)
            $count++
        }

        $untagged = (Invoke-GraphQuery "$rgs | where isempty(tags.Creator) | count")[0].Count

        Write-Host ""
        Write-Host "$count resource group(s) created by $email"
        Write-Host "$untagged resource group(s) in the subscription have no Creator tag and were not checked"
    }
    "export-rg-urls" {
        # This function is useful for getting values for your .env file.
        Assert-Args 1
        $keyPattern = '(?i)(endpoint|url|uri|hostname|fqdn|loginserver|domainname)'
        $excludePattern = '(?i)(privateendpoint|networkacls)'
        $valuePattern = '^(https?|wss?)://|^[A-Za-z0-9-]+(\.[A-Za-z0-9-]+)+(:[0-9]+)?$'

        New-Item -ItemType Directory -Force -Path tmp | Out-Null
        $showFile = Join-Path "tmp" "rg-resources-$ResourceGroupName.json"
        $jsonFile = Join-Path "tmp" "rg-urls-$ResourceGroupName.json"
        $tsvFile = Join-Path "tmp" "rg-urls-$ResourceGroupName.tsv"

        Write-Host "Listing resources in resource group: $ResourceGroupName"
        $list = @((az resource list --resource-group $ResourceGroupName --query "[].{type: type, id: id}" --output json) -join "`n" | ConvertFrom-Json)
        if ($LASTEXITCODE -ne 0) { exit 1 }
        if ($list.Count -eq 0) {
            Write-Host "No resources found in resource group: $ResourceGroupName"
            exit 1
        }

        # Show the resources one type at a time, so that each type can fall back to an older
        # API version (see Show-Resources) without affecting the others.
        # Out-File -Encoding utf8 avoids the UTF-16 output of '>' in Windows PowerShell 5.1
        Write-Host "Showing $($list.Count) resources -> $showFile"
        $resources = @()
        foreach ($group in ($list | Group-Object type)) {
            $resources += Show-Resources $group.Name @($group.Group | ForEach-Object { $_.id })
        }
        ConvertTo-Json -InputObject $resources -Depth 100 | Out-File -FilePath $showFile -Encoding utf8

        Write-Host "Extracting endpoints -> $jsonFile"

        $rows = foreach ($r in $resources) {
            Get-StringLeaves $r.properties '' |
                Where-Object {
                    $_.Key -match $keyPattern -and
                    $_.Key -notmatch $excludePattern -and
                    $_.Value -cmatch $valuePattern
                } |
                ForEach-Object {
                    # -cmatch: case-sensitive, like jq's test() in rg.sh
                    $url = if ($_.Value -cmatch '^[a-z]+://') { $_.Value } else { "https://$($_.Value)" }
                    [PSCustomObject]@{ name = $r.name; type = $r.type; key = $_.Key; url = $url }
                } |
                Sort-Object key, url -Unique
        }
        $rows = @($rows)

        ConvertTo-Json -InputObject $rows -Depth 3 | Out-File -FilePath $jsonFile -Encoding utf8

        Write-Host "Writing tsv -> $tsvFile"
        $lines = @("name`ttype`tkey`turl") + ($rows | ForEach-Object { "$($_.name)`t$($_.type)`t$($_.key)`t$($_.url)" })
        $lines | Out-File -FilePath $tsvFile -Encoding utf8

        Write-Host ""
        Get-Content -Raw -Path $jsonFile | Write-Host
        Write-Host "$($rows.Count) endpoints"
        Write-Host "done"
    }
    "get-ai-project-id" {
        if ([string]::IsNullOrWhiteSpace($ResourceGroupName)) { $ResourceGroupName = $env:AZURE_RESOURCE_GROUP }
        if ([string]::IsNullOrWhiteSpace($ResourceGroupName) -or
            [string]::IsNullOrWhiteSpace($env:AZURE_FOUNDRY_NAME) -or
            [string]::IsNullOrWhiteSpace($env:AZURE_FOUNDRY_PROJECT_NAME)) {
            Write-Host "AZURE_FOUNDRY_NAME and AZURE_FOUNDRY_PROJECT_NAME must be set, and AZURE_RESOURCE_GROUP"
            Write-Host "unless the resource group is given"
            Show-Usage
        }
        az resource show `
            --resource-group $ResourceGroupName `
            --namespace Microsoft.CognitiveServices `
            --parent "accounts/$env:AZURE_FOUNDRY_NAME" `
            --resource-type projects `
            --name $env:AZURE_FOUNDRY_PROJECT_NAME `
            --query id -o tsv
        if ($LASTEXITCODE -ne 0) { exit 1 }
    }
    "my-ip" {
        try { (Invoke-RestMethod -Uri 'https://api.ipify.org' -TimeoutSec 10).ToString().Trim() }
        catch {
            Write-Host "Error: $($_.Exception.Message)"
            exit 1
        }
    }
    "show-foundry-project" {
        if ([string]::IsNullOrWhiteSpace($ResourceGroupName)) { $ResourceGroupName = $env:AZURE_RESOURCE_GROUP }
        if ([string]::IsNullOrWhiteSpace($ResourceGroupName) -or
            [string]::IsNullOrWhiteSpace($env:AZURE_FOUNDRY_NAME) -or
            [string]::IsNullOrWhiteSpace($env:AZURE_FOUNDRY_PROJECT_NAME)) {
            Write-Host "AZURE_FOUNDRY_NAME and AZURE_FOUNDRY_PROJECT_NAME must be set, and AZURE_RESOURCE_GROUP"
            Write-Host "unless the resource group is given"
            Show-Usage
        }
        New-Item -ItemType Directory -Force -Path tmp | Out-Null
        $outFile = Join-Path "tmp" "foundry-project-$env:AZURE_FOUNDRY_PROJECT_NAME.json"

        # Out-File -Encoding utf8 avoids the UTF-16 output of '>' in Windows PowerShell 5.1
        az cognitiveservices account project show `
            --resource-group $ResourceGroupName `
            --name $env:AZURE_FOUNDRY_NAME `
            --project-name $env:AZURE_FOUNDRY_PROJECT_NAME `
            --output json | Out-File -FilePath $outFile -Encoding utf8
        if ($LASTEXITCODE -ne 0) { exit 1 }

        Get-Content $outFile
        Write-Host "done"
    }
    default {
        Show-Usage
    }
}
