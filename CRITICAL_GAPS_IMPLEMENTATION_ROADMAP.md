# Critical Gaps Implementation Roadmap
## Immediate Actions for Business Continuity

**Priority**: P0 (Critical)
**Timeline**: Next 4 weeks
**Responsibility**: DevOps Team
**Success Metric**: All P0 items complete, DR drill successful

---

## Week 1: Foundation - Backup & RTO/RPO

### Objective: Protect against data loss

#### Task 1.1: Enable PostgreSQL Backups [4 hours]

**Current State**:
- No automated backups configured
- Manual backups not scheduled
- No retention policy

**Implementation**:

1. Create `terraform/backup.tf`:
```hcl
# PostgreSQL Automated Backup
resource "azurerm_postgresql_flexible_server_configuration" "backup_retention" {
  name                = "backup_retention_days"
  resource_group_name = azurerm_resource_group.main.name
  server_name         = azurerm_postgresql_flexible_server.knowledge.name
  value               = "30"
}

resource "azurerm_postgresql_flexible_server_configuration" "geo_restore" {
  name                = "geo_redundant_backup_enabled"
  resource_group_name = azurerm_resource_group.main.name
  server_name         = azurerm_postgresql_flexible_server.knowledge.name
  value               = "true"
}

# Backup vault for additional protection
resource "azurerm_data_protection_backup_vault" "db" {
  name                = "${var.project_name}-db-vault"
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  datastore_type      = "VaultStore"
  redundancy          = "GeoRedundant"
}

# Backup policy: Daily backups, 30-day retention
resource "azurerm_data_protection_backup_policy_postgresql" "db" {
  name                           = "${var.project_name}-db-policy"
  resource_group_name            = azurerm_resource_group.main.name
  vault_id                       = azurerm_data_protection_backup_vault.db.id
  backup_repeating_time_intervals = ["R/2026-02-08T02:00:00+00:00/P1D"]

  default_retention_rule {
    lifetime = "P30D"
  }
}
```

2. Apply Terraform:
```bash
cd /Users/reecefrazier/DEVOPS_NOMARK/devops-agent/terraform
terraform plan -var-file=secrets.tfvars
terraform apply -var-file=secrets.tfvars
```

3. Create manual backup script (`scripts/backup-database.sh`):
```bash
#!/bin/bash
# Manual database backup script

set -e

BACKUP_DIR="/home/devops/backups"
DB_NAME="nomark_devops"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/db_backup_$TIMESTAMP.sql.gz"

# Create backup directory
mkdir -p "$BACKUP_DIR"

echo "[$(date)] Starting database backup..."

# Backup database
PGPASSWORD="$DB_PASSWORD" pg_dump \
  -h "$DB_HOST" \
  -U "$DB_USER" \
  -d "$DB_NAME" \
  -F c | gzip > "$BACKUP_FILE"

echo "[$(date)] Backup complete: $BACKUP_FILE"

# Keep only last 7 manual backups
find "$BACKUP_DIR" -name "db_backup_*.sql.gz" -mtime +7 -delete

echo "[$(date)] Old backups cleaned up"
```

4. Schedule daily backups via cron:
```bash
# Add to crontab
0 2 * * * /home/devops/scripts/backup-database.sh >> /home/devops/logs/backup.log 2>&1
```

**Verification**:
```bash
# Check backup status
az backup job list \
  --vault-name "<vault-name>" \
  --resource-group "<rg-name>"

# Verify backup file exists
ls -lh ~/backups/db_backup_*.sql.gz
```

---

#### Task 1.2: Define RTO/RPO Targets [2 hours]

**Create `/Users/reecefrazier/DEVOPS_NOMARK/RTO_RPO_TARGETS.md`:**

