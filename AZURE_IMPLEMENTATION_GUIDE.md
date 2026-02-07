# Azure Implementation Guide: Slack Bot Project Selector

## Overview

This guide covers implementing the interactive project selector for your Slack bot running on Azure VM infrastructure. The implementation includes configuration management, deployment automation, and integration with your existing Azure resources.

---

## Architecture Summary

Your current Azure setup:
- **VM**: `nomark-devops-vm` (Standard_B4ms, Ubuntu 22.04/24.04)
- **Resource Group**: `nomark-devops-rg` (australiaeast)
- **Key Vault**: `nomark-devops-kv` (secrets storage)
- **PostgreSQL**: `nomark-devops-db` (project metadata)
- **Azure Function**: `nomark-vm-starter` (Slack `/nomark-start` handler)
- **Slack Bot**: Runs as systemd service on VM

---

## Implementation Steps

### Phase 1: Update Configuration Files (Local Machine)

#### Step 1.1: Create Enhanced Projects Template

Update your `setup-vm.sh` script to include the enhanced projects.json with inhhale-v2:

```bash
# File: nomark-method/scripts/setup-vm.sh
# Add this section around line 74-108 (replace existing projects template)

# Create enhanced projects configuration
cat > ~/config/projects.json << 'EOF'
{
  "projects": [
    {
      "id": "flowmetrics",
      "name": "FlowMetrics",
      "repo": "NOMARK/flowmetrics-portal",
      "stack": "sveltekit-postgres",
      "description": "Flow metrics portal with Svelte and PostgreSQL",
      "priority": 1,
      "active": true,
      "azure": {
        "resourceGroup": "flowmetrics-rg",
        "deploymentSlots": ["staging", "production"]
      }
    },
    {
      "id": "instaindex",
      "name": "InstaIndex",
      "repo": "NOMARK/instaindex",
      "stack": "nextjs-supabase",
      "description": "Instant indexing service with Next.js and Supabase",
      "priority": 2,
      "active": true,
      "azure": {
        "resourceGroup": "instaindex-rg",
        "deploymentSlots": ["staging", "production"]
      }
    },
    {
      "id": "inhhale-v2",
      "name": "Inhhale iOS App",
      "repo": "NOMARK/inhhale-v2",
      "stack": "swift-ios",
      "description": "Medical breathing therapy iOS app for VCD/ILO patients implementing clinically-validated EILOBI techniques",
      "priority": 4,
      "active": true,
      "azure": {
        "resourceGroup": "inhhale-rg",
        "storageAccount": "inhhalestorage",
        "appCenter": {
          "org": "NOMARK",
          "app": "inhhale-ios"
        }
      }
    },
    {
      "id": "policyai",
      "name": "PolicyAI",
      "repo": "NOMARK/policyai",
      "stack": "nextjs-supabase",
      "description": "AI-powered policy analysis and generation",
      "priority": 3,
      "active": false,
      "azure": {
        "resourceGroup": "policyai-rg"
      }
    }
  ],
  "defaults": {
    "model": "claude-opus-4-5-20251101",
    "maxConcurrentTasks": 1,
    "autoShutdown": true,
    "azure": {
      "subscription": "ac7254fa-1f0b-433e-976c-b0430909c5ac",
      "location": "australiaeast",
      "vmAutoShutdownTime": "19:00"
    }
  }
}
EOF
```

#### Step 1.2: Create Azure-Specific Deployment Script

Create a new deployment script specifically for the project selector:

**File**: `nomark-method/scripts/deploy-project-selector.sh`

