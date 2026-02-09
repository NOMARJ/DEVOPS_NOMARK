#!/bin/bash
# =============================================================================
# Ralph - Autonomous Development Agent
# =============================================================================
# Enhanced version with n8n/Slack progress notifications
#
# Usage:
#   ./ralph.sh --tool claude 5
#   TASK_ID=abc123 ./ralph.sh --tool claude 10
#
# Environment variables:
#   N8N_WEBHOOK_BASE_URL - Base URL for n8n webhooks
#   TASK_ID - Optional task ID for tracking (auto-generated if not set)
#   ANTHROPIC_API_KEY - Required for Claude Code
# =============================================================================

set -e

# Configuration
TOOL="claude"
MAX_STORIES=50
STORIES_TO_RUN=5
TEAM_MODE=false

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --tool)
            TOOL="$2"
            shift 2
            ;;
        --team)
            TEAM_MODE=true
            shift
            ;;
        *)
            if [[ "$1" =~ ^[0-9]+$ ]]; then
                STORIES_TO_RUN="$1"
            fi
            shift
            ;;
    esac
done

# Ensure we don't run too many stories
if [ "$STORIES_TO_RUN" -gt "$MAX_STORIES" ]; then
    STORIES_TO_RUN=$MAX_STORIES
fi

# Find script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PRD_FILE="$SCRIPT_DIR/prd.json"
PROGRESS_FILE="$SCRIPT_DIR/progress.txt"
CLAUDE_MD="$SCRIPT_DIR/CLAUDE.md"

# Task tracking
TASK_ID="${TASK_ID:-$(date +%s)}"
STORIES_COMPLETED=0

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# =============================================================================
# Notification Functions
# =============================================================================

notify() {
    local status="$1"
    local message="$2"
    local extra="${3:-{}}"
    
    # Log locally
    echo -e "${BLUE}[NOTIFY]${NC} $status: $message"
    
    # Send to n8n if configured
    if [ -n "$N8N_WEBHOOK_BASE_URL" ]; then
        curl -s -X POST "$N8N_WEBHOOK_BASE_URL/task-progress" \
            -H "Content-Type: application/json" \
            -d "{
                \"task_id\": \"$TASK_ID\",
                \"status\": \"$status\",
                \"message\": \"$message\",
                \"timestamp\": \"$(date -u +%Y-%m-%dT%H:%M:%SZ)\",
                \"extra\": $extra
            }" > /dev/null 2>&1 || true
    fi
}

log() {
    echo -e "${GREEN}[RALPH]${NC} $1"
}

warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# =============================================================================
# PRD Functions
# =============================================================================

check_prerequisites() {
    # Check for required files
    if [ ! -f "$PRD_FILE" ]; then
        error "PRD file not found: $PRD_FILE"
        exit 1
    fi
    
    # Check for jq
    if ! command -v jq &> /dev/null; then
        error "jq is required but not installed"
        exit 1
    fi
    
    # Check for Claude Code
    if [ "$TOOL" = "claude" ]; then
        if ! command -v claude &> /dev/null; then
            error "Claude Code CLI not found. Install with: npm install -g @anthropic-ai/claude-code"
            exit 1
        fi
        
        if [ -z "$ANTHROPIC_API_KEY" ]; then
            error "ANTHROPIC_API_KEY environment variable not set"
            exit 1
        fi
    fi
}

get_incomplete_stories() {
    jq -r '.userStories[] | select(.passes == false or .passes == null) | .id' "$PRD_FILE"
}

get_story_details() {
    local story_id="$1"
    jq -r ".userStories[] | select(.id == \"$story_id\")" "$PRD_FILE"
}

get_story_title() {
    local story_id="$1"
    jq -r ".userStories[] | select(.id == \"$story_id\") | .title" "$PRD_FILE"
}

mark_story_complete() {
    local story_id="$1"
    local temp_file=$(mktemp)
    
    jq "(.userStories[] | select(.id == \"$story_id\")).passes = true" "$PRD_FILE" > "$temp_file"
    mv "$temp_file" "$PRD_FILE"
    
    log "Marked $story_id as complete"
}

# =============================================================================
# Execution Functions
# =============================================================================