```markdown
# Recovery Time & Point Objectives

## Component RTO/RPO Matrix

### Knowledge Database (PostgreSQL)
- **RTO**: 1 hour
- **RPO**: 15 minutes
- **Rationale**: Core learning system; losing hours impacts agent intelligence
- **Backup Method**: Automated daily + hourly snapshots
- **Recovery Method**: Point-in-time restore from snapshot

### PostgreSQL Data Volume
- **RTO**: 30 minutes
- **RPO**: 1 hour
- **Rationale**: Decision logs and patterns; essential but lower priority than embeddings
- **Backup Method**: Transaction log archiving every 15 min
- **Recovery Method**: Replay logs from backup + transaction logs

### Secrets (Azure Key Vault)
- **RTO**: 15 minutes (failover)
- **RPO**: Real-time (geo-redundant)
- **Rationale**: Access blocker; unavailability = complete system down
- **Backup Method**: Azure-managed geo-redundancy
- **Recovery Method**: Automatic failover

### VM Configuration
- **RTO**: 4 hours
- **RPO**: N/A (recreatable from Terraform)
- **Rationale**: Recreatable; not critical for data
- **Backup Method**: Terraform state
- **Recovery Method**: terraform apply

### Code Repositories
- **RTO**: 30 minutes (pull from GitHub)
- **RPO**: 0 minutes (Git is source of truth)
- **Rationale**: GitHub is primary; VM copy is cache
- **Backup Method**: GitHub native (we only use as secondary)
- **Recovery Method**: git clone

## Priority-Based Recovery Order
1. **P0 (Critical)**: Secrets (15 min) → Database (1 hour)
2. **P1 (High)**: VM configuration (4 hours) → Code repos (30 min)
3. **P2 (Medium)**: Knowledge base rebuild (24 hours) if needed

## Service Level Impacts

### If Database Unavailable
- **0-15 min**: Query cache holds - system operational
- **15-60 min**: Cache stale - new learning blocked, queries degraded
- **60+ min**: System degraded - manual operations required

### If VM Unavailable
- **0-4 hours**: Manual task execution via command line on backup VM
- **4+ hours**: Slack integration offline, development blocked

### If Knowledge Base Unavailable
- **0-24 hours**: Agent operates without learned patterns (baseline performance)
- **24+ hours**: Recreate from git history and task logs
```

---

#### Task 1.3: Document Recovery Procedures [3 hours]

**Create `/Users/reecefrazier/DEVOPS_NOMARK/RECOVERY_PROCEDURES.md`:**

```markdown
# Database Recovery Procedures

## Full Database Recovery from Backup

### Scenario: Database Corruption or Data Loss

**Estimated Recovery Time**: 1-2 hours
**Effort**: 1 DevOps Engineer

### Prerequisites
```bash
# Verify backup exists
ls -la ~/backups/

# Note the backup timestamp
# Example: db_backup_20260208_020000.sql.gz
```

### Step 1: Stop Active Connections (5 minutes)

```bash
# Connect to PostgreSQL
PGPASSWORD="$DB_PASSWORD" psql \
  -h "$DB_HOST" \
  -U "$DB_USER" \
  -d "postgres"

-- Terminate other connections
SELECT pg_terminate_backend(pid)
FROM pg_stat_activity
WHERE database = 'nomark_devops'
AND pid != pg_backend_pid();

-- Verify all connections closed
SELECT count(*) FROM pg_stat_activity
WHERE database = 'nomark_devops';
-- Should return: 1 (only your connection)

-- Exit
\q
```

### Step 2: Drop and Recreate Database (5 minutes)

```bash
# Drop existing database
PGPASSWORD="$DB_PASSWORD" psql \
  -h "$DB_HOST" \
  -U "$DB_USER" \
  -d "postgres" \
  -c "DROP DATABASE nomark_devops;"

# Recreate database
PGPASSWORD="$DB_PASSWORD" psql \
  -h "$DB_HOST" \
  -U "$DB_USER" \
  -d "postgres" \
  -c "CREATE DATABASE nomark_devops;"

# Enable extensions
PGPASSWORD="$DB_PASSWORD" psql \
  -h "$DB_HOST" \
  -U "$DB_USER" \
  -d "nomark_devops" << EOF
CREATE EXTENSION IF NOT EXISTS pgvector;
CREATE EXTENSION IF NOT EXISTS pg_trgm;
EOF
```

### Step 3: Restore from Backup (10-30 minutes depending on size)

```bash
# Extract and restore backup
gunzip -c ~/backups/db_backup_20260208_020000.sql.gz | \
  PGPASSWORD="$DB_PASSWORD" pg_restore \
    -h "$DB_HOST" \
    -U "$DB_USER" \
    -d "nomark_devops"

