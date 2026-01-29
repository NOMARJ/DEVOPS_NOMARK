# NOMARK DevOps - Setup Guide

## Assessment: Is This the Right Approach?

**Yes, with refinements.**

Your architecture is solid. Here's what works and what to adjust:

### What's Right

| Aspect | Assessment |
|--------|------------|
| Single VM for all projects | Simple, cost-effective, easy to manage |
| PostgreSQL + pgvector | Right choice for learning + vector search |
| Slack integration | Good for async task dispatch |
| Learning from PRs | Key differentiator from basic automation |
| Project isolation via paths | Simple and effective |

### Refinements

| Current | Suggested |
|---------|-----------|
| B4ms VM (4 vCPU, 16GB) | Start with B2ms (2 vCPU, 8GB) - scale up if needed |
| Always-on VM | Use Azure Automation for on-demand start |
| n8n workflows | Keep simple - Python script + systemd initially |
| Full Terraform from start | Phase it - manual first, then automate |

---

## Phase 1: Manual Setup (This Week)

### Step 1: Create Azure Subscription

```bash
# In Azure Portal or CLI
az account create --name "NOMARK-DevOps"
```

Or via Portal:
1. Go to Azure Portal → Subscriptions
2. Add → Create new subscription
3. Name: "NOMARK-DevOps"
4. Link to your Pay-As-You-Go or existing billing

### Step 2: Create Resource Group

```bash
az group create \
  --name nomark-devops-rg \
  --location australiaeast \
  --tags environment=production project=nomark-devops
```

### Step 3: Create PostgreSQL Flexible Server

```bash
# Create PostgreSQL
az postgres flexible-server create \
  --resource-group nomark-devops-rg \
  --name nomark-devops-db \
  --location australiaeast \
  --admin-user devops_admin \
  --admin-password "<STRONG_PASSWORD>" \
  --sku-name Standard_B1ms \
  --storage-size 32 \
  --version 15 \
  --public-access 0.0.0.0

# Enable pgvector extension
az postgres flexible-server parameter set \
  --resource-group nomark-devops-rg \
  --server-name nomark-devops-db \
  --name azure.extensions \
  --value "VECTOR,PG_TRGM"
```

### Step 4: Create DevOps VM

```bash
# Create VM
az vm create \
  --resource-group nomark-devops-rg \
  --name nomark-devops-vm \
  --image Ubuntu2404 \
  --size Standard_B2ms \
  --admin-username devops \
  --ssh-key-values ~/.ssh/id_rsa.pub \
  --public-ip-sku Standard \
  --os-disk-size-gb 128

# Open ports for SSH (will use Azure Bastion later for security)
az vm open-port \
  --resource-group nomark-devops-rg \
  --name nomark-devops-vm \
  --port 22 \
  --priority 1000
```

### Step 5: Configure VM

SSH into the VM and run:

```bash
#!/bin/bash
# setup-vm.sh

# Update system
sudo apt update && sudo apt upgrade -y

# Install essentials
sudo apt install -y \
  git \
  curl \
  wget \
  jq \
  postgresql-client \
  python3-pip \
  python3-venv

# Install Node.js 20
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install -y nodejs

# Install Claude Code
sudo npm install -g @anthropic-ai/claude-code

# Install GitHub CLI
curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg | sudo dd of=/usr/share/keyrings/githubcli-archive-keyring.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" | sudo tee /etc/apt/sources.list.d/github-cli.list > /dev/null
sudo apt update && sudo apt install gh -y

# Create directory structure
mkdir -p ~/repos ~/config ~/logs ~/scripts

# Create projects config
cat > ~/config/projects.json << 'EOF'
{
  "projects": [
    {
      "id": "flowmetrics",
      "name": "FlowMetrics",
      "repo": "flowmetrics/flowmetrics-portal",
      "stack": "sveltekit-postgres",
      "priority": 1
    },
    {
      "id": "instaindex",
      "name": "InstaIndex",
      "repo": "nomark-dev/instaindex",
      "stack": "nextjs-supabase",
      "priority": 1
    },
    {
      "id": "policyai",
      "name": "PolicyAI",
      "repo": "nomark-dev/policyai",
      "stack": "nextjs-supabase",
      "priority": 2
    }
  ]
}
EOF

echo "VM setup complete!"
```

### Step 6: Create Key Vault

