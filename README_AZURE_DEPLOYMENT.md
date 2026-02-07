# Azure Deployment: Slack Bot Project Selector - Complete Package

## 🎯 What You're Getting

A complete, production-ready implementation of the Slack bot project selector for your Azure infrastructure. This eliminates the `❌ Unknown project: 'inhhale-v2'` error and adds interactive dropdown menus to prevent future typos.

---

## 📦 Files Included

### Core Implementation Files

| File | Purpose | Use When |
|------|---------|----------|
| [AZURE_QUICK_START.md](AZURE_QUICK_START.md) | 5-minute deployment guide | You want to deploy NOW |
| [AZURE_IMPLEMENTATION_GUIDE.md](AZURE_IMPLEMENTATION_GUIDE.md) | Complete technical guide | You want full understanding |
| [nomark-method/scripts/deploy-project-selector.sh](nomark-method/scripts/deploy-project-selector.sh) | Automated deployment script | Automated deployment |
| [config/projects.json.azure](config/projects.json.azure) | Azure-optimized project configuration | Reference/template |

### Reference Documentation

| File | Purpose | Use When |
|------|---------|----------|
| [QUICK_FIX_GUIDE.md](QUICK_FIX_GUIDE.md) | General troubleshooting | Something breaks |
| [SLACK_PROJECT_SELECTOR_IMPLEMENTATION.md](SLACK_PROJECT_SELECTOR_IMPLEMENTATION.md) | Detailed implementation details | Deep dive needed |
| [slack-bot-project-selector.py](slack-bot-project-selector.py) | Code to add to slack-bot.py | Manual code updates |
| [PROJECT_SELECTOR_SUMMARY.md](PROJECT_SELECTOR_SUMMARY.md) | Executive summary | Share with team |
| [test-project-selector.sh](test-project-selector.sh) | Validation script | Verify configuration |

---

## 🚀 Quick Deploy (5 Minutes)

### Prerequisites Check

- [ ] Azure VM deployed (`nomark-devops-vm`)
- [ ] Azure CLI installed on your machine
- [ ] SSH access to VM configured
- [ ] Slack bot tokens configured

### Deploy Now

```bash
# 1. Navigate to project directory
cd /Users/reecefrazier/DEVOPS_NOMARK

# 2. Run automated deployment
./nomark-method/scripts/deploy-project-selector.sh

# 3. Test in Slack
# @DevOps task inhhale-v2 complete the iOS audit
```

That's it! ✅

---

## 📋 What Gets Deployed

### Configuration Files

**On Azure VM (`~/config/projects.json`):**
```json
{
  "projects": [
    {
      "id": "flowmetrics",
      "name": "FlowMetrics",
      "stack": "sveltekit-postgres",
      "active": true
    },
    {
      "id": "instaindex",
      "name": "InstaIndex",
      "stack": "nextjs-supabase",
      "active": true
    },
    {
      "id": "inhhale-v2",
      "name": "Inhhale iOS App",
      "stack": "swift-ios",
      "active": true  ← This fixes your error!
    }
  ]
}
```

### Code Updates

**Enhanced slack-bot.py features:**
- ✅ Validates project IDs against projects.json
- ✅ Shows interactive dropdown when project not found
- ✅ Preserves task description during error recovery
- ✅ Lists all active projects with quick selector

---

## 🎨 User Experience Improvements

### Before (Current State)

```
User: @DevOps task inhale-v2 complete audit
Bot:  ❌ Unknown project: `inhale-v2`

      Available Projects:
      • flowmetrics - FlowMetrics
      • instaindex - InstaIndex
      • inhhale-v2 - Inhhale iOS App

User: [Has to retype everything with correct spelling]
      @DevOps task inhhale-v2 complete audit
```

**Problems:**
- ❌ User must retype entire command
- ❌ Easy to make another typo
- ❌ Task description is lost
- ❌ Frustrating experience

### After (With Project Selector)

```
User: @DevOps task inhale-v2 complete audit
Bot:  ❌ Unknown project: `inhale-v2`

      🎯 Select the correct project:
      [Dropdown Menu]
      ▼ Choose a project...
        • FlowMetrics (sveltekit-postgres) [P1]
        • InstaIndex (nextjs-supabase) [P2]
        • Inhhale iOS App (swift-ios) [P4]     ← User clicks this

      💡 Tip: Available IDs: flowmetrics, instaindex, inhhale-v2

User: [Clicks "Inhhale iOS App"]
Bot:  ✅ Project selected: Inhhale iOS App
      🚀 Starting task on `inhhale-v2`...
      Task: complete audit
```

**Benefits:**
- ✅ One click to fix
- ✅ No retyping needed
- ✅ Task description preserved
- ✅ Visual project list
- ✅ No typos possible

---

## 🏗️ Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    LOCAL MACHINE                            │
│  ┌───────────────────────────────────────────────────────┐  │
│  │ /DEVOPS_NOMARK/                                       │  │
│  │ ├── nomark-method/scripts/                            │  │
│  │ │   ├── deploy-project-selector.sh  ← Run this       │  │
│  │ │   └── slack-bot.py                ← Updated code    │  │
│  │ └── config/                                           │  │
│  │     └── projects.json.azure         ← Template        │  │
│  └───────────────────────────────────────────────────────┘  │
└────────────────────┬────────────────────────────────────────┘
                     │ SCP/SSH
                     ▼
