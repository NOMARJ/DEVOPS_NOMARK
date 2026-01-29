#!/bin/bash
# NOMARK DevOps - Azure Deployment Script
# Run this from your local machine with Azure CLI installed

set -e

# Configuration
SUBSCRIPTION_ID="ac7254fa-1f0b-433e-976c-b0430909c5ac"
SUBSCRIPTION_NAME="NOMARK"
RESOURCE_GROUP="nomark-devops-rg"
LOCATION="australiaeast"
VM_NAME="nomark-devops-vm"
DB_NAME="nomark-devops-db"
KEYVAULT_NAME="nomark-devops-kv"
DB_ADMIN_USER="devops_admin"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}   NOMARK DevOps - Azure Deployment    ${NC}"
echo -e "${GREEN}========================================${NC}"

# Check Azure CLI
if ! command -v az &> /dev/null; then
    echo -e "${RED}Error: Azure CLI not installed${NC}"
    echo "Install from: https://docs.microsoft.com/en-us/cli/azure/install-azure-cli"
    exit 1
fi

# Login check
echo -e "\n${YELLOW}Checking Azure login...${NC}"
if ! az account show &> /dev/null; then
    echo "Not logged in. Running az login..."
    az login
fi

# Set subscription
echo -e "\n${YELLOW}Setting subscription...${NC}"
az account set --subscription "$SUBSCRIPTION_ID"
echo -e "${GREEN}Using subscription: $SUBSCRIPTION_ID${NC}"

# Prompt for sensitive values
echo -e "\n${YELLOW}Enter sensitive configuration values:${NC}"
read -sp "PostgreSQL Admin Password (min 8 chars, uppercase, lowercase, number): " DB_PASSWORD
echo ""

