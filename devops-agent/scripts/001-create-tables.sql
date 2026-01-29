-- ============================================================================
-- DevOps Agent - Database Schema
-- ============================================================================
-- Run this migration against your existing n8n/FlowMetrics database
-- or create a new database for the DevOps Agent
-- ============================================================================

-- Task queue table
CREATE TABLE IF NOT EXISTS dev_tasks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Task configuration
    prd_name TEXT NOT NULL,                    -- e.g., 'platform-wizard', 'file-ingestion'
    story_count INTEGER DEFAULT 5,
    branch TEXT DEFAULT 'main',
    repo_url TEXT,                             -- Optional: override default repo
    
    -- Status tracking
    status TEXT DEFAULT 'queued',              -- queued, starting, running, paused, completed, error
    current_story TEXT,                        -- Current story ID being worked on
    stories_completed INTEGER DEFAULT 0,
    error_message TEXT,
    
    -- Timing
    created_at TIMESTAMPTZ DEFAULT NOW(),
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    last_update TIMESTAMPTZ DEFAULT NOW(),
    
    -- User context
    requested_by TEXT,
    slack_channel_id TEXT,
    slack_response_url TEXT,
    slack_thread_ts TEXT,                      -- For threaded updates
    
    -- Metadata
    metadata JSONB DEFAULT '{}'::jsonb
);

-- Index for efficient queries
CREATE INDEX IF NOT EXISTS idx_dev_tasks_status ON dev_tasks(status);
CREATE INDEX IF NOT EXISTS idx_dev_tasks_created ON dev_tasks(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_dev_tasks_prd ON dev_tasks(prd_name);

-- Task logs table (for detailed progress)
CREATE TABLE IF NOT EXISTS dev_task_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id UUID REFERENCES dev_tasks(id) ON DELETE CASCADE,
    timestamp TIMESTAMPTZ DEFAULT NOW(),
    level TEXT DEFAULT 'info',                 -- info, warn, error, debug
    message TEXT NOT NULL,
    story_id TEXT,
    metadata JSONB DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS idx_dev_task_logs_task ON dev_task_logs(task_id);
CREATE INDEX IF NOT EXISTS idx_dev_task_logs_timestamp ON dev_task_logs(timestamp DESC);

-- PRD configurations (optional - for storing repo/path defaults per PRD)
CREATE TABLE IF NOT EXISTS dev_prd_configs (
    prd_name TEXT PRIMARY KEY,
    repo_url TEXT NOT NULL,
    default_branch TEXT DEFAULT 'main',
    prd_path TEXT DEFAULT 'ralph/scripts/ralph',
    description TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Insert some default PRD configs (customize for your projects)
INSERT INTO dev_prd_configs (prd_name, repo_url, prd_path, description)
VALUES 
    ('platform-wizard', 'https://github.com/YOUR_ORG/FlowMetrics.git', 'ralph/ralph-platform-wizard/scripts/ralph', 'Platform wizard feature'),
    ('file-ingestion', 'https://github.com/YOUR_ORG/FlowMetrics.git', 'ralph/ralph-file-ingestion/scripts/ralph', 'SFTP file ingestion feature')
ON CONFLICT (prd_name) DO NOTHING;

-- View for active tasks with PRD config
CREATE OR REPLACE VIEW dev_active_tasks AS
SELECT 
    t.*,
    COALESCE(t.repo_url, c.repo_url) AS effective_repo_url,
    COALESCE(c.prd_path, 'ralph/scripts/ralph') AS effective_prd_path,
    EXTRACT(EPOCH FROM (NOW() - t.started_at)) / 60 AS running_minutes
FROM dev_tasks t
LEFT JOIN dev_prd_configs c ON t.prd_name = c.prd_name
WHERE t.status IN ('queued', 'starting', 'running');

-- Function to clean up old completed tasks (keep last 100)
CREATE OR REPLACE FUNCTION cleanup_old_tasks() RETURNS void AS $$
BEGIN
    DELETE FROM dev_tasks 
    WHERE status IN ('completed', 'error') 
    AND id NOT IN (
        SELECT id FROM dev_tasks 
        WHERE status IN ('completed', 'error')
        ORDER BY completed_at DESC 
        LIMIT 100
    );
END;
$$ LANGUAGE plpgsql;

-- Comments
COMMENT ON TABLE dev_tasks IS 'Queue of autonomous development tasks for the DevOps Agent';
COMMENT ON TABLE dev_task_logs IS 'Detailed logs for task execution';
COMMENT ON TABLE dev_prd_configs IS 'Default configurations for each PRD type';
