# PostgreSQL Skill

> Read this before creating database migrations, tables, or queries.

## Migration File Format

```sql
-- migrations/YYYYMMDD_HHMMSS_description.sql
-- Description: Brief description of what this migration does
-- Author: DevOps Agent
-- Date: 2024-01-15

BEGIN;

-- Your migration here

COMMIT;
```

## Table Creation Pattern

```sql
CREATE TABLE IF NOT EXISTS platforms (
    -- Primary key (always UUID)
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Foreign keys
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    created_by UUID REFERENCES users(id) ON DELETE SET NULL,
    
    -- Business fields
    name TEXT NOT NULL,
    code TEXT NOT NULL,
    description TEXT,
    config JSONB DEFAULT '{}'::jsonb,
    is_active BOOLEAN DEFAULT true,
    
    -- Timestamps (always include)
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Constraints
    CONSTRAINT platforms_code_unique UNIQUE (tenant_id, code),
    CONSTRAINT platforms_code_format CHECK (code ~ '^[A-Z0-9]{3,10}$')
);

-- Indexes
CREATE INDEX idx_platforms_tenant ON platforms(tenant_id);
CREATE INDEX idx_platforms_code ON platforms(code);
CREATE INDEX idx_platforms_active ON platforms(is_active) WHERE is_active = true;

-- Updated at trigger
CREATE TRIGGER update_platforms_updated_at
    BEFORE UPDATE ON platforms
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Comments
COMMENT ON TABLE platforms IS 'Configuration for data platforms (Asgard, Netwealth, etc.)';
COMMENT ON COLUMN platforms.code IS 'Unique platform code, e.g., ASGARD, NETWEALTH';
COMMENT ON COLUMN platforms.config IS 'Platform-specific configuration as JSON';
```

## Row Level Security (RLS)

```sql
-- Enable RLS
ALTER TABLE platforms ENABLE ROW LEVEL SECURITY;

-- Force RLS for table owner too
ALTER TABLE platforms FORCE ROW LEVEL SECURITY;

-- Tenant isolation policy
CREATE POLICY tenant_isolation_platforms ON platforms
    USING (tenant_id = current_setting('app.current_tenant', true)::uuid);

-- Alternative: Using auth.uid() for Supabase
CREATE POLICY user_platforms ON platforms
    FOR ALL
    USING (
        tenant_id IN (
            SELECT tenant_id FROM user_tenants 
            WHERE user_id = auth.uid()
        )
    );

-- Admin bypass policy
CREATE POLICY admin_bypass_platforms ON platforms
    FOR ALL
    TO service_role
    USING (true);
```

## Common Patterns

### JSONB Queries

```sql
-- Query JSONB field
SELECT * FROM platforms 
WHERE config->>'sftp_host' IS NOT NULL;

-- Query nested JSONB
SELECT * FROM platforms 
WHERE config->'mapping'->>'source_column' = 'amount';

-- Update JSONB field
UPDATE platforms 
SET config = config || '{"sftp_enabled": true}'::jsonb
WHERE id = $1;

-- Remove JSONB key
UPDATE platforms 
SET config = config - 'deprecated_field'
WHERE id = $1;
```

### Array Operations

```sql
-- Create table with array
CREATE TABLE processing_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    file_ids UUID[] DEFAULT '{}',
    tags TEXT[] DEFAULT '{}'
);

-- Array contains
SELECT * FROM processing_jobs WHERE 'urgent' = ANY(tags);

-- Array overlap
SELECT * FROM processing_jobs WHERE tags && ARRAY['urgent', 'priority'];

-- Append to array
UPDATE processing_jobs 
SET file_ids = array_append(file_ids, $1)
WHERE id = $2;
```

### Upsert Pattern

```sql
INSERT INTO platform_configs (tenant_id, platform_code, config)
VALUES ($1, $2, $3)
ON CONFLICT (tenant_id, platform_code) 
DO UPDATE SET 
    config = EXCLUDED.config,
    updated_at = NOW();
```

### Soft Delete