if [ ${#DB_PASSWORD} -lt 8 ]; then
    echo -e "${RED}Password must be at least 8 characters${NC}"
    exit 1
fi

read -sp "Anthropic API Key: " ANTHROPIC_KEY
echo ""

read -sp "GitHub Personal Access Token: " GITHUB_TOKEN
echo ""

# Cost tracking tags (for filtering in Cost Management)
COST_TAGS="project=nomark-devops cost-center=devops environment=production owner=nomark created-by=azure-deploy-script"

# Create Resource Group
echo -e "\n${YELLOW}Creating resource group...${NC}"
az group create \
    --name "$RESOURCE_GROUP" \
    --location "$LOCATION" \
    --tags $COST_TAGS

echo -e "${GREEN}✓ Resource group created${NC}"

# Create Key Vault
echo -e "\n${YELLOW}Creating Key Vault...${NC}"
az keyvault create \
    --resource-group "$RESOURCE_GROUP" \
    --name "$KEYVAULT_NAME" \
    --location "$LOCATION" \
    --retention-days 7 \
    --tags $COST_TAGS

echo -e "${GREEN}✓ Key Vault created${NC}"

# Store secrets
echo -e "\n${YELLOW}Storing secrets in Key Vault...${NC}"
az keyvault secret set --vault-name "$KEYVAULT_NAME" --name "DB-PASSWORD" --value "$DB_PASSWORD" > /dev/null
az keyvault secret set --vault-name "$KEYVAULT_NAME" --name "ANTHROPIC-API-KEY" --value "$ANTHROPIC_KEY" > /dev/null
az keyvault secret set --vault-name "$KEYVAULT_NAME" --name "GITHUB-TOKEN" --value "$GITHUB_TOKEN" > /dev/null
echo -e "${GREEN}✓ Secrets stored${NC}"

# Create PostgreSQL Flexible Server
echo -e "\n${YELLOW}Creating PostgreSQL Flexible Server (this takes 5-10 minutes)...${NC}"
az postgres flexible-server create \
    --resource-group "$RESOURCE_GROUP" \
    --name "$DB_NAME" \
    --location "$LOCATION" \
    --admin-user "$DB_ADMIN_USER" \
    --admin-password "$DB_PASSWORD" \
    --sku-name Standard_B1ms \
    --storage-size 32 \
    --version 15 \
    --public-access 0.0.0.0 \
    --tags $COST_TAGS \
    --yes

echo -e "${GREEN}✓ PostgreSQL server created${NC}"

# Enable extensions
echo -e "\n${YELLOW}Enabling PostgreSQL extensions...${NC}"
az postgres flexible-server parameter set \
    --resource-group "$RESOURCE_GROUP" \
    --server-name "$DB_NAME" \
    --name azure.extensions \
    --value "VECTOR,PG_TRGM,UUID-OSSP"

echo -e "${GREEN}✓ Extensions enabled${NC}"

# Create VM
echo -e "\n${YELLOW}Creating DevOps VM...${NC}"

# Check for SSH key
if [ ! -f ~/.ssh/id_rsa.pub ]; then
    echo -e "${YELLOW}No SSH key found, generating one...${NC}"
    ssh-keygen -t rsa -b 4096 -f ~/.ssh/id_rsa -N ""
fi

az vm create \
    --resource-group "$RESOURCE_GROUP" \
    --name "$VM_NAME" \
    --image Ubuntu2404 \
    --size Standard_B2ms \
    --admin-username devops \
    --ssh-key-values ~/.ssh/id_rsa.pub \
    --public-ip-sku Standard \
    --os-disk-size-gb 128 \
    --tags $COST_TAGS role=agent-runner

echo -e "${GREEN}✓ VM created${NC}"

# Open SSH port
echo -e "\n${YELLOW}Configuring network security...${NC}"
az vm open-port \
    --resource-group "$RESOURCE_GROUP" \
    --name "$VM_NAME" \
    --port 22 \
    --priority 1000

echo -e "${GREEN}✓ SSH port opened${NC}"

# Configure auto-shutdown
echo -e "\n${YELLOW}Configuring auto-shutdown at 8 PM AEST...${NC}"
az vm auto-shutdown \
    --resource-group "$RESOURCE_GROUP" \
    --name "$VM_NAME" \
    --time 2000 \
    --timezone "AUS Eastern Standard Time"

echo -e "${GREEN}✓ Auto-shutdown configured${NC}"

# Get VM IP
VM_IP=$(az vm show -g "$RESOURCE_GROUP" -n "$VM_NAME" --show-details --query publicIps -o tsv)
DB_HOST="${DB_NAME}.postgres.database.azure.com"

# Create connection info file
echo -e "\n${YELLOW}Creating connection info...${NC}"
cat > ~/.nomark-devops.env << EOF
# NOMARK DevOps Connection Info
# Generated: $(date)

export NOMARK_VM_IP="$VM_IP"
export NOMARK_VM_USER="devops"
export NOMARK_DB_HOST="$DB_HOST"
export NOMARK_DB_NAME="postgres"
export NOMARK_DB_USER="$DB_ADMIN_USER"
export NOMARK_KEYVAULT="$KEYVAULT_NAME"
export NOMARK_RESOURCE_GROUP="$RESOURCE_GROUP"

# Aliases
alias nomark-ssh="ssh devops@\$NOMARK_VM_IP"
alias nomark-start="az vm start --resource-group $RESOURCE_GROUP --name $VM_NAME"
alias nomark-stop="az vm deallocate --resource-group $RESOURCE_GROUP --name $VM_NAME"
alias nomark-status="az vm get-instance-view --resource-group $RESOURCE_GROUP --name $VM_NAME --query instanceView.statuses[1].displayStatus -o tsv"
EOF

chmod 600 ~/.nomark-devops.env

echo -e "${GREEN}✓ Connection info saved to ~/.nomark-devops.env${NC}"

# Summary
echo -e "\n${GREEN}========================================${NC}"
echo -e "${GREEN}   Deployment Complete!                ${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "VM IP Address: ${YELLOW}$VM_IP${NC}"
echo -e "Database Host: ${YELLOW}$DB_HOST${NC}"
echo -e "Key Vault:     ${YELLOW}$KEYVAULT_NAME${NC}"
echo ""
echo "Next steps:"
echo "1. Source the env file: source ~/.nomark-devops.env"
echo "2. SSH to VM: nomark-ssh"
echo "3. Run VM setup script: ~/scripts/setup-vm.sh"
echo ""
echo "Estimated monthly cost: ~\$88-98 (with auto-shutdown)"
