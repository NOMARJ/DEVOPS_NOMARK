# GitHub Actions Deployment Guide

Deploy your DevOps Agent infrastructure to Azure automatically using GitHub Actions with OIDC authentication.

## 🎯 Overview

This setup provides:
- **Automated deployments** from GitHub Actions
- **OIDC authentication** (no long-lived credentials)
- **Pull request previews** with Terraform plans
- **Manual workflow dispatch** for controlled deployments
- **Automatic deployments** on push to main branch
- **State management** with Azure Storage backend (optional)

## 🚀 Quick Setup

### 1. Run the Setup Script

```bash
cd devops-agent/scripts
./setup-github-actions.sh
```

This script will:
- Create an Azure Service Principal with OIDC federated credentials
- Assign Contributor role for your subscription
- Configure GitHub repository secrets
- Set up authentication for the `main` branch

### 2. (Optional) Configure Remote State Backend

For production deployments, use remote state storage:

```bash
cd devops-agent/scripts
./setup-terraform-backend.sh
```

Then update `devops-agent/terraform/backend.tf` with the output configuration and run:

```bash
cd devops-agent/terraform
terraform init -migrate-state
```

### 3. Trigger a Deployment

**Via GitHub UI:**
1. Go to **Actions** → **Deploy DevOps Agent to Azure**
2. Click **Run workflow**
3. Select action: `plan`, `apply`, or `destroy`
4. Click **Run workflow**

**Via GitHub CLI:**
```bash
# Plan changes
gh workflow run deploy-devops-agent.yml -f action=plan

# Apply changes
gh workflow run deploy-devops-agent.yml -f action=apply

# Apply with custom VM size
gh workflow run deploy-devops-agent.yml -f action=apply -f vm_size=Standard_D8ds_v5

# Destroy infrastructure
gh workflow run deploy-devops-agent.yml -f action=destroy
```

## 🔐 GitHub Secrets

The following secrets are configured by the setup script:

| Secret | Description |
|--------|-------------|
| `AZURE_CLIENT_ID` | Service Principal Application ID |
| `AZURE_TENANT_ID` | Azure Active Directory Tenant ID |
| `AZURE_SUBSCRIPTION_ID` | Azure Subscription ID |
| `SSH_PUBLIC_KEY` | SSH public key for VM access |
| `ANTHROPIC_API_KEY` | Anthropic API key for Claude Code |
| `GH_PAT_TOKEN` | GitHub Personal Access Token |
| `N8N_WEBHOOK_BASE_URL` | n8n webhook base URL |
| `DEFAULT_REPO_URL` | Default repository URL |

### Updating Secrets

```bash
# Update individual secrets
gh secret set ANTHROPIC_API_KEY -b "sk-ant-..."
gh secret set N8N_WEBHOOK_BASE_URL -b "https://n8n.yourdomain.com/webhook"

# List all secrets
gh secret list
```

## 🔄 Workflow Triggers

### 1. Manual Workflow Dispatch

Triggered manually from GitHub Actions UI or CLI:
- Choose action: `plan`, `apply`, or `destroy`
- Optionally specify VM size

### 2. Automatic on Push

Automatically runs on push to `main` branch when:
- Files in `devops-agent/terraform/` change
- The workflow file itself changes

**Behavior:**
- Always runs `terraform plan`
- Automatically runs `terraform apply` on main branch

### 3. Pull Request Comments

On pull requests, the workflow:
- Runs `terraform plan`
- Posts the plan as a PR comment
- Does NOT apply changes

## 📋 Workflow Steps

1. **Checkout** - Clone repository
2. **Setup Terraform** - Install Terraform CLI
3. **Azure Login** - Authenticate via OIDC
4. **Create Variables** - Generate `secrets.tfvars` from GitHub secrets
5. **Terraform Init** - Initialize Terraform
6. **Terraform Plan** - Create execution plan
7. **Upload Artifact** - Save plan for review
8. **Terraform Apply** - Apply changes (if action=apply or push to main)
9. **Get Outputs** - Extract deployment information
10. **Summary** - Display deployment details

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  GitHub Actions Workflow                                    │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  1. Trigger (manual / push / PR)                            │
│  2. Authenticate to Azure (OIDC)                            │
│  3. Generate secrets.tfvars from GitHub Secrets             │
│  4. Terraform Plan                                          │
│  5. Upload Plan Artifact                                    │
│  6. Terraform Apply (if approved)                           │
│  7. Output deployment details                               │
│                                                              │
└──────────────────┬──────────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────────────┐
│  Azure Subscription                                         │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ├─ Resource Group: devops-agent-rg                         │
│  ├─ Virtual Network                                         │
│  ├─ Network Security Group                                  │
│  ├─ Public IP                                               │
│  ├─ VM: devops-agent-vm                                     │
│  └─ Auto-shutdown Schedule                                  │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

