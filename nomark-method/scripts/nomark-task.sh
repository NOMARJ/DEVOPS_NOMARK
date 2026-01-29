#!/bin/bash
# NOMARK Task Runner - Executes tasks using Claude Code with NOMARK method
# Outputs JSON result for Slack bot parsing

set -e

PROJECT=$1
TASK=$2
CONTINUE_BRANCH=$3  # Optional: continue on existing branch

# Load environment
if [ -f ~/config/.env ]; then
    export $(cat ~/config/.env | grep -v '^#' | xargs)
fi

# Configure git to use GitHub token for authentication
if [ -n "$GITHUB_TOKEN" ]; then
    git config --global credential.helper store
    git config --global url."https://${GITHUB_TOKEN}@github.com/".insteadOf "https://github.com/"
fi

if [ -z "$PROJECT" ] || [ -z "$TASK" ]; then
    echo "Usage: nomark-task.sh <project> <task-description>"
    echo ""
    echo "Available projects:"
    jq -r '.projects[] | select(.active == true) | "  - \(.id): \(.name)"' ~/config/projects.json 2>/dev/null || echo "  (no projects configured)"
    exit 1
fi

# Validate project
PROJECT_PATH="$HOME/repos/$PROJECT"
if [ ! -d "$PROJECT_PATH" ]; then
    echo "Project not found: $PROJECT"
    echo "Run: gh repo clone <owner>/$PROJECT ~/repos/$PROJECT"
    exit 1
fi

# Get project info from config
PROJECT_INFO=$(jq -r --arg id "$PROJECT" '.projects[] | select(.id == $id)' ~/config/projects.json 2>/dev/null || echo "{}")
REPO_OWNER=$(echo "$PROJECT_INFO" | jq -r '.repo // empty' | cut -d'/' -f1)
REPO_NAME=$(echo "$PROJECT_INFO" | jq -r '.repo // empty' | cut -d'/' -f2)

# Change to project directory
cd "$PROJECT_PATH"

# Ensure on main and up to date
DEFAULT_BRANCH=$(git symbolic-ref refs/remotes/origin/HEAD 2>/dev/null | sed 's@^refs/remotes/origin/@@' || echo "main")
git checkout "$DEFAULT_BRANCH" 2>/dev/null || git checkout main
git pull origin "$DEFAULT_BRANCH" 2>/dev/null || git pull origin main 2>/dev/null || true

# Create or continue on feature branch
if [ -n "$CONTINUE_BRANCH" ]; then
    BRANCH_NAME="$CONTINUE_BRANCH"
    git checkout "$BRANCH_NAME" 2>/dev/null || git checkout -b "$BRANCH_NAME"
    echo "Continuing on existing branch: $BRANCH_NAME"
else
    BRANCH_NAME="ralph/$(echo "$TASK" | tr ' ' '-' | tr '[:upper:]' '[:lower:]' | sed 's/[^a-z0-9-]//g' | cut -c1-50)"
    git checkout -b "$BRANCH_NAME" 2>/dev/null || git checkout "$BRANCH_NAME"
fi

# Create task ID and log
TASK_ID=$(date +%Y%m%d-%H%M%S)
RESULT_FILE="$HOME/logs/task-${TASK_ID}.json"
mkdir -p ~/logs
echo "[$(date)] [$TASK_ID] Starting: $TASK on $PROJECT" >> ~/logs/tasks.log

# Ensure Claude Code is available
if ! command -v claude &> /dev/null; then
    echo '{"status":"error","error":"Claude Code not installed"}' > "$RESULT_FILE"
    exit 1
fi

# Activate Python venv for any scripts
source ~/venv/bin/activate 2>/dev/null || true

# Run Claude Code with NOMARK method and capture structured output
claude --dangerously-skip-permissions --print "
You are working on the $PROJECT project using the NOMARK method.

## Context
- Project: $PROJECT
- Branch: $BRANCH_NAME
- Task ID: $TASK_ID
- Working directory: $PROJECT_PATH

## Your Task
$TASK

## NOMARK Method Flow
Follow this flow strictly:

### 1. /think - First Principles Analysis
Before coding, understand:
- What is the actual problem?
- What are the constraints?
- What existing patterns should I follow?

Read progress.txt for learned patterns.
Read CLAUDE.md for project conventions.

### 2. /plan - Design Solution
Create atomic user stories:
- Each story completable in one session
- Ordered by dependencies
- Clear acceptance criteria

### 3. /build - Execute One Story
For each story:
1. Implement the change
2. Run typecheck: npm run typecheck (or equivalent)
3. Run tests: npm test (or equivalent)
4. Verify in browser if UI change
5. Commit with descriptive message

### 4. /verify - Full Verification
- All tests pass
- Typecheck clean
- No console errors
- UI renders correctly

### 5. /simplify - Clean Up
- Remove unused code
- Simplify complex logic
- Ensure consistent style

