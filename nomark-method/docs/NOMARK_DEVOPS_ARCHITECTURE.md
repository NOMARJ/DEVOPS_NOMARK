# NOMARK DevOps - Intelligent Multi-Project Development System

## Executive Summary

NOMARK DevOps is an Azure-hosted autonomous development system that manages multiple NOMARK projects (InstaIndex, PolicyAI, Transform, FlowMetrics, etc.) through a single intelligent agent. The system learns from every interaction, building a knowledge base that improves code quality and development speed over time.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         NOMARK DevOps Architecture                          │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌────────────┐  │
│   │ InstaIndex  │    │  PolicyAI   │    │  Transform  │    │ FlowMetrics│  │
│   │    Repo     │    │    Repo     │    │    Repo     │    │    Repo    │  │
│   └──────┬──────┘    └──────┬──────┘    └──────┬──────┘    └─────┬──────┘  │
│          │                  │                  │                  │         │
│          └──────────────────┴──────────────────┴──────────────────┘         │
│                                    │                                        │
│                                    ▼                                        │
│   ┌─────────────────────────────────────────────────────────────────────┐  │
│   │                    NOMARK DevOps Agent (Azure VM)                    │  │
│   │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌────────────┐  │  │
│   │  │   Ralph     │  │   Claude    │  │   Skills    │  │  Knowledge │  │  │
│   │  │   Runner    │  │    Code     │  │   Library   │  │    Base    │  │  │
│   │  └─────────────┘  └─────────────┘  └─────────────┘  └────────────┘  │  │
│   └─────────────────────────────────────────────────────────────────────┘  │
│                                    │                                        │
│                                    ▼                                        │
│   ┌─────────────────────────────────────────────────────────────────────┐  │
│   │                      Learning & Memory Layer                         │  │
│   │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌────────────┐  │  │
│   │  │  pgvector   │  │   Pattern   │  │    Error    │  │  Decision  │  │  │
│   │  │ Embeddings  │  │   Library   │  │   History   │  │    Log     │  │  │
│   │  └─────────────┘  └─────────────┘  └─────────────┘  └────────────┘  │  │
│   └─────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Core Components

### 1. Multi-Project Repository Management

The system manages multiple NOMARK projects through a unified interface:

```
~/repos/
├── instaindex/              # SEO optimization SaaS
├── policyai/                # Healthcare policy AI
├── transform-fullstack/     # Developer training platform
├── flowmetrics/             # Fund management analytics
├── opshub/                  # Operations dashboard
└── nomark-shared/           # Shared components library
```

**Project Registry** (`/home/devops/config/projects.json`):
```json
{
  "projects": [
    {
      "id": "instaindex",
      "name": "InstaIndex",
      "repo": "nomark-dev/instaindex",
      "stack": "nextjs-supabase",
      "priority": 1,
      "colors": {
        "primary": "#475569",
        "accent": "#3B82F6"
      }
    },
    {
      "id": "policyai",
      "name": "PolicyAI",
      "repo": "nomark-dev/policyai",
      "stack": "nextjs-supabase",
      "priority": 2,
      "colors": {
        "primary": "#7A7A52",
        "accent": "#22C55E"
      }
    },
    {
      "id": "flowmetrics",
      "name": "FlowMetrics",
      "repo": "flowmetrics/flowmetrics-portal",
      "stack": "sveltekit-postgres",
      "priority": 1,
      "colors": {
        "primary": "#1E40AF",
        "accent": "#3B82F6"
      }
    }
  ]
}
```

### 2. Intelligent Task Routing

When a task comes in, the system:

1. **Identifies the project** from context or explicit specification
2. **Loads project-specific context** (stack, patterns, recent changes)
3. **Retrieves relevant knowledge** from the learning database
4. **Applies NOMARK standards** consistently across all projects
5. **Executes with project-aware tooling**

