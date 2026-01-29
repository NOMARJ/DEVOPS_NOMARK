# NOMARK DevOps - Slack Integration Setup

## Overview

The Slack bot allows you to dispatch tasks to the NOMARK DevOps VM directly from Slack. Simply mention `@nomark` with a command.

## Commands

| Command | Description |
|---------|-------------|
| `@nomark task <project> <description>` | Run a development task |
| `@nomark status` | Check VM and current task status |
| `@nomark projects` | List available projects |
| `@nomark logs [n]` | Show recent task logs |

### Examples

```
@nomark task flowmetrics add priority filter to task list
@nomark task instaindex implement dark mode toggle
@nomark status
@nomark logs 20
```

---

## Setup Instructions

### Step 1: Create Slack App

1. Go to [api.slack.com/apps](https://api.slack.com/apps)
2. Click **Create New App** → **From scratch**
3. Name: `NOMARK DevOps`
4. Workspace: Select your NOMARK workspace
5. Click **Create App**

### Step 2: Configure Bot Permissions

1. Go to **OAuth & Permissions** in the sidebar
2. Under **Bot Token Scopes**, add:
   - `app_mentions:read` - Read mentions
   - `chat:write` - Send messages
   - `im:history` - Read DM history (optional)
   - `im:write` - Send DMs (optional)

### Step 3: Enable Socket Mode

1. Go to **Socket Mode** in the sidebar
2. Enable Socket Mode
3. Create an **App-Level Token**:
   - Name: `nomark-socket`
   - Scopes: `connections:write`
4. Copy the token (starts with `xapp-`)

### Step 4: Subscribe to Events

1. Go to **Event Subscriptions** in the sidebar
2. Enable Events
3. Under **Subscribe to bot events**, add:
   - `app_mention` - When someone mentions @nomark
   - `message.im` - Direct messages (optional)
4. Save Changes

### Step 5: Install App to Workspace

1. Go to **Install App** in the sidebar
2. Click **Install to Workspace**
3. Authorize the app
4. Copy the **Bot User OAuth Token** (starts with `xoxb-`)

### Step 6: Configure VM

1. SSH to your NOMARK DevOps VM
2. Edit `~/config/.env`:

```bash
# Slack Configuration
SLACK_BOT_TOKEN=xoxb-your-bot-token-here
SLACK_APP_TOKEN=xapp-your-app-token-here
SLACK_CHANNEL_ID=C0123456789  # Optional: default channel for notifications
```

3. Start the Slack bot:

```bash
# Manual start
source ~/venv/bin/activate
python ~/scripts/slack-bot.py

# Or enable as service
sudo systemctl enable nomark-slack
sudo systemctl start nomark-slack
```

### Step 7: Test

1. In Slack, invite the bot to a channel:
   ```
   /invite @nomark
   ```

2. Test with:
   ```
   @nomark status
   @nomark projects
   ```

---

## Troubleshooting

### Bot not responding

1. Check if the service is running:
   ```bash
   sudo systemctl status nomark-slack
   ```

2. Check logs:
   ```bash
   sudo journalctl -u nomark-slack -f
   ```

3. Verify tokens are correct in `~/config/.env`

### Permission errors

1. Ensure all required scopes are added in Slack app settings
2. Reinstall the app to the workspace after adding scopes

### Connection issues

1. Verify Socket Mode is enabled
2. Check the app-level token has `connections:write` scope
3. Verify VM has outbound internet access

---

## Security Notes

- Store tokens only in `~/config/.env` (not in code)
- The `.env` file should have restricted permissions:
  ```bash
  chmod 600 ~/config/.env
  ```
- Consider using Azure Key Vault for production:
  ```bash
  az keyvault secret set --vault-name nomark-devops-kv --name SLACK-BOT-TOKEN --value "xoxb-..."
  ```

---

## Architecture

```
┌─────────────┐     ┌────────────────┐     ┌─────────────────┐
│   Slack     │────▶│  Socket Mode   │────▶│  NOMARK VM      │
│   Channel   │     │  (WebSocket)   │     │                 │
└─────────────┘     └────────────────┘     │  slack-bot.py   │
                                           │       │         │
                                           │       ▼         │
                                           │  nomark-task.sh │
                                           │       │         │
                                           │       ▼         │
                                           │  Claude Code    │
                                           └─────────────────┘
```

The bot uses Socket Mode (WebSocket) which:
- Doesn't require a public URL
- Works behind firewalls
- Maintains persistent connection
- Lower latency than HTTP webhooks