┌─────────────────────────────────────────────────────────────┐
│                  AZURE VM (nomark-devops-vm)                │
│  ┌───────────────────────────────────────────────────────┐  │
│  │ /home/devops/                                         │  │
│  │ ├── config/                                           │  │
│  │ │   └── projects.json        ← Deployed here         │  │
│  │ ├── scripts/                                          │  │
│  │ │   └── slack-bot.py         ← Updated here          │  │
│  │ └── backups/                                          │  │
│  │     ├── projects.json.<timestamp>  ← Auto backup     │  │
│  │     └── slack-bot.py.<timestamp>                     │  │
│  └───────────────────────────────────────────────────────┘  │
│                                                              │
│  systemd service: nomark-slack.service                      │
│  Status: sudo systemctl status nomark-slack.service         │
└─────────────────────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│                    SLACK WORKSPACE                          │
│  User: @DevOps task <project> <description>                │
│  Bot:  [Interactive dropdown if project invalid]            │
└─────────────────────────────────────────────────────────────┘
```

---

## 🔧 Deployment Script Features

The [deploy-project-selector.sh](nomark-method/scripts/deploy-project-selector.sh) script includes:

- ✅ **Automatic VM detection** - Fetches IP from Azure CLI
- ✅ **VM status check** - Starts VM if needed
- ✅ **SSH connectivity test** - Validates connection before deploy
- ✅ **Automatic backups** - Saves current config with timestamp
- ✅ **Configuration upload** - Deploys projects.json
- ✅ **Code deployment** - Updates slack-bot.py
- ✅ **Service restart** - Restarts Slack bot automatically
- ✅ **Validation checks** - Verifies JSON syntax and required projects
- ✅ **Error handling** - Clear error messages with rollback instructions
- ✅ **Comprehensive logging** - Shows every step

---

## 📊 Testing Checklist

After deployment, test these scenarios:

### ✅ Basic Functionality

- [ ] **Valid project name works**
  ```
  @DevOps task inhhale-v2 complete the iOS audit
  → Should start task successfully
  ```

- [ ] **Invalid project shows dropdown**
  ```
  @DevOps task wrongname test feature
  → Should show dropdown menu
  → Click correct project
  → Task should start with preserved description
  ```

- [ ] **List projects command**
  ```
  @DevOps projects
  → Should show: flowmetrics, instaindex, inhhale-v2
  ```

### ✅ Advanced Features

- [ ] **Project selector preserves task**
  ```
  @DevOps task typo this is a long task description with details
  → Select correct project from dropdown
  → Verify "this is a long task description with details" is preserved
  ```

- [ ] **Active/inactive projects**
  ```
  @DevOps task policyai test
  → Should reject (policyai is inactive)
  ```

### ✅ System Health

- [ ] **Bot process running**
  ```bash
  ssh devops@<VM_IP>
  ps aux | grep slack-bot.py
  → Should show running process
  ```

- [ ] **Service status healthy**
  ```bash
  sudo systemctl status nomark-slack.service
  → Should show "active (running)"
  ```

- [ ] **No errors in logs**
  ```bash
  sudo journalctl -u nomark-slack.service -n 50
  → Check for errors
  ```

---

## 🆘 Troubleshooting Guide

### Issue: Deployment script fails

**Check 1: Azure CLI authenticated?**
```bash
az account show
# If not logged in:
az login
```

**Check 2: VM is running?**
```bash
az vm get-instance-view -g nomark-devops-rg -n nomark-devops-vm --query "instanceView.statuses[1].displayStatus"
# Should return: "VM running"
```

**Check 3: SSH key configured?**
```bash
ssh-add -l
# If empty:
ssh-add ~/.ssh/id_rsa
```

### Issue: Bot doesn't recognize project

**Check 1: File was deployed?**
```bash
ssh devops@<VM_IP> "cat ~/config/projects.json | jq ."
```

**Check 2: Project exists in file?**
```bash
ssh devops@<VM_IP> "jq '.projects[] | select(.id == \"inhhale-v2\")' ~/config/projects.json"
```

**Check 3: Bot was restarted?**
```bash
ssh devops@<VM_IP> "sudo systemctl restart nomark-slack.service && sudo systemctl status nomark-slack.service"
```

### Issue: Dropdown doesn't appear

**Cause**: Dropdown feature requires code changes to slack-bot.py

**Solution**:
1. The deployment script handles this if `nomark-method/scripts/slack-bot.py` has the selector code
2. If not, manually update slack-bot.py using code from [slack-bot-project-selector.py](slack-bot-project-selector.py)
3. See [AZURE_IMPLEMENTATION_GUIDE.md](AZURE_IMPLEMENTATION_GUIDE.md) Section "Phase 2: Update Slack Bot Code"

---

## 🔄 Rollback Procedure

If something goes wrong:

```bash
# 1. SSH to VM
ssh devops@<VM_IP>

