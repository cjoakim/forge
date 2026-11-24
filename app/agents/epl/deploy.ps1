# Build and deploy this hosted agent with azd, then check that the new version works.
# The steps are:
#   1. azd deploy: builds the container image, pushes it to ACR, and creates a new agent version;
#      the script stops here if the deploy fails, so the later steps never run against the
#      previous version
#   2. assigns the agent's Entra identity its roles (see below); existing assignments are left
#      as is, so this does nothing after the first deploy unless the roles were removed
#   3. waits <wait-seconds> (default 30) for the new version to start
#   4. azd ai agent show: displays the agent's status and version
#   5. azd ai agent invoke: sends the agent a test question
#   6. azd ai agent monitor: displays the last 100 lines of the agent's console logs
#
# Foundry creates an Entra agent identity (instance_identity) per agent, shared by all of its
# versions; the agent's container authenticates as this identity. azd deploy doesn't give it any
# data-plane roles, so step 2 assigns it 'Foundry User' (formerly 'Azure AI User') so the
# container can call the model deployment, plus data-plane roles on AI Search (default
# 'Search Index Data Contributor') and Storage (default 'Storage Blob Data Contributor') so it
# can read and write index documents and blobs. New role assignments can take a few minutes to
# take effect.
#
# The agent name and the azd environment name are both the name of this script's directory
# (e.g. epl for agents\epl). The script can be run from any directory; azd commands run in this
# script's directory, where azure.yaml is.
#
# Settings are read from the azd environment, which is created from the app/.env file.
# Required:
#   AZURE_SUBSCRIPTION_ID, AZURE_RESOURCE_GROUP, AZURE_FOUNDRY_NAME, AZURE_FOUNDRY_PROJECT_NAME
# Optional; a service gets no role when its name is empty or its FORGE_AGENT_*_ROLE setting
# is 'none':
#   AZURE_AI_SEARCH_NAME, AZURE_STORAGE_ACCOUNT_NAME
#   FORGE_AGENT_ROLE             default 'Foundry User'; role name or id for the agent identity
#   FORGE_AGENT_ROLE_SCOPE       default project; 'project' or 'account'
#   FORGE_AGENT_SEARCH_ROLE      default 'Search Index Data Contributor'; 'none' to skip
#   FORGE_AGENT_STORAGE_ROLE     default 'Storage Blob Data Contributor'; 'none' to skip
#
# Prerequisite: create the agent's azd environment from the app/.env file by running this from
# the app directory:
#   .\set-azd-env.ps1 agents\epl
#
# Usage:   .\deploy.ps1 [wait-seconds]
# Examples:
#   .\deploy.ps1
#   .\deploy.ps1 60
#   .\agents\epl\deploy.ps1             (from the app directory)

param(
    [ValidateRange(0, [int]::MaxValue)]
    [int]$WaitSeconds = 30
)

