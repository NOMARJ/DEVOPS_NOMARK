#!/bin/bash
#
# Deploy Project Selector Updates to Azure VM
# This script deploys the enhanced Slack bot with project selector to your Azure VM
#
# Usage: ./deploy-project-selector.sh
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

echo "=========================================="
echo "Azure Project Selector Deployment"
echo "=========================================="
echo ""

# Load Azure configuration
if [[ -f ~/.nomark-devops.env ]]; then
    source ~/.nomark-devops.env
    echo "✓ Loaded configuration from ~/.nomark-devops.env"
else
    echo "⚠ ~/.nomark-devops.env not found"
    echo "Attempting to fetch VM info from Azure..."
fi

# Configuration
RESOURCE_GROUP="${RESOURCE_GROUP:-nomark-devops-rg}"
VM_NAME="${VM_NAME:-nomark-devops-vm}"
VM_USER="${VM_USER:-devops}"
VM_IP="${VM_IP:-}"

# Fetch VM IP if not set
if [[ -z "$VM_IP" ]]; then
    echo "Fetching VM IP address from Azure..."
    if command -v az &> /dev/null; then
        VM_IP=$(az vm show -d -g "$RESOURCE_GROUP" -n "$VM_NAME" --query publicIps -o tsv 2>/dev/null || echo "")
        if [[ -n "$VM_IP" ]]; then
            echo "✓ Found VM IP: $VM_IP"
        else
            echo "✗ Failed to fetch VM IP from Azure"
            read -p "Enter VM IP address manually: " VM_IP
        fi
    else
        echo "✗ Azure CLI not found"
        read -p "Enter VM IP address: " VM_IP
    fi
fi

echo ""
echo "Deployment Configuration:"
echo "  VM: $VM_NAME"
echo "  Resource Group: $RESOURCE_GROUP"
echo "  IP: $VM_IP"
echo "  User: $VM_USER"
echo ""

# Check VM is running
echo "Checking VM status..."
if command -v az &> /dev/null; then
    VM_STATUS=$(az vm get-instance-view -g "$RESOURCE_GROUP" -n "$VM_NAME" --query "instanceView.statuses[?starts_with(code, 'PowerState/')].displayStatus" -o tsv 2>/dev/null || echo "Unknown")

    if [[ "$VM_STATUS" == "VM running" ]]; then
        echo "✓ VM is running"
    elif [[ "$VM_STATUS" == "Unknown" ]]; then
        echo "⚠ Could not determine VM status, proceeding anyway..."
    else
        echo "⚠ VM is not running (status: $VM_STATUS)"
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
else
    echo "⚠ Azure CLI not available, assuming VM is running..."
fi

# Test SSH connectivity
echo ""
echo "Testing SSH connectivity..."
if ssh -o ConnectTimeout=5 -o BatchMode=yes "$VM_USER@$VM_IP" exit 2>/dev/null; then
    echo "✓ SSH connection successful"
else
    echo "✗ SSH connection failed"
    echo "Make sure:"
    echo "  1. VM is running"
    echo "  2. SSH key is added to ssh-agent: ssh-add ~/.ssh/id_rsa"
    echo "  3. Your IP is allowed in NSG rules"
    exit 1
fi

echo ""
echo "Step 1: Backup current configuration"
ssh "$VM_USER@$VM_IP" "
    mkdir -p ~/backups
    TIMESTAMP=\$(date +%Y%m%d_%H%M%S)

    if [[ -f ~/config/projects.json ]]; then
        cp ~/config/projects.json ~/backups/projects.json.\$TIMESTAMP
        echo '✓ Backed up projects.json'
    else
        echo '⚠ No existing projects.json to backup'
    fi

    if [[ -f ~/scripts/slack-bot.py ]]; then
        cp ~/scripts/slack-bot.py ~/backups/slack-bot.py.\$TIMESTAMP
        echo '✓ Backed up slack-bot.py'
    else
        echo '⚠ No existing slack-bot.py to backup'
    fi

    echo \"Backups saved with timestamp: \$TIMESTAMP\"
"

echo ""
echo "Step 2: Create config directory if needed"
ssh "$VM_USER@$VM_IP" "
    mkdir -p ~/config
    mkdir -p ~/scripts
    echo '✓ Directories ready'
"

echo ""
echo "Step 3: Upload enhanced projects.json"
if [[ -f "$PROJECT_ROOT/config/projects.json.azure" ]]; then
    scp "$PROJECT_ROOT/config/projects.json.azure" "$VM_USER@$VM_IP:~/config/projects.json"
    echo "✓ Uploaded Azure-specific projects configuration"
elif [[ -f "$PROJECT_ROOT/config/projects.json" ]]; then
    scp "$PROJECT_ROOT/config/projects.json" "$VM_USER@$VM_IP:~/config/projects.json"
    echo "✓ Uploaded default projects configuration"