```bash
az keyvault create \
  --resource-group nomark-devops-rg \
  --name nomark-devops-kv \
  --location australiaeast

# Add secrets
az keyvault secret set --vault-name nomark-devops-kv --name ANTHROPIC-API-KEY --value "<YOUR_KEY>"
az keyvault secret set --vault-name nomark-devops-kv --name GITHUB-TOKEN --value "<YOUR_TOKEN>"
```

### Step 7: Initialize Knowledge Base

Connect to PostgreSQL and run:

```sql
-- Enable extensions
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- Knowledge embeddings
CREATE TABLE knowledge_embeddings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    content TEXT NOT NULL,
    embedding vector(1536),
    category TEXT NOT NULL,
    project_id TEXT,
    source_type TEXT,
    source_ref TEXT,
    usage_count INTEGER DEFAULT 0,
    success_rate DECIMAL(3,2),
    last_used_at TIMESTAMP,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX ON knowledge_embeddings USING ivfflat (embedding vector_cosine_ops);
CREATE INDEX ON knowledge_embeddings (project_id, category);

-- Code patterns
CREATE TABLE code_patterns (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    slug TEXT UNIQUE NOT NULL,
    category TEXT NOT NULL,
    projects TEXT[],
    stack TEXT[],
    description TEXT NOT NULL,
    template TEXT NOT NULL,
    example TEXT,
    usage_count INTEGER DEFAULT 0,
    success_rate DECIMAL(3,2) DEFAULT 1.0,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Decision log
CREATE TABLE decision_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id TEXT NOT NULL,
    task_id TEXT,
    branch_name TEXT,
    decision_type TEXT NOT NULL,
    question TEXT NOT NULL,
    chosen_option TEXT NOT NULL,
    alternatives JSONB,
    reasoning TEXT NOT NULL,
    outcome TEXT,
    outcome_notes TEXT,
    pr_number INTEGER,
    pr_feedback TEXT,
    should_repeat BOOLEAN DEFAULT TRUE,
    learned_lesson TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    resolved_at TIMESTAMP
);

-- Error history
CREATE TABLE error_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id TEXT NOT NULL,
    file_path TEXT,
    task_id TEXT,
    error_type TEXT NOT NULL,
    error_message TEXT NOT NULL,
    error_context TEXT,
    fix_applied TEXT,
    fix_worked BOOLEAN,
    prevention_rule TEXT,
    embedding vector(1536),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX ON error_history USING ivfflat (embedding vector_cosine_ops);

-- Performance views
CREATE VIEW agent_performance AS
SELECT
    DATE_TRUNC('week', created_at) AS week,
    project_id,
    COUNT(*) AS tasks_attempted,
    COUNT(*) FILTER (WHERE outcome = 'success') AS tasks_succeeded,
    ROUND(
        COUNT(*) FILTER (WHERE outcome = 'success')::DECIMAL /
        NULLIF(COUNT(*)::DECIMAL, 0) * 100, 2
    ) AS success_rate
FROM decision_log
WHERE resolved_at IS NOT NULL
GROUP BY 1, 2
ORDER BY 1 DESC, 2;
```

---

## Phase 2: Clone Repos & Configure

### Clone All Project Repos

```bash
# On the VM
cd ~/repos

# Authenticate with GitHub
gh auth login

# Clone projects (adjust for your repos)
gh repo clone flowmetrics/flowmetrics-portal flowmetrics
gh repo clone nomark-dev/instaindex instaindex
gh repo clone nomark-dev/policyai policyai
```

### Set Up NOMARK Method in Each Repo

```bash
# Copy NOMARK method to each project
for project in flowmetrics instaindex policyai; do
  cp -r ~/nomark-method/.claude ~/repos/$project/
  cp ~/nomark-method/templates/CLAUDE.md ~/repos/$project/
  cp ~/nomark-method/templates/progress.txt ~/repos/$project/
done
```

### Configure Claude Code

```bash
# Create global Claude config
mkdir -p ~/.claude

cat > ~/.claude/settings.json << 'EOF'
{
  "permissions": {
    "allow": [
      "Bash(npm run *)",
      "Bash(npx *)",
      "Bash(pnpm *)",
      "Bash(git *)",
      "Bash(gh *)",
      "Bash(ls *)",
      "Bash(cat *)",
      "Bash(grep *)"
    ]
  },
  "model": "claude-opus-4-5-20251101"
}
EOF
```

---

## Phase 3: Task Runner Setup

### Simple Task Runner Script

