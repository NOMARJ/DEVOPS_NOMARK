# DevOps Stack Setup Guide - Mac

## Quick Reference

```bash
# 1. Extract your skills
cd ~/devops-mcp/scripts
./extract-skills.sh

# 2. Consolidate into standard structure
./consolidate-skills.sh

# 3. Install MCP server
cd ~/devops-mcp
pip install -e ".[all]"

# 4. Configure Claude Desktop
# Add to ~/Library/Application Support/Claude/claude_desktop_config.json

# 5. Test
python -m devops_mcp  # Should start without errors
```

---

## Step-by-Step Setup

### Prerequisites

- [ ] Python 3.10+ installed
- [ ] pip/pipx available
- [ ] Azure CLI installed (`brew install azure-cli`)
- [ ] GitHub CLI installed (`brew install gh`)

### Step 1: Extract Your Skills

```bash
# Navigate to the scripts directory
cd ~/devops-mcp/scripts

# Make executable
chmod +x *.sh

# Run extraction
./extract-skills.sh --output ~/flowmetrics-skills
```

This will scan:
- `~/.windsurfrules` (global Windsurf rules)
- `~/Library/Application Support/Windsurf/` (Windsurf configs)
- `~/Library/Application Support/Claude/` (Claude Desktop)
- `~/CascadeProjects/` and other project directories

### Step 2: Review Extracted Content

```bash
# See what was extracted
ls -la ~/flowmetrics-skills/extracted/

# Review the manifest
cat ~/flowmetrics-skills/extracted/MANIFEST.md
```

### Step 3: Consolidate Skills

```bash
./consolidate-skills.sh --dir ~/flowmetrics-skills
```

This will:
- Parse .windsurfrules into categorized skills
- Create skill templates for missing categories
- Generate `manifest.json` for MCP discovery

### Step 4: Customize Skills

```bash
# Edit skills as needed
code ~/flowmetrics-skills

# Or use your preferred editor
open ~/flowmetrics-skills
```

Each skill has a `SKILL.md` file you can customize.

### Step 5: Install MCP Server

```bash
cd ~/devops-mcp

# Install with all integrations
pip install -e ".[all]"

# Or specific integrations only
pip install -e ".[azure,github,supabase]"
```

### Step 6: Configure Environment

Create `~/.devops-env`:

```bash
cat > ~/.devops-env << 'EOF'
# Azure
export AZURE_SUBSCRIPTION_ID="your-subscription-id"
export AZURE_TENANT_ID="your-tenant-id"
export AZURE_CLIENT_ID="your-client-id"
export AZURE_CLIENT_SECRET="your-client-secret"

# Supabase
export SUPABASE_URL="https://your-project.supabase.co"
export SUPABASE_SERVICE_KEY="your-service-key"

# GitHub
export GITHUB_TOKEN="ghp_your-token"

# Vercel
export VERCEL_TOKEN="your-vercel-token"
export VERCEL_TEAM_ID="your-team-id"

# n8n
export N8N_URL="https://n8n.yourdomain.com"
export N8N_API_KEY="your-api-key"

# Slack
export SLACK_BOT_TOKEN="xoxb-your-token"
export SLACK_WEBHOOK_URL="https://hooks.slack.com/services/..."

# Metabase
export METABASE_URL="https://metabase.yourdomain.com"
export METABASE_USERNAME="your-username"
export METABASE_PASSWORD="your-password"
export METABASE_EMBED_SECRET="your-embed-secret"

# Carbone
export CARBONE_API_KEY="your-api-key"  # Or leave empty for local
export CARBONE_TEMPLATES_DIR="$HOME/flowmetrics-skills/templates"

# Skills
export SKILLS_DIR="$HOME/flowmetrics-skills"
EOF

# Add to your shell profile
echo 'source ~/.devops-env' >> ~/.zshrc
source ~/.devops-env
```

### Step 7: Configure Claude Desktop

Edit `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "devops": {
      "command": "python",
      "args": ["-m", "devops_mcp"],
      "cwd": "/Users/YOUR_USERNAME/devops-mcp",
      "env": {
        "AZURE_SUBSCRIPTION_ID": "...",
        "SUPABASE_URL": "...",
        "GITHUB_TOKEN": "...",
        "SKILLS_DIR": "/Users/YOUR_USERNAME/flowmetrics-skills"
      }
    }
  }
}
```