### 6. /commit - Ship It
IMPORTANT: You MUST commit your changes. Run:
git add -A
git commit -m 'feat: <description>' -m 'Co-Authored-By: NOMARK DevOps <devops@nomark.au>'

### 7. /pr - Create Pull Request
After committing, create PR using: gh pr create --title '<title>' --body '<body>'
The PR body should include:
- Summary of changes
- Test plan
- Screenshots if UI change

## CRITICAL REQUIREMENTS
1. You MUST make code changes to complete the task
2. You MUST commit all changes before finishing
3. You MUST create a PR with gh pr create
4. Do NOT just analyze - implement the solution

## Resources
- Check .claude/skills/ for available skills
- Check .claude/patterns/ for code patterns

Begin with /think to analyze the task, then IMPLEMENT the solution.
"

# Gather results after Claude Code completes
echo "[$(date)] [$TASK_ID] Gathering results..." >> ~/logs/tasks.log

# Get changed files
FILES_CHANGED=$(git diff --name-only "$DEFAULT_BRANCH"..."$BRANCH_NAME" 2>/dev/null | head -20 || echo "")
if [ -n "$FILES_CHANGED" ]; then
    FILES_COUNT=$(echo "$FILES_CHANGED" | wc -l | xargs)
else
    FILES_COUNT=0
fi

# Get commit summary
COMMITS=$(git log "$DEFAULT_BRANCH".."$BRANCH_NAME" --oneline 2>/dev/null | head -10 || echo "")
if [ -n "$COMMITS" ]; then
    COMMIT_COUNT=$(echo "$COMMITS" | wc -l | xargs)
else
    COMMIT_COUNT=0
fi

# Check for PR
PR_URL=$(gh pr view "$BRANCH_NAME" --json url -q '.url' 2>/dev/null || echo "")

# If no PR exists but there are commits, create one
if [ -z "$PR_URL" ] && [ "$COMMIT_COUNT" -gt 0 ]; then
    # Push branch first
    git push -u origin "$BRANCH_NAME" 2>/dev/null || true

    # Create PR
    PR_TITLE="$TASK"
    PR_BODY="## Summary
Automated implementation via NOMARK DevOps.

**Task:** $TASK
**Branch:** \`$BRANCH_NAME\`
**Task ID:** \`$TASK_ID\`

## Changes
$COMMITS

## Files Changed
\`\`\`
$FILES_CHANGED
\`\`\`

---
Generated by NOMARK DevOps"

    PR_URL=$(gh pr create --title "$PR_TITLE" --body "$PR_BODY" --head "$BRANCH_NAME" 2>/dev/null | grep -oE 'https://github.com/[^ ]+' || echo "")
fi

# Get insertions/deletions
DIFF_STATS=$(git diff --stat "$DEFAULT_BRANCH"..."$BRANCH_NAME" 2>/dev/null | tail -1 || echo "")
INSERTIONS=$(echo "$DIFF_STATS" | grep -oE '[0-9]+ insertion' | grep -oE '[0-9]+' || echo "0")
DELETIONS=$(echo "$DIFF_STATS" | grep -oE '[0-9]+ deletion' | grep -oE '[0-9]+' || echo "0")

# Determine next actions based on what was done
NEXT_ACTIONS=""
if [ -n "$PR_URL" ]; then
    NEXT_ACTIONS="Review and merge the PR"
elif [ "$COMMIT_COUNT" -eq 0 ]; then
    NEXT_ACTIONS="No changes were made - task may need clarification"
else
    NEXT_ACTIONS="Push changes and create PR manually"
fi

# Check if tests passed (look for common patterns in git log)
TESTS_PASSED="unknown"
if git log -1 --pretty=%B 2>/dev/null | grep -qi "test.*pass\|all.*pass\|verified"; then
    TESTS_PASSED="true"
fi

# Build JSON result
cat > "$RESULT_FILE" << EOF
{
  "status": "success",
  "task_id": "$TASK_ID",
  "project": "$PROJECT",
  "branch": "$BRANCH_NAME",
  "task": "$TASK",
  "pr_url": "$PR_URL",
  "commits": $COMMIT_COUNT,
  "files_changed": $FILES_COUNT,
  "insertions": ${INSERTIONS:-0},
  "deletions": ${DELETIONS:-0},
  "files": $(echo "$FILES_CHANGED" | jq -R -s 'split("\n") | map(select(length > 0))'),
  "commit_messages": $(echo "$COMMITS" | jq -R -s 'split("\n") | map(select(length > 0))'),
  "next_actions": "$NEXT_ACTIONS",
  "tests_passed": "$TESTS_PASSED"
}
EOF

# Log completion
echo "[$(date)] [$TASK_ID] Completed: $TASK on $PROJECT" >> ~/logs/tasks.log

# Output result file path for the bot to read
echo "RESULT_FILE:$RESULT_FILE"
