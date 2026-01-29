# VM Starter Function Setup

## What This Does

An Azure Function that allows you to start the DevOps VM from Slack using the `/nomark-start` command.

## Deployed Function

- **URL:** `https://nomark-vm-starter.azurewebsites.net/api/start-vm`
- **Health Check:** `https://nomark-vm-starter.azurewebsites.net/api/health`

## Slack Setup

### 1. Create Slash Command

1. Go to https://api.slack.com/apps
2. Select your NOMARK app
3. Click **Slash Commands** in the left menu
4. Click **Create New Command**
5. Fill in:
   - **Command:** `/nomark-start`
   - **Request URL:** `https://nomark-vm-starter.azurewebsites.net/api/start-vm`
   - **Short Description:** `Start the DevOps VM`
   - **Usage Hint:** `[no arguments needed]`
6. Click **Save**

### 2. Get Verification Token (Optional but Recommended)

1. Go to **Basic Information** in your Slack app settings
2. Scroll to **App Credentials**
3. Copy the **Verification Token**
4. Add it to the Function App settings:

```bash
az functionapp config appsettings set \
  --name nomark-vm-starter \
  --resource-group nomark-devops-rg \
  --settings "SLACK_VERIFICATION_TOKEN=your-token-here"
```

### 3. Reinstall App (if needed)

If the slash command doesn't appear:
1. Go to **Install App** in your Slack app settings
2. Click **Reinstall to Workspace**
3. Authorize the permissions

## Usage

In any Slack channel:

```
/nomark-start
```

Response:
- If VM is **stopped**: "🚀 Starting VM... This will take 1-2 minutes"
- If VM is **already running**: "✅ VM is already running" with IP and MCP URL

## Cost

Azure Functions Consumption Plan:
- **First 1M executions:** FREE
- **After:** $0.20 per million executions
- **Expected cost:** $0/month (well within free tier)

## Architecture

```
Slack Command (/nomark-start)
    ↓
Azure Function (nomark-vm-starter)
    ↓
Azure VM Management API
    ↓
VM starts (1-2 minutes)
    ↓
Services auto-start (nomark-slack, devops-mcp, caddy)
```

## Testing

Test the function directly:

```bash
# Health check
curl https://nomark-vm-starter.azurewebsites.net/api/health

# Start VM (requires Slack token in body)
curl -X POST https://nomark-vm-starter.azurewebsites.net/api/start-vm \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "user_name=test&token=YOUR_SLACK_TOKEN"
```

## Troubleshooting

### Slash command not appearing
- Reinstall the Slack app
- Check that the command was saved correctly

### "Unauthorized" error
- Add `SLACK_VERIFICATION_TOKEN` to Function App settings
- Or remove token check from `function_app.py`

### VM not starting
- Check Function App logs:
  ```bash
  az functionapp log tail --name nomark-vm-starter --resource-group nomark-devops-rg
  ```
- Verify managed identity has "Virtual Machine Contributor" role

### Function timeout
- The function returns immediately with "Starting VM..."
- VM actually takes 1-2 minutes to start in the background

## Monitoring

View logs in Azure Portal:
1. Go to Function App: `nomark-vm-starter`
2. Click **Monitor** → **Logs**
3. See execution history and errors

## Update Function

To redeploy after making changes:

```bash
cd /Users/reecefrazier/DEVOPS_NOMARK/vm-starter-function
func azure functionapp publish nomark-vm-starter --python
```