```
┌─────────────────────────────────────────────────────────────────┐
│                      Task Routing Flow                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   Slack: /dev instaindex add-seo-analyzer                       │
│                          │                                      │
│                          ▼                                      │
│   ┌─────────────────────────────────────────┐                   │
│   │           Task Router                    │                   │
│   │  1. Parse project: "instaindex"         │                   │
│   │  2. Parse feature: "add-seo-analyzer"   │                   │
│   │  3. Load project config                 │                   │
│   │  4. Query knowledge base                │                   │
│   └─────────────────────────────────────────┘                   │
│                          │                                      │
│                          ▼                                      │
│   ┌─────────────────────────────────────────┐                   │
│   │        Context Assembly                  │                   │
│   │  • NOMARK global standards              │                   │
│   │  • InstaIndex specific patterns         │                   │
│   │  • Similar past implementations         │                   │
│   │  • Recent repo changes                  │                   │
│   └─────────────────────────────────────────┘                   │
│                          │                                      │
│                          ▼                                      │
│   ┌─────────────────────────────────────────┐                   │
│   │        Ralph Execution                   │                   │
│   │  Working in: ~/repos/instaindex         │                   │
│   │  Branch: ralph/add-seo-analyzer         │                   │
│   └─────────────────────────────────────────┘                   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Learning & Memory System

### Why Not Just RAG?

Traditional RAG (Retrieval Augmented Generation) is good for static knowledge, but NOMARK DevOps needs:

1. **Active Learning**: Learn from successes AND failures
2. **Pattern Recognition**: Identify what works across projects
3. **Decision Memory**: Remember why certain approaches were chosen
4. **Error Prevention**: Avoid repeating past mistakes

### The NOMARK Learning Stack

```
┌─────────────────────────────────────────────────────────────────┐
│                    Learning Architecture                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Layer 1: Vector Knowledge Base (pgvector)                      │
│  ─────────────────────────────────────────                      │
│  • Code patterns and examples                                   │
│  • Documentation chunks                                         │
│  • PRD history                                                  │
│  • Error solutions                                              │
│                                                                 │
│  Layer 2: Structured Pattern Library (PostgreSQL)               │
│  ─────────────────────────────────────────                      │
│  • Reusable code templates                                      │
│  • Component patterns per project                               │
│  • Database schema patterns                                     │
│  • API endpoint patterns                                        │
│                                                                 │
│  Layer 3: Decision & Outcome Log (PostgreSQL + JSONB)           │
│  ─────────────────────────────────────────                      │
│  • What was decided and why                                     │
│  • What worked / what didn't                                    │
│  • PR feedback incorporated                                     │
│  • Human corrections                                            │
│                                                                 │
│  Layer 4: Cross-Project Intelligence (Derived)                  │
│  ─────────────────────────────────────────                      │
│  • Patterns that work across all projects                       │
│  • Common pitfalls to avoid                                     │
│  • Performance optimizations                                    │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Database Schema

