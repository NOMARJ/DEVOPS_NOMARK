#!/bin/bash
# NOMARK DevOps - Knowledge Base Initialization
# Run this after VM setup to create the learning database

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}   NOMARK Knowledge Base Setup         ${NC}"
echo -e "${GREEN}========================================${NC}"

# Load environment
if [ -f ~/config/.env ]; then
    source ~/config/.env
else
    echo -e "${RED}Error: ~/config/.env not found${NC}"
    echo "Copy template: cp ~/config/.env.template ~/config/.env"
    exit 1
fi

# Validate required vars
if [ -z "$DB_HOST" ] || [ -z "$DB_USER" ] || [ -z "$DB_PASSWORD" ]; then
    echo -e "${RED}Error: Database credentials not configured${NC}"
    exit 1
fi

DB_NAME="${DB_NAME:-nomark_devops}"

echo -e "\n${YELLOW}Connecting to PostgreSQL...${NC}"
echo "Host: $DB_HOST"
echo "Database: $DB_NAME"

# Create database if not exists
echo -e "\n${YELLOW}Creating database...${NC}"
PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -U "$DB_USER" -d postgres -c "CREATE DATABASE $DB_NAME;" 2>/dev/null || echo "Database already exists"

# Connect and create schema
echo -e "\n${YELLOW}Creating schema...${NC}"
PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -U "$DB_USER" -d "$DB_NAME" << 'SQLEOF'

