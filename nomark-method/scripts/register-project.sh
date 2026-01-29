#!/bin/bash
# NOMARK Project Registration - Clones a GitHub repo and sets it up for NOMARK
# Usage: register-project.sh <github-url> [project-id]

set -e

GITHUB_URL=$1
PROJECT_ID=$2

# Load environment
if [ -f ~/config/.env ]; then
    export $(cat ~/config/.env | grep -v '^#' | xargs)
fi

# Configure git to use GitHub token for authentication
if [ -n "$GITHUB_TOKEN" ]; then
    git config --global credential.helper store
    git config --global url."https://${GITHUB_TOKEN}@github.com/".insteadOf "https://github.com/"
fi

if [ -z "$GITHUB_URL" ]; then
    echo '{"status":"error","error":"GitHub URL required"}'
    exit 1
fi

# Parse GitHub URL to extract owner/repo
# Supports: https://github.com/owner/repo, https://github.com/owner/repo.git, git@github.com:owner/repo.git
REPO_FULL=""
if [[ "$GITHUB_URL" =~ github\.com[:/]([^/]+)/([^/\.]+) ]]; then
    OWNER="${BASH_REMATCH[1]}"
    REPO="${BASH_REMATCH[2]}"
    REPO_FULL="$OWNER/$REPO"
else
    echo '{"status":"error","error":"Invalid GitHub URL format"}'
    exit 1
fi

# Use provided project ID or derive from repo name
if [ -z "$PROJECT_ID" ]; then
    PROJECT_ID=$(echo "$REPO" | tr '[:upper:]' '[:lower:]' | sed 's/[^a-z0-9-]/-/g')
fi

PROJECT_PATH="$HOME/repos/$PROJECT_ID"
CONFIG_FILE="$HOME/config/projects.json"

# Check if project already exists
if [ -d "$PROJECT_PATH" ]; then
    echo "{\"status\":\"error\",\"error\":\"Project directory already exists: $PROJECT_ID\"}"
    exit 1
fi

# Check if project ID already in config
if jq -e --arg id "$PROJECT_ID" '.projects[] | select(.id == $id)' "$CONFIG_FILE" > /dev/null 2>&1; then
    echo "{\"status\":\"error\",\"error\":\"Project ID already registered: $PROJECT_ID\"}"
    exit 1
fi

echo "Cloning $REPO_FULL to $PROJECT_PATH..." >&2

# Clone the repository
mkdir -p "$HOME/repos"
if ! gh repo clone "$REPO_FULL" "$PROJECT_PATH" >&2 2>&1; then
    echo '{"status":"error","error":"Failed to clone repository. Check URL and permissions."}'
    exit 1
fi

cd "$PROJECT_PATH"

# Detect project stack
STACK="unknown"
if [ -f "package.json" ]; then
    if grep -q '"next"' package.json; then
        STACK="nextjs"
    elif grep -q '"vite"' package.json; then
        STACK="vite"
    elif grep -q '"react"' package.json; then
        STACK="react"
    elif grep -q '"vue"' package.json; then
        STACK="vue"
    else
        STACK="node"
    fi

    # Check for TypeScript
    if [ -f "tsconfig.json" ] || grep -q '"typescript"' package.json; then
        STACK="$STACK-typescript"
    fi

    # Check for common backends
    if grep -q '"prisma"' package.json || grep -q '"@prisma"' package.json; then
        STACK="$STACK-prisma"
    elif grep -q '"supabase"' package.json || grep -q '"@supabase"' package.json; then
        STACK="$STACK-supabase"
    fi
elif [ -f "requirements.txt" ] || [ -f "pyproject.toml" ]; then
    STACK="python"
    if [ -f "manage.py" ]; then
        STACK="django"
    elif grep -q "flask" requirements.txt 2>/dev/null || grep -q "Flask" requirements.txt 2>/dev/null; then
        STACK="flask"
    elif grep -q "fastapi" requirements.txt 2>/dev/null || grep -q "FastAPI" pyproject.toml 2>/dev/null; then
        STACK="fastapi"
    fi