```sql
-- Knowledge embeddings for semantic search
CREATE TABLE knowledge_embeddings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    content TEXT NOT NULL,
    embedding vector(1536),
    
    -- Categorization
    category TEXT NOT NULL,  -- 'code', 'pattern', 'error', 'decision', 'prd'
    project_id TEXT,         -- NULL = cross-project knowledge
    
    -- Source tracking
    source_type TEXT,        -- 'file', 'pr', 'chat', 'error_log'
    source_ref TEXT,         -- File path, PR number, etc.
    
    -- Quality signals
    usage_count INTEGER DEFAULT 0,
    success_rate DECIMAL(3,2),
    last_used_at TIMESTAMP,
    
    -- Metadata
    metadata JSONB,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX ON knowledge_embeddings 
    USING ivfflat (embedding vector_cosine_ops);
CREATE INDEX ON knowledge_embeddings (project_id, category);


-- Structured patterns (not just embeddings)
CREATE TABLE code_patterns (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Identity
    name TEXT NOT NULL,
    slug TEXT UNIQUE NOT NULL,
    category TEXT NOT NULL,  -- 'component', 'api', 'database', 'workflow'
    
    -- Applicability
    projects TEXT[],         -- Which projects this applies to, NULL = all
    stack TEXT[],            -- ['nextjs', 'sveltekit', 'supabase']
    
    -- The pattern itself
    description TEXT NOT NULL,
    template TEXT NOT NULL,  -- Code template with {{placeholders}}
    example TEXT,            -- Concrete example
    
    -- Quality
    usage_count INTEGER DEFAULT 0,
    success_rate DECIMAL(3,2) DEFAULT 1.0,
    
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);


-- Decision log - remembers WHY things were done
CREATE TABLE decision_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Context
    project_id TEXT NOT NULL,
    task_id TEXT,            -- PRD story ID or task reference
    branch_name TEXT,
    
    -- The decision
    decision_type TEXT NOT NULL,  -- 'architecture', 'library', 'pattern', 'approach'
    question TEXT NOT NULL,       -- What was being decided
    chosen_option TEXT NOT NULL,  -- What was chosen
    alternatives JSONB,           -- Other options considered
    reasoning TEXT NOT NULL,      -- Why this was chosen
    
    -- Outcome tracking
    outcome TEXT,                 -- 'success', 'partial', 'failed', 'reverted'
    outcome_notes TEXT,
    pr_number INTEGER,
    pr_feedback TEXT,
    
    -- Learning
    should_repeat BOOLEAN DEFAULT TRUE,
    learned_lesson TEXT,
    
    created_at TIMESTAMP DEFAULT NOW(),
    resolved_at TIMESTAMP
);


-- Error history - learn from mistakes
CREATE TABLE error_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Context
    project_id TEXT NOT NULL,
    file_path TEXT,
    task_id TEXT,
    
    -- The error
    error_type TEXT NOT NULL,     -- 'typecheck', 'runtime', 'test', 'lint', 'logic'
    error_message TEXT NOT NULL,
    error_context TEXT,           -- Surrounding code or circumstances
    
    -- The fix
    fix_applied TEXT,
    fix_worked BOOLEAN,
    
    -- Prevention
    prevention_rule TEXT,         -- How to avoid this in future
    embedding vector(1536),       -- For similarity search
    
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX ON error_history 
    USING ivfflat (embedding vector_cosine_ops);
```

### Learning Workflows

#### 1. Learning from Successful PRs

```python
async def learn_from_merged_pr(pr: PullRequest):
    """Extract learnings when a PR is merged."""
    
    # Get the diff and changes
    changes = await github.get_pr_diff(pr.number)
    
    # Extract patterns from successful code
    for file_change in changes:
        if is_new_pattern(file_change):
            pattern = extract_pattern(file_change)
            await store_pattern(pattern, project_id=pr.repo)
    
    # Record the successful decision
    if pr.has_prd:
        await decision_log.update(
            task_id=pr.prd_story_id,
            outcome='success',
            pr_number=pr.number
        )
    
    # Embed the code for future retrieval
    for file in changes.added_files:
        embedding = await embed(file.content)
        await knowledge_embeddings.insert(
            content=file.content,
            embedding=embedding,
            category='code',
            project_id=pr.repo,
            source_type='pr',
            source_ref=str(pr.number)
        )
```

#### 2. Learning from Errors

```python
async def learn_from_error(error: BuildError, fix: str, worked: bool):
    """Record error and fix for future prevention."""
    
    # Embed the error for similarity search
    error_embedding = await embed(f"{error.message}\n{error.context}")
    
    await error_history.insert(
        project_id=error.project,
        error_type=error.type,
        error_message=error.message,
        error_context=error.context,
        fix_applied=fix,
        fix_worked=worked,
        prevention_rule=generate_prevention_rule(error, fix) if worked else None,
        embedding=error_embedding
    )
```

#### 3. Retrieving Relevant Knowledge

```python
async def get_context_for_task(task: Task) -> Context:
    """Assemble all relevant knowledge for a task."""
    
    # 1. Get project-specific patterns
    project_patterns = await code_patterns.query(
        projects__contains=task.project_id,
        category=task.category
    )
    
    # 2. Semantic search for similar past work
    task_embedding = await embed(task.description)
    similar_code = await knowledge_embeddings.similarity_search(
        embedding=task_embedding,
        filter={'project_id': task.project_id},
        limit=5
    )
    
    # 3. Find similar errors to avoid
    similar_errors = await error_history.similarity_search(
        embedding=task_embedding,
        filter={'project_id': task.project_id, 'fix_worked': True},
        limit=3
    )
    
    # 4. Get relevant decisions
    past_decisions = await decision_log.query(
        project_id=task.project_id,
        decision_type__in=task.relevant_decision_types,
        should_repeat=True
    )
    
    # 5. Cross-project learnings
    global_patterns = await code_patterns.query(
        projects__is_null=True,  # Applies to all
        category=task.category
    )
    
    return Context(
        project_patterns=project_patterns,
        similar_code=similar_code,
        errors_to_avoid=similar_errors,
        past_decisions=past_decisions,
        global_patterns=global_patterns
    )
```

