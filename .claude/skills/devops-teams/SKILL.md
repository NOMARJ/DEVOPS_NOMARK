# DevOps Agent Teams

Skill for orchestrating Claude Code agent teams on DevOps tasks.

## When to Use Teams

Use agent teams when the task involves **parallel, independent work** across multiple components:

| Scenario | Team Structure |
|----------|---------------|
| Infrastructure + MCP changes | infra-specialist + mcp-developer |
| Security audit | security-reviewer + infra-specialist + mcp-developer |
| New integration (end-to-end) | workflow-builder + mcp-developer + qa-verifier |
| Major refactor | mcp-developer + qa-verifier + security-reviewer |
| Full release prep | all 5 roles |

## Team Spawn Templates

### Infrastructure Change

```
Create an agent team for this infrastructure change. Spawn:
- An infra-specialist to modify the Terraform and Azure resources
- A security-reviewer to audit the changes for compliance
- A qa-verifier to validate everything passes
Require plan approval for the infra-specialist before they make changes.
```

### New MCP Tool

```
Create an agent team to add a new MCP tool. Spawn:
- An mcp-developer to implement the tool handler and tests
- A workflow-builder to create n8n workflow integration
- A qa-verifier to run the full test suite
```

### Security Audit

```
Create an agent team for a security audit. Spawn:
- A security-reviewer to scan for vulnerabilities and credential issues
- An infra-specialist to review network exposure and Azure RBAC
- A mcp-developer to review OAuth and API auth implementation
Have them share and challenge each other's findings.
```

## File Ownership

To prevent conflicts, teammates should own distinct file sets:

| Role | Owns |
|------|------|
| infra-specialist | `devops-agent/terraform/`, `devops-agent/scripts/` |
| mcp-developer | `devops-mcp/devops_mcp/`, `devops-mcp/tests/` |
| security-reviewer | Read-only across all (reports findings) |
| workflow-builder | `devops-agent/n8n-workflows/`, `nomark-method/scripts/` |
| qa-verifier | Read-only across all (runs verification) |

## Task Sizing

- 5-6 tasks per teammate keeps everyone productive
- Each task should produce a clear deliverable
- Dependencies should be explicit (schema before API, API before workflow)
