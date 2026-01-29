# FlowMetrics Skills Repository

A centralized repository of skills, agents, patterns, and tools that works across:
- Claude Desktop (via MCP)
- Windsurf (via .windsurfrules)
- Claude Code CLI
- DevOps Agent VM

## Quick Start

```bash
# Clone
git clone https://github.com/your-org/flowmetrics-skills.git
cd flowmetrics-skills

# Generate configs for your tools
./scripts/generate-configs.sh

# Output:
# - .windsurfrules (copy to your projects)
# - claude-project-instructions.md (paste into Claude Projects)
# - manifest.json (used by MCP server)
```

## Structure

```
flowmetrics-skills/
├── manifest.json                 # Auto-generated skill index
├── CLAUDE.md                     # Master context (generated)
├── .windsurfrules                # Generated for Windsurf
│
├── documents/                    # Document generation skills
│   ├── docx/
│   │   ├── SKILL.md             # Instructions for Claude
│   │   ├── templates/           # Document templates
│   │   └── examples/            # Example outputs
│   ├── xlsx/
│   ├── pptx/
│   ├── pdf/
│   └── carbone/                 # Carbone template system
│
├── patterns/                     # Code patterns & conventions
│   ├── sveltekit/
│   ├── python/
│   ├── postgres/
│   ├── typescript/
│   └── terraform/
│
├── integrations/                 # External service integrations
│   ├── n8n/
│   ├── metabase/
│   ├── azure/
│   ├── supabase/
│   ├── stripe/
│   └── sftpgo/
│
├── agents/                       # Autonomous agent configs
│   ├── ralph/
│   ├── data-processor/
│   ├── report-generator/
│   └── client-provisioner/
│
├── data/                         # Data processing skills
│   ├── sftp/
│   ├── csv/
│   ├── validation/
│   ├── transformation/
│   └── reconciliation/
│
├── prompts/                      # Reusable prompts
│   ├── analysis/
│   ├── writing/
│   ├── code-review/
│   └── debugging/
│
├── workflows/                    # n8n workflow templates
│   ├── client-provisioning/
│   ├── data-ingestion/
│   └── reporting/
│
└── scripts/                      # Utility scripts
    ├── generate-configs.sh
    ├── validate-skills.py
    └── sync-to-mcp.sh
```

## Skill File Format

Each skill has a `SKILL.md` file that Claude reads:

```markdown
# Skill Name

> One-line description for manifest

## When to Use
- Trigger condition 1
- Trigger condition 2

## Prerequisites
- Required packages
- Required credentials

## Instructions
Step-by-step instructions for Claude...

## Examples
Code examples, templates, etc.

## Common Issues
Troubleshooting tips...
```

## Adding a New Skill

1. Create directory: `mkdir -p category/skill-name`
2. Create `SKILL.md` with the format above
3. Run `./scripts/generate-configs.sh` to update manifest
4. Commit and push

## Syncing to Tools

### Claude Desktop (MCP)
Set `SKILLS_DIR` environment variable in your MCP config:
```json
{
  "env": {
    "SKILLS_DIR": "/path/to/flowmetrics-skills"
  }
}
```

### Windsurf
Copy generated `.windsurfrules` to your project root.

### Claude Projects
Copy `claude-project-instructions.md` content to your project instructions.

### DevOps Agent VM
The VM automatically syncs skills on startup.

## Categories

| Category | Purpose | Examples |
|----------|---------|----------|
| `documents` | Document generation | Word, Excel, PDF, Carbone |
| `patterns` | Code patterns | SvelteKit, Python, SQL |
| `integrations` | External services | n8n, Metabase, Stripe |
| `agents` | Autonomous configs | Ralph, data processors |
| `data` | Data processing | SFTP, validation, ETL |
| `prompts` | Reusable prompts | Analysis, writing |
| `workflows` | n8n templates | Provisioning, reporting |
