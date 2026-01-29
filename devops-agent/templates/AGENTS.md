# AGENTS.md - Project Conventions for AI Agents

> This file defines conventions that AI coding tools should follow.
> It is read automatically by Claude Code, Cursor, Windsurf, and similar tools.

## ⚠️ CRITICAL: Fix Before New

**ALWAYS check existing implementation against requirements BEFORE creating anything new.**

```
CHECK  → Does something already exist for this story?
FIX    → If exists but broken, fix it
ENHANCE → If exists but incomplete, enhance it
CREATE → ONLY if nothing exists at all
```

## Project Context

**Project**: FlowMetrics
**Type**: Multi-tenant BPO Analytics Platform
**Stack**: SvelteKit + Python + PostgreSQL + n8n

## Repository Structure

```
├── apps/
│   ├── admin-portal/        # BPO staff portal (SvelteKit)
│   └── client-portal/       # Client-facing portal (SvelteKit)
├── packages/
│   ├── shared/              # Shared TypeScript utilities
│   ├── ui/                  # Shared UI components
│   └── database/            # Database types and utilities
├── functions/               # Azure Functions (Python)
├── infrastructure/          # Terraform IaC
├── ralph/                   # Autonomous development PRDs
│   ├── ralph-platform-wizard/
│   └── ralph-file-ingestion/
├── skills/                  # Reusable skill instructions
└── docs/                    # Documentation
```

## Coding Standards

### TypeScript/SvelteKit

```typescript
// ✅ DO: Use type imports
import type { PageServerLoad } from './$types';

// ✅ DO: Use Zod for validation
const schema = z.object({
    name: z.string().min(1),
    email: z.string().email()
});

// ✅ DO: Handle errors explicitly
const { data, error } = await supabase.from('table').select();
if (error) throw error(500, error.message);

// ❌ DON'T: Use any
const data: any = {}; // Bad!

// ❌ DON'T: Ignore errors
await supabase.from('table').delete(); // Missing error handling!
```

### Python

```python
# ✅ DO: Use type hints
def process_file(file_path: str, client_id: UUID) -> ProcessingResult:
    pass

# ✅ DO: Use dataclasses or Pydantic
@dataclass
class ProcessingResult:
    success: bool
    records_processed: int
    errors: list[str]

# ❌ DON'T: Use bare except
try:
    process()
except:  # Bad!
    pass

# ✅ DO: Catch specific exceptions
try:
    process()
except ValidationError as e:
    logger.error(f"Validation failed: {e}")
    raise
```

### SQL/Database

```sql
-- ✅ DO: Use UUID primary keys
CREATE TABLE platforms (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ✅ DO: Add indexes for foreign keys and common queries
CREATE INDEX idx_platforms_tenant ON platforms(tenant_id);

-- ✅ DO: Use RLS for multi-tenancy
ALTER TABLE platforms ENABLE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation ON platforms
    USING (tenant_id = current_setting('app.current_tenant')::uuid);

-- ❌ DON'T: Use serial IDs for public-facing entities
CREATE TABLE bad_example (
    id SERIAL PRIMARY KEY  -- Predictable, leaks info
);
```

## File Naming Conventions

| Type | Convention | Example |
|------|------------|---------|
| Components | PascalCase | `DataTable.svelte` |
| Routes | kebab-case | `platform-wizard/` |
| Utilities | camelCase | `formatCurrency.ts` |
| Database | snake_case | `platform_configs` |
| Migrations | date prefix | `20240115_add_platforms.sql` |

## Component Patterns

### SvelteKit Page Structure

```
src/routes/platforms/
├── +page.svelte          # UI component
├── +page.server.ts       # Server load function
├── +layout.svelte        # Shared layout (if needed)
├── [id]/
│   ├── +page.svelte      # Detail view
│   └── +page.server.ts   # Load single platform
└── new/
    ├── +page.svelte      # Create form
    └── +page.server.ts   # Form action
```

