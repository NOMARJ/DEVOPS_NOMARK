# DevOps MCP Server

A Model Context Protocol (MCP) server that gives Claude direct access to your infrastructure. Connect to Azure, Supabase, GitHub, Vercel, n8n, and Slack from any MCP-compatible client.

## Features

### 🔧 Azure Tools
- **VM Management**: Start, stop, list, and run commands on VMs
- **Container Apps**: List, restart, view logs
- **Key Vault**: Get and set secrets

### 🗄️ Supabase Tools
- **Database**: Query, insert, update, delete with filters
- **Storage**: List, upload, download files
- **Schema**: List tables, get column info
- **RPC**: Call database functions

### 🐙 GitHub Tools
- **Repositories**: List, get info, file contents
- **Pull Requests**: List, create, merge
- **Issues**: List, create
- **Actions**: List runs, trigger workflows
- **Branches**: List branches

### ▲ Vercel Tools
- **Deployments**: List, create, cancel
- **Projects**: List projects
- **Environment**: List and set env vars

### ⚡ n8n Tools
- **Workflows**: List, get, activate, deactivate, execute
- **Executions**: List, get details
- **Webhooks**: Trigger webhook workflows
- **Credentials**: List available credentials

### 💬 Slack Tools
- **Messages**: Send to channels, reply in threads
- **Webhooks**: Send via incoming webhooks
- **Channels**: List, get history
- **Files**: Upload files
- **Deployments**: Formatted deployment notifications

### 📚 Skills Tools
- **Discovery**: List and search skills
- **Content**: Get skill documentation
- **Recommendations**: Get skill suggestions for tasks

## Installation

```bash
# Clone the repository
git clone https://github.com/your-org/devops-mcp.git
cd devops-mcp

# Install with all integrations
pip install -e ".[all]"

# Or install specific integrations
pip install -e ".[azure,github]"
```

## Configuration

### Environment Variables

Create a `.env` file or set environment variables:

```bash
# Azure (uses DefaultAzureCredential)
AZURE_SUBSCRIPTION_ID=your-subscription-id
AZURE_TENANT_ID=your-tenant-id
AZURE_CLIENT_ID=your-client-id
AZURE_CLIENT_SECRET=your-client-secret

# Supabase
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_KEY=your-service-key

# GitHub
GITHUB_TOKEN=ghp_your-token

# Vercel
VERCEL_TOKEN=your-vercel-token
VERCEL_TEAM_ID=your-team-id  # Optional

# n8n
N8N_URL=https://n8n.yourdomain.com
N8N_API_KEY=your-n8n-api-key

# Slack
SLACK_BOT_TOKEN=xoxb-your-token
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...

# Skills
SKILLS_DIR=/path/to/your/skills
```

### Claude Desktop

Add to your Claude Desktop config (`~/Library/Application Support/Claude/claude_desktop_config.json` on macOS):

```json
{
  "mcpServers": {
    "devops": {
      "command": "python",
      "args": ["-m", "devops_mcp"],
      "cwd": "/path/to/devops-mcp",
      "env": {
        "AZURE_SUBSCRIPTION_ID": "...",
        "SUPABASE_URL": "...",
        "GITHUB_TOKEN": "..."
      }
    }
  }
}
```

### Windsurf

Add to your Windsurf MCP settings:

```json
{
  "mcp": {
    "servers": {
      "devops": {
        "command": "python",
        "args": ["-m", "devops_mcp"],
        "cwd": "/path/to/devops-mcp"
      }
    }
  }
}
```

### Claude Code CLI

```bash
# Set environment variables
export AZURE_SUBSCRIPTION_ID=...
export GITHUB_TOKEN=...

# Run with MCP
claude --mcp devops-mcp
```

## Usage Examples

Once connected, Claude can use the tools directly:

### Start a VM
```
"Start the devops-agent VM in the devops-agent-rg resource group"
→ Claude calls azure_vm_start(resource_group="devops-agent-rg", vm_name="devops-agent-vm")
```

### Query Database
```
"Show me all active platforms from Supabase"
→ Claude calls supabase_query(table="platforms", filters=[{"column": "is_active", "operator": "eq", "value": true}])
```

### Create PR
```
"Create a PR from feature/login to main with title 'Add login feature'"
→ Claude calls github_pr_create(owner="org", repo="app", title="Add login feature", head="feature/login", base="main")
```

### Trigger Workflow
```
"Trigger the client-provisioning workflow in n8n"
→ Claude calls n8n_webhook_trigger(webhook_path="client-provisioning", data={...})
```

### Deploy Notification
```
"Send a deployment success notification to #deployments"
→ Claude calls slack_notify_deployment(channel="#deployments", project="FlowMetrics", environment="production", status="success")
```

### Find Skills
```
"What skills do I have for creating Excel reports?"
→ Claude calls skills_search(query="excel")
```

## Skills Integration

The MCP server can discover and serve skills from your skills directory:

```
skills/
├── manifest.json           # Auto-generated index
├── documents/
│   ├── docx/SKILL.md
│   ├── xlsx/SKILL.md
│   └── pdf/SKILL.md
├── patterns/
│   ├── sveltekit/SKILL.md
│   └── postgres/SKILL.md
└── agents/
    └── ralph/SKILL.md
```

Claude can:
1. List available skills
2. Search for relevant skills
3. Get full skill content
4. Get recommendations based on task

## Security Notes

1. **Credentials**: Never commit credentials. Use environment variables or secure secret management.

2. **Service Keys**: Use service role keys for Supabase (not anon keys) as they bypass RLS.

3. **Azure**: Use managed identity in production instead of client secrets.

4. **Network**: Consider running the MCP server in a private network with your infrastructure.

5. **Audit**: All tool calls can be logged for audit purposes.

## Development

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Format code
black src/
ruff check src/

# Run locally
python -m devops_mcp
```

## Adding New Tools

1. Create a new file in `src/tools/`:

```python
class MyTools:
    def get_tools(self) -> dict[str, dict]:
        return {
            "my_tool": {
                "description": "What this tool does",
                "input_schema": {
                    "type": "object",
                    "properties": {...},
                    "required": [...],
                },
                "handler": self.my_handler,
            }
        }
    
    async def my_handler(self, **kwargs) -> dict:
        # Implementation
        return {"result": "..."}
```

2. Import and register in `__main__.py`:

```python
from tools.my_tools import MyTools

my_tools = MyTools()

ALL_TOOLS = {
    ...
    **my_tools.get_tools(),
}
```

## Troubleshooting

### "Tool not found"
- Check that the integration is configured (environment variables set)
- Verify the MCP server is running

### "Authentication failed"
- Verify credentials are correct
- Check token expiration
- Ensure required scopes/permissions

### "Connection refused"
- Check the service URL is correct
- Verify network connectivity
- Check firewall rules

## License

MIT