```sql
-- Add soft delete column
ALTER TABLE platforms ADD COLUMN deleted_at TIMESTAMPTZ;

-- Create index for soft delete queries
CREATE INDEX idx_platforms_not_deleted ON platforms(id) WHERE deleted_at IS NULL;

-- Soft delete
UPDATE platforms SET deleted_at = NOW() WHERE id = $1;

-- Query non-deleted
SELECT * FROM platforms WHERE deleted_at IS NULL;

-- Create view for convenience
CREATE VIEW active_platforms AS
SELECT * FROM platforms WHERE deleted_at IS NULL;
```

## Functions

### Updated At Trigger Function

```sql
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
```

### Audit Log Function

```sql
CREATE OR REPLACE FUNCTION audit_log()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO audit_logs (
        table_name,
        record_id,
        action,
        old_data,
        new_data,
        user_id,
        timestamp
    ) VALUES (
        TG_TABLE_NAME,
        COALESCE(NEW.id, OLD.id),
        TG_OP,
        CASE WHEN TG_OP = 'DELETE' THEN to_jsonb(OLD) ELSE NULL END,
        CASE WHEN TG_OP != 'DELETE' THEN to_jsonb(NEW) ELSE NULL END,
        current_setting('app.current_user', true)::uuid,
        NOW()
    );
    RETURN COALESCE(NEW, OLD);
END;
$$ LANGUAGE plpgsql;
```

### Generate Slug Function

```sql
CREATE OR REPLACE FUNCTION generate_slug(input_text TEXT)
RETURNS TEXT AS $$
BEGIN
    RETURN lower(
        regexp_replace(
            regexp_replace(input_text, '[^a-zA-Z0-9\s-]', '', 'g'),
            '\s+', '-', 'g'
        )
    );
END;
$$ LANGUAGE plpgsql IMMUTABLE;
```

## Views

### Materialized View with Refresh

```sql
CREATE MATERIALIZED VIEW platform_stats AS
SELECT 
    p.id AS platform_id,
    p.name AS platform_name,
    COUNT(DISTINCT f.id) AS total_files,
    COUNT(DISTINCT f.id) FILTER (WHERE f.status = 'processed') AS processed_files,
    MAX(f.processed_at) AS last_processed_at
FROM platforms p
LEFT JOIN files f ON f.platform_id = p.id
GROUP BY p.id, p.name;

-- Create unique index for concurrent refresh
CREATE UNIQUE INDEX idx_platform_stats_id ON platform_stats(platform_id);

-- Refresh (can be done concurrently with the unique index)
REFRESH MATERIALIZED VIEW CONCURRENTLY platform_stats;
```

## Query Optimization

### Explain Analyze

```sql
EXPLAIN (ANALYZE, BUFFERS, FORMAT TEXT)
SELECT * FROM platforms 
WHERE tenant_id = 'uuid-here' 
AND is_active = true;
```

### Partial Index

```sql
-- Index only active platforms
CREATE INDEX idx_active_platforms 
ON platforms(tenant_id, code) 
WHERE is_active = true AND deleted_at IS NULL;
```

### Expression Index

```sql
-- Index on lowercase name for case-insensitive search
CREATE INDEX idx_platforms_name_lower 
ON platforms(lower(name));

-- Query using the index
SELECT * FROM platforms WHERE lower(name) = lower($1);
```

## Migrations Best Practices

1. **Always use transactions**: Wrap in `BEGIN`/`COMMIT`
2. **Make migrations idempotent**: Use `IF NOT EXISTS`, `IF EXISTS`
3. **Add rollback comments**: Document how to undo
4. **Test on copy first**: Never run untested migrations on production
5. **Keep migrations small**: One logical change per file
6. **Use descriptive names**: `20240115_add_sftp_config_to_platforms.sql`

## Rollback Template

```sql
-- Migration: 20240115_add_sftp_config.sql
-- Rollback: Run the following to undo this migration

BEGIN;

ALTER TABLE platforms DROP COLUMN IF EXISTS sftp_config;
DROP INDEX IF EXISTS idx_platforms_sftp;

COMMIT;
```

## Testing Queries

```sql
-- Create test tenant
INSERT INTO tenants (id, name) 
VALUES ('00000000-0000-0000-0000-000000000001', 'Test Tenant')
ON CONFLICT (id) DO NOTHING;

-- Set tenant context
SET app.current_tenant = '00000000-0000-0000-0000-000000000001';

-- Run your queries here...

-- Reset
RESET app.current_tenant;
```
