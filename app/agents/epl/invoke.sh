#!/bin/bash

# cd app/agents/epl
azd env select epl-dev 2>/dev/null || azd env new epl-dev
azd env set AZURE_FOUNDRY_PROJECT_URL "https://cjoakimforge1020a.services.ai.azure.com/api/projects/epl"
azd env set AZURE_TENANT_ID "ttt"
azd env set AZURE_SUBSCRIPTION_ID "sss"

azd ai agent invoke epl "Which team won the 2023-24 Premier League?" --protocol responses


# $ ./invoke.sh
# New environment 'epl-dev' was set as default

# ERROR: failed to resolve agent service "epl" for remote invoke: checking whether agent "epl" exists in the adopted Foundry project: GET https://cjoakimforge1020a.services.ai.azure.com/api/projects/epl/agents/epl
# --------------------------------------------------------------------------------
# RESPONSE 403: 403 Forbidden
# ERROR CODE: UserError
# --------------------------------------------------------------------------------
# {
#   "error": {
#     "code": "UserError",
#     "severity": null,
#     "message": "Identity(object id: a0896f6d-1210-4923-91db-cd7b5d621228) does not have permissions for Microsoft.CognitiveServices/accounts/AIServices/agents/read actions. Please refer to https://learn.microsoft.com/en-us/azure/foundry/concepts/rbac-foundry to fix the permissions issue.",
#     "messageFormat": null,
#     "messageParameters": null,
#     "referenceCode": null,
#     "detailsUri": null,
#     "target": null,
#     "details": [],
#     "innerError": {
#       "code": "ForbiddenError",
#       "innerError": null
#     },
#     "debugInfo": null,
#     "additionalInfo": null
#   },
#   "correlation": {
#     "operation": "16638ec9epl8f3f6f31a2a9c628ad8990",
#     "request": "78d829663db3c974"
#   },
#   "environment": "southcentralus",
#   "location": "southcentralus",
#   "time": "2026-10-20T21:48:46.6545753+00:00",
#   "componentName": null,
#   "statusCode": 403
# }
