# 🚀 DevOps Agent Deployment - Quick Reference

## Deploy via GitHub Actions (Recommended)

### Initial Setup (One-time)
```bash
cd devops-agent/scripts
./setup-github-actions.sh
```

### Deploy
```bash
# Plan changes
gh workflow run deploy-devops-agent.yml -f action=plan

# Apply changes
gh workflow run deploy-devops-agent.yml -f action=apply

# Custom VM size
gh workflow run deploy-devops-agent.yml -f action=apply -f vm_size=Standard_D8ds_v5

# Destroy infrastructure
gh workflow run deploy-devops-agent.yml -f action=destroy
```

### Monitor
```bash
# Watch workflow
gh run list --workflow=deploy-devops-agent.yml
gh run watch

# Check VM status
az vm show -g devops-agent-rg -n devops-agent-vm --query powerState -o tsv
```

---

## Deploy Locally

### Quick Deploy
```bash
cd devops-agent/terraform
terraform init
terraform plan -var-file="secrets.tfvars"
terraform apply -var-file="secrets.tfvars"
```

### Manage VM
```bash
# Start
az vm start --resource-group devops-agent-rg --name devops-agent-vm

# Stop (saves costs)
az vm deallocate --resource-group devops-agent-rg --name devops-agent-vm

# Status
az vm show -g devops-agent-rg -n devops-agent-vm -d --query powerState -o tsv
```

---

## Access VM

```bash
# SSH
ssh devops@<VM_IP>

# Health check
~/scripts/health-check.sh

# View logs
tail -f ~/logs/task-*.log

# Check webhook service
sudo systemctl status devops-webhook
```

---

## Useful Commands

```bash
# Get VM IP
az vm show -g devops-agent-rg -n devops-agent-vm -d --query publicIps -o tsv

# Test webhook
curl http://$(az vm show -g devops-agent-rg -n devops-agent-vm -d --query publicIps -o tsv):9000/health

# Update GitHub secret
gh secret set ANTHROPIC_API_KEY -b "sk-ant-..."

# List GitHub secrets
gh secret list
```

---

## Cost Optimization

- **Auto-shutdown**: VM stops daily at 7 PM UTC (5 AM AEST)
- **Manual stop**: `az vm deallocate -g devops-agent-rg -n devops-agent-vm`
- **Event-driven**: Only run when needed via n8n triggers
- **Estimated cost**: $10-20/month (2-4 hours/day usage)

---

## Documentation

- [Full README](README.md)
- [GitHub Actions Guide](docs/GITHUB_ACTIONS_DEPLOYMENT.md)
- [Troubleshooting](docs/troubleshooting.md)

---

## Support

- **Issues**: https://github.com/NOMARJ/DEVOPS_NOMARK/issues
- **VM Logs**: `/home/devops/logs/`
- **Service Status**: `systemctl status devops-webhook`