else
    echo "⚠ No projects.json found, creating default..."
    ssh "$VM_USER@$VM_IP" "cat > ~/config/projects.json << 'EOFPROJECTS'
{
  \"projects\": [
    {
      \"id\": \"flowmetrics\",
      \"name\": \"FlowMetrics\",
      \"repo\": \"NOMARK/flowmetrics-portal\",
      \"stack\": \"sveltekit-postgres\",
      \"priority\": 1,
      \"active\": true
    },
    {
      \"id\": \"instaindex\",
      \"name\": \"InstaIndex\",
      \"repo\": \"NOMARK/instaindex\",
      \"stack\": \"nextjs-supabase\",
      \"priority\": 2,
      \"active\": true
    },
    {
      \"id\": \"inhhale-v2\",
      \"name\": \"Inhhale iOS App\",
      \"repo\": \"NOMARK/inhhale-v2\",
      \"stack\": \"swift-ios\",
      \"description\": \"Medical breathing therapy iOS app for VCD/ILO patients\",
      \"priority\": 4,
      \"active\": true
    }
  ],
  \"defaults\": {
    \"model\": \"claude-opus-4-5-20251101\",
    \"maxConcurrentTasks\": 1,
    \"autoShutdown\": true
  }
}
EOFPROJECTS
"
    echo "✓ Created default projects.json"
fi

echo ""
echo "Step 4: Upload updated slack-bot.py"
if [[ -f "$SCRIPT_DIR/slack-bot.py" ]]; then
    echo "Uploading slack-bot.py from nomark-method/scripts..."
    scp "$SCRIPT_DIR/slack-bot.py" "$VM_USER@$VM_IP:~/scripts/slack-bot.py"
    echo "✓ Uploaded slack bot code"
else
    echo "⚠ slack-bot.py not found at expected location"
    echo "Expected: $SCRIPT_DIR/slack-bot.py"
    echo ""
    echo "Please update slack-bot.py manually with project selector code from:"
    echo "  $PROJECT_ROOT/slack-bot-project-selector.py"
    read -p "Continue without updating slack-bot.py? (y/n): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Deployment cancelled"
        exit 1
    fi
fi

echo ""
echo "Step 5: Set correct permissions"
ssh "$VM_USER@$VM_IP" "
    chmod 644 ~/config/projects.json
    chmod 755 ~/scripts/slack-bot.py 2>/dev/null || true
    echo '✓ Permissions set'
"

echo ""
echo "Step 6: Validate configuration"
ssh "$VM_USER@$VM_IP" "
    echo 'Validating projects.json...'

    if command -v jq &> /dev/null; then
        if jq empty ~/config/projects.json 2>/dev/null; then
            echo '✓ Valid JSON syntax'
        else
            echo '✗ Invalid JSON syntax'
            exit 1
        fi

        if jq -e '.projects[] | select(.id == \"inhhale-v2\")' ~/config/projects.json > /dev/null 2>&1; then
            echo '✓ inhhale-v2 project found'
        else
            echo '⚠ inhhale-v2 project not found in configuration'
        fi

        ACTIVE_COUNT=\$(jq '[.projects[] | select(.active == true)] | length' ~/config/projects.json)
        echo \"✓ Found \$ACTIVE_COUNT active projects\"
    else
        echo '⚠ jq not installed, skipping JSON validation'
    fi
"

echo ""
echo "Step 7: Restart Slack bot service"
echo "Checking if nomark-slack service exists..."
SERVICE_EXISTS=$(ssh "$VM_USER@$VM_IP" "systemctl list-unit-files | grep -c 'nomark-slack.service' || echo 0")

if [[ "$SERVICE_EXISTS" -gt 0 ]]; then
    echo "✓ Service exists, restarting..."
    ssh "$VM_USER@$VM_IP" "
        sudo systemctl restart nomark-slack.service
        echo 'Waiting 3 seconds for service to start...'
        sleep 3
        sudo systemctl status nomark-slack.service --no-pager || true
    "
else
    echo "⚠ nomark-slack.service not found"
    echo "You may need to create the service or start the bot manually"
    echo "To start manually:"
    echo "  ssh $VM_USER@$VM_IP"
    echo "  cd ~/scripts"
    echo "  python3 slack-bot.py &"
fi

echo ""
echo "Step 8: Verify deployment"
ssh "$VM_USER@$VM_IP" "
    echo 'Checking projects.json content...'
    if command -v jq &> /dev/null; then
        echo ''
        echo 'Active projects:'
        jq -r '.projects[] | select(.active == true) | \"  • \\(.id) - \\(.name) (\\(.stack))\"' ~/config/projects.json
    fi

    echo ''
    echo 'Checking Slack bot process...'
    if pgrep -f slack-bot.py > /dev/null 2>&1; then
        BOT_PID=\$(pgrep -f slack-bot.py)
        echo \"✓ Slack bot is running (PID: \$BOT_PID)\"
    else
        echo '⚠ Slack bot process not found'
        if [[ \"$SERVICE_EXISTS\" -gt 0 ]]; then
            echo 'Checking service logs...'
            sudo journalctl -u nomark-slack.service -n 20 --no-pager || true
        fi
    fi
"

echo ""
echo "=========================================="
echo "✓ Deployment Complete!"
echo "=========================================="
echo ""
echo "Testing Instructions:"
echo "  1. Valid project test:"
echo "     @DevOps task inhhale-v2 complete the iOS audit"
echo ""
echo "  2. Invalid project test (triggers dropdown):"
echo "     @DevOps task wrongname test feature"
echo ""
echo "  3. List projects:"
echo "     @DevOps projects"
echo ""
echo "View Logs:"
echo "  ssh $VM_USER@$VM_IP"
echo "  sudo journalctl -u nomark-slack.service -f"
echo ""
echo "Rollback if needed:"
echo "  ssh $VM_USER@$VM_IP"
echo "  ls ~/backups/  # Find your backup timestamp"
echo "  cp ~/backups/projects.json.<timestamp> ~/config/projects.json"
echo "  sudo systemctl restart nomark-slack.service"
echo ""
