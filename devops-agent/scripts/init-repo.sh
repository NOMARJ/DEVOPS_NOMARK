#!/bin/bash
# =============================================================================
# Initialize Repository with DevOps Agent Structure
# =============================================================================
# This script sets up a repository with the necessary files for autonomous
# development via the DevOps Agent.
#
# Usage:
#   ./init-repo.sh /path/to/your/repo
#   ./init-repo.sh /path/to/your/repo --prd my-feature
# =============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEVOPS_AGENT_DIR="$(dirname "$SCRIPT_DIR")"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log() { echo -e "${GREEN}[INIT]${NC} $1"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
error() { echo -e "${RED}[ERROR]${NC} $1"; exit 1; }

# Parse arguments
REPO_PATH=""
PRD_NAME=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --prd)
            PRD_NAME="$2"
            shift 2
            ;;
        *)
            REPO_PATH="$1"
            shift
            ;;
    esac
done

if [ -z "$REPO_PATH" ]; then
    echo "Usage: $0 /path/to/repo [--prd feature-name]"
    exit 1
fi

if [ ! -d "$REPO_PATH" ]; then
    error "Repository path does not exist: $REPO_PATH"
fi

cd "$REPO_PATH"
log "Initializing DevOps Agent structure in: $REPO_PATH"

# =============================================================================
# Create directory structure
# =============================================================================

log "Creating directory structure..."

mkdir -p skills/{sveltekit,postgres,n8n,docx,xlsx,pptx,pdf}
mkdir -p ralph

# =============================================================================
# Copy templates
# =============================================================================

log "Copying templates..."

# Copy CLAUDE.md if it doesn't exist
if [ ! -f "CLAUDE.md" ]; then
    cp "$DEVOPS_AGENT_DIR/templates/CLAUDE.md" ./CLAUDE.md
    log "Created CLAUDE.md"
else
    warn "CLAUDE.md already exists, skipping"
fi

# Copy AGENTS.md if it doesn't exist
if [ ! -f "AGENTS.md" ]; then
    cp "$DEVOPS_AGENT_DIR/templates/AGENTS.md" ./AGENTS.md
    log "Created AGENTS.md"
else
    warn "AGENTS.md already exists, skipping"
fi

# =============================================================================
# Copy Claude Code team configuration
# =============================================================================

log "Setting up Claude Code agent teams config..."

DEVOPS_NOMARK_DIR="$(dirname "$DEVOPS_AGENT_DIR")"