build_prompt() {
    local story_id="$1"
    local story_details="$2"
    
    local title=$(echo "$story_details" | jq -r '.title')
    local description=$(echo "$story_details" | jq -r '.description')
    local acceptance_criteria=$(echo "$story_details" | jq -r '.acceptanceCriteria | join("\n- ")')
    local implementation_notes=$(echo "$story_details" | jq -r '.implementationNotes // "" | if type == "array" then join("\n- ") else . end')
    
    cat << PROMPT
# Task: Implement User Story $story_id

## Story Details
**Title:** $title

**Description:** $description

## Acceptance Criteria
- $acceptance_criteria

${implementation_notes:+## Implementation Notes
- $implementation_notes}

## Instructions

1. First, read the AGENTS.md file if it exists to understand project conventions
2. Check if any implementation already exists for this story (FIX before CREATE)
3. Implement the story following the acceptance criteria
4. Write or update tests as needed
5. Commit your changes with message: "feat($story_id): $title"

When complete, respond with "STORY COMPLETE" on its own line.
If you encounter a blocker, respond with "BLOCKED: <reason>" on its own line.
PROMPT
}

run_claude() {
    local story_id="$1"
    local prompt="$2"
    local output_file=$(mktemp)

    log "Running Claude Code for $story_id..."

    # Run Claude Code with the prompt
    # Using --print to get output, and piping the prompt
    echo "$prompt" | claude --print 2>&1 | tee "$output_file"

    local exit_code=${PIPESTATUS[1]}
    local output=$(cat "$output_file")
    rm -f "$output_file"

    # Check for completion or blocking
    if echo "$output" | grep -q "STORY COMPLETE"; then
        return 0
    elif echo "$output" | grep -q "BLOCKED:"; then
        local reason=$(echo "$output" | grep "BLOCKED:" | head -1)
        warn "Story blocked: $reason"
        return 2
    else
        # Assume success if no explicit failure
        return 0
    fi
}

run_claude_team() {
    local stories_json="$1"
    local output_file=$(mktemp)

    log "Running Claude Code in AGENT TEAM mode..."
    log "Spawning team for parallel story execution..."

    # Build a team prompt that includes all stories to process in parallel
    local team_prompt
    team_prompt=$(cat << TEAMPROMPT
# Agent Team Task: Parallel Story Execution

You are the team lead for a DevOps development task. Create an agent team to work on the following stories in parallel.

## Stories to Implement

$stories_json

## Team Structure

Spawn teammates based on the stories above. Each teammate should:
1. Own one or more stories (avoid file conflicts between teammates)
2. Read CLAUDE.md and any relevant AGENTS.md for project conventions
3. Check if implementation already exists before creating new code
4. Implement the story following acceptance criteria
5. Run verification (tests, linting) before marking complete
6. Commit with message format: "feat(<story-id>): <title>"

## Coordination Rules

- Require plan approval for teammates before they make changes
- Each teammate must run verification before completing their task
- If a story depends on another, ensure the dependency completes first
- Message teammates when changes affect shared files

## Completion

When ALL stories are complete, output "STORY COMPLETE" on its own line.
If any story is blocked, output "BLOCKED: <reason>" on its own line.

Wait for all teammates to finish before reporting completion.
TEAMPROMPT
    )

    echo "$team_prompt" | claude --print 2>&1 | tee "$output_file"

    local exit_code=${PIPESTATUS[1]}
    local output=$(cat "$output_file")
    rm -f "$output_file"

    if echo "$output" | grep -q "STORY COMPLETE"; then
        return 0
    elif echo "$output" | grep -q "BLOCKED:"; then
        local reason=$(echo "$output" | grep "BLOCKED:" | head -1)
        warn "Team blocked: $reason"
        return 2
    else
        return 0
    fi
}

# =============================================================================
# Main Loop
# =============================================================================