```bash
#!/bin/bash
#
# Deploy Project Selector Updates to Azure VM
# This script deploys the enhanced Slack bot with project selector to your Azure VM
#

set -e

echo "=========================================="
echo "Azure Project Selector Deployment"
echo "=========================================="
echo ""

# Load Azure configuration
if [[ -f ~/.nomark-devops.env ]]; then
    source ~/.nomark-devops.env
else
    echo "Error: ~/.nomark-devops.env not found"
    echo "Run azure-deploy.sh first to create infrastructure"
    exit 1
fi

# Configuration
VM_IP="${VM_IP:-}"
VM_USER="${VM_USER:-devops}"
RESOURCE_GROUP="nomark-devops-rg"
VM_NAME="nomark-devops-vm"

if [[ -z "$VM_IP" ]]; then
    echo "Fetching VM IP address from Azure..."
    VM_IP=$(az vm show -d -g "$RESOURCE_GROUP" -n "$VM_NAME" --query publicIps -o tsv)
fi

echo "Deployment Configuration:"
echo "  VM: $VM_NAME"
echo "  Resource Group: $RESOURCE_GROUP"
echo "  IP: $VM_IP"
echo "  User: $VM_USER"
echo ""

# Check VM is running
echo "Checking VM status..."
VM_STATUS=$(az vm get-instance-view -g "$RESOURCE_GROUP" -n "$VM_NAME" --query "instanceView.statuses[?starts_with(code, 'PowerState/')].displayStatus" -o tsv)

if [[ "$VM_STATUS" != "VM running" ]]; then
    echo "VM is not running (status: $VM_STATUS)"
    read -p "Start the VM? (y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "Starting VM..."
        az vm start -g "$RESOURCE_GROUP" -n "$VM_NAME"
        echo "Waiting 30 seconds for VM to fully start..."
        sleep 30
    else
        echo "Deployment cancelled"
        exit 1
    fi
fi

echo ""
echo "Step 1: Backup current configuration"
ssh "$VM_USER@$VM_IP" "
    mkdir -p ~/backups
    if [[ -f ~/config/projects.json ]]; then
        cp ~/config/projects.json ~/backups/projects.json.\$(date +%Y%m%d_%H%M%S)
        echo '✓ Backed up projects.json'
    fi
    if [[ -f ~/scripts/slack-bot.py ]]; then
        cp ~/scripts/slack-bot.py ~/backups/slack-bot.py.\$(date +%Y%m%d_%H%M%S)
        echo '✓ Backed up slack-bot.py'
    fi
"

echo ""
echo "Step 2: Upload enhanced projects.json"
scp "$(dirname "$0")/../../config/projects.json.azure" "$VM_USER@$VM_IP:~/config/projects.json"
echo "✓ Uploaded projects configuration"

echo ""
echo "Step 3: Upload updated slack-bot.py with project selector"
scp "$(dirname "$0")/slack-bot.py" "$VM_USER@$VM_IP:~/scripts/slack-bot.py"
echo "✓ Uploaded slack bot code"

echo ""
echo "Step 4: Restart Slack bot service"
ssh "$VM_USER@$VM_IP" "
    sudo systemctl restart nomark-slack.service
    sleep 3
    sudo systemctl status nomark-slack.service --no-pager
"

echo ""
echo "Step 5: Verify deployment"
ssh "$VM_USER@$VM_IP" "
    echo 'Checking projects.json...'
    if jq -e '.projects[] | select(.id == \"inhhale-v2\")' ~/config/projects.json > /dev/null; then
        echo '✓ inhhale-v2 project found'
    else
        echo '✗ inhhale-v2 project missing'
        exit 1
    fi

    echo ''
    echo 'Active projects:'
    jq -r '.projects[] | select(.active == true) | \"  • \\(.id) - \\(.name) (\\(.stack))\"' ~/config/projects.json

    echo ''
    echo 'Checking Slack bot process...'
    if pgrep -f slack-bot.py > /dev/null; then
        echo '✓ Slack bot is running'
    else
        echo '✗ Slack bot is not running'
        echo 'Checking logs...'
        sudo journalctl -u nomark-slack.service -n 20 --no-pager
        exit 1
    fi
"

echo ""
echo "=========================================="
echo "✓ Deployment Complete!"
echo "=========================================="
echo ""
echo "Test the deployment:"
echo "  1. In Slack: @DevOps task inhhale-v2 complete the iOS audit"
echo "  2. Test invalid project: @DevOps task wrongname test"
echo "  3. Check projects list: @DevOps projects"
echo ""
echo "View logs:"
echo "  ssh $VM_USER@$VM_IP"
echo "  sudo journalctl -u nomark-slack.service -f"
echo ""
```

---

### Phase 2: Update Slack Bot Code

#### Step 2.1: Copy Project Selector Code

1. Open your existing [nomark-method/scripts/slack-bot.py](nomark-method/scripts/slack-bot.py)

2. Add the project selector functions from [slack-bot-project-selector.py](slack-bot-project-selector.py):

**Insert after line ~150 (after `format_project_list()`):**

