# CLAUDE.md - DevOps Agent Context

> This file is automatically read by Claude Code to understand the project context.
> Place this in your repo root or in the Ralph PRD directory.

## Agent Identity

You are an autonomous development agent running as part of the DevOps Agent system. You execute user stories from PRD files without human intervention.

## Environment

- **Runtime**: Azure VM (Ubuntu 22.04)
- **Orchestration**: Ralph script → Claude Code CLI
- **Notifications**: Progress sent to n8n → Slack
- **Task ID**: Available as `$TASK_ID` environment variable

## Critical Rules

### 1. Fix Before Create
```
CHECK  → Does something already exist for this story?
FIX    → If exists but broken, fix it
ENHANCE → If exists but incomplete, enhance it
CREATE → ONLY if nothing exists at all
```

**Always search the codebase before creating new files.**

### 2. Atomic Commits
- One commit per story
- Format: `feat(<story-id>): <title>`
- Example: `feat(PWZ-001): Create master_platform_configs table`

### 3. Story Completion
When you complete a story, output exactly:
```
STORY COMPLETE
```

If blocked, output:
```
BLOCKED: <reason>
```

### 4. No Interactive Prompts
You are running autonomously. Never:
- Ask clarifying questions
- Wait for user input
- Suggest alternatives without implementing

If requirements are ambiguous, make the most reasonable choice and document it.

## Project Context

### Stack
- **Frontend**: SvelteKit + TypeScript + Tailwind CSS
- **Backend**: Python (Azure Functions) / Node.js
- **Database**: PostgreSQL with Row-Level Security
- **Workflows**: n8n for orchestration
- **Analytics**: Self-hosted Metabase

### Key Directories
```
/apps/admin-portal/     # BPO admin SvelteKit app
/apps/client-portal/    # Client-facing SvelteKit app
/packages/shared/       # Shared TypeScript utilities
/functions/             # Azure Functions (Python)
/infrastructure/        # Terraform configs
/ralph/                 # PRD directories for autonomous dev
```

### Database Conventions
- Use UUID primary keys: `id UUID PRIMARY KEY DEFAULT gen_random_uuid()`
- Always add `created_at` and `updated_at` timestamps
- Use snake_case for column names
- Add RLS policies for multi-tenant tables

### TypeScript Conventions
- Strict mode enabled
- Use Zod for runtime validation
- Prefer `type` over `interface`
- Use barrel exports (index.ts)

### SvelteKit Conventions
- Use `+page.server.ts` for data loading
- Form actions for mutations
- Superforms for form handling
- Use `$lib` alias for imports

## Skills Available

Skills are reusable instructions in `/skills/` directory:

| Skill | Purpose |
|-------|---------|
| `docx` | Creating Word documents |
| `xlsx` | Creating Excel spreadsheets |
| `pptx` | Creating PowerPoint presentations |
| `pdf` | Creating/filling PDF documents |
| `sveltekit` | SvelteKit component patterns |
| `postgres` | Database migration patterns |
| `n8n` | Workflow creation patterns |

**Read the relevant SKILL.md before creating artifacts.**

## Testing

### Running Tests
```bash
# TypeScript/SvelteKit
pnpm test
pnpm test:unit
pnpm test:integration

# Python
pytest
pytest -v -k "test_name"
```

### Test Requirements
- Unit tests for business logic
- Integration tests for API endpoints
- E2E tests for critical user flows (if applicable)

## Common Patterns

### Database Migration
```sql
-- migrations/YYYYMMDD_description.sql
BEGIN;

CREATE TABLE IF NOT EXISTS table_name (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    -- columns
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_table_column ON table_name(column);

COMMIT;
```

### SvelteKit API Route
```typescript
// src/routes/api/resource/+server.ts
import { json, error } from '@sveltejs/kit';
import type { RequestHandler } from './$types';

export const GET: RequestHandler = async ({ locals }) => {
    const { supabase, session } = locals;
    
    if (!session) {
        throw error(401, 'Unauthorized');
    }
    
    const { data, error: dbError } = await supabase
        .from('table')
        .select('*');
    
    if (dbError) {
        throw error(500, dbError.message);
    }
    
    return json(data);
};
```

### n8n Webhook Handler
```python
# functions/webhook_handler/__init__.py
import azure.functions as func
import json

def main(req: func.HttpRequest) -> func.HttpResponse:
    try:
        body = req.get_json()
        # Process webhook
        return func.HttpResponse(
            json.dumps({"status": "ok"}),
            mimetype="application/json"
        )
    except Exception as e:
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            status_code=500,
            mimetype="application/json"
        )
```

## Debugging

### Logs
- Check `/home/devops/logs/task-*.log` on the VM
- n8n execution history for workflow issues
- Azure Function logs in Application Insights

### Common Issues
1. **Database connection**: Check connection string and firewall rules
2. **Auth failures**: Verify JWT secret and token expiry
3. **Build failures**: Clear node_modules and reinstall

## Progress Reporting

The agent automatically reports progress via environment variables:
- `N8N_WEBHOOK_BASE_URL` - Webhook endpoint for updates
- `TASK_ID` - Current task identifier

Progress is sent at:
- Task start
- Each story start
- Each story completion
- Task completion or failure