---

## Azure Infrastructure

### Resource Layout

```
Azure Resource Group: nomark-devops-rg
├── Virtual Machine: nomark-devops-vm (B4ms - 4 vCPU, 16GB RAM)
│   ├── OS: Ubuntu 24.04 LTS
│   ├── Storage: 128GB Premium SSD
│   └── Auto-shutdown: Enabled (cost savings)
│
├── PostgreSQL Flexible Server: nomark-devops-db
│   ├── SKU: Burstable B1ms (dev) / GP D2s (prod)
│   ├── Storage: 32GB
│   └── Extensions: pgvector, pg_trgm
│
├── Container Registry: nomarkdevopsacr
│   └── For custom tool images
│
├── Key Vault: nomark-devops-kv
│   ├── GITHUB_TOKEN
│   ├── ANTHROPIC_API_KEY
│   ├── SLACK_BOT_TOKEN
│   ├── SUPABASE_* (per project)
│   └── Project-specific secrets
│
└── Storage Account: nomarkdevopsstorage
    ├── Container: artifacts (build outputs)
    ├── Container: logs (execution logs)
    └── Container: backups (knowledge base backups)
```

### Terraform Configuration

```hcl
# main.tf - NOMARK DevOps Infrastructure

terraform {
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.0"
    }
  }
}

variable "projects" {
  type = list(object({
    id       = string
    repo     = string
    secrets  = map(string)
  }))
  description = "List of NOMARK projects to configure"
}

# Resource Group
resource "azurerm_resource_group" "devops" {
  name     = "nomark-devops-rg"
  location = "Australia East"
  
  tags = {
    environment = "production"
    project     = "nomark-devops"
  }
}

# PostgreSQL for Knowledge Base
resource "azurerm_postgresql_flexible_server" "knowledge" {
  name                   = "nomark-devops-db"
  resource_group_name    = azurerm_resource_group.devops.name
  location               = azurerm_resource_group.devops.location
  version                = "15"
  administrator_login    = "devops_admin"
  administrator_password = var.db_password
  
  storage_mb = 32768
  sku_name   = "B_Standard_B1ms"
  
  # Enable pgvector
  azure_extensions = ["PGVECTOR", "PG_TRGM"]
}

# DevOps VM
resource "azurerm_linux_virtual_machine" "devops" {
  name                = "nomark-devops-vm"
  resource_group_name = azurerm_resource_group.devops.name
  location            = azurerm_resource_group.devops.location
  size                = "Standard_B4ms"
  admin_username      = "devops"
  
  network_interface_ids = [azurerm_network_interface.devops.id]
  
  admin_ssh_key {
    username   = "devops"
    public_key = var.ssh_public_key
  }
  
  os_disk {
    caching              = "ReadWrite"
    storage_account_type = "Premium_LRS"
    disk_size_gb         = 128
  }
  
  source_image_reference {
    publisher = "Canonical"
    offer     = "0001-com-ubuntu-server-jammy"
    sku       = "24_04-lts-gen2"
    version   = "latest"
  }
  
  custom_data = base64encode(local.cloud_init)
}

# Cloud-init for VM setup
locals {
  cloud_init = <<-EOF
    #cloud-config
    package_update: true
    packages:
      - git
      - python3-pip
      - nodejs
      - npm
      - postgresql-client
    
    write_files:
      - path: /home/devops/config/projects.json
        content: ${jsonencode(var.projects)}
      
      - path: /home/devops/.env
        content: |
          DATABASE_URL=${azurerm_postgresql_flexible_server.knowledge.fqdn}
          GITHUB_TOKEN=${var.github_token}
          ANTHROPIC_API_KEY=${var.anthropic_api_key}
    
    runcmd:
      # Install Claude Code
      - npm install -g @anthropic-ai/claude-code
      
      # Clone all project repos
      %{ for project in var.projects ~}
      - git clone https://${var.github_token}@github.com/${project.repo}.git /home/devops/repos/${project.id}
      %{ endfor ~}
      
      # Setup knowledge base
      - psql $DATABASE_URL -f /home/devops/scripts/init-knowledge-base.sql
      
      # Install devops tools
      - pip3 install -r /home/devops/requirements.txt
  EOF
}

# Key Vault for secrets
resource "azurerm_key_vault" "devops" {
  name                = "nomark-devops-kv"
  resource_group_name = azurerm_resource_group.devops.name
  location            = azurerm_resource_group.devops.location
  tenant_id           = data.azurerm_client_config.current.tenant_id
  sku_name            = "standard"
}

# Store project-specific secrets
resource "azurerm_key_vault_secret" "project_secrets" {
  for_each = { for p in var.projects : "${p.id}-${k}" => v 
               for k, v in p.secrets }
  
  name         = each.key
  value        = each.value
  key_vault_id = azurerm_key_vault.devops.id
}
```