Push-Location $PSScriptRoot
try {
    $agentName = Split-Path -Leaf $PSScriptRoot
    $envName = $agentName

    # The value of the named entry in the azd environment, else the default.
    function AzdEnvOrDefault([string]$name, [string]$default) {
        $value = azd env get-value $name --environment $envName 2>$null
        if ($LASTEXITCODE -ne 0 -or -not $value) { return $default }
        return ($value | Out-String).Trim()
    }

    # The value of the named entry in the azd environment; exits if it's missing or empty.
    function AzdEnvRequired([string]$name) {
        $value = AzdEnvOrDefault $name ''
        if (-not $value) {
            Write-Host "$name must be set in azd environment $envName; see set-azd-env.ps1"
            exit 1
        }
        return $value
    }

    $subscriptionId = AzdEnvRequired 'AZURE_SUBSCRIPTION_ID'
    $resourceGroup = AzdEnvRequired 'AZURE_RESOURCE_GROUP'
    $foundryName = AzdEnvRequired 'AZURE_FOUNDRY_NAME'
    $projectName = AzdEnvRequired 'AZURE_FOUNDRY_PROJECT_NAME'
    $searchName = AzdEnvOrDefault 'AZURE_AI_SEARCH_NAME' ''
    $storageName = AzdEnvOrDefault 'AZURE_STORAGE_ACCOUNT_NAME' ''
    $role = AzdEnvOrDefault 'FORGE_AGENT_ROLE' 'Foundry User'
    $roleScope = AzdEnvOrDefault 'FORGE_AGENT_ROLE_SCOPE' 'project'
    $searchRole = AzdEnvOrDefault 'FORGE_AGENT_SEARCH_ROLE' 'Search Index Data Contributor'
    $storageRole = AzdEnvOrDefault 'FORGE_AGENT_STORAGE_ROLE' 'Storage Blob Data Contributor'

    if ($searchRole -eq 'none') { $searchName = '' }
    if ($storageRole -eq 'none') { $storageName = '' }
    if ($roleScope -ne 'project' -and $roleScope -ne 'account') {
        Write-Host "FORGE_AGENT_ROLE_SCOPE must be 'project' or 'account'"
        exit 1
    }

    Write-Host "Building and deploying agent $agentName to azd environment $envName ..."
    azd deploy $agentName --environment $envName --no-prompt
    if ($LASTEXITCODE -ne 0) { exit 1 }

    Write-Host "Getting the resource ids for the role assignment scopes ..."
    $accountId = az cognitiveservices account show --subscription $subscriptionId `
        --resource-group $resourceGroup --name $foundryName --query id -o tsv
    if ($LASTEXITCODE -ne 0) { exit 1 }
    if ($roleScope -eq 'account') {
        $scope = $accountId
    }
    else {
        $scope = "$accountId/projects/$projectName"
    }
    $searchId = ''
    if ($searchName) {
        $searchId = az search service show --subscription $subscriptionId `
            --resource-group $resourceGroup --name $searchName --query id -o tsv
        if ($LASTEXITCODE -ne 0) { exit 1 }
    }
    $storageId = ''
    if ($storageName) {
        $storageId = az storage account show --subscription $subscriptionId `
            --resource-group $resourceGroup --name $storageName --query id -o tsv
        if ($LASTEXITCODE -ne 0) { exit 1 }
    }

    Write-Host "Getting the $agentName agent identity ..."
    $principalId = az cognitiveservices agent show `
        --subscription $subscriptionId `
        --account-name $foundryName `
        --project-name $projectName `
        --name $agentName `
        --only-show-errors `
        --query instance_identity.principal_id `
        -o tsv
    if ($LASTEXITCODE -ne 0) { exit 1 }
    if (-not $principalId) {
        Write-Host "agent identity not found for agent $agentName"
        exit 1
    }
    Write-Host "agent identity principal id: $principalId"

    # Assign the role to the agent identity unless it already has it.
    function Grant-AgentRole([string]$roleName, [string]$roleScopeId) {
        # List by scope and filter on principalId, rather than using --assignee, which looks up the
        # principal in Microsoft Graph and can fail for agent identities.
        $existing = az role assignment list --subscription $subscriptionId --scope $roleScopeId --role $roleName `
            --query "[?principalId=='$principalId'] | length(@)" -o tsv
        if ($existing -ne '0') {
            Write-Host "role '$roleName' is already assigned to the agent identity"
            return
        }
        # A new agent identity can take a little while to replicate in Entra, so retry.
        for ($attempt = 1; $attempt -le 5; $attempt++) {
            Write-Host "assigning role '$roleName' to the agent identity (attempt $attempt) ..."
            az role assignment create `
                --subscription $subscriptionId `
                --assignee-object-id $principalId `
                --assignee-principal-type ServicePrincipal `
                --role $roleName `
                --scope $roleScopeId `
                --only-show-errors `
                -o none
            if ($LASTEXITCODE -eq 0) {
                Write-Host "role assigned"
                return
            }
            if ($attempt -eq 5) {
                Write-Host "ERROR: role assignment failed"
                exit 1
            }
            Start-Sleep -Seconds 15
        }
    }

    Grant-AgentRole $role $scope
    if ($searchId) { Grant-AgentRole $searchRole $searchId }
    if ($storageId) { Grant-AgentRole $storageRole $storageId }

    Write-Host "Waiting $WaitSeconds seconds for the new version to start ..."
    Start-Sleep -Seconds $WaitSeconds

    Write-Host "Showing $agentName agent ..."
    azd ai agent show $agentName --environment $envName
    if ($LASTEXITCODE -ne 0) { exit 1 }

    # See https://aka.ms/azd-agents-invoke
    # Write-Host "Invoking $agentName agent ..."
    # azd ai agent invoke $agentName 'where is raleigh?' --environment $envName
    # if ($LASTEXITCODE -ne 0) { exit 1 }

    # Write-Host "Monitoring $agentName agent, tail 100 ..."
    # azd ai agent monitor $agentName --tail 100 --environment $envName
}
finally {
    Pop-Location
}