```python
def create_project_selector_blocks(command_text: str = "", original_project: str = "") -> list:
    """Create Slack Block Kit blocks with a project selector menu."""
    projects = get_active_projects()

    if not projects:
        return [{
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "❌ No active projects configured.\n\nUse `@nomark register <github-url>` to add a project."
            }
        }]

    # Build options for select menu
    options = []
    for p in projects:
        stack = p.get("stack", "unknown")
        priority = p.get("priority", "-")
        label = f"{p['name']} ({stack}) [P{priority}]"[:75]

        options.append({
            "text": {"type": "plain_text", "text": label},
            "value": json.dumps({
                "project_id": p["id"],
                "command": command_text
            })
        })

    return [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"❌ Unknown project: `{original_project}`\n\n🎯 *Select the correct project:*"
            }
        },
        {
            "type": "actions",
            "elements": [{
                "type": "static_select",
                "action_id": "select_project_for_task",
                "placeholder": {"type": "plain_text", "text": "Choose a project..."},
                "options": options
            }]
        },
        {
            "type": "context",
            "elements": [{
                "type": "mrkdwn",
                "text": f"💡 *Tip:* Available project IDs: {', '.join([f'`{p[\"id\"]}`' for p in projects])}"
            }]
        }
    ]
```

**Insert after line ~1540 (after existing @app.action handlers):**

```python
@app.action("select_project_for_task")
async def handle_project_selection_for_task(ack, body, action):
    """Handle project selection from dropdown when fixing invalid project."""
    await ack()

    try:
        value_data = json.loads(action["selected_option"]["value"])
        project_id = value_data["project_id"]
        command = value_data.get("command", "")

        channel = body["channel"]["id"]
        message_ts = body["message"]["ts"]
        thread_ts = body["message"].get("thread_ts", message_ts)

        # Update message to show selection
        selected_project_name = action["selected_option"]["text"]["text"]
        await app.client.chat_update(
            channel=channel,
            ts=message_ts,
            text=f"✅ Project selected: `{project_id}`",
            blocks=[{
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"✅ *Project selected:* {selected_project_name}"
                }
            }]
        )

        if not command:
            await app.client.chat_postMessage(
                channel=channel,
                thread_ts=thread_ts,
                text=f"✅ Project `{project_id}` selected.\n\nNow, what would you like me to do?\n\nReply with: `@nomark task {project_id} <your task description>`"
            )
            return

        # Execute the task
        await app.client.chat_postMessage(
            channel=channel,
            thread_ts=thread_ts,
            text=f"🚀 Starting task on `{project_id}`...\n\n*Task:* {command}"
        )

        files = body.get("message", {}).get("files", [])
        asyncio.create_task(run_task(project_id, command, channel, thread_ts, attachments=files))

    except Exception as e:
        logger.error(f"Error handling project selection: {e}")
        await app.client.chat_postMessage(
            channel=body["channel"]["id"],
            thread_ts=body["message"].get("thread_ts", body["message"]["ts"]),
            text=f"❌ Error processing selection: {e}"
        )
```

**Replace the "task" command handler (around line ~2180):**

Find the section that starts with `if command == "task":` and replace it with:

```python
if command == "task":
    # Usage: @nomark task <project> <task_description>
    if len(parts) < 2:
        await say(
            text="*Usage:* `@nomark task <project> <task_description>`\n\n*Example:* `@nomark task flowmetrics add dark mode toggle`",
            thread_ts=thread_ts
        )
        return

    if len(parts) < 3:
        # Only project provided, no task
        await say(
            text=f"Please provide a task description for `{parts[1]}`",
            thread_ts=thread_ts
        )
        return

    project = parts[1]
    task = parts[2]

    # Validate project
    projects = get_active_projects()
    project_ids = [p["id"] for p in projects]

    if project not in project_ids:
        # Project invalid - show selector with task preserved
        blocks = create_project_selector_blocks(
            command_text=task,
            original_project=project
        )
        await app.client.chat_postMessage(
            channel=channel,
            thread_ts=thread_ts,
            text=f"❌ Unknown project: `{project}`",
            blocks=blocks
        )
        return

    # Valid project - continue with task
    asyncio.create_task(run_task(project, task, channel, thread_ts, attachments=files))
    return