# 2. List backups
ls -la ~/backups/

# 3. Find your backup (look for timestamp before deployment)
# Example: projects.json.20260131_143022

# 4. Restore
cp ~/backups/projects.json.20260131_143022 ~/config/projects.json
cp ~/backups/slack-bot.py.20260131_143022 ~/scripts/slack-bot.py

# 5. Restart service
sudo systemctl restart nomark-slack.service

# 6. Verify
sudo systemctl status nomark-slack.service
```

---

## 📈 Monitoring

### Real-time Logs

```bash
ssh devops@<VM_IP>
sudo journalctl -u nomark-slack.service -f
```

### Check Bot Health

```bash
# Service status
sudo systemctl status nomark-slack.service

# Process check
ps aux | grep slack-bot.py

# Recent errors
sudo journalctl -u nomark-slack.service | grep -i error | tail -20
```

### Azure Portal Monitoring

1. Go to Azure Portal → Resource Groups → `nomark-devops-rg`
2. Click on `nomark-devops-vm`
3. View metrics: CPU, Memory, Network
4. Check auto-shutdown schedule (should be 19:00 UTC)

---

## 💰 Cost Impact

**No additional costs!** This is a configuration update only.

**Current Azure costs remain the same:**
- VM (with auto-shutdown): ~$20-30/month
- PostgreSQL: ~$25/month
- Key Vault: ~$1/month
- Functions: Free tier
- **Total**: ~$50-60/month

---

## 🔐 Security Notes

- ✅ All backups stored on VM (not transmitted)
- ✅ Deployment uses SSH keys (no passwords)
- ✅ projects.json contains no secrets
- ✅ Slack tokens remain in environment variables
- ✅ Database credentials in Azure Key Vault

---

## 📚 Additional Resources

### Documentation

- **Quick Start**: [AZURE_QUICK_START.md](AZURE_QUICK_START.md) - 5-minute guide
- **Full Guide**: [AZURE_IMPLEMENTATION_GUIDE.md](AZURE_IMPLEMENTATION_GUIDE.md) - Complete documentation
- **Troubleshooting**: [QUICK_FIX_GUIDE.md](QUICK_FIX_GUIDE.md) - Problem solving

### Code Examples

- **Project Selector Code**: [slack-bot-project-selector.py](slack-bot-project-selector.py)
- **Configuration Template**: [config/projects.json.azure](config/projects.json.azure)
- **Deployment Script**: [nomark-method/scripts/deploy-project-selector.sh](nomark-method/scripts/deploy-project-selector.sh)

### Testing

- **Validation Script**: [test-project-selector.sh](test-project-selector.sh)

---

## ✅ Summary Checklist

### Pre-Deployment

- [ ] Azure VM is accessible
- [ ] SSH keys configured
- [ ] Azure CLI authenticated
- [ ] Reviewed [AZURE_QUICK_START.md](AZURE_QUICK_START.md)

### Deployment

- [ ] Ran `deploy-project-selector.sh`
- [ ] Deployment completed successfully
- [ ] No errors in script output
- [ ] Backups created

### Validation

- [ ] Tested valid project: `@DevOps task inhhale-v2 test`
- [ ] Tested invalid project: `@DevOps task wrongname test`
- [ ] Dropdown appeared for invalid project
- [ ] Selected project from dropdown worked
- [ ] Checked service status: `systemctl status nomark-slack.service`
- [ ] Reviewed logs for errors

### Documentation

- [ ] Shared [AZURE_QUICK_START.md](AZURE_QUICK_START.md) with team
- [ ] Documented rollback procedure location
- [ ] Noted backup timestamps for recovery

---

## 🎉 Success Criteria

You'll know the deployment is successful when:

1. ✅ `@DevOps task inhhale-v2 <task>` starts tasks without error
2. ✅ Invalid project names show interactive dropdown menu
3. ✅ Selecting from dropdown preserves task description
4. ✅ `@DevOps projects` lists all active projects
5. ✅ No errors in `sudo journalctl -u nomark-slack.service`

---

## 🚀 Next Steps

After successful deployment:

1. **Test with your team** - Have team members try the dropdown feature
2. **Add more projects** - Use `@DevOps register <github-url>`
3. **Customize configuration** - Edit `~/config/projects.json` on VM
4. **Set up monitoring** - Configure Azure Monitor alerts
5. **Document team usage** - Share Slack commands with team

---

## 📞 Support

If you encounter issues:

1. **Check logs**: `sudo journalctl -u nomark-slack.service -n 100`
2. **Review troubleshooting**: [QUICK_FIX_GUIDE.md](QUICK_FIX_GUIDE.md)
3. **Rollback if needed**: See "Rollback Procedure" section above
4. **Test configuration**: Run `test-project-selector.sh` on VM

---

**Ready to deploy?** Run this now:

```bash
cd /Users/reecefrazier/DEVOPS_NOMARK
./nomark-method/scripts/deploy-project-selector.sh
```

Good luck! 🚀