# Monitor progress
tail -f ~/logs/restore.log
```

### Step 4: Verify Recovery (5 minutes)

```bash
# Connect and verify
PGPASSWORD="$DB_PASSWORD" psql \
  -h "$DB_HOST" \
  -U "$DB_USER" \
  -d "nomark_devops" << EOF
-- Check table counts
SELECT
  schemaname,
  tablename,
  (SELECT count(*) FROM pg_stat_user_tables
   WHERE relname = tablename) as row_count
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY tablename;

-- Verify critical tables exist
\d knowledge_embeddings
\d code_patterns
\d decision_log
\d error_history

-- Sample recent records
SELECT count(*) FROM knowledge_embeddings;
SELECT count(*) FROM code_patterns;
SELECT count(*) FROM decision_log;
EOF
```

### Step 5: Restart Services (5 minutes)

```bash
# Restart devops agent
sudo systemctl restart devops-webhook

# Restart Slack bot if running
pkill -f slack-bot.py
nohup python3 ~/scripts/slack-bot.py > ~/logs/slack-bot.log 2>&1 &

# Verify services running
ps aux | grep -E "slack-bot|webhook"
```

### Step 6: Notification (2 minutes)

```bash
# Send notification to team
curl -X POST $SLACK_WEBHOOK_URL \
  -H 'Content-Type: application/json' \
  -d '{
    "text": "Database Recovery Complete",
    "attachments": [{
      "color": "good",
      "title": "Database Recovery Status",
      "text": "Database restored from backup successfully",
      "fields": [
        {"title": "Backup Time", "value": "2026-02-08 02:00:00", "short": true},
        {"title": "Recovery Time", "value": "90 minutes", "short": true},
        {"title": "Data Loss", "value": "0 records", "short": true},
        {"title": "Status", "value": "Normal Operations", "short": true}
      ]
    }]
  }'
```

---

## Point-in-Time Recovery (PITR)

### Scenario: Want to restore to specific timestamp

**Prerequisites**: Transaction log archiving enabled

```bash
# Using Azure Portal
# 1. Go to PostgreSQL Server → Backups
# 2. Click "Restore"
# 3. Select target time
# 4. Create new server with restored data

# Or via CLI
az postgres flexible-server restore \
  --resource-group <rg> \
  --name <new-server-name> \
  --source-server <original-server> \
  --restore-time "2026-02-08T01:00:00"
```

---

## Backup Restoration Testing

### Monthly Test Procedure

```bash
#!/bin/bash
# Monthly backup restoration test (1st of month)

set -e

echo "[$(date)] Starting monthly backup test..."

# 1. List available backups
echo "Available backups:"
ls -lh ~/backups/

# 2. Pick a backup older than 7 days
BACKUP_FILE=$(ls -t ~/backups/db_backup_*.sql.gz | tail -1)
echo "Testing restore from: $BACKUP_FILE"

# 3. Create test database
PGPASSWORD="$DB_PASSWORD" psql \
  -h "$DB_HOST" \
  -U "$DB_USER" \
  -d "postgres" \
  -c "DROP DATABASE IF EXISTS test_restore;"

PGPASSWORD="$DB_PASSWORD" psql \
  -h "$DB_HOST" \
  -U "$DB_USER" \
  -d "postgres" \
  -c "CREATE DATABASE test_restore;"

# 4. Restore to test database
echo "Restoring..."
gunzip -c "$BACKUP_FILE" | \
  PGPASSWORD="$DB_PASSWORD" pg_restore \
    -h "$DB_HOST" \
    -U "$DB_USER" \
    -d "test_restore"

# 5. Verify integrity
echo "Verifying..."
RECORD_COUNT=$(PGPASSWORD="$DB_PASSWORD" psql \
  -h "$DB_HOST" \
  -U "$DB_USER" \
  -d "test_restore" \
  -t \
  -c "SELECT count(*) FROM knowledge_embeddings;")