```

#### Step 2.2: Create Updated Slack Bot File for Azure

Save your updated `slack-bot.py` to ensure it's ready for deployment.

---

### Phase 3: Create Azure-Specific Configuration

#### Step 3.1: Create projects.json Template for Azure

**File**: `config/projects.json.azure`

```json
{
  "projects": [
    {
      "id": "flowmetrics",
      "name": "FlowMetrics",
      "repo": "NOMARK/flowmetrics-portal",
      "stack": "sveltekit-postgres",
      "description": "Flow metrics portal with Svelte and PostgreSQL",
      "priority": 1,
      "active": true,
      "azure": {
        "resourceGroup": "flowmetrics-rg",
        "location": "australiaeast",
        "deploymentSlots": ["staging", "production"]
      }
    },
    {
      "id": "instaindex",
      "name": "InstaIndex",
      "repo": "NOMARK/instaindex",
      "stack": "nextjs-supabase",
      "description": "Instant indexing service with Next.js and Supabase",
      "priority": 2,
      "active": true,
      "azure": {
        "resourceGroup": "instaindex-rg",
        "location": "australiaeast",
        "deploymentSlots": ["staging", "production"]
      }
    },
    {
      "id": "inhhale-v2",
      "name": "Inhhale iOS App",
      "repo": "NOMARK/inhhale-v2",
      "stack": "swift-ios",
      "description": "Medical breathing therapy iOS app for VCD/ILO patients implementing clinically-validated EILOBI techniques prescribed by Speech-Language Pathologists",
      "priority": 4,
      "active": true,
      "azure": {
        "resourceGroup": "inhhale-rg",
        "location": "australiaeast",
        "storageAccount": "inhhalestorage",
        "appCenter": {
          "org": "NOMARK",
          "app": "inhhale-ios",
          "ownerName": "NOMARK",
          "appName": "inhhale-ios"
        }
      },
      "ios": {
        "bundleId": "com.nomark.inhhale",
        "teamId": "YOUR_TEAM_ID",
        "provisioning": "automatic"
      }
    },
    {
      "id": "policyai",
      "name": "PolicyAI",
      "repo": "NOMARK/policyai",
      "stack": "nextjs-supabase",
      "description": "AI-powered policy analysis and generation",
      "priority": 3,
      "active": false,
      "azure": {
        "resourceGroup": "policyai-rg",
        "location": "australiaeast"
      }
    }
  ],
  "defaults": {
    "model": "claude-opus-4-5-20251101",
    "maxConcurrentTasks": 1,
    "autoShutdown": true,
    "azure": {
      "subscription": "ac7254fa-1f0b-433e-976c-b0430909c5ac",
      "subscriptionName": "NOMARK",
      "location": "australiaeast",
      "vmResourceGroup": "nomark-devops-rg",
      "vmName": "nomark-devops-vm",
      "vmAutoShutdownTime": "19:00",
      "keyVault": "nomark-devops-kv",
      "database": {
        "host": "nomark-devops-db.postgres.database.azure.com",
        "name": "nomark_devops",
        "user": "devops_admin"
      }
    }
  },
  "metadata": {
    "version": "2.0.0",
    "lastUpdated": "2026-01-31",
    "deployedOn": "azure",
    "projectSelectorEnabled": true
  }
}
```

---

### Phase 4: Deploy to Azure

#### Option A: Manual Deployment (Quick)

```bash
# 1. Get VM IP from Azure
az vm show -d -g nomark-devops-rg -n nomark-devops-vm --query publicIps -o tsv

# 2. SSH to VM
ssh devops@<VM_IP>

# 3. Backup current config
mkdir -p ~/backups
cp ~/config/projects.json ~/backups/projects.json.$(date +%Y%m%d_%H%M%S)
cp ~/scripts/slack-bot.py ~/backups/slack-bot.py.$(date +%Y%m%d_%H%M%S)

# 4. Update projects.json
nano ~/config/projects.json
# Paste the content from config/projects.json.azure above

# 5. Update slack-bot.py
nano ~/scripts/slack-bot.py
# Add the project selector functions as described in Step 2.1

# 6. Restart Slack bot
sudo systemctl restart nomark-slack.service
sudo systemctl status nomark-slack.service

# 7. Verify
jq '.projects[] | select(.id == "inhhale-v2")' ~/config/projects.json
```

#### Option B: Automated Deployment (Recommended)

```bash
# From your local machine
cd /Users/reecefrazier/DEVOPS_NOMARK

# 1. Make deployment script executable
chmod +x nomark-method/scripts/deploy-project-selector.sh