---

## Workflow Integration

### Slack Command Interface

```
/dev <project> <command> [options]

Commands:
  /dev instaindex start add-user-auth     # Start feature from PRD
  /dev policyai status                    # Check current task status
  /dev transform stop                     # Stop current task
  /dev flowmetrics logs                   # View recent logs
  /dev list                               # List all projects
  /dev learn                              # Trigger learning from recent PRs
```

### n8n Workflow: Multi-Project Task Handler

```json
{
  "name": "NOMARK DevOps - Multi-Project Handler",
  "nodes": [
    {
      "name": "Slack Command",
      "type": "n8n-nodes-base.webhook",
      "parameters": {
        "path": "nomark-devops",
        "httpMethod": "POST"
      }
    },
    {
      "name": "Parse Command",
      "type": "n8n-nodes-base.code",
      "parameters": {
        "jsCode": "const text = $input.first().json.text;\nconst parts = text.split(' ');\n\n// Handle 'list' command\nif (parts[0] === 'list') {\n  return [{ json: { command: 'list' } }];\n}\n\n// Handle project-specific commands\nconst [project, command, ...args] = parts;\n\nreturn [{\n  json: {\n    project,\n    command,\n    args: args.join(' '),\n    user: $input.first().json.user_name\n  }\n}];"
      }
    },
    {
      "name": "Route by Project",
      "type": "n8n-nodes-base.switch",
      "parameters": {
        "rules": [
          { "value": "instaindex" },
          { "value": "policyai" },
          { "value": "flowmetrics" },
          { "value": "transform" }
        ]
      }
    },
    {
      "name": "Load Project Context",
      "type": "n8n-nodes-base.httpRequest",
      "parameters": {
        "url": "http://devops-vm:8080/api/context/{{ $json.project }}",
        "method": "GET"
      }
    },
    {
      "name": "Query Knowledge Base",
      "type": "n8n-nodes-base.postgres",
      "parameters": {
        "operation": "executeQuery",
        "query": "SELECT * FROM get_task_context($1, $2)",
        "additionalFields": {
          "queryParams": "{{ $json.project }},{{ $json.args }}"
        }
      }
    },
    {
      "name": "Start DevOps Agent",
      "type": "n8n-nodes-base.ssh",
      "parameters": {
        "command": "cd /home/devops/repos/{{ $json.project }} && ./ralph.sh start {{ $json.args }}"
      }
    }
  ]
}
```

### GitHub Webhook: Learn from Merged PRs