if [ -d "$DEVOPS_NOMARK_DIR/.claude" ]; then
    mkdir -p .claude/agents .claude/commands .claude/hooks .claude/skills/devops-teams

    # Copy settings.json (agent teams enabled)
    if [ -f "$DEVOPS_NOMARK_DIR/.claude/settings.json" ]; then
        cp "$DEVOPS_NOMARK_DIR/.claude/settings.json" .claude/settings.json
        log "Copied .claude/settings.json (agent teams enabled)"
    fi

    # Copy agent definitions
    for agent in "$DEVOPS_NOMARK_DIR"/.claude/agents/*.md; do
        if [ -f "$agent" ]; then
            cp "$agent" ".claude/agents/$(basename "$agent")"
        fi
    done
    log "Copied agent team definitions"

    # Copy team commands
    for cmd in "$DEVOPS_NOMARK_DIR"/.claude/commands/team-*.md; do
        if [ -f "$cmd" ]; then
            cp "$cmd" ".claude/commands/$(basename "$cmd")"
        fi
    done
    log "Copied team commands"

    # Copy hooks
    for hook in "$DEVOPS_NOMARK_DIR"/.claude/hooks/*.sh; do
        if [ -f "$hook" ]; then
            cp "$hook" ".claude/hooks/$(basename "$hook")"
            chmod +x ".claude/hooks/$(basename "$hook")"
        fi
    done
    log "Copied quality gate hooks"

    # Copy team skill
    if [ -f "$DEVOPS_NOMARK_DIR/.claude/skills/devops-teams/SKILL.md" ]; then
        cp "$DEVOPS_NOMARK_DIR/.claude/skills/devops-teams/SKILL.md" ".claude/skills/devops-teams/SKILL.md"
        log "Copied devops-teams skill"
    fi
else
    warn "DEVOPS_NOMARK .claude/ directory not found at $DEVOPS_NOMARK_DIR, skipping team config"
fi

# =============================================================================
# Copy skills
# =============================================================================

log "Copying skills..."

for skill in sveltekit postgres n8n; do
    if [ -f "$DEVOPS_AGENT_DIR/skills/$skill/SKILL.md" ]; then
        cp "$DEVOPS_AGENT_DIR/skills/$skill/SKILL.md" "./skills/$skill/SKILL.md"
        log "Copied $skill skill"
    fi
done

# Create placeholder skills for document generation
for skill in docx xlsx pptx pdf; do
    if [ ! -f "./skills/$skill/SKILL.md" ]; then
        cat > "./skills/$skill/SKILL.md" << 'EOF'
# Document Generation Skill

> Placeholder skill file. Copy content from your main devops-agent skills directory.

See: https://github.com/your-org/devops-agent/skills/
EOF
        log "Created placeholder for $skill skill"
    fi
done

# =============================================================================
# Create PRD structure (if requested)
# =============================================================================

if [ -n "$PRD_NAME" ]; then
    log "Creating PRD structure for: $PRD_NAME"
    
    PRD_DIR="ralph/ralph-$PRD_NAME"
    mkdir -p "$PRD_DIR/scripts/ralph"
    mkdir -p "$PRD_DIR/docs"
    
    # Copy ralph.sh
    if [ -f "$DEVOPS_AGENT_DIR/scripts/ralph.sh" ]; then
        cp "$DEVOPS_AGENT_DIR/scripts/ralph.sh" "$PRD_DIR/scripts/ralph/ralph.sh"
        chmod +x "$PRD_DIR/scripts/ralph/ralph.sh"
    fi
    
    # Create empty PRD file
    cat > "$PRD_DIR/scripts/ralph/prd.json" << EOF
{
  "name": "$PRD_NAME",
  "description": "Description of $PRD_NAME feature",
  "branchName": "feature/$PRD_NAME",
  "repoContext": {
    "stack": "SvelteKit + Python + PostgreSQL + n8n",
    "conventions": {
      "frontend": "SvelteKit with TypeScript, Tailwind CSS",
      "backend": "Python Azure Functions",
      "database": "PostgreSQL with RLS"
    }
  },
  "userStories": [
    {
      "id": "${PRD_NAME^^}-001",
      "title": "First story title",
      "description": "Description of what this story accomplishes",
      "acceptanceCriteria": [
        "Criterion 1",
        "Criterion 2"
      ],
      "implementationNotes": [
        "Note about implementation"
      ],
      "passes": false
    }
  ]
}
EOF
    
    # Create CLAUDE.md for PRD
    cat > "$PRD_DIR/scripts/ralph/CLAUDE.md" << EOF
# $PRD_NAME - Claude Context

## Feature Overview
Describe the feature here.

## Current Focus
Working on PRD: $PRD_NAME

## Key Files
- scripts/ralph/prd.json - User stories
- docs/ - Feature documentation

## Instructions
Follow the AGENTS.md conventions in the repository root.
Read the relevant skills before creating files.
EOF
    
    # Create progress file
    touch "$PRD_DIR/scripts/ralph/progress.txt"
    
    # Create README
    cat > "$PRD_DIR/README.md" << EOF
# $PRD_NAME

Ralph PRD for the $PRD_NAME feature.

## Quick Start

\`\`\`bash
cd $PRD_DIR
./scripts/ralph/ralph.sh --tool claude 5
\`\`\`

## Structure

\`\`\`
$PRD_DIR/
├── scripts/
│   └── ralph/
│       ├── ralph.sh      # Runner script
│       ├── prd.json      # User stories
│       ├── CLAUDE.md     # Context for Claude
│       └── progress.txt  # Completion log
├── docs/
│   └── use-case.md       # Feature documentation
└── README.md
\`\`\`
EOF
    
    log "Created PRD structure at: $PRD_DIR"
fi

# =============================================================================
# Update .gitignore
# =============================================================================

log "Updating .gitignore..."

GITIGNORE_ADDITIONS="
# DevOps Agent
*.log
ralph/**/progress.txt
.env.local
secrets.tfvars
"

if [ -f ".gitignore" ]; then
    if ! grep -q "DevOps Agent" .gitignore; then
        echo "$GITIGNORE_ADDITIONS" >> .gitignore
        log "Updated .gitignore"
    fi
else
    echo "$GITIGNORE_ADDITIONS" > .gitignore
    log "Created .gitignore"
fi

# =============================================================================
# Summary
# =============================================================================

echo ""
echo -e "${GREEN}════════════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}  DevOps Agent structure initialized successfully!${NC}"
echo -e "${GREEN}════════════════════════════════════════════════════════════════${NC}"
echo ""
echo "Created files:"
echo "  - CLAUDE.md (project context for Claude)"
echo "  - AGENTS.md (coding conventions)"
echo "  - skills/ (reusable skill instructions)"
echo "  - .claude/ (agent teams config, hooks, commands)"
if [ -n "$PRD_NAME" ]; then
    echo "  - ralph/ralph-$PRD_NAME/ (PRD structure)"
fi
echo ""
echo "Agent Teams:"
echo "  - 5 specialist agents (infra, mcp, security, workflow, qa)"
echo "  - 3 team commands (/team-infra, /team-review, /team-deploy)"
echo "  - Quality gate hooks (TeammateIdle, TaskCompleted)"
echo ""
echo "Next steps:"
echo "  1. Edit CLAUDE.md with your project details"
echo "  2. Edit AGENTS.md with your coding conventions"
if [ -n "$PRD_NAME" ]; then
    echo "  3. Edit ralph/ralph-$PRD_NAME/scripts/ralph/prd.json with user stories"
    echo "  4. Run: /dev start $PRD_NAME 5"
    echo "  5. Run with teams: /dev start $PRD_NAME 5 --team"
fi
echo ""