echo "Test database contains $RECORD_COUNT knowledge records"

# 6. Cleanup test database
PGPASSWORD="$DB_PASSWORD" psql \
  -h "$DB_HOST" \
  -U "$DB_USER" \
  -d "postgres" \
  -c "DROP DATABASE test_restore;"

echo "[$(date)] Backup test completed successfully"
echo "Result: PASS" > ~/logs/backup_test_$(date +%Y%m%d).log
```

Schedule monthly:
```bash
# Add to crontab (runs on 1st of month at 3 AM)
0 3 1 * * /home/devops/scripts/test-backup-restoration.sh
```
```

---

#### Task 1.4: Create Incident Severity Matrix [1 hour]

**Create `/Users/reecefrazier/DEVOPS_NOMARK/INCIDENT_SEVERITY_MATRIX.md`:**

```markdown
# Incident Severity Classification & Response Matrix

## Severity Levels

### P0 - Critical (All Systems Down)
- **Definition**: Complete system outage affecting all users
- **Duration Impact**: Every minute = $150+ in lost productivity
- **SLA Response**: 15 minutes
- **SLA Resolution**: 1 hour
- **Escalation**: Immediate (all hands on deck)
- **Examples**:
  - Database completely offline
  - All VMs down
  - Secrets completely inaccessible
  - Slack bot completely unresponsive

**Response Checklist**:
```
[ ] Page on-call immediately
[ ] Start incident war room (Slack channel)
[ ] Identify root cause (< 15 min)
[ ] Implement temporary workaround (< 30 min)
[ ] Begin full recovery (parallel with workaround)
[ ] Notify all stakeholders every 15 min
[ ] Full resolution target: 1 hour
```

### P1 - High (Partial Degradation)
- **Definition**: Significant functionality unavailable but workarounds exist
- **Duration Impact**: 10% to 50% capability loss
- **SLA Response**: 30 minutes
- **SLA Resolution**: 4 hours
- **Escalation**: Page on-call if during business hours
- **Examples**:
  - Database occasional timeouts (5-10% queries fail)
  - Slack bot slow (responses > 30 seconds)
  - One project affected
  - Learning system offline but manual operations work
  - High CPU/memory but still operational

**Response Checklist**:
```
[ ] Create incident ticket
[ ] Assess impact scope and duration
[ ] If ongoing: page on-call
[ ] Implement mitigation (< 1 hour)
[ ] Root cause analysis (parallel)
[ ] Notify affected teams every 30 min
[ ] Resolution target: 4 hours
```

### P2 - Medium (Minor Degradation)
- **Definition**: Minor functionality unavailable, workarounds easily available
- **Duration Impact**: < 10% capability loss
- **SLA Response**: 2 hours
- **SLA Resolution**: 24 hours
- **Escalation**: Create ticket, no immediate page
- **Examples**:
  - Dashboard unavailable but tasks still run
  - Specific project slow (other projects normal)
  - Logs not being archived (real-time operations fine)
  - Non-critical feature unavailable

**Response Checklist**:
```
[ ] Create incident ticket
[ ] Schedule within 24 hours
[ ] Users notified via email
[ ] Resolution target: 24 hours (can be scheduled)
```

### P3 - Low (Cosmetic/Future)
- **Definition**: No impact on operations, cosmetic issues
- **Duration Impact**: None
- **SLA Response**: 1 week
- **SLA Resolution**: No SLA
- **Examples**:
  - Documentation error
  - UI formatting issue
  - Non-urgent improvement request
  - Minor configuration

**Response Checklist**:
```
[ ] Create ticket for backlog
[ ] Schedule for future sprint
[ ] No user notification needed
```

## Detection & Escalation

### Automated Detection

```
P0 Triggers (Auto-escalate to on-call):
├── Database connection failures (> 5 consecutive)
├── VM status = "Deallocated" or "Failed"
├── Slack bot process not running
├── API response time > 30 seconds (p95)
├── Database query time > 5 seconds (p95)
└── Disk space > 90%

