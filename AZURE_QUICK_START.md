# Azure Quick Start: Deploy Project Selector in 5 Minutes

## Prerequisites

- Azure VM (`nomark-devops-vm`) is deployed
- Azure CLI installed locally
- SSH access to VM configured
- Slack bot configured with tokens

## Option 1: Automated Deployment (Recommended)

```bash
# From your local machine
cd /Users/reecefrazier/DEVOPS_NOMARK

# Run the deployment script
./nomark-method/scripts/deploy-project-selector.sh
```

**What it does:**
1. ✅ Backs up current configuration
2. ✅ Uploads enhanced projects.json with inhhale-v2
3. ✅ Uploads updated slack-bot.py (if available)
4. ✅ Restarts Slack bot service
5. ✅ Verifies deployment

**Duration**: ~2 minutes

---

## Option 2: Manual Deployment (If Script Fails)

### Step 1: Get VM IP

```bash
az vm show -d -g nomark-devops-rg -n nomark-devops-vm --query publicIps -o tsv
```

### Step 2: SSH to VM

```bash
ssh devops@<VM_IP>
```

### Step 3: Backup Current Config

```bash
mkdir -p ~/backups
cp ~/config/projects.json ~/backups/projects.json.$(date +%Y%m%d_%H%M%S)
cp ~/scripts/slack-bot.py ~/backups/slack-bot.py.$(date +%Y%m%d_%H%M%S)
```

### Step 4: Update projects.json

```bash
cat > ~/config/projects.json << 'EOF'
{
  "projects": [
    {
      "id": "flowmetrics",
      "name": "FlowMetrics",
      "repo": "NOMARK/flowmetrics-portal",
      "stack": "sveltekit-postgres",
      "priority": 1,
      "active": true
    },
    {
      "id": "instaindex",
      "name": "InstaIndex",
      "repo": "NOMARK/instaindex",
      "stack": "nextjs-supabase",
      "priority": 2,
      "active": true
    },
    {
      "id": "inhhale-v2",
      "name": "Inhhale iOS App",
      "repo": "NOMARK/inhhale-v2",
      "stack": "swift-ios",
      "description": "Medical breathing therapy iOS app for VCD/ILO patients",
      "priority": 4,
      "active": true
    }
  ],
  "defaults": {
    "model": "claude-opus-4-5-20251101",
    "maxConcurrentTasks": 1,
    "autoShutdown": true
  }
}
EOF
```

### Step 5: Validate Configuration

```bash
# Check JSON is valid
jq . ~/config/projects.json

# Verify inhhale-v2 exists
jq '.projects[] | select(.id == "inhhale-v2")' ~/config/projects.json
```

### Step 6: Restart Slack Bot

```bash
sudo systemctl restart nomark-slack.service
sudo systemctl status nomark-slack.service
```

### Step 7: Verify Bot is Running

```bash
# Check process
ps aux | grep slack-bot.py

# Check logs
sudo journalctl -u nomark-slack.service -n 50
```

---

## Testing

### Test 1: Valid Project

In Slack:
```
@DevOps task inhhale-v2 complete the iOS audit from inhhale-ios-audit-prompt.md
```

Expected: ✅ Task starts successfully

### Test 2: Invalid Project (Triggers Dropdown)

In Slack:
```
@DevOps task wrongproject add feature
```

Expected:
- ❌ Error message appears
- 🎯 Dropdown menu shows with all projects
- Click "Inhhale iOS App (swift-ios) [P4]"
- ✅ Task starts with "add feature" description

### Test 3: List Projects

In Slack:
```
@DevOps projects
```

Expected: Shows flowmetrics, instaindex, inhhale-v2

---

## Adding the Dropdown Feature

The automated deployment script handles configuration. To manually add the dropdown selector code to slack-bot.py:

### Copy Functions

Open [slack-bot-project-selector.py](slack-bot-project-selector.py) and copy these sections into [nomark-method/scripts/slack-bot.py](nomark-method/scripts/slack-bot.py):

