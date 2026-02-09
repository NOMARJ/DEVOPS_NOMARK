#!/bin/bash
# =============================================================================
# Setup GitHub Actions for DevOps Agent Deployment
# =============================================================================
# This script configures Azure Service Principal with OIDC authentication
# for GitHub Actions to deploy infrastructure.
# =============================================================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== DevOps Agent - GitHub Actions Setup ===${NC}\n"

# Check prerequisites
command -v az >/dev/null 2>&1 || { echo -e "${RED}Error: Azure CLI not installed${NC}"; exit 1; }
command -v gh >/dev/null 2>&1 || { echo -e "${RED}Error: GitHub CLI not installed${NC}"; exit 1; }

# Get current Azure subscription
SUBSCRIPTION_ID=$(az account show --query id -o tsv)
TENANT_ID=$(az account show --query tenantId -o tsv)

echo -e "${YELLOW}Current Azure Subscription:${NC} $SUBSCRIPTION_ID"
echo -e "${YELLOW}Tenant ID:${NC} $TENANT_ID\n"

# Get GitHub repository info
REPO_OWNER=$(gh repo view --json owner -q '.owner.login')
REPO_NAME=$(gh repo view --json name -q '.name')
REPO_FULL="${REPO_OWNER}/${REPO_NAME}"

echo -e "${YELLOW}GitHub Repository:${NC} $REPO_FULL\n"

# Create Azure AD Application
APP_NAME="github-actions-devops-agent"
echo -e "${GREEN}Creating Azure AD Application: $APP_NAME${NC}"

# Check if app already exists
APP_ID=$(az ad app list --display-name "$APP_NAME" --query '[0].appId' -o tsv)

if [ -z "$APP_ID" ]; then
  APP_ID=$(az ad app create --display-name "$APP_NAME" --query appId -o tsv)
  echo -e "${GREEN}✓ Created application: $APP_ID${NC}"
else
  echo -e "${YELLOW}! Application already exists: $APP_ID${NC}"
fi

# Create Service Principal
echo -e "\n${GREEN}Creating Service Principal${NC}"
SP_ID=$(az ad sp list --filter "appId eq '$APP_ID'" --query '[0].id' -o tsv)

if [ -z "$SP_ID" ]; then
  SP_ID=$(az ad sp create --id "$APP_ID" --query id -o tsv)
  echo -e "${GREEN}✓ Created service principal: $SP_ID${NC}"
else
  echo -e "${YELLOW}! Service principal already exists: $SP_ID${NC}"
fi

# Assign Contributor role
echo -e "\n${GREEN}Assigning Contributor role${NC}"
az role assignment create \
  --assignee "$APP_ID" \
  --role "Contributor" \
  --scope "/subscriptions/$SUBSCRIPTION_ID" \
  2>/dev/null && echo -e "${GREEN}✓ Role assigned${NC}" || echo -e "${YELLOW}! Role already assigned${NC}"

# Configure federated credential for GitHub Actions
echo -e "\n${GREEN}Configuring OIDC federated credential${NC}"

CREDENTIAL_NAME="github-actions-main"
SUBJECT="repo:${REPO_FULL}:ref:refs/heads/main"

# Remove existing credential if it exists
az ad app federated-credential delete \
  --id "$APP_ID" \
  --federated-credential-id "$CREDENTIAL_NAME" \
  2>/dev/null || true

# Create federated credential
az ad app federated-credential create \
  --id "$APP_ID" \
  --parameters '{
    "name": "'"$CREDENTIAL_NAME"'",
    "issuer": "https://token.actions.githubusercontent.com",
    "subject": "'"$SUBJECT"'",
    "description": "GitHub Actions federated credential for main branch",
    "audiences": ["api://AzureADTokenExchange"]
  }' >/dev/null

echo -e "${GREEN}✓ Federated credential configured${NC}"

# Get SSH public key
if [ -f ~/.ssh/id_rsa.pub ]; then
  SSH_PUBLIC_KEY=$(cat ~/.ssh/id_rsa.pub)
else
  echo -e "${RED}Error: SSH public key not found at ~/.ssh/id_rsa.pub${NC}"
  exit 1
fi

# Read values from .env if available
if [ -f "$(git rev-parse --show-toplevel)/.env" ]; then
  source "$(git rev-parse --show-toplevel)/.env"
fi

# Set GitHub Secrets
echo -e "\n${GREEN}Setting GitHub repository secrets${NC}"

gh secret set AZURE_CLIENT_ID -b "$APP_ID"
gh secret set AZURE_TENANT_ID -b "$TENANT_ID"
gh secret set AZURE_SUBSCRIPTION_ID -b "$SUBSCRIPTION_ID"
gh secret set SSH_PUBLIC_KEY -b "$SSH_PUBLIC_KEY"
gh secret set ANTHROPIC_API_KEY -b "${CLAUDE_CODE_OAUTH_TOKEN:-placeholder}"
gh secret set GH_PAT_TOKEN -b "${GITHUB_TOKEN:-placeholder}"
gh secret set N8N_WEBHOOK_BASE_URL -b "${N8N_WEBHOOK_BASE_URL:-https://n8n.placeholder.local/webhook}"
gh secret set DEFAULT_REPO_URL -b "https://github.com/${REPO_FULL}.git"

echo -e "${GREEN}✓ GitHub secrets configured${NC}"

# Summary
echo -e "\n${GREEN}=== Setup Complete ===${NC}\n"
echo -e "GitHub Actions is now configured to deploy DevOps Agent to Azure.\n"
echo -e "${YELLOW}Service Principal Details:${NC}"
echo -e "  Application ID: ${APP_ID}"
echo -e "  Object ID: ${SP_ID}"
echo -e "  Subscription: ${SUBSCRIPTION_ID}"
echo -e "  Repository: ${REPO_FULL}\n"

echo -e "${YELLOW}Next Steps:${NC}"
echo -e "  1. Go to: https://github.com/${REPO_FULL}/actions"
echo -e "  2. Select 'Deploy DevOps Agent to Azure' workflow"
echo -e "  3. Click 'Run workflow' and choose action (plan/apply/destroy)"
echo -e "  4. Monitor the deployment\n"

echo -e "${YELLOW}To deploy now:${NC}"
echo -e "  gh workflow run deploy-devops-agent.yml -f action=apply\n"