P1 Triggers (Alert + email):
├── Database connection slow (> 2 seconds)
├── High error rate (> 5% of requests)
├── High CPU (> 80% for > 5 min)
├── High memory (> 85% for > 5 min)
├── API response time > 5 seconds (p95)
└── Backup job failed

P2 Triggers (Alert only):
├── Non-critical service unavailable
├── Backup running (expected, no escalation)
├── Update in progress (expected)
└── Performance degradation (< 20% impact)
```

### Manual Escalation

If automated alert doesn't trigger but you suspect P0:

```
1. Check /home/devops/logs/
2. Run health check: bash ~/scripts/health-check.sh
3. If P0 confirmed:
   - Page on-call: Send emergency message
   - Start incident channel: #incident-response
   - Execute relevant runbook
```

---

## On-Call Response Matrix

| Severity | Response Time | Resolution Time | Notification | Escalation |
|----------|---------------|-----------------|--------------|------------|
| P0 | 15 minutes | 1 hour | Every 15 min | Entire team |
| P1 | 30 minutes | 4 hours | Every 30 min | On-call |
| P2 | 2 hours | 24 hours | Every 2 hours | Ticket |
| P3 | N/A | 1 week | None | Backlog |

---

## Incident Communication Template

### For All Severities

**Initial Report (within SLA Response time)**:
```
INCIDENT DETECTED: [Severity] [Component]
Time: [Timestamp]
Impact: [Brief description of what's affected]
Status: [Investigating/Mitigating/Monitoring]

Next update: [In X minutes]
```

**Status Update (every 15-30 min depending on severity)**:
```
Status Update #[N]
Component: [Component]
Status: [Investigating/Mitigating/Monitoring]

What we've done:
- [Action 1]
- [Action 2]

What we're doing:
- [Action 3]
- [Action 4]

ETA: [Estimated time to resolution]
```

**Resolution (when issue resolved)**:
```
INCIDENT RESOLVED
Component: [Component]
Root Cause: [Brief description]
Resolution: [What was done]
Duration: [Total time]
Impact: [How many users affected, for how long]

Follow-up:
- Post-mortem scheduled for [Date/Time]
- Preventive measures: [List items]
```
```

---

### Task 1.5: Establish On-Call Rotation [1 hour]

**Create `/Users/reecefrazier/DEVOPS_NOMARK/ON_CALL_SCHEDULE.md`:**

```markdown
# On-Call Rotation & Response

## Current Schedule (Update as needed)

### Primary On-Call
| Week | Engineer | Days | Contact |
|------|----------|------|---------|
| Feb 8-14 | [Name] | Mon-Sun | Slack: @[user] |
| Feb 15-21 | [Name] | Mon-Sun | Slack: @[user] |
| Feb 22-28 | [Name] | Mon-Sun | Slack: @[user] |

### Backup On-Call (escalation if primary unavailable)
| Week | Engineer | Contact |
|------|----------|---------|
| Feb 8-14 | [Name] | Slack: @[user] |
| Feb 15-21 | [Name] | Slack: @[user] |

## On-Call Responsibilities

### During Business Hours (9 AM - 5 PM AEST)
- Monitor Slack #incidents channel
- Respond to P0/P1 alerts within SLA
- Run incident response procedures
- Keep stakeholders updated

### Outside Business Hours
- Monitor automated alerts
- Be available for P0 emergencies (15 min response)
- P1/P2 can wait until morning shift

## Escalation Contacts

| Role | Name | Phone | Email |
|------|------|-------|-------|
| DevOps Lead | [Name] | [Number] | [Email] |
| Infrastructure Lead | [Name] | [Number] | [Email] |
| Emergency Contact | [Name] | [Number] | [Email] |

## On-Call Handoff

Every Monday 9 AM:
1. Outgoing on-call updates: known issues, in-progress items
2. Incoming on-call reviews: escalation procedures, recent incidents
3. Verify alert routing working
4. Review contact information
```

---

## Week 2: Response & Documentation

### Objective: Enable fast incident response

**Parallel Tasks**:
- Task 2.1: Common incident runbooks (8 hours)
- Task 2.2: DR runbook - database recovery (4 hours)
- Task 2.3: DR runbook - VM rebuild (3 hours)
- Task 2.4: Monitoring setup (6 hours)

---

### Task 2.1: Create Common Incident Runbooks [8 hours]

**Create `/Users/reecefrazier/DEVOPS_NOMARK/OPERATIONAL_RUNBOOKS/` directory with:**

#### `01_SLACK_BOT_NOT_RESPONDING.md`
```markdown
# Runbook: Slack Bot Not Responding

## Symptoms
- Commands timeout in Slack
- No response after 30+ seconds
- "Request timeout" errors

## Detection Time: < 5 minutes
## Typical Duration: 15-30 minutes

## Diagnosis (5 minutes)

### Step 1: Check if process running
```bash
ssh devops@<VM_IP>

ps aux | grep slack-bot.py
# Should show: python3 /home/devops/scripts/slack-bot.py

# If not running:
ps aux | grep slack-bot
# Shows nothing → Process crashed
```

### Step 2: Check logs for errors
```bash
tail -50 ~/logs/slack-bot.log

# Look for:
# - "Connection refused"
# - "Timeout"
# - "Authentication failed"
# - Stack traces
```

### Step 3: Check system resources
```bash
free -h
# If < 500 MB free: Memory issue

df -h
# If < 10% free: Disk issue

top -bn1 | head -20
# Check CPU usage
```

## Resolution Options

### If process crashed (not in ps output)

```bash
# 1. Check what happened
tail -100 ~/logs/slack-bot.log | grep -i error

# 2. Restart bot
cd ~/scripts
nohup python3 slack-bot.py > ~/logs/slack-bot.log 2>&1 &

# 3. Verify restarted
sleep 5
ps aux | grep slack-bot.py

# 4. Test in Slack
# @DevOps projects (should list projects)
```

**If restart fails**: Check /home/devops/.env file permissions and SLACK_BOT_TOKEN

### If memory exhausted

```bash
# 1. Find process using memory
ps aux --sort=-%mem | head -5

# 2. Free memory
sync; echo 3 > /proc/sys/vm/drop_caches

# 3. Check if bot still running
ps aux | grep slack-bot.py

# 4. If crashed, restart (see above)

# 5. Implement memory limit for bot
# Edit /etc/systemd/system/slack-bot.service:
# MemoryMax=2G
# MemoryHigh=1.5G
```

### If Slack authentication failed

```bash
# Check token validity
curl -s -X POST https://slack.com/api/auth.test \
  -H "Authorization: Bearer $SLACK_BOT_TOKEN"

# If returns "invalid_token":
# 1. Go to Slack workspace settings
# 2. Find bot token
# 3. Update .env: export SLACK_BOT_TOKEN="xoxb-..."
# 4. Restart bot
```

## Verification

```bash
# 1. Check process running
ps aux | grep slack-bot

# 2. Check logs for recent activity
tail -20 ~/logs/slack-bot.log | grep -i "listening\|started"

# 3. Test in Slack (wait 30 seconds for response)
# @DevOps projects
# Should respond with project list

# 4. Check response time
# @DevOps projects (should respond in < 5 seconds)
```

## Notification

```bash
# If fix took > 15 minutes:
curl -X POST $SLACK_WEBHOOK_URL \
  -H 'Content-Type: application/json' \
  -d '{
    "text": "Slack Bot Restored",
    "attachments": [{
      "color": "warning",
      "title": "Incident Summary",
      "text": "Slack bot was offline for 20 minutes",
      "fields": [
        {"title": "Issue", "value": "Process crash", "short": true},
        {"title": "Fix", "value": "Process restarted", "short": true},
        {"title": "Status", "value": "Operating normally", "short": true}
      ]
    }]
  }'
