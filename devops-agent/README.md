# DevOps Agent

An event-driven, autonomous development system that runs Claude Code via Slack commands. Perfect for continuous development when you're away from your desk.

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│  YOU (Phone/Laptop anywhere)                                            │
│  └─> Slack: /dev start platform-wizard 5                                │
└─────────────────────────────────┬───────────────────────────────────────┘
                                  ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  n8n (Your existing instance)                                           │
│  ├─> Parse Slack command                                                │
│  ├─> Insert task into PostgreSQL queue                                  │
│  ├─> Start Azure VM via API                                             │
│  └─> Trigger webhook on VM                                              │
└─────────────────────────────────┬───────────────────────────────────────┘
                                  ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  Azure VM (B4ms - only runs when needed)                                │
│  ├─> Clone/update repo                                                  │
│  ├─> Run Ralph → Claude Code executes stories                           │
│  ├─> Send progress updates to n8n                                       │
│  └─> Auto-stops when complete                                           │
└─────────────────────────────────┬───────────────────────────────────────┘
                                  ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  Slack Notifications                                                    │
│  ├─> "🚀 Started: platform-wizard (5 stories)"                          │
│  ├─> "⚡ Working on: PWZ-001 - Create database table"                   │
│  ├─> "✅ Completed: PWZ-001"                                            │
│  └─> "🎉 All done! 5/5 stories completed"                               │
└─────────────────────────────────────────────────────────────────────────┘
```

## Cost

| Scenario | Monthly Cost |
|----------|--------------|
| Running 24/7 (not recommended) | ~$121/month |
| Event-driven, 4 hrs/day | ~$20/month |
| Event-driven, 2 hrs/day | ~$10/month |

The VM auto-stops after task completion, so you only pay when work is being done.

## Prerequisites

- Azure subscription
- Terraform installed
- n8n instance (self-hosted or cloud)
- Slack workspace with ability to create apps
- Anthropic API key
- GitHub Personal Access Token

## Quick Start

### 1. Clone and Configure

```bash
git clone <this-repo> devops-agent
cd devops-agent/terraform

# Copy and edit secrets
cp secrets.tfvars.example secrets.tfvars
```

Edit `secrets.tfvars`:

```hcl
ssh_public_key = "ssh-rsa AAAA... your-email@example.com"
anthropic_api_key = "sk-ant-..."
github_token = "ghp_..."
n8n_webhook_base_url = "https://n8n.yourdomain.com/webhook"
```

### 2. Deploy Infrastructure

```bash
# Login to Azure
az login

# Initialize Terraform
terraform init

# Preview changes
terraform plan -var-file="secrets.tfvars"

# Deploy
terraform apply -var-file="secrets.tfvars"
```

Note the outputs:
- `vm_public_ip` - IP address of your VM
- `webhook_url` - URL to trigger tasks
- `ssh_command` - How to SSH into the VM

### 3. Set Up Database

Run the SQL migration against your database:

```bash
psql -h your-db-host -U your-user -d your-database -f scripts/001-create-tables.sql
```

### 4. Configure n8n

1. Import the workflows from `n8n-workflows/`:
   - `01-slack-command-handler.json`
   - `02-task-progress-handler.json`

2. Update credentials in each workflow:
   - PostgreSQL connection
   - Slack Bot token
   - Azure OAuth (for VM start/stop)

3. Set environment variables in n8n:
   - `AZURE_SUBSCRIPTION_ID` - Your Azure subscription
   - `DEVOPS_AGENT_WEBHOOK_URL` - From Terraform output
   - `FLOWMETRICS_REPO_URL` - Your default repo URL

### 5. Create Slack App

1. Go to [api.slack.com/apps](https://api.slack.com/apps)
2. Create New App → From scratch
3. Add Slash Command:
   - Command: `/dev`
   - Request URL: `https://n8n.yourdomain.com/webhook/slack-dev-command`
   - Description: "DevOps Agent - Autonomous development"
4. Install to workspace
5. Copy Bot Token to n8n credentials

### 6. Configure Your Repos

Add PRD configurations for your projects:

