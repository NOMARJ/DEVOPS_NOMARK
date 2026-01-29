#!/bin/bash
# NOMARK DevOps - VM Setup Script
# Run this on the Azure VM after SSHing in

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}   NOMARK DevOps - VM Setup           ${NC}"
echo -e "${GREEN}========================================${NC}"

# Update system
echo -e "\n${YELLOW}Updating system packages...${NC}"
sudo apt update && sudo apt upgrade -y

# Install essentials
echo -e "\n${YELLOW}Installing essential packages...${NC}"
sudo apt install -y \
    git \
    curl \
    wget \
    jq \
    unzip \
    build-essential \
    postgresql-client \
    python3-pip \
    python3-venv \
    python3-dev

# Install Node.js 20
echo -e "\n${YELLOW}Installing Node.js 20...${NC}"
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install -y nodejs

# Install Claude Code
echo -e "\n${YELLOW}Installing Claude Code...${NC}"
sudo npm install -g @anthropic-ai/claude-code

# Install GitHub CLI
echo -e "\n${YELLOW}Installing GitHub CLI...${NC}"
curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg | sudo dd of=/usr/share/keyrings/githubcli-archive-keyring.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" | sudo tee /etc/apt/sources.list.d/github-cli.list > /dev/null
sudo apt update && sudo apt install gh -y

# Install Azure CLI
echo -e "\n${YELLOW}Installing Azure CLI...${NC}"
curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash

# Install Python packages for AI/embeddings
echo -e "\n${YELLOW}Setting up Python environment...${NC}"
python3 -m venv ~/venv
source ~/venv/bin/activate
pip install --upgrade pip
pip install \
    anthropic \
    openai \
    psycopg2-binary \
    pgvector \
    slack-sdk \
    python-dotenv \
    requests \
    aiohttp

# Create directory structure
echo -e "\n${YELLOW}Creating directory structure...${NC}"
mkdir -p ~/repos ~/config ~/logs ~/scripts ~/nomark-method

# Create projects config
echo -e "\n${YELLOW}Creating projects configuration...${NC}"
cat > ~/config/projects.json << 'EOF'
{
  "projects": [
    {
      "id": "flowmetrics",
      "name": "FlowMetrics",
      "repo": "NOMARK/flowmetrics-portal",
      "stack": "sveltekit-postgres",
      "priority": 1,
      "active": true
    },
    {
      "id": "instaindex",
      "name": "InstaIndex",
      "repo": "NOMARK/instaindex",
      "stack": "nextjs-supabase",
      "priority": 2,
      "active": true
    },
    {
      "id": "policyai",
      "name": "PolicyAI",
      "repo": "NOMARK/policyai",
      "stack": "nextjs-supabase",
      "priority": 3,
      "active": false
    }
  ],
  "defaults": {
    "model": "claude-opus-4-5-20251101",
    "maxConcurrentTasks": 1,
    "autoShutdown": true
  }
}
EOF

# Create environment config template
echo -e "\n${YELLOW}Creating environment template...${NC}"
cat > ~/config/.env.template << 'EOF'
# NOMARK DevOps Environment
# Copy to .env and fill in values

# Anthropic
ANTHROPIC_API_KEY=

# GitHub
GITHUB_TOKEN=

# Database
DB_HOST=nomark-devops-db.postgres.database.azure.com
DB_NAME=nomark_devops
DB_USER=devops_admin
DB_PASSWORD=

# Slack (optional)
SLACK_BOT_TOKEN=
SLACK_APP_TOKEN=
SLACK_CHANNEL_ID=

# Azure
AZURE_KEYVAULT_NAME=nomark-devops-kv
EOF

# Create Claude global settings
echo -e "\n${YELLOW}Configuring Claude Code...${NC}"
mkdir -p ~/.claude

cat > ~/.claude/settings.json << 'EOF'
{
  "permissions": {
    "allow": [
      "Bash(npm run *)",
      "Bash(npx *)",
      "Bash(pnpm *)",
      "Bash(bun *)",
      "Bash(yarn *)",
      "Bash(git *)",
      "Bash(gh *)",
      "Bash(ls *)",
      "Bash(cat *)",
      "Bash(head *)",
      "Bash(tail *)",
      "Bash(grep *)",
      "Bash(find *)",
      "Bash(which *)",
      "Bash(echo *)",
      "Bash(pwd)",
      "Bash(cd *)",
      "Bash(psql *)",
      "Bash(python3 *)"
    ],
    "deny": []
  },
  "model": "claude-opus-4-5-20251101"
}
EOF