```

## Prevention

- Monitor process: `*/5 * * * * pgrep -f slack-bot.py || restart`
- Memory limits: Set MemoryMax=2G in systemd service
- Auto-restart: `Restart=always` in systemd service
```

#### Similar runbooks for:
- `02_DATABASE_CONNECTION_ERRORS.md` (4 hours)
- `03_TASK_EXECUTION_HANGS.md` (2 hours)
- `04_HIGH_CPU_MEMORY.md` (1 hour)
- `05_DISK_SPACE_FULL.md` (1 hour)

---

### Task 2.2: Create DR Runbooks [7 hours]

Create runbooks for:
- Database complete recovery (see Week 1, Task 1.3)
- VM rebuild from Terraform
- Knowledge base recovery from backup
- Secret recovery from Key Vault

---

### Task 2.3: Monitoring & Alerting Setup [6 hours]

**Create `terraform/monitoring.tf`:**

```hcl
# Azure Monitor for DevOps System

# Action Group for notifications
resource "azurerm_monitor_action_group" "devops" {
  name                = "${var.project_name}-alerts"
  resource_group_name = azurerm_resource_group.main.name
  short_name          = "devops"

  email_receiver {
    name           = "DevOps Team"
    email_address  = var.devops_email
  }

  email_receiver {
    name           = "On-Call"
    email_address  = var.oncall_email
  }

  webhook_receiver {
    name        = "Slack"
    service_uri = var.slack_webhook_url
  }
}

# PostgreSQL connection failures alert
resource "azurerm_monitor_metric_alert" "db_connection_failed" {
  name                = "${var.project_name}-db-connection-failed"
  resource_group_name = azurerm_resource_group.main.name
  scopes              = [azurerm_postgresql_flexible_server.knowledge.id]
  description         = "Alert when database connections fail"

  criteria {
    metric_name       = "active_connections"
    metric_namespace  = "Microsoft.DBforPostgreSQL/flexibleServers"
    aggregation       = "Average"
    operator          = "LessThan"
    threshold         = 1
    evaluation_periods = 2
    frequency          = "PT5M"
  }

  action {
    action_group_id = azurerm_monitor_action_group.devops.id
  }
}

# VM CPU high alert
resource "azurerm_monitor_metric_alert" "vm_cpu_high" {
  name                = "${var.project_name}-vm-cpu-high"
  resource_group_name = azurerm_resource_group.main.name
  scopes              = [azurerm_linux_virtual_machine.main.id]

  criteria {
    metric_name       = "Percentage CPU"
    aggregation       = "Average"
    operator          = "GreaterThan"
    threshold         = 80
    evaluation_periods = 2
    frequency          = "PT1M"
  }

  action {
    action_group_id = azurerm_monitor_action_group.devops.id
  }
}

# VM memory high alert (use Azure Monitor Agent)
resource "azurerm_monitor_metric_alert" "vm_memory_high" {
  name                = "${var.project_name}-vm-memory-high"
  resource_group_name = azurerm_resource_group.main.name
  scopes              = [azurerm_linux_virtual_machine.main.id]

  criteria {
    metric_name       = "Available Memory Bytes"
    aggregation       = "Average"
    operator          = "LessThan"
    threshold         = 536870912  # 500 MB
    evaluation_periods = 2
    frequency          = "PT1M"
  }

  action {
    action_group_id = azurerm_monitor_action_group.devops.id
  }
}

# Disk space alert
resource "azurerm_monitor_metric_alert" "vm_disk_full" {
  name                = "${var.project_name}-vm-disk-full"
  resource_group_name = azurerm_resource_group.main.name
  scopes              = [azurerm_linux_virtual_machine.main.id]

  criteria {
    metric_name       = "OS Disk Used Percentage"
    aggregation       = "Average"
    operator          = "GreaterThan"
    threshold         = 90
    evaluation_periods = 1
    frequency          = "PT5M"
  }

  action {
    action_group_id = azurerm_monitor_action_group.devops.id
  }
}

# Query rule for Slack bot process check (requires Azure Monitor Agent)
resource "azurerm_monitor_scheduled_query_rules_alert_v2" "slack_bot_process" {
  name                = "${var.project_name}-slack-bot-running"
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location

  scopes = [azurerm_log_analytics_workspace.devops.id]

  description       = "Alert if Slack bot process not running"
  enabled           = true
  evaluation_frequency = "PT5M"
  window_duration   = "PT5M"
  severity          = 2

  criteria {
    metric_measurement {
      column  = "Computer"
      aggregation = "Count"
    }

    query = <<-QUERY
    let threshold = 0;
    Perf
    | where ObjectName == "Processes" and CounterName == "% Processor Time"
    | where InstanceName contains "slack-bot"
    | summarize ProcessCount = count() by Computer
    | where ProcessCount < threshold
    QUERY

    operator = "LessThan"
    threshold = 1
    failing_periods = 1
    metric_trigger {
      operator = "GreaterThan"
      threshold = 0
      metric_trigger_type = "Consecutive"
      metric_trigger_column = "ProcessCount"
    }
  }

  action {
    action_groups = [azurerm_monitor_action_group.devops.id]
  }
}

# Log Analytics Workspace for detailed logging
resource "azurerm_log_analytics_workspace" "devops" {
  name                = "${var.project_name}-logs"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  sku                 = "PerGB2018"
  retention_in_days   = 30

  tags = var.tags
}
```