```json
{
  "name": "NOMARK DevOps - PR Learning",
  "nodes": [
    {
      "name": "GitHub PR Webhook",
      "type": "n8n-nodes-base.webhook",
      "parameters": {
        "path": "github-pr-merged",
        "httpMethod": "POST"
      }
    },
    {
      "name": "Filter Merged PRs",
      "type": "n8n-nodes-base.if",
      "parameters": {
        "conditions": {
          "string": [
            {
              "value1": "={{ $json.action }}",
              "value2": "closed"
            },
            {
              "value1": "={{ $json.pull_request.merged }}",
              "value2": "true"
            }
          ]
        }
      }
    },
    {
      "name": "Extract Learnings",
      "type": "n8n-nodes-base.httpRequest",
      "parameters": {
        "url": "http://devops-vm:8080/api/learn/from-pr",
        "method": "POST",
        "body": {
          "repo": "={{ $json.repository.full_name }}",
          "pr_number": "={{ $json.pull_request.number }}",
          "diff_url": "={{ $json.pull_request.diff_url }}"
        }
      }
    }
  ]
}
```

---

## Getting Smarter Over Time

### Intelligence Metrics

Track these to measure improvement:

```sql
-- View: Agent Performance Over Time
CREATE VIEW agent_performance AS
SELECT 
    DATE_TRUNC('week', created_at) AS week,
    project_id,
    COUNT(*) AS tasks_attempted,
    COUNT(*) FILTER (WHERE outcome = 'success') AS tasks_succeeded,
    ROUND(
        COUNT(*) FILTER (WHERE outcome = 'success')::DECIMAL / 
        COUNT(*)::DECIMAL * 100, 2
    ) AS success_rate,
    AVG(EXTRACT(EPOCH FROM (resolved_at - created_at)) / 3600) AS avg_hours_to_complete
FROM decision_log
WHERE resolved_at IS NOT NULL
GROUP BY 1, 2
ORDER BY 1 DESC, 2;

-- View: Most Valuable Patterns
CREATE VIEW valuable_patterns AS
SELECT 
    name,
    category,
    projects,
    usage_count,
    success_rate,
    ROUND(usage_count * success_rate, 2) AS value_score
FROM code_patterns
ORDER BY value_score DESC;

-- View: Common Errors and Fixes
CREATE VIEW common_errors AS
SELECT 
    error_type,
    error_message,
    COUNT(*) AS occurrence_count,
    COUNT(*) FILTER (WHERE fix_worked) AS times_fixed,
    MODE() WITHIN GROUP (ORDER BY fix_applied) AS most_common_fix
FROM error_history
GROUP BY error_type, error_message
HAVING COUNT(*) > 2
ORDER BY occurrence_count DESC;
```

### Continuous Improvement Loop

```
┌─────────────────────────────────────────────────────────────────┐
│                 Continuous Learning Loop                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│    ┌──────────┐                                                 │
│    │  Task    │                                                 │
│    │ Assigned │                                                 │
│    └────┬─────┘                                                 │
│         │                                                       │
│         ▼                                                       │
│    ┌──────────────────────────────────────┐                     │
│    │     Query Knowledge Base             │                     │
│    │  • Similar past tasks                │                     │
│    │  • Relevant patterns                 │                     │
│    │  • Errors to avoid                   │                     │
│    └────┬─────────────────────────────────┘                     │
│         │                                                       │
│         ▼                                                       │
│    ┌──────────┐                                                 │
│    │ Execute  │                                                 │
│    │  Task    │                                                 │
│    └────┬─────┘                                                 │
│         │                                                       │
│         ├────────────────┬────────────────┐                     │
│         ▼                ▼                ▼                     │
│    ┌─────────┐     ┌─────────┐     ┌─────────┐                  │
│    │ Success │     │ Partial │     │ Failed  │                  │
│    └────┬────┘     └────┬────┘     └────┬────┘                  │
│         │               │               │                       │
│         ▼               ▼               ▼                       │
│    ┌─────────────────────────────────────────┐                  │
│    │          Record Outcome                 │                  │
│    │  • What worked / didn't                 │                  │
│    │  • Why (from PR feedback or analysis)   │                  │
│    │  • Extract new patterns                 │                  │
│    │  • Update error prevention rules        │                  │
│    └─────────────────────────────────────────┘                  │
│         │                                                       │
│         ▼                                                       │
│    ┌─────────────────────────────────────────┐                  │
│    │       Weekly Consolidation              │                  │
│    │  • Identify cross-project patterns      │                  │
│    │  • Promote successful patterns          │                  │
│    │  • Deprecate failing approaches         │                  │
│    │  • Update NOMARK standards if needed    │                  │
│    └─────────────────────────────────────────┘                  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Security Considerations

### Secret Management

```yaml
# Each project has isolated secrets
project_secrets:
  instaindex:
    - SUPABASE_URL
    - SUPABASE_SERVICE_KEY
    - RESEND_API_KEY
  
  flowmetrics:
    - SUPABASE_URL
    - SUPABASE_SERVICE_KEY
    - AZURE_STORAGE_KEY