### Form Handling

```typescript
// +page.server.ts
import { superValidate, fail } from 'sveltekit-superforms';
import { zod } from 'sveltekit-superforms/adapters';

const schema = z.object({
    name: z.string().min(1, 'Name is required'),
    code: z.string().regex(/^[A-Z]{3,10}$/, 'Invalid code format')
});

export const load = async () => {
    const form = await superValidate(zod(schema));
    return { form };
};

export const actions = {
    default: async ({ request, locals }) => {
        const form = await superValidate(request, zod(schema));
        
        if (!form.valid) {
            return fail(400, { form });
        }
        
        // Process form...
        
        return { form };
    }
};
```

## API Design

### REST Endpoints

```
GET    /api/platforms          # List all
GET    /api/platforms/:id      # Get one
POST   /api/platforms          # Create
PUT    /api/platforms/:id      # Update
DELETE /api/platforms/:id      # Delete
```

### Response Format

```typescript
// Success
{
    "data": { ... },
    "meta": { "total": 100, "page": 1 }
}

// Error
{
    "error": {
        "code": "VALIDATION_ERROR",
        "message": "Invalid input",
        "details": [...]
    }
}
```

## Testing Requirements

### Unit Tests
- All utility functions must have tests
- Business logic must have >80% coverage
- Use vitest for TypeScript, pytest for Python

### Integration Tests
- All API endpoints must have tests
- Database operations must be tested
- Use test database with seed data

### Test File Location
```
src/lib/utils/
├── formatCurrency.ts
└── formatCurrency.test.ts    # Co-located

# OR

tests/
├── unit/
│   └── formatCurrency.test.ts
└── integration/
    └── api/platforms.test.ts
```

## Git Workflow

### Branch Naming
```
feature/<story-id>-short-description
bugfix/<issue-id>-short-description
hotfix/<issue-id>-short-description
```

### Commit Messages
```
feat(PWZ-001): Add platform creation wizard
fix(FI-003): Handle empty SFTP responses
docs: Update API documentation
refactor: Extract validation utilities
```

### PR Requirements
- Linked to story/issue
- Tests passing
- No linting errors
- Reviewed by at least 1 person (when not autonomous)

## Environment Variables

### Required
```env
DATABASE_URL=postgresql://...
SUPABASE_URL=https://...
SUPABASE_ANON_KEY=...
SUPABASE_SERVICE_KEY=...
```

### Optional
```env
N8N_WEBHOOK_URL=https://...
SLACK_WEBHOOK_URL=https://...
SENTRY_DSN=https://...
```

## Skills Reference

When creating documents or complex outputs, read the relevant skill file first:

| Task | Skill Path |
|------|------------|
| Word documents | `/skills/docx/SKILL.md` |
| Excel spreadsheets | `/skills/xlsx/SKILL.md` |
| PowerPoint | `/skills/pptx/SKILL.md` |
| PDF generation | `/skills/pdf/SKILL.md` |
| SvelteKit patterns | `/skills/sveltekit/SKILL.md` |
| Database migrations | `/skills/postgres/SKILL.md` |
| n8n workflows | `/skills/n8n/SKILL.md` |

## Common Gotchas

1. **RLS Policies**: Always test with actual tenant context, not service role
2. **Timezone**: Store all times as UTC, convert on display
3. **File uploads**: Max 50MB, use signed URLs for large files
4. **Rate limiting**: API endpoints have 100 req/min limit
5. **Caching**: Metabase embeds cache for 10 minutes

## Useful Commands

```bash
# Development
pnpm dev                    # Start all apps
pnpm build                  # Build for production
pnpm test                   # Run tests
pnpm lint                   # Lint code
pnpm db:migrate             # Run migrations
pnpm db:seed                # Seed test data

# Infrastructure
terraform plan              # Preview changes
terraform apply             # Apply changes
az login                    # Azure CLI login

# Ralph
./scripts/ralph/ralph.sh --tool claude 5
```