1. **`create_project_selector_blocks()`** → Insert after line ~150
2. **`@app.action("select_project_for_task")`** → Insert after line ~1540
3. **Update `task` command handler** → Replace around line ~2180

See [AZURE_IMPLEMENTATION_GUIDE.md](AZURE_IMPLEMENTATION_GUIDE.md) for detailed code snippets.

---

## Troubleshooting

### Issue: Bot still says "Unknown project"

```bash
# SSH to VM
ssh devops@<VM_IP>

# Check if file exists
cat ~/config/projects.json | jq .

# Check if project exists
cat ~/config/projects.json | jq '.projects[] | select(.id == "inhhale-v2")'

# Restart bot
sudo systemctl restart nomark-slack.service
```

### Issue: Dropdown doesn't appear

**Cause**: Code not yet updated with project selector.

**Solution**: Follow "Adding the Dropdown Feature" section above or run the automated deployment.

### Issue: SSH connection fails

```bash
# Check VM is running
az vm get-instance-view -g nomark-devops-rg -n nomark-devops-vm

# Start VM if stopped
az vm start -g nomark-devops-rg -n nomark-devops-vm

# Wait 30 seconds then retry SSH
```

### Issue: Service won't start

```bash
# Check service logs
sudo journalctl -u nomark-slack.service -n 100 --no-pager

# Check for Python errors
sudo journalctl -u nomark-slack.service | grep -i error

# Test bot manually
cd ~/scripts
python3 slack-bot.py
# Look for error messages
```

---

## Rollback

If something breaks:

```bash
# SSH to VM
ssh devops@<VM_IP>

# List backups
ls -la ~/backups/

# Find your backup timestamp, then:
cp ~/backups/projects.json.20260131_120000 ~/config/projects.json
cp ~/backups/slack-bot.py.20260131_120000 ~/scripts/slack-bot.py

# Restart
sudo systemctl restart nomark-slack.service
```

---

## View Logs

```bash
# Real-time logs
sudo journalctl -u nomark-slack.service -f

# Last 50 lines
sudo journalctl -u nomark-slack.service -n 50

# Logs from today
sudo journalctl -u nomark-slack.service --since today

# Errors only
sudo journalctl -u nomark-slack.service | grep -i error
```

---

## Useful Commands

```bash
# List all projects
jq '.projects[] | "\(.id) - \(.name)"' ~/config/projects.json

# Count active projects
jq '[.projects[] | select(.active == true)] | length' ~/config/projects.json

# Add new project
jq '.projects += [{"id":"newproj","name":"New Project","repo":"org/repo","stack":"nextjs","priority":5,"active":true}]' ~/config/projects.json > ~/config/projects.json.tmp && mv ~/config/projects.json.tmp ~/config/projects.json

# Toggle project active status
jq '(.projects[] | select(.id == "policyai") | .active) = true' ~/config/projects.json > ~/config/projects.json.tmp && mv ~/config/projects.json.tmp ~/config/projects.json
```

---

## Summary

**Immediate fix** (5 min):
1. Run `./nomark-method/scripts/deploy-project-selector.sh`
2. Test in Slack: `@DevOps task inhhale-v2 <task>`
3. Done!

**Manual fix** (10 min):
1. SSH to VM
2. Update `~/config/projects.json`
3. Restart service
4. Test in Slack

**Full dropdown feature** (30 min):
1. Update `slack-bot.py` with selector code
2. Deploy using script
3. Test dropdown with invalid project name
4. Celebrate! 🎉

For full details, see:
- [AZURE_IMPLEMENTATION_GUIDE.md](AZURE_IMPLEMENTATION_GUIDE.md) - Complete guide
- [slack-bot-project-selector.py](slack-bot-project-selector.py) - Code to copy
- [config/projects.json.azure](config/projects.json.azure) - Full configuration example
