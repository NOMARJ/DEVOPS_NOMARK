# CLAUDE.md - DEVOPS_NOMARK

> This file is read by all Claude Code sessions and teammates. Keep it accurate.

## Project Overview

DevOps automation framework for autonomous AI-driven development using Claude Code. Four main components:

| Component | Purpose | Tech |
|-----------|---------|------|
| `devops-mcp/` | MCP server exposing Azure, Supabase, GitHub, Slack, n8n tools | Python 3.10+, MCP SDK |
| `devops-agent/` | Autonomous VM orchestration (Slack -> n8n -> Azure VM -> Claude) | Terraform, n8n, Shell |
| `nomark-method/` | NOMARK development methodology (THINK-PLAN-BUILD-VERIFY) | Skills, Shell, Python |
| `flowmetrics-skills/` | Centralized reusable skills repository | Markdown, Python |

## Tech Stack

- **Language**: Python 3.10+, Shell (Bash), HCL (Terraform)
- **Cloud**: Microsoft Azure (VMs, Container Apps, Key Vault, Functions)
- **IaC**: Terraform >= 1.0 (Azure provider 3.80+)
- **Orchestration**: n8n (self-hosted)
- **Database**: PostgreSQL (Supabase)
- **Linting**: Black (line-length: 100), Ruff (rules: E, F, I, N, W)
- **Testing**: pytest, pytest-asyncio
- **Build**: Hatchling

## Workflow

1. Run linter: `black --check . && ruff check .`
2. Run tests: `cd devops-mcp && pytest`
3. Validate Terraform: `cd devops-agent/terraform && terraform validate`
4. Before PR: Full verification across all components

## Code Style

- Python: Black formatter, line-length 100
- Ruff linter rules: E, F, I, N, W (ignore E501)
- Use type hints everywhere in Python
- Use snake_case for Python, kebab-case for file names
- Keep functions small and focused
- Handle errors explicitly

## DO NOT

- Commit secrets, .env files, or credentials
- Skip running tests before committing
- Modify terraform state files directly
- Hard-code cloud resource IDs or connection strings
- Over-engineer simple solutions
- Make breaking API changes to MCP tools without discussion

## Key Directories

```
devops-mcp/              # MCP server (Python package)
  devops_mcp/            #   Main implementation
    tools/               #   Tool handlers (azure, supabase, github, etc.)
devops-agent/            # Agent VM orchestration
  terraform/             #   Azure infrastructure
  n8n-workflows/         #   Workflow definitions
  scripts/               #   Ralph agent, init scripts
nomark-method/           # NOMARK methodology
  .claude/               #   Claude skills, agents, commands
  scripts/               #   Task execution, integrations
  templates/             #   CLAUDE.md, PRD, progress templates
flowmetrics-skills/      # Skills library
  documents/             #   Document generation skills
  patterns/              #   Code pattern skills
  integrations/          #   Service integration skills
```

## Agent Teams

This project uses Claude Code Agent Teams for parallel DevOps work. Teams are configured in `.claude/settings.json` with the `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS` feature flag enabled.

### Team Roles

Teammates should specialize in one area:
- **infra-specialist**: Terraform, Azure resources, networking
- **mcp-developer**: MCP server tools, Python implementation
- **security-reviewer**: Credentials, RBAC, network policies, Key Vault
- **workflow-builder**: n8n workflows, Slack integrations, automation
- **qa-verifier**: Testing, linting, verification across components

### Teammate Guidelines

- Each teammate owns distinct files - avoid editing the same files
- Use the shared task list to coordinate dependencies
- Run verification before marking tasks complete
- Message other teammates when your work affects their area
- Follow existing codebase patterns found in each component

## Commands Reference

```sh
# MCP Server
cd devops-mcp && pip install -e ".[dev]"    # Install with dev deps
cd devops-mcp && pytest                      # Run tests
cd devops-mcp && black --check .             # Check formatting
cd devops-mcp && ruff check .                # Lint

# Terraform
cd devops-agent/terraform && terraform init     # Initialize
cd devops-agent/terraform && terraform validate # Validate
cd devops-agent/terraform && terraform plan     # Plan changes

# Skills
ls flowmetrics-skills/                       # Browse skills
```