# Shared secrets (DevOps infrastructure)
shared_secrets:
  - GITHUB_TOKEN (with access to all repos)
  - ANTHROPIC_API_KEY
  - SLACK_BOT_TOKEN
```

### Access Control

```
┌─────────────────────────────────────────────────────────────────┐
│                    Access Control Matrix                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  GitHub Permissions:                                            │
│  ├── nomark-dev org: Admin (all repos)                          │
│  └── flowmetrics org: Write (specific repos)                    │
│                                                                 │
│  Azure RBAC:                                                    │
│  ├── DevOps VM: Managed Identity with:                          │
│  │   ├── Key Vault Reader (secrets access)                      │
│  │   ├── Storage Blob Contributor (artifacts)                   │
│  │   └── PostgreSQL Contributor (knowledge base)                │
│  │                                                              │
│  └── Your account: Owner (full control)                         │
│                                                                 │
│  Slack:                                                         │
│  └── Restricted to #devops-agent channel                        │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Cost Optimization

### Estimated Monthly Costs

| Resource | SKU | Cost/Month |
|----------|-----|------------|
| VM (B4ms, auto-shutdown) | Pay-as-you-go | ~$50-80 |
| PostgreSQL (B1ms) | Burstable | ~$25 |
| Storage (128GB) | Premium SSD | ~$15 |
| Blob Storage | Hot tier | ~$5 |
| Bandwidth | Egress | ~$10 |
| **Total** | | **~$105-135/month** |

### Cost Saving Strategies

1. **Auto-shutdown VM** when not in use (nights/weekends)
2. **Spot instances** for non-critical workloads
3. **Scale PostgreSQL** down during low usage
4. **Archive old knowledge** to cold storage
5. **Use reserved instances** when stable

---

## Getting Started

### Phase 1: Basic Setup (Week 1)
- [ ] Deploy Azure infrastructure with Terraform
- [ ] Configure GitHub access for all repos
- [ ] Set up Slack integration
- [ ] Test with single project (FlowMetrics)

### Phase 2: Multi-Project (Week 2)
- [ ] Add all NOMARK projects to registry
- [ ] Configure project-specific secrets
- [ ] Test cross-project task routing
- [ ] Verify isolation between projects

### Phase 3: Learning System (Week 3-4)
- [ ] Deploy PostgreSQL with pgvector
- [ ] Implement knowledge embedding pipeline
- [ ] Set up PR learning webhook
- [ ] Create initial pattern library from existing code

### Phase 4: Optimization (Ongoing)
- [ ] Monitor agent performance metrics
- [ ] Refine patterns based on outcomes
- [ ] Expand knowledge base
- [ ] Tune retrieval for better context

---

## Commands Reference

```bash
# Start task on specific project
/dev instaindex start user-authentication

# Check status across all projects
/dev status

# View logs for a project
/dev flowmetrics logs

# Manually trigger learning
/dev learn --from-prs --days 7

# List all registered projects
/dev list

# Query knowledge base
/dev search "how to implement pagination"

# View agent metrics
/dev metrics --week
```

---

## Appendix: NOMARK Standards Integration

The system automatically applies NOMARK standards to all projects:

1. **Global Rules**: Always applied (from your Windsurf config)
2. **Stack-Specific**: NextJS patterns for NOMARK projects, SvelteKit for FlowMetrics
3. **Project Colors**: Auto-applied based on project registry
4. **Cost Tracking**: Enforced across all projects
5. **Security**: RLS and validation patterns always included

The learning system will identify when NOMARK standards need updating based on cross-project success patterns.