# 2. Create projects.json.azure
cat > config/projects.json.azure << 'EOF'
# ... paste content from Step 3.1 ...
EOF

# 3. Run deployment
./nomark-method/scripts/deploy-project-selector.sh

# 4. Test in Slack
# @DevOps task inhhale-v2 complete the iOS audit
```

---

### Phase 5: Update Azure Key Vault (Optional)

Store projects configuration in Azure Key Vault for disaster recovery:

```bash
# Upload projects.json to Key Vault
az keyvault secret set \
  --vault-name nomark-devops-kv \
  --name projects-config \
  --file config/projects.json.azure

# Retrieve when needed
az keyvault secret show \
  --vault-name nomark-devops-kv \
  --name projects-config \
  --query value -o tsv > ~/config/projects.json
```

---

## Testing on Azure

### Test 1: Valid Project

```
Slack: @DevOps task inhhale-v2 complete the iOS audit from inhhale-ios-audit-prompt.md
Expected: ✅ Task starts, Claude reads the audit prompt file
```

### Test 2: Invalid Project (Dropdown Appears)

```
Slack: @DevOps task wrongproject add feature
Expected: ❌ Error message with dropdown showing all projects
Action: Click "Inhhale iOS App (swift-ios) [P4]"
Expected: ✅ Task starts with "add feature" description
```

### Test 3: List Projects

```
Slack: @DevOps projects
Expected: Shows all active projects (flowmetrics, instaindex, inhhale-v2)
```

### Test 4: Project Registration

```
Slack: @DevOps register https://github.com/NOMARK/new-project
Expected: Clones repo, detects stack, adds to projects.json
```

---

## Monitoring and Logs

### View Slack Bot Logs

```bash
# SSH to Azure VM
ssh devops@<VM_IP>

# Real-time logs
sudo journalctl -u nomark-slack.service -f

# Last 50 lines
sudo journalctl -u nomark-slack.service -n 50

# Logs from today
sudo journalctl -u nomark-slack.service --since today
```

### Check Bot Status

```bash
# Service status
sudo systemctl status nomark-slack.service

# Process check
ps aux | grep slack-bot.py

# Check if listening
netstat -tulpn | grep python
```

---

## Rollback Procedure

If something goes wrong:

```bash
# SSH to VM
ssh devops@<VM_IP>

# Stop bot
sudo systemctl stop nomark-slack.service

# Restore backup
cp ~/backups/projects.json.<timestamp> ~/config/projects.json
cp ~/backups/slack-bot.py.<timestamp> ~/scripts/slack-bot.py

# Restart bot
sudo systemctl start nomark-slack.service
sudo systemctl status nomark-slack.service
```

---

## Cost Considerations

**Current Azure Costs:**
- VM (Standard_B4ms): ~$120/month (with auto-shutdown: ~$20-30/month)
- PostgreSQL (Standard_B1ms): ~$25/month
- Key Vault: ~$1/month
- Functions: Free tier (1M executions/month)
- Storage: <$5/month

**Total**: ~$50-160/month depending on VM usage

**Cost Optimization:**
- Auto-shutdown enabled (7 PM UTC daily)
- VM only runs when needed
- Functions use consumption plan
- PostgreSQL uses burstable tier

---

## Security Checklist

- [ ] VM has SSH key authentication only (no passwords)
- [ ] SSH restricted to allowed IPs in NSG
- [ ] Slack tokens stored in Key Vault or environment variables
- [ ] Database password in Key Vault
- [ ] GitHub token has minimal required scopes
- [ ] Anthropic API key secured
- [ ] VM auto-shutdown enabled
- [ ] Regular backups of projects.json

---

## Next Steps

1. ✅ Review this guide
2. ✅ Update `setup-vm.sh` with enhanced projects template
3. ✅ Create `deploy-project-selector.sh` script
4. ✅ Update `slack-bot.py` with selector code
5. ✅ Create `config/projects.json.azure`
6. ✅ Run deployment script
7. ✅ Test in Slack
8. ✅ Monitor logs for errors
9. ✅ Store config in Key Vault
10. ✅ Document for team

---

## Summary

This implementation guide provides:
- Complete Azure deployment workflow
- Automated deployment script
- Enhanced projects.json with Azure metadata
- Updated Slack bot with project selector
- Testing procedures
- Monitoring and rollback procedures

All files are ready to deploy to your Azure VM infrastructure!