---

## Week 3: Compliance & Access Control

**Parallel Tasks**:
- Task 3.1: Audit trail setup (8 hours)
- Task 3.2: Access control policies (6 hours)
- Task 3.3: Compliance documentation (5 hours)

---

## Week 4: Validation & Testing

**Tasks**:
- Task 4.1: First DR drill (complete system recovery test)
- Task 4.2: Incident response testing
- Task 4.3: Access control verification
- Task 4.4: SLA tracking setup

---

## Success Metrics

### By End of Week 1
✅ Database backups automated and tested
✅ RTO/RPO targets defined
✅ Recovery procedures documented
✅ Incident severity matrix created
✅ On-call rotation established

### By End of Week 2
✅ Common incident runbooks created (5+)
✅ DR runbooks created and tested
✅ Monitoring and alerting configured
✅ Alerts routing to on-call
✅ First alert triggered and verified

### By End of Week 3
✅ Audit trail logging configured
✅ Access control policies documented
✅ Compliance matrix completed
✅ Data classification defined
✅ Secrets management audit completed

### By End of Week 4
✅ Full DR drill completed successfully
✅ Recovery time measured vs. RTO
✅ All runbooks validated in test
✅ Access controls enforced
✅ SLA metrics being tracked

---

## File Locations & Templates