## 🛡️ Security Best Practices

### OIDC vs Service Principal Keys

This setup uses **OIDC** (OpenID Connect) instead of long-lived service principal keys:

✅ **OIDC Benefits:**
- No credentials stored in GitHub
- Short-lived tokens (valid only during workflow)
- Federated trust with GitHub
- Automatic rotation

❌ **Old approach (avoid):**
- Service principal client secret stored as GitHub secret
- Credentials can expire
- Must be manually rotated
- Risk of credential leakage

### Principle of Least Privilege

The Service Principal has:
- **Scope:** Limited to your Azure subscription
- **Role:** Contributor (can manage resources but not access management)
- **Trust:** Only from your GitHub repository's main branch

### Secret Management

- Secrets are encrypted at rest in GitHub
- Only accessible during workflow execution
- `secrets.tfvars` is created temporarily and deleted after use
- Never committed to version control

## 🔧 Customization

### Change VM Size

```bash
# Via workflow input
gh workflow run deploy-devops-agent.yml -f action=apply -f vm_size=Standard_B2ms

# Or update secrets.tfvars default in the workflow file
```

### Add Additional Branch Protection

Edit `.github/workflows/deploy-devops-agent.yml` to add approval requirements:

```yaml
jobs:
  terraform:
    environment: production  # Requires environment approval
    name: Terraform
    ...
```

Then configure the `production` environment in GitHub Settings with required reviewers.

### Use Terraform Workspaces

For multiple environments (dev, staging, prod):

```yaml
- name: Select Workspace
  run: terraform workspace select ${{ github.event.inputs.environment }} || terraform workspace new ${{ github.event.inputs.environment }}
```

## 📊 Monitoring Deployments

### View Workflow Runs

```bash
# List recent workflow runs
gh run list --workflow=deploy-devops-agent.yml

# View specific run
gh run view <run-id>

# Watch run in real-time
gh run watch <run-id>
```

### Check Deployment Status

After deployment completes:

```bash
# Get VM status
az vm show -g devops-agent-rg -n devops-agent-vm --query "powerState" -o tsv

# Get public IP
az vm show -g devops-agent-rg -n devops-agent-vm -d --query publicIps -o tsv

# Test webhook
curl http://$(az vm show -g devops-agent-rg -n devops-agent-vm -d --query publicIps -o tsv):9000/health
```

## 🐛 Troubleshooting

### Authentication Fails

```bash
# Verify Service Principal exists
az ad sp list --display-name "github-actions-devops-agent"

# Check role assignment
az role assignment list --assignee <APP_ID> --subscription <SUBSCRIPTION_ID>

# Re-run setup
./scripts/setup-github-actions.sh
```

### Plan Fails

```bash
# Check Terraform syntax locally
cd devops-agent/terraform
terraform fmt -check
terraform validate

# Download plan artifact from GitHub Actions
gh run download <run-id> -n terraform-plan
terraform show tfplan
```

### State Lock Issues

If using remote state:

```bash
# Check for locks
az storage blob list \
  --account-name <STORAGE_ACCOUNT> \
  --container-name tfstate \
  --auth-mode login

# Force unlock (use with caution)
terraform force-unlock <LOCK_ID>
```

### VM Size Unavailable

If you get capacity errors:

```bash
# List available VM sizes in region
az vm list-skus --location australiaeast --size Standard_D --output table

# Try different region
gh workflow run deploy-devops-agent.yml -f action=apply -f location=eastus
```

## 🔄 Migration from Local to GitHub Actions

If you've been deploying locally:

1. **Export current state:**
   ```bash
   cd devops-agent/terraform
   terraform state pull > local-state.json
   ```

2. **Setup remote backend:**
   ```bash
   ./scripts/setup-terraform-backend.sh
   ```

3. **Migrate state:**
   ```bash
   terraform init -migrate-state
   ```

4. **Run first deployment via GitHub Actions:**
   ```bash
   gh workflow run deploy-devops-agent.yml -f action=plan
   # Review plan, then:
   gh workflow run deploy-devops-agent.yml -f action=apply
   ```

## 📚 Additional Resources

- [GitHub Actions - Azure Login](https://github.com/Azure/login)
- [Terraform Azure Backend](https://www.terraform.io/docs/language/settings/backends/azurerm.html)
- [Azure OIDC with GitHub Actions](https://docs.microsoft.com/en-us/azure/developer/github/connect-from-azure)
- [GitHub Encrypted Secrets](https://docs.github.com/en/actions/security-guides/encrypted-secrets)
