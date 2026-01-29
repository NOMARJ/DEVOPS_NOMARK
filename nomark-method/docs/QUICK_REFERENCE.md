# NOMARK DevOps - Quick Reference Guide

## Slack Commands

All commands use `@nomark` mention in the configured channel.

### Task Execution

```
@nomark task <project> <description>
```

**Examples:**
```
@nomark task flowmetrics add priority filter to task list
@nomark task flowmetrics implement dark mode toggle
@nomark task flowmetrics fix typescript errors in dashboard component
@nomark task flowmetrics add user avatar upload feature
@nomark task flowmetrics optimize database queries for advisor list
```

### Status & Monitoring

| Command | Description |
|---------|-------------|
| `@nomark status` | Check VM status and recent activity |
| `@nomark projects` | List available projects |
| `@nomark logs` | Show last 10 task log entries |
| `@nomark logs 20` | Show last 20 log entries |
| `@nomark help` | Show all commands |

---

## What Happens When You Run a Task

1. **Acknowledgment** - Bot confirms task received
2. **Branch Creation** - Creates `ralph/<task-name>` branch
3. **NOMARK Flow** - Executes:
   - `/think` - Analyzes problem
   - `/plan` - Designs atomic stories
   - `/build` - Implements one story at a time
   - `/verify` - Tests, typechecks, browser verify
   - `/simplify` - Cleans up code
   - `/commit` - Commits changes
4. **Completion** - Bot notifies in thread with results

---

## From Your Mac

### Quick Commands

```bash
# Load environment (add to ~/.zshrc for persistence)
source ~/.nomark-devops.env

# SSH to VM
nomark-ssh

# Start/Stop VM (cost management)
nomark-start
nomark-stop

# Check VM status
nomark-status
```

### Manual SSH

```bash
ssh devops@20.5.185.136
```

---

## On the VM

### Run Tasks Directly

```bash
# Run a task
task flowmetrics 'add priority filter to task list'

# Watch task logs
logs

# Watch Slack bot logs
slack-logs
```

### Check Services

```bash
# Slack bot status
sudo systemctl status nomark-slack

# Restart Slack bot
sudo systemctl restart nomark-slack

# View Slack bot logs
sudo journalctl -u nomark-slack -f
```

### Project Management

```bash
# Go to FlowMetrics
cd ~/repos/flowmetrics

# Check current branch
git branch

# See recent commits
git log --oneline -10

# Pull latest changes
git pull origin main
```

---

## Task Types & Examples

### Feature Development
```
@nomark task flowmetrics add dark mode toggle to settings page
@nomark task flowmetrics implement CSV export for advisor list
@nomark task flowmetrics add search functionality to tasks table
```

### Bug Fixes
```
@nomark task flowmetrics fix login redirect not working after session timeout
@nomark task flowmetrics fix date formatting in transaction history
@nomark task flowmetrics resolve typescript error in DashboardCard component
```

### Refactoring
```
@nomark task flowmetrics refactor advisor service to use React Query
@nomark task flowmetrics extract common form validation logic
@nomark task flowmetrics improve error handling in API calls
```

### UI/UX
```
@nomark task flowmetrics improve mobile responsiveness of sidebar
@nomark task flowmetrics add loading skeletons to data tables
@nomark task flowmetrics implement toast notifications for actions
```

---

## Troubleshooting

### Bot Not Responding

1. Check VM is running:
   ```bash
   nomark-status
   ```

2. If stopped, start it:
   ```bash
   nomark-start
   ```

3. SSH and check bot:
   ```bash
   nomark-ssh
   sudo systemctl status nomark-slack
   ```

4. Restart if needed:
   ```bash
   sudo systemctl restart nomark-slack
   ```

### Task Stuck or Failed

1. Check logs in Slack thread
2. SSH to VM and check:
   ```bash
   logs                    # Task logs
   cat ~/logs/tasks.log    # Full log file
   ```

3. Check the branch:
   ```bash
   cd ~/repos/flowmetrics
   git status
   git log --oneline -5
   ```

### VM Auto-Shutdown

The VM shuts down daily at **10:00 UTC (8 PM AEST)** to save costs.

To restart:
```bash
nomark-start
```

Wait ~2 minutes for boot, then Slack bot will reconnect automatically.

---

## Cost Management

| Action | Command |
|--------|---------|
| Stop VM (save costs) | `nomark-stop` |
| Start VM | `nomark-start` |
| Check status | `nomark-status` |

**Estimated Costs:**
- VM running 12hr/day: ~$40/month
- PostgreSQL: ~$25/month
- Storage & networking: ~$10/month
- **Total: ~$75/month**

---

## Available Skills & Agents

The NOMARK method includes 167 skills across these categories:

| Category | Examples |
|----------|----------|
| **anthropic-official** | pdf, docx, xlsx, webapp-testing |
| **claude-code** | plan-mode, codebase-discovery |
| **development** | code patterns, testing |
| **deployment** | CI/CD, docker |
| **analysis** | code review, performance |

---

## Key Files on VM

| Path | Purpose |
|------|---------|
| `~/repos/flowmetrics/` | FlowMetrics codebase |
| `~/repos/flowmetrics/.claude/` | NOMARK method + skills |
| `~/config/.env` | Environment variables |
| `~/config/projects.json` | Project configuration |
| `~/logs/tasks.log` | Task execution logs |
| `~/scripts/nomark-task.sh` | Task runner script |
| `~/scripts/slack-bot.py` | Slack bot |

---

## Adding New Projects

1. Clone the repo:
   ```bash
   gh repo clone OWNER/repo-name ~/repos/project-id
   ```

2. Copy NOMARK method:
   ```bash
   cp -r ~/flowmetrics-skills/organized/* ~/repos/project-id/.claude/
   ```

3. Update projects.json:
   ```bash
   nano ~/config/projects.json
   ```

4. Add entry:
   ```json
   {
     "id": "project-id",
     "name": "Project Name",
     "repo": "OWNER/repo-name",
     "stack": "nextjs-supabase",
     "priority": 2,
     "active": true
   }
   ```

---

## Support

- **VM IP:** 20.5.185.136
- **Slack Channel:** C0AATMZ41M3
- **PostgreSQL:** nomark-devops-db.postgres.database.azure.com
- **Key Vault:** nomark-devops-kv
