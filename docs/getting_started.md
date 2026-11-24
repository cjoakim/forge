# Getting Started

This page outlines how to get started with the Forge accelerator.

## Pre-Deployment

### Install the necessary tools on your laptop/workstation

- Operating System: Windows 11 or macOS 
- [python.org Python version 3.14.x](https://www.python.org/downloads/)
- [az Azure CLI](https://learn.microsoft.com/en-us/cli/azure/install-azure-cli-windows?view=azure-cli-latest&pivots=winget)
- [azd Azure Developer CLI](https://learn.microsoft.com/en-us/azure/developer/azure-developer-cli/install-azd)
- [uv - the Python package and project manager tool](https://docs.astral.sh/uv/getting-started/installation/)
- [ruff (optional) - the Python linter and code formatter ](https://docs.astral.sh/ruff/)

### Get your Azure Subscription ID

Use of this accelerator requires the following:

- An **Entra Identity** (i.e. - a logon ID)
- Access to an **Azure Subscription** 
- Your Identity has the **Contributor role** on your Azure subscription 

### Login to Azure with the az CLI tool

- See https://learn.microsoft.com/en-us/cli/azure/authenticate-azure-cli?view=azure-cli-latest
- Select your Azure Subscription ID at time of login; it may already be the selected default
  ```
  az login
  ```

- Alternatively, you can set your Azure subscription with this command
  ```
  az account set --subscription "<subscription ID or name>"
  ```

### Login to the Azure Developer azd CLI tool

- See https://learn.microsoft.com/en-us/azure/developer/azure-developer-cli/reference

```
azd extension update azure.ai.agents
azd extension update --all

azd auth login
```

### Clone this GitHub Repository

```
git clone ...
cd forge
```

**This repo is intended to be copied or forked by you, for your use, rather than edited by you.**

---

## Next Steps

See the [Deployment](deployment.md) documentation.
