# Ralph Autonomous Development Agent

> Configure and run Ralph for PRD-driven autonomous development with Claude Code.

## When to Use

- Running unattended development sessions
- Processing multiple user stories automatically
- Overnight or batch development tasks
- CI/CD triggered development

## Prerequisites

- Claude Code CLI installed (`npm install -g @anthropic-ai/claude-code`)
- ANTHROPIC_API_KEY environment variable
- Git configured with push access
- PRD file with user stories (prd.json)

## PRD File Structure

```json
{
  "name": "feature-name",
  "description": "What this feature does",
  "branchName": "feature/feature-name",
  "repoContext": {
    "stack": "SvelteKit + Python + PostgreSQL",
    "conventions": {
      "commits": "feat(scope): description",
      "testing": "vitest for unit, playwright for e2e"
    }
  },
  "userStories": [
    {
      "id": "FEAT-001",
      "title": "Create database table",
      "description": "Create the platforms table with proper schema",
      "acceptanceCriteria": [
        "Table created with UUID primary key",
        "RLS policies applied",
        "Migration file created"
      ],
      "implementationNotes": [
        "Use gen_random_uuid() for ID",
        "Add tenant_id for multi-tenancy"
      ],
      "passes": false
    }
  ]
}
```

## Directory Structure

```
ralph/
└── ralph-<feature>/
    ├── scripts/
    │   └── ralph/
    │       ├── ralph.sh        # Runner script
    │       ├── prd.json        # User stories
    │       ├── progress.txt    # Completion log
    │       └── CLAUDE.md       # Context for Claude
    ├── docs/
    │   └── use-case.md
    └── AGENTS.md
```

## Running Ralph

### Local Execution
```bash
cd ralph/ralph-feature/scripts/ralph
./ralph.sh --tool claude 5  # Run 5 stories
```

### Via DevOps Agent
```
/dev start feature-name 5
```

### Via n8n Webhook
```bash
curl -X POST https://n8n.example.com/webhook/dev-task \
  -H "Content-Type: application/json" \
  -d '{"prd": "feature-name", "stories": 5}'
```

## Ralph Script Behavior

1. **Load PRD**: Read prd.json to get stories
2. **Filter incomplete**: Find stories where `passes: false`
3. **Build prompt**: Generate Claude Code prompt from story
4. **Execute**: Run `claude --dangerously-skip-permissions`
5. **Detect completion**: Look for "STORY COMPLETE" in output
6. **Mark complete**: Update prd.json with `passes: true`
7. **Commit**: Auto-commit with conventional message
8. **Notify**: Send progress to n8n/Slack webhook
9. **Loop**: Continue to next story

## Prompt Template

```markdown
## Story: {id} - {title}

{description}

### Acceptance Criteria
{acceptance_criteria as bullet list}

### Implementation Notes
{implementation_notes as bullet list}

### Instructions
1. Implement this story completely
2. Follow project conventions in AGENTS.md
3. Create tests if applicable
4. When complete, output exactly: STORY COMPLETE
5. If blocked, output: BLOCKED: <reason>
```

## Configuration Options

### Environment Variables
```bash
ANTHROPIC_API_KEY=sk-ant-...     # Required
TASK_ID=uuid                      # For webhook notifications
N8N_WEBHOOK_BASE_URL=https://... # Progress updates
REPOS_DIR=/home/devops/repos     # Where to clone repos
LOGS_DIR=/home/devops/logs       # Log file location
```

### ralph.sh Options
```bash
./ralph.sh --tool claude 5       # Run 5 stories with Claude
./ralph.sh --tool cursor 3       # Run 3 stories with Cursor
./ralph.sh --dry-run             # Show what would run
./ralph.sh --continue            # Resume from last story
```

## Notification Events

Ralph sends progress updates to the configured webhook:

| Event | Payload |
|-------|---------|
| `started` | `{task_id, prd, total_stories}` |
| `running` | `{task_id, story_id, story_title}` |
| `progress` | `{task_id, story_id, completed, total}` |
| `blocked` | `{task_id, story_id, reason}` |
| `error` | `{task_id, story_id, error}` |
| `completed` | `{task_id, stories_completed, total}` |

## CLAUDE.md Context

Each PRD should have a CLAUDE.md file providing context:

```markdown
# Feature Context

## What We're Building
Brief description of the feature.

## Current State
What exists now, what's missing.

## Key Files
- src/routes/feature/+page.svelte
- src/lib/stores/feature.ts

## Conventions
- Use existing component patterns
- Follow form handling with Superforms
```

## Best Practices

1. **Small stories**: 1-2 hours of work each
2. **Clear criteria**: Unambiguous acceptance criteria
3. **Context files**: Include CLAUDE.md with relevant context
4. **Test locally**: Run one story manually first
5. **Monitor progress**: Watch Slack notifications
6. **Review commits**: Check git log after completion

## Troubleshooting

### "BLOCKED" on every story
- Check if CLAUDE.md has enough context
- Verify acceptance criteria are clear
- Try running manually to see the issue

### Stories not completing
- Check Claude Code output in logs
- Verify API key has sufficient credits
- Check for permission issues (file access)

### Commits not pushing
- Verify GITHUB_TOKEN has push access
- Check branch protection rules
- Ensure remote is configured

## Integration with DevOps Agent

The DevOps Agent VM runs Ralph automatically:

```
Slack /dev start → n8n → VM webhook → ralph.sh → Claude Code
                                          ↓
                                    Git push
                                          ↓
                                    Slack notification
```

VM auto-stops after completion to save costs.
