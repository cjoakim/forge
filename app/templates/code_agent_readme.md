# README for the {{agent_name}} agent

Example CLI Commands - for macOS and Linux.  The Windows PowerShell commands are similar.

```
Command:                                 Description
--------------------------------------   ----------------------------------------------------------
cd app/                                  cd to the app/ directory within the repository root directory
source set-os-env.sh                     Set OS environment variables per your app/.env file                
./set-azd-env.sh agents/{{agent_name}}   Set azd `epl` environment variables per your app/.env file  

cd agents/{{agent_name}}                 Navigate to the agent directory

./copy-master-src.sh                     Get the latest reusable python modules from app/src/

azd ai agent run {{agent_name}} --environment {{agent_name}}   Run the Python agent locally
                                         Visit the Foundry Toolkit with your browser at http://127.0.0.1:8087/

./deploy.sh                              Build the Docker container and deploy to Foundry.
                                         Ensure that Docker Desktop is running on your workstation/laptop.

azd ai agent show {{agent_name}}         Display the deployment details and version

azd ai agent monitor --follow            Stream the logs to your terminal.  CTRL-C to stop.

azd ai agent invoke {{agent_name}} 'where is arsenal?' --environment {{agent_name}} --protocol responses
azd ai agent invoke {{agent_name}} 'What teams are in the epl, where are they located, and who is their goalkeeper?' --environment {{agent_name}} --protocol responses       Invoke the deployed agent
azd ai agent invoke epl 'what teams are in the EPL?' --environment epl --protocol responses
```
