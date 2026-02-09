#!/bin/bash
# =============================================================================
# Setup Terraform Remote State Backend in Azure Storage
# =============================================================================
# Creates an Azure Storage Account to store Terraform state remotely.
# This enables state locking and prevents concurrent modifications.
# =============================================================================

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}=== Setting up Terraform Remote State Backend ===${NC}\n"

# Configuration
RESOURCE_GROUP="devops-tfstate-rg"
LOCATION="australiaeast"
STORAGE_ACCOUNT="devopstfstate$(openssl rand -hex 3)"
CONTAINER_NAME="tfstate"

echo -e "${YELLOW}Configuration:${NC}"
echo -e "  Resource Group: ${RESOURCE_GROUP}"
echo -e "  Storage Account: ${STORAGE_ACCOUNT}"
echo -e "  Container: ${CONTAINER_NAME}"
echo -e "  Location: ${LOCATION}\n"

# Create resource group
echo -e "${GREEN}Creating resource group...${NC}"
az group create \
  --name "$RESOURCE_GROUP" \
  --location "$LOCATION" \
  --output none

echo -e "${GREEN}✓ Resource group created${NC}\n"

# Create storage account
echo -e "${GREEN}Creating storage account...${NC}"
az storage account create \
  --name "$STORAGE_ACCOUNT" \
  --resource-group "$RESOURCE_GROUP" \
  --location "$LOCATION" \
  --sku Standard_LRS \
  --kind StorageV2 \
  --encryption-services blob \
  --output none

echo -e "${GREEN}✓ Storage account created${NC}\n"

# Create blob container
echo -e "${GREEN}Creating blob container...${NC}"
az storage container create \
  --name "$CONTAINER_NAME" \
  --account-name "$STORAGE_ACCOUNT" \
  --auth-mode login \
  --output none

echo -e "${GREEN}✓ Container created${NC}\n"

# Get storage account key
ACCOUNT_KEY=$(az storage account keys list \
  --resource-group "$RESOURCE_GROUP" \
  --account-name "$STORAGE_ACCOUNT" \
  --query '[0].value' -o tsv)

# Output configuration
echo -e "${GREEN}=== Setup Complete ===${NC}\n"
echo -e "${YELLOW}Add this to your backend.tf:${NC}\n"

cat <<EOF
terraform {
  backend "azurerm" {
    resource_group_name  = "$RESOURCE_GROUP"
    storage_account_name = "$STORAGE_ACCOUNT"
    container_name       = "$CONTAINER_NAME"
    key                  = "devops-agent.tfstate"
  }
}
EOF

echo -e "\n${YELLOW}For GitHub Actions, set these secrets:${NC}"
echo -e "  gh secret set TF_BACKEND_RESOURCE_GROUP -b \"$RESOURCE_GROUP\""
echo -e "  gh secret set TF_BACKEND_STORAGE_ACCOUNT -b \"$STORAGE_ACCOUNT\""
echo -e "  gh secret set TF_BACKEND_CONTAINER -b \"$CONTAINER_NAME\""
echo -e "  gh secret set TF_BACKEND_KEY -b \"devops-agent.tfstate\"\n"

echo -e "${YELLOW}To migrate existing state:${NC}"
echo -e "  cd devops-agent/terraform"
echo -e "  terraform init -migrate-state\n"