elif [ -f "Cargo.toml" ]; then
    STACK="rust"
elif [ -f "go.mod" ]; then
    STACK="go"
elif [ -f "pom.xml" ] || [ -f "build.gradle" ]; then
    STACK="java"
fi

# Get repo description from GitHub
DESCRIPTION=$(gh repo view "$REPO_FULL" --json description -q '.description' 2>/dev/null || echo "")
if [ -z "$DESCRIPTION" ]; then
    DESCRIPTION="$REPO project"
fi

# Get default branch
DEFAULT_BRANCH=$(git symbolic-ref refs/remotes/origin/HEAD 2>/dev/null | sed 's@^refs/remotes/origin/@@' || echo "main")

# Install dependencies if needed
echo "Installing dependencies..." >&2
if [ -f "package.json" ]; then
    npm install >&2 2>&1 || yarn install >&2 2>&1 || true
elif [ -f "requirements.txt" ]; then
    pip install -r requirements.txt >&2 2>&1 || true
fi

# Copy NOMARK method files if they exist
SKILLS_SOURCE="$HOME/flowmetrics-skills/organized"
if [ -d "$SKILLS_SOURCE" ]; then
    echo "Setting up NOMARK method..." >&2
    mkdir -p "$PROJECT_PATH/.claude"
    cp -r "$SKILLS_SOURCE"/* "$PROJECT_PATH/.claude/" 2>/dev/null || true
fi

# Create CLAUDE.md if it doesn't exist
if [ ! -f "$PROJECT_PATH/CLAUDE.md" ]; then
    cat > "$PROJECT_PATH/CLAUDE.md" << CLAUDEMD
# $REPO - Claude Code Configuration

## Project Overview
$DESCRIPTION

## Stack
- **Framework:** $STACK
- **Repository:** $REPO_FULL

## Development Commands
\`\`\`bash
# Install dependencies
npm install  # or yarn/pip as appropriate

# Run dev server
npm run dev

# Run tests
npm test

# Type check
npm run typecheck
\`\`\`

## Coding Conventions
- Follow existing code style
- Use TypeScript strict mode where applicable
- Write tests for new features
- Keep commits atomic and descriptive

## File Structure
(Add project-specific structure notes here)
CLAUDEMD
fi

# Update projects.json
echo "Updating projects configuration..." >&2
TEMP_CONFIG=$(mktemp)

# Get current max priority
MAX_PRIORITY=$(jq '[.projects[].priority // 0] | max // 0' "$CONFIG_FILE" 2>/dev/null || echo "0")
NEW_PRIORITY=$((MAX_PRIORITY + 1))

# Add new project entry
jq --arg id "$PROJECT_ID" \
   --arg name "$REPO" \
   --arg repo "$REPO_FULL" \
   --arg stack "$STACK" \
   --arg desc "$DESCRIPTION" \
   --argjson priority "$NEW_PRIORITY" \
   '.projects += [{
       "id": $id,
       "name": $name,
       "repo": $repo,
       "stack": $stack,
       "description": $desc,
       "priority": $priority,
       "active": true
   }]' "$CONFIG_FILE" > "$TEMP_CONFIG"

mv "$TEMP_CONFIG" "$CONFIG_FILE"

# Get file count and size
FILE_COUNT=$(find "$PROJECT_PATH" -type f | wc -l | xargs)
TOTAL_SIZE=$(du -sh "$PROJECT_PATH" 2>/dev/null | cut -f1)

# Output result JSON
cat << EOF
{
    "status": "success",
    "project_id": "$PROJECT_ID",
    "repo": "$REPO_FULL",
    "path": "$PROJECT_PATH",
    "stack": "$STACK",
    "description": "$DESCRIPTION",
    "default_branch": "$DEFAULT_BRANCH",
    "file_count": $FILE_COUNT,
    "total_size": "$TOTAL_SIZE",
    "nomark_setup": $([ -d "$PROJECT_PATH/.claude" ] && echo "true" || echo "false")
}
EOF