-- Enable extensions
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Projects table
CREATE TABLE IF NOT EXISTS projects (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    repo TEXT NOT NULL,
    stack TEXT NOT NULL,
    priority INTEGER DEFAULT 1,
    active BOOLEAN DEFAULT TRUE,
    config JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Knowledge embeddings (RAG)
CREATE TABLE IF NOT EXISTS knowledge_embeddings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    content TEXT NOT NULL,
    embedding vector(1536),
    category TEXT NOT NULL,
    project_id TEXT REFERENCES projects(id),
    source_type TEXT NOT NULL,
    source_ref TEXT,
    usage_count INTEGER DEFAULT 0,
    success_rate DECIMAL(3,2) DEFAULT 1.0,
    last_used_at TIMESTAMP,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Code patterns (reusable solutions)
CREATE TABLE IF NOT EXISTS code_patterns (
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

-- Decision log (learning from choices)
CREATE TABLE IF NOT EXISTS decision_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id TEXT REFERENCES projects(id),
    task_id TEXT,
    branch_name TEXT,
    decision_type TEXT NOT NULL,
    question TEXT NOT NULL,
    chosen_option TEXT NOT NULL,
    alternatives JSONB DEFAULT '[]',
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

-- Error history (learning from mistakes)
CREATE TABLE IF NOT EXISTS error_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id TEXT REFERENCES projects(id),
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

-- Task history
CREATE TABLE IF NOT EXISTS task_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id TEXT NOT NULL,
    project_id TEXT REFERENCES projects(id),
    branch_name TEXT,
    description TEXT NOT NULL,
    status TEXT DEFAULT 'pending',
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    duration_seconds INTEGER,
    pr_number INTEGER,
    pr_url TEXT,
    pr_status TEXT,
    files_changed TEXT[],
    commits INTEGER DEFAULT 0,
    errors_encountered INTEGER DEFAULT 0,
    notes TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_knowledge_embedding ON knowledge_embeddings USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
CREATE INDEX IF NOT EXISTS idx_knowledge_category ON knowledge_embeddings (category);
CREATE INDEX IF NOT EXISTS idx_knowledge_project ON knowledge_embeddings (project_id);
CREATE INDEX IF NOT EXISTS idx_knowledge_source ON knowledge_embeddings (source_type, source_ref);

CREATE INDEX IF NOT EXISTS idx_error_embedding ON error_history USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
CREATE INDEX IF NOT EXISTS idx_error_project ON error_history (project_id);
CREATE INDEX IF NOT EXISTS idx_error_type ON error_history (error_type);

CREATE INDEX IF NOT EXISTS idx_decision_project ON decision_log (project_id);
CREATE INDEX IF NOT EXISTS idx_decision_type ON decision_log (decision_type);
CREATE INDEX IF NOT EXISTS idx_decision_outcome ON decision_log (outcome);

CREATE INDEX IF NOT EXISTS idx_task_project ON task_history (project_id);
CREATE INDEX IF NOT EXISTS idx_task_status ON task_history (status);

CREATE INDEX IF NOT EXISTS idx_pattern_category ON code_patterns (category);
CREATE INDEX IF NOT EXISTS idx_pattern_slug ON code_patterns (slug);

-- Views for analytics
CREATE OR REPLACE VIEW agent_performance AS
SELECT
    DATE_TRUNC('week', created_at) AS week,
    project_id,
    COUNT(*) AS tasks_attempted,
    COUNT(*) FILTER (WHERE outcome = 'success') AS tasks_succeeded,
    COUNT(*) FILTER (WHERE outcome = 'failure') AS tasks_failed,
    ROUND(
        COUNT(*) FILTER (WHERE outcome = 'success')::DECIMAL /
        NULLIF(COUNT(*)::DECIMAL, 0) * 100, 2
    ) AS success_rate,
    AVG(EXTRACT(EPOCH FROM (resolved_at - created_at))) AS avg_duration_seconds
FROM decision_log
WHERE resolved_at IS NOT NULL
GROUP BY 1, 2
ORDER BY 1 DESC, 2;

CREATE OR REPLACE VIEW pattern_effectiveness AS
SELECT
    cp.name,
    cp.category,
    cp.usage_count,
    cp.success_rate,
    cp.projects,
    COUNT(dl.id) AS decision_uses,
    COUNT(dl.id) FILTER (WHERE dl.outcome = 'success') AS successful_uses
FROM code_patterns cp
LEFT JOIN decision_log dl ON dl.chosen_option LIKE '%' || cp.slug || '%'
GROUP BY cp.id
ORDER BY cp.usage_count DESC;

CREATE OR REPLACE VIEW error_trends AS
SELECT
    DATE_TRUNC('week', created_at) AS week,
    project_id,
    error_type,
    COUNT(*) AS occurrences,
    COUNT(*) FILTER (WHERE fix_worked = TRUE) AS fixed_count,
    ROUND(
        COUNT(*) FILTER (WHERE fix_worked = TRUE)::DECIMAL /
        NULLIF(COUNT(*)::DECIMAL, 0) * 100, 2
    ) AS fix_rate
FROM error_history
GROUP BY 1, 2, 3
ORDER BY 1 DESC, 4 DESC;

-- Functions for knowledge retrieval
CREATE OR REPLACE FUNCTION find_similar_knowledge(
    query_embedding vector(1536),
    match_threshold FLOAT DEFAULT 0.7,
    match_count INT DEFAULT 5,
    filter_project TEXT DEFAULT NULL
)
RETURNS TABLE (
    id UUID,
    content TEXT,
    category TEXT,
    project_id TEXT,
    source_type TEXT,
    similarity FLOAT
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        ke.id,
        ke.content,
        ke.category,
        ke.project_id,
        ke.source_type,
        1 - (ke.embedding <=> query_embedding) AS similarity
    FROM knowledge_embeddings ke
    WHERE
        (filter_project IS NULL OR ke.project_id = filter_project)
        AND 1 - (ke.embedding <=> query_embedding) > match_threshold
    ORDER BY ke.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;

CREATE OR REPLACE FUNCTION find_similar_errors(
    query_embedding vector(1536),
    match_threshold FLOAT DEFAULT 0.8,
    match_count INT DEFAULT 3
)
RETURNS TABLE (
    id UUID,
    error_type TEXT,
    error_message TEXT,
    fix_applied TEXT,
    fix_worked BOOLEAN,
    similarity FLOAT
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        eh.id,
        eh.error_type,
        eh.error_message,
        eh.fix_applied,
        eh.fix_worked,
        1 - (eh.embedding <=> query_embedding) AS similarity
    FROM error_history eh
    WHERE
        eh.embedding IS NOT NULL
        AND 1 - (eh.embedding <=> query_embedding) > match_threshold
    ORDER BY eh.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;

-- Insert initial data
INSERT INTO projects (id, name, repo, stack, priority, active)
VALUES
    ('flowmetrics', 'FlowMetrics', 'NOMARK/flowmetrics-portal', 'sveltekit-postgres', 1, TRUE),
    ('instaindex', 'InstaIndex', 'NOMARK/instaindex', 'nextjs-supabase', 2, TRUE),
    ('policyai', 'PolicyAI', 'NOMARK/policyai', 'nextjs-supabase', 3, FALSE)
ON CONFLICT (id) DO UPDATE SET
    name = EXCLUDED.name,
    repo = EXCLUDED.repo,
    stack = EXCLUDED.stack,
    priority = EXCLUDED.priority,
    updated_at = NOW();

-- Insert seed patterns
INSERT INTO code_patterns (name, slug, category, stack, description, template, example)
VALUES
    ('SvelteKit Server Action', 'sk-server-action', 'backend', ARRAY['sveltekit'],
     'Type-safe server action with validation and error handling',
     E'// +page.server.ts\nimport { fail } from ''@sveltejs/kit'';\nimport { z } from ''zod'';\n\nconst schema = z.object({\n  // fields\n});\n\nexport const actions = {\n  default: async ({ request }) => {\n    const form = await request.formData();\n    const result = schema.safeParse(Object.fromEntries(form));\n    \n    if (!result.success) {\n      return fail(400, { errors: result.error.flatten() });\n    }\n    \n    // Process validated data\n    return { success: true };\n  }\n};',
     NULL),

    ('React Query Hook', 'rq-hook', 'frontend', ARRAY['nextjs', 'react'],
     'Type-safe React Query hook with optimistic updates',
     E'import { useMutation, useQueryClient } from ''@tanstack/react-query'';\n\nexport function use[Name]Mutation() {\n  const queryClient = useQueryClient();\n  \n  return useMutation({\n    mutationFn: async (data: [Type]) => {\n      const res = await fetch(''/api/[endpoint]'', {\n        method: ''POST'',\n        body: JSON.stringify(data),\n      });\n      if (!res.ok) throw new Error(''Failed'');\n      return res.json();\n    },\n    onSuccess: () => {\n      queryClient.invalidateQueries({ queryKey: [''[key]''] });\n    },\n  });\n}',
     NULL),

    ('Drizzle Schema', 'drizzle-schema', 'database', ARRAY['drizzle'],
     'Type-safe Drizzle ORM table definition',
     E'import { pgTable, text, timestamp, uuid } from ''drizzle-orm/pg-core'';\n\nexport const [tableName] = pgTable(''[table_name]'', {\n  id: uuid(''id'').primaryKey().defaultRandom(),\n  // columns\n  createdAt: timestamp(''created_at'').defaultNow().notNull(),\n  updatedAt: timestamp(''updated_at'').defaultNow().notNull(),\n});',
     NULL)
ON CONFLICT (slug) DO NOTHING;

SQLEOF

echo -e "${GREEN}✓ Schema created${NC}"

# Verify
echo -e "\n${YELLOW}Verifying installation...${NC}"
PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -U "$DB_USER" -d "$DB_NAME" << 'VERIFYEOF'
SELECT 'Tables:' AS info;
SELECT tablename FROM pg_tables WHERE schemaname = 'public';

SELECT 'Extensions:' AS info;
SELECT extname FROM pg_extension WHERE extname IN ('vector', 'pg_trgm', 'uuid-ossp');

SELECT 'Projects:' AS info;
SELECT id, name, active FROM projects;

SELECT 'Patterns:' AS info;
SELECT name, category FROM code_patterns;
VERIFYEOF

echo -e "\n${GREEN}========================================${NC}"
echo -e "${GREEN}   Knowledge Base Ready!               ${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "Database: $DB_NAME"
echo "Host: $DB_HOST"
echo ""
echo "Tables created:"
echo "  - projects"
echo "  - knowledge_embeddings"
echo "  - code_patterns"
echo "  - decision_log"
echo "  - error_history"
echo "  - task_history"
echo ""
echo "Views created:"
echo "  - agent_performance"
echo "  - pattern_effectiveness"
echo "  - error_trends"
echo ""
echo "Functions created:"
echo "  - find_similar_knowledge()"
echo "  - find_similar_errors()"