# Create task runner script
echo -e "\n${YELLOW}Creating task runner...${NC}"
cat > ~/scripts/nomark-task.sh << 'TASKSCRIPT'
#!/bin/bash
# NOMARK Task Runner

set -e

PROJECT=$1
TASK=$2

if [ -z "$PROJECT" ] || [ -z "$TASK" ]; then
    echo "Usage: nomark-task.sh <project> <task-description>"
    echo ""
    echo "Available projects:"
    jq -r '.projects[] | select(.active == true) | "  - \(.id): \(.name)"' ~/config/projects.json
    exit 1
fi

# Load environment
source ~/config/.env

# Validate project
PROJECT_PATH="$HOME/repos/$PROJECT"
if [ ! -d "$PROJECT_PATH" ]; then
    echo "Project not found: $PROJECT"
    echo "Run: gh repo clone $(jq -r ".projects[] | select(.id == \"$PROJECT\") | .repo" ~/config/projects.json) ~/repos/$PROJECT"
    exit 1
fi

# Change to project directory
cd "$PROJECT_PATH"

# Ensure on main and up to date
git checkout main 2>/dev/null || git checkout master
git pull origin $(git rev-parse --abbrev-ref HEAD)

# Create feature branch
BRANCH_NAME="ralph/$(echo "$TASK" | tr ' ' '-' | tr '[:upper:]' '[:lower:]' | cut -c1-50)"
git checkout -b "$BRANCH_NAME" 2>/dev/null || git checkout "$BRANCH_NAME"

# Log start
TASK_ID=$(date +%Y%m%d-%H%M%S)
echo "[$(date)] [$TASK_ID] Starting: $TASK on $PROJECT" >> ~/logs/tasks.log

# Run Claude Code
claude --print "
Load the NOMARK method from .claude/.

Task: $TASK

Follow the NOMARK flow:
1. /think - Understand the problem first
2. /plan - Design solution with atomic stories
3. /build - Execute one story at a time
4. /verify - Ensure quality (typecheck, tests, browser)
5. /simplify - Clean up code
6. /commit - Ship when done

Project: $PROJECT
Branch: $BRANCH_NAME
Task ID: $TASK_ID

Remember:
- Check progress.txt for learned patterns
- Update CLAUDE.md with new learnings
- Create PR when ready
"

# Log completion
echo "[$(date)] [$TASK_ID] Completed: $TASK on $PROJECT" >> ~/logs/tasks.log
TASKSCRIPT

chmod +x ~/scripts/nomark-task.sh

# Create systemd service for Slack bot (optional)
echo -e "\n${YELLOW}Creating Slack bot service template...${NC}"
sudo tee /etc/systemd/system/nomark-slack.service > /dev/null << 'SVCFILE'
[Unit]
Description=NOMARK DevOps Slack Bot
After=network.target

[Service]
Type=simple
User=devops
WorkingDirectory=/home/devops
Environment="PATH=/home/devops/venv/bin:/usr/local/bin:/usr/bin:/bin"
EnvironmentFile=/home/devops/config/.env
ExecStart=/home/devops/venv/bin/python /home/devops/scripts/slack-bot.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
SVCFILE

# Add shell aliases
echo -e "\n${YELLOW}Adding shell aliases...${NC}"
cat >> ~/.bashrc << 'ALIASES'

# NOMARK DevOps Aliases
alias task="~/scripts/nomark-task.sh"
alias logs="tail -f ~/logs/tasks.log"
alias projects="jq '.projects[] | select(.active == true)' ~/config/projects.json"

# Activate Python venv
source ~/venv/bin/activate

# Load environment
if [ -f ~/config/.env ]; then
    export $(cat ~/config/.env | grep -v '^#' | xargs)
fi
ALIASES

# Summary
echo -e "\n${GREEN}========================================${NC}"
echo -e "${GREEN}   VM Setup Complete!                  ${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "Next steps:"
echo ""
echo "1. Configure environment:"
echo "   cp ~/config/.env.template ~/config/.env"
echo "   nano ~/config/.env"
echo ""
echo "2. Login to GitHub:"
echo "   gh auth login"
echo ""
echo "3. Clone FlowMetrics (first project):"
echo "   gh repo clone NOMARK/flowmetrics-portal ~/repos/flowmetrics"
echo ""
echo "4. Copy NOMARK method to project:"
echo "   # From local machine, scp the nomark-method folder"
echo ""
echo "5. Initialize knowledge base:"
echo "   ~/scripts/init-knowledge-base.sh"
echo ""
echo "6. Run first task:"
echo "   task flowmetrics 'add priority filter to task list'"
echo ""
echo "Reload shell: source ~/.bashrc"