```bash
#!/bin/bash
# ~/scripts/nomark-task.sh

set -e

PROJECT=$1
TASK=$2

if [ -z "$PROJECT" ] || [ -z "$TASK" ]; then
    echo "Usage: nomark-task.sh <project> <task-description>"
    exit 1
fi

# Validate project
if [ ! -d "$HOME/repos/$PROJECT" ]; then
    echo "Unknown project: $PROJECT"
    echo "Available: $(ls ~/repos)"
    exit 1
fi

# Change to project directory
cd "$HOME/repos/$PROJECT"

# Ensure on main and up to date
git checkout main
git pull origin main

# Create feature branch
BRANCH_NAME="ralph/$(echo $TASK | tr ' ' '-' | tr '[:upper:]' '[:lower:]')"
git checkout -b "$BRANCH_NAME" 2>/dev/null || git checkout "$BRANCH_NAME"

# Log start
echo "[$(date)] Starting task: $TASK on $PROJECT" >> ~/logs/tasks.log

# Run Claude Code with the task
claude --print "
Load the NOMARK method from .claude/.

Task: $TASK

Follow the NOMARK flow:
1. /think - Understand the problem
2. /plan - Design solution with atomic stories
3. /build - Execute one story at a time
4. /verify - Ensure quality
5. /simplify - Clean up
6. /commit - Ship when done

Project: $PROJECT
Branch: $BRANCH_NAME
"

# Log completion
echo "[$(date)] Completed task: $TASK on $PROJECT" >> ~/logs/tasks.log
```

### Make Executable

```bash
chmod +x ~/scripts/nomark-task.sh
```

### Usage

```bash
# Run a task
~/scripts/nomark-task.sh flowmetrics "add priority filter to task list"
~/scripts/nomark-task.sh instaindex "implement SEO analyzer component"
```

---

## Phase 4: Auto-Shutdown (Cost Saving)

### Create Auto-Shutdown Schedule

```bash
# Enable auto-shutdown at 8 PM AEST
az vm auto-shutdown \
  --resource-group nomark-devops-rg \
  --name nomark-devops-vm \
  --time 2000 \
  --timezone "AUS Eastern Standard Time"
```

### Start VM On-Demand

```bash
# From your local machine
az vm start --resource-group nomark-devops-rg --name nomark-devops-vm

# Or create an alias
alias devops-start="az vm start --resource-group nomark-devops-rg --name nomark-devops-vm"
alias devops-stop="az vm deallocate --resource-group nomark-devops-rg --name nomark-devops-vm"
alias devops-ssh="ssh devops@$(az vm show -g nomark-devops-rg -n nomark-devops-vm --show-details --query publicIps -o tsv)"
```

---

## Estimated Costs (Refined)

| Resource | SKU | Monthly Cost |
|----------|-----|--------------|
| VM (B2ms, 12hr/day avg) | Pay-as-you-go | ~$35-45 |
| PostgreSQL (B1ms) | Burstable | ~$25 |
| OS Disk (128GB Premium) | P10 | ~$15 |
| Blob Storage | Hot | ~$5 |
| Key Vault | Standard | ~$3 |
| Bandwidth | Egress | ~$5 |
| **Total** | | **~$88-98/month** |

With auto-shutdown, you save 50% on VM costs.

---

## Next Steps

### Week 1: Basic Setup
- [ ] Create Azure subscription "NOMARK-DevOps"
- [ ] Deploy VM + PostgreSQL manually
- [ ] Clone repos and configure NOMARK method
- [ ] Test single task execution

### Week 2: Learning System
- [ ] Initialize knowledge base schema
- [ ] Create embedding pipeline (Python + OpenAI/Anthropic)
- [ ] Test pattern storage and retrieval

### Week 3: Integration
- [ ] Set up GitHub webhook for PR learning
- [ ] Add Slack bot for task dispatch (optional)
- [ ] Create monitoring dashboard

### Week 4: Optimization
- [ ] Review agent performance metrics
- [ ] Tune knowledge retrieval
- [ ] Add more projects as needed

---

## Quick Start with Scripts

All deployment scripts are in `scripts/`:

```bash
# From your local machine
./scripts/azure-deploy.sh     # Deploy all Azure resources

# On the VM (after SSH)
./scripts/setup-vm.sh         # Install packages, configure environment
./scripts/init-knowledge-base.sh  # Create database schema
```

See also:
- [SLACK_SETUP.md](./SLACK_SETUP.md) - Slack bot configuration