All files created in `/Users/reecefrazier/DEVOPS_NOMARK/`:

```
├── RTO_RPO_TARGETS.md
├── RECOVERY_PROCEDURES.md
├── INCIDENT_SEVERITY_MATRIX.md
├── ON_CALL_SCHEDULE.md
├── OPERATIONAL_RUNBOOKS/
│   ├── 01_SLACK_BOT_NOT_RESPONDING.md
│   ├── 02_DATABASE_CONNECTION_ERRORS.md
│   ├── 03_TASK_EXECUTION_HANGS.md
│   ├── 04_HIGH_CPU_MEMORY.md
│   ├── 05_DISK_SPACE_FULL.md
│   ├── 06_N8N_WORKFLOW_HANGS.md
│   ├── 07_AZURE_LIMITS_HIT.md
│   ├── DR_DATABASE_FULL_RECOVERY.md
│   ├── DR_VM_REBUILD.md
│   └── DR_COMPLETE_SYSTEM_RECOVERY.md
├── devops-agent/terraform/
│   ├── backup.tf (NEW)
│   ├── monitoring.tf (NEW)
│   └── main.tf (existing, updated)
└── scripts/
    ├── backup-database.sh (NEW)
    ├── test-backup-restoration.sh (NEW)
    ├── health-check.sh (existing, enhanced)
    └── incident-response.sh (NEW)
```

---

## Next Steps

1. **This Week**: Complete Week 1 tasks
2. **Week 2**: Implement operational runbooks
3. **Week 3**: Set up compliance controls
4. **Week 4**: Validate with DR drill

Progress tracking: `/Users/reecefrazier/DEVOPS_NOMARK/IMPLEMENTATION_PROGRESS.md` (create weekly)

---

**Owner**: DevOps Team
**Target Completion**: March 8, 2026
**Review Date**: Weekly (every Monday)
**Success Criteria**: All critical gaps resolved, DR drill successful