```sql
INSERT INTO dev_prd_configs (prd_name, repo_url, prd_path, description)
VALUES 
    ('platform-wizard', 'https://github.com/yourorg/FlowMetrics.git', 
     'ralph/ralph-platform-wizard/scripts/ralph', 'Platform wizard feature'),
    ('file-ingestion', 'https://github.com/yourorg/FlowMetrics.git', 
     'ralph/ralph-file-ingestion/scripts/ralph', 'File ingestion feature');
```

## Usage

### Slack Commands

```
/dev start <prd> [stories] [branch]
  Start autonomous development
  Examples:
    /dev start platform-wizard 5
    /dev start file-ingestion 10 feature/upload

/dev status [task_id]
  Check current task status

/dev stop [task_id]
  Stop running task and deallocate VM

/dev list [active|completed|all]
  List recent tasks

/dev help
  Show help
```

### Manual VM Control

```bash
# Start VM
az vm start --resource-group devops-agent-rg --name devops-agent-vm

# Stop VM (deallocate to stop billing)
az vm deallocate --resource-group devops-agent-rg --name devops-agent-vm

# Check status
az vm show --resource-group devops-agent-rg --name devops-agent-vm --show-details --query powerState
```

### SSH Access

```bash
ssh devops@<vm-public-ip>

# Check health
~/scripts/health-check.sh

# View logs
tail -f ~/logs/task-*.log

# Check webhook service
sudo systemctl status devops-webhook
```

## Project Structure

```
devops-agent/
├── terraform/
│   ├── main.tf                 # Infrastructure definition
│   ├── secrets.tfvars.example  # Template for secrets
│   └── .gitignore
├── n8n-workflows/
│   ├── 01-slack-command-handler.json
│   └── 02-task-progress-handler.json
├── scripts/
│   ├── 001-create-tables.sql   # Database migration
│   └── ralph.sh                # Enhanced Ralph with notifications
├── docs/
│   └── troubleshooting.md
└── README.md
```

## Ralph PRD Structure

Each PRD in your repo should follow this structure:

```
ralph/
└── ralph-<feature>/
    ├── scripts/
    │   └── ralph/
    │       ├── ralph.sh        # Can use the enhanced version
    │       ├── prd.json        # User stories
    │       ├── progress.txt    # Completion log
    │       └── CLAUDE.md       # Context for Claude
    ├── docs/
    │   └── use-case.md
    └── AGENTS.md               # Project conventions
```

## Troubleshooting

### VM Won't Start

```bash
# Check VM state
az vm show -g devops-agent-rg -n devops-agent-vm --query powerState

# Check activity log
az monitor activity-log list --resource-group devops-agent-rg --max-events 10
```

### Webhook Not Responding

```bash
# SSH into VM and check service
ssh devops@<ip>
sudo systemctl status devops-webhook
sudo journalctl -u devops-webhook -f
```

### Claude Code Errors

```bash
# Check Claude CLI is installed
ssh devops@<ip>
claude --version

# Check API key
echo $ANTHROPIC_API_KEY | head -c 10
```

### n8n Workflow Failures

1. Check execution history in n8n
2. Verify credentials are valid
3. Check webhook URLs match

## Security Notes

1. **Restrict SSH access**: Update `allowed_ssh_ips` in Terraform to your IP ranges
2. **Use Azure Key Vault**: For production, store secrets in Key Vault instead of cloud-init
3. **Network isolation**: Consider VNet peering if VM needs to access private resources
4. **Rotate tokens**: Regularly rotate GitHub PAT and API keys

## Extending

### Add New PRD

1. Create Ralph structure in your repo
2. Add config to `dev_prd_configs` table
3. Use `/dev start <new-prd-name>`

### Add Custom Notifications

Modify the n8n workflow to add:
- Email notifications
- Teams messages
- Discord webhooks
- SMS alerts

### Multiple Repos

Update `dev_prd_configs` to point to different repos:

```sql
INSERT INTO dev_prd_configs (prd_name, repo_url, prd_path, description)
VALUES ('opshub-auth', 'https://github.com/yourorg/OpsHub.git', 
        'ralph/auth/scripts/ralph', 'OpsHub authentication');
```

## License

MIT
