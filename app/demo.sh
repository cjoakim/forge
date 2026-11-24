#!/bin/bash

# This script demonstrates the Agent generation and deployment process.
# The generated agents are git-ignored.

# remove any existing example agents
rm -rf agents/xpa
rm -rf agents/xca

mkdir -p tmp
source .venv/bin/activate

echo ""
echo "==== Updating azd extensions ===="
azd extension update --all
sleep 8

echo ""
echo "==== Setting OS environment variables ===="
source ./set-os-env.sh 
sleep 8 

echo ""
echo "==== Generating the generator configuration file ===="
uv run main-generator.py gen_generator_config
sleep 8  

echo ""
echo "==== Displaying the generator configuration file ===="
cat generator_config.json
sleep 12

echo ""
echo "==== Generating example prompt agent ===="
uv run main-generator.py gen_prompt_agent xpA   # xpa = Example Prompt Agent
sleep 8  

echo ""
echo "==== Generating example code agent ===="
uv run main-generator.py gen_code_agent xcA     # xca = Example Code Agent
sleep 8  

echo "==== Deploying example prompt agent ===="
./deploy-foundry-prompt-agent.sh aif-cjoakimforge1102b epl 2025-11-15-preview agents/xpa/azure.yaml
sleep 8  

echo ""
echo "==== Setting azd environment variables for the xca code agent ===="
./set-azd-env.sh agents/xca     
sleep 8  

echo ""
echo "==== Changing to the xca code agent directory ===="
cd agents/xca
pwd
sleep 8  

echo ""
echo "==== Executing the generated script to copy the core python src/ files ===="
chmod 744 ./*.sh
./copy-master-src.sh
sleep 8

echo ""
echo "==== Displaying the generated agent-specific readme.md ===="
cat readme.md
sleep 12

echo ""
echo "==== Running the python xca agent locally.  ===="
echo "Enter the prompt: What teams are in the EPL?"
echo "CTRL-C when done. "
echo "Then run the generated ./deploy.sh script to deploy the xca code agent."
sleep 8

azd ai agent run xca --environment xca

# What teams are in the epl, where are they located, and who are their goalkeepers? 