### Step 8: Configure Windsurf (Optional)

Add to Windsurf MCP settings:

```json
{
  "mcp": {
    "servers": {
      "devops": {
        "command": "python",
        "args": ["-m", "devops_mcp"],
        "cwd": "/Users/YOUR_USERNAME/devops-mcp"
      }
    }
  }
}
```

### Step 9: Test the Setup

```bash
# Source environment
source ~/.devops-env

# Test MCP server starts
python -m devops_mcp &
# Should start without errors

# Kill background process
kill %1

# Restart Claude Desktop
# The DevOps tools should now be available
```

### Step 10: Deploy DevOps Agent VM (Optional)

If you want the autonomous development agent:

```bash
cd ~/devops-agent/terraform

# Create secrets file
cp secrets.tfvars.example secrets.tfvars
# Edit secrets.tfvars with your values

# Deploy
terraform init
terraform apply -var-file="secrets.tfvars"
```

---

## Available Tools After Setup

### Azure
- `azure_vm_list` - List VMs
- `azure_vm_start` / `azure_vm_stop` - Control VMs
- `azure_vm_run_command` - Execute commands
- `azure_keyvault_get_secret` / `azure_keyvault_set_secret`

### Supabase
- `supabase_query` - Query tables
- `supabase_insert` / `supabase_update` / `supabase_delete`
- `supabase_rpc` - Call functions
- `supabase_storage_*` - File operations

### GitHub
- `github_repo_list` / `github_repo_info`
- `github_pr_list` / `github_pr_create` / `github_pr_merge`
- `github_issue_list` / `github_issue_create`
- `github_actions_list` / `github_actions_trigger`

### Vercel
- `vercel_project_list` / `vercel_deployment_list`
- `vercel_deployment_create` / `vercel_deployment_cancel`
- `vercel_env_list` / `vercel_env_set`

### n8n
- `n8n_workflow_list` / `n8n_workflow_execute`
- `n8n_webhook_trigger`
- `n8n_execution_list`

### Slack
- `slack_send_message` / `slack_send_webhook`
- `slack_notify_deployment`
- `slack_channel_list`

### Carbone
- `carbone_render` - Generate documents from templates
- `carbone_render_report` - Pre-configured FlowMetrics reports
- `carbone_batch_render` - Batch document generation

### Metabase
- `metabase_question_run` - Execute saved questions
- `metabase_query_run` - Run SQL queries
- `metabase_embed_url` - Generate embed URLs
- `metabase_dashboard_get`

### Skills
- `skills_list` - List available skills
- `skills_search` - Find skills by keyword
- `skills_get` - Get skill documentation
- `skills_recommend` - Get suggestions for a task

---

## Troubleshooting

### MCP Server Won't Start

```bash
# Check Python version
python --version  # Should be 3.10+

# Check dependencies
pip install -e ".[all]"

# Check environment variables
env | grep -E "(AZURE|SUPABASE|GITHUB)"
```

### Claude Desktop Doesn't Show Tools

1. Check config file is valid JSON
2. Restart Claude Desktop completely
3. Check MCP server can start manually

### Azure Authentication Fails

```bash
# Login with CLI
az login

# Or set service principal
export AZURE_CLIENT_ID=...
export AZURE_CLIENT_SECRET=...
export AZURE_TENANT_ID=...
```

### Skills Not Found

```bash
# Check SKILLS_DIR is set
echo $SKILLS_DIR

# Check manifest exists
cat $SKILLS_DIR/manifest.json

# Regenerate manifest
./consolidate-skills.sh
```

---

## Directory Reference

```
~/
├── devops-mcp/              # MCP Server
│   ├── src/
│   │   └── tools/           # Tool implementations
│   ├── scripts/
│   │   ├── extract-skills.sh
│   │   └── consolidate-skills.sh
│   └── config/
│
├── devops-agent/            # Autonomous Dev Agent
│   ├── terraform/
│   ├── n8n-workflows/
│   └── scripts/
│
├── flowmetrics-skills/      # Your Skills Library
│   ├── manifest.json
│   ├── documents/
│   ├── patterns/
│   ├── integrations/
│   ├── agents/
│   └── extracted/           # Raw extracted content
│
└── .devops-env              # Environment variables
```