main() {
    log "Starting Ralph - Autonomous Development Agent"
    log "Task ID: $TASK_ID"
    log "Tool: $TOOL"
    log "Stories to run: $STORIES_TO_RUN"
    
    check_prerequisites
    
    # Get PRD name for notifications
    PRD_NAME=$(jq -r '.name // "Unknown"' "$PRD_FILE")
    
    notify "started" "Starting $PRD_NAME development" "{\"prd\": \"$PRD_NAME\", \"stories\": $STORIES_TO_RUN}"
    
    # Get incomplete stories
    mapfile -t incomplete_stories < <(get_incomplete_stories)
    local total_incomplete=${#incomplete_stories[@]}
    
    log "Found $total_incomplete incomplete stories"
    
    if [ "$total_incomplete" -eq 0 ]; then
        log "All stories are complete!"
        notify "completed" "All stories already complete" "{\"stories_completed\": 0}"
        exit 0
    fi
    
    # Limit to requested number
    local stories_to_process=("${incomplete_stories[@]:0:$STORIES_TO_RUN}")
    
    log "Will process ${#stories_to_process[@]} stories"
    if [ "$TEAM_MODE" = true ]; then
        log "MODE: Agent Team (parallel execution)"
    else
        log "MODE: Sequential (one story at a time)"
    fi

    # =========================================================================
    # Team Mode: Process stories in parallel via agent teams
    # =========================================================================
    if [ "$TEAM_MODE" = true ]; then
        notify "running" "Spawning agent team for ${#stories_to_process[@]} stories" "{\"mode\": \"team\", \"stories\": ${#stories_to_process[@]}}"

        # Build JSON array of all stories for the team
        local stories_for_team=""
        for story_id in "${stories_to_process[@]}"; do
            local story_details=$(get_story_details "$story_id")
            local title=$(echo "$story_details" | jq -r '.title')
            local description=$(echo "$story_details" | jq -r '.description')
            local criteria=$(echo "$story_details" | jq -r '.acceptanceCriteria | join("; ")')
            stories_for_team="${stories_for_team}
### $story_id: $title
**Description:** $description
**Acceptance Criteria:** $criteria
"
        done

        local result=0
        run_claude_team "$stories_for_team" || result=$?

        if [ $result -eq 0 ]; then
            # Mark all stories as complete
            for story_id in "${stories_to_process[@]}"; do
                mark_story_complete "$story_id"
                STORIES_COMPLETED=$((STORIES_COMPLETED + 1))
                local story_title=$(get_story_title "$story_id")
                echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] Completed (team): $story_id - $story_title" >> "$PROGRESS_FILE"
            done
            notify "progress" "Team completed all ${#stories_to_process[@]} stories" "{\"stories_completed\": $STORIES_COMPLETED, \"mode\": \"team\"}"
            log "Team completed all stories"
        elif [ $result -eq 2 ]; then
            warn "Team encountered blockers"
            notify "blocked" "Team blocked on some stories" "{\"mode\": \"team\"}"
        else
            error "Team execution failed"
            notify "error" "Team execution failed" "{\"mode\": \"team\"}"
        fi
    else

    # =========================================================================
    # Sequential Mode: Process stories one at a time
    # =========================================================================

    # Process each story
    for story_id in "${stories_to_process[@]}"; do
        local story_title=$(get_story_title "$story_id")
        
        log "=========================================="
        log "Starting: $story_id - $story_title"
        log "=========================================="
        
        notify "running" "Working on: $story_id - $story_title" "{\"story_id\": \"$story_id\", \"stories_completed\": $STORIES_COMPLETED}"
        
        # Get story details and build prompt
        local story_details=$(get_story_details "$story_id")
        local prompt=$(build_prompt "$story_id" "$story_details")
        
        # Run the appropriate tool
        local result=0
        case "$TOOL" in
            claude)
                run_claude "$story_id" "$prompt" || result=$?
                ;;
            *)
                error "Unknown tool: $TOOL"
                exit 1
                ;;
        esac
        
        # Handle result
        if [ $result -eq 0 ]; then
            mark_story_complete "$story_id"
            STORIES_COMPLETED=$((STORIES_COMPLETED + 1))
            
            # Log progress
            echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] Completed: $story_id - $story_title" >> "$PROGRESS_FILE"
            
            notify "progress" "Completed: $story_id - $story_title" "{\"story_id\": \"$story_id\", \"stories_completed\": $STORIES_COMPLETED}"
            
            log "✅ Completed: $story_id"
        elif [ $result -eq 2 ]; then
            warn "Story $story_id is blocked, skipping..."
            notify "blocked" "Blocked: $story_id" "{\"story_id\": \"$story_id\"}"
        else
            error "Story $story_id failed"
            notify "error" "Failed: $story_id" "{\"story_id\": \"$story_id\"}"
            
            # Continue to next story instead of failing completely
            warn "Continuing to next story..."
        fi
        
        # Small delay between stories
        sleep 2
    done

    fi  # End of team mode / sequential mode branch

    log "=========================================="
    log "Ralph completed!"
    log "Stories completed: $STORIES_COMPLETED / ${#stories_to_process[@]}"
    log "=========================================="
    
    # Final notification
    if [ $STORIES_COMPLETED -eq ${#stories_to_process[@]} ]; then
        notify "completed" "All $STORIES_COMPLETED stories completed successfully!" "{\"stories_completed\": $STORIES_COMPLETED, \"total\": ${#stories_to_process[@]}}"
    else
        notify "completed" "Completed $STORIES_COMPLETED of ${#stories_to_process[@]} stories" "{\"stories_completed\": $STORIES_COMPLETED, \"total\": ${#stories_to_process[@]}, \"partial\": true}"
    fi
    
    # Push changes
    if [ $STORIES_COMPLETED -gt 0 ]; then
        log "Pushing changes..."
        git push origin HEAD 2>/dev/null || warn "Could not push changes automatically"
    fi
}

# Run main
main "$@"
