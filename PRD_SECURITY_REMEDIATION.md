# Product Requirements Document: Security Remediation Implementation

## Document Information
- **PRD ID**: SEC-REM-001
- **Version**: 1.0
- **Created**: 2026-02-08
- **Priority**: P0 (Critical)
- **Estimated Effort**: 58 hours over 4 weeks
- **Target Completion**: 2026-03-08

---

## Executive Summary

### Problem Statement
Forensic security audit revealed critical vulnerabilities in the NOMARK DevOps infrastructure:
- **16/100 overall security score** (CRITICAL FAILURE)
- Exposed credentials in version control (6 secrets compromised)
- SQL injection vulnerabilities allowing database takeover
- Network exposed to internet (SSH, PostgreSQL, webhook server)
- Zero automated backups (complete data loss risk)
- No CI/CD pipeline or automated testing
- No monitoring or incident detection

### Solution Overview
Implement cost-optimized security hardening across 4 phases:
1. **Phase 1 (6h)**: Eliminate active security threats - $0/month
2. **Phase 2 (16h)**: Essential infrastructure - $35/month
3. **Phase 3 (24h)**: CI/CD & automated testing - $0/month
4. **Phase 4 (12h)**: Incident response procedures - $0/month

### Success Metrics
- Security score: 16/100 → 70/100 (+338%)
- Monthly cost: $35 (vs $520 for full DR stack)
- Risk reduction: 95%
- Zero exposed credentials
- 60%+ test coverage
- <5 minute incident recovery

---

## User Stories & Acceptance Criteria

### Epic 1: Eliminate Active Security Threats (Phase 1)

#### Story 1.1: Rotate All Exposed Credentials
**Priority**: P0 - CRITICAL
**Effort**: 2 hours

**As a** security engineer
**I want to** rotate all 6 exposed credentials and remove them from git history
**So that** attackers cannot compromise our systems using leaked secrets

**Acceptance Criteria**:
- [ ] All 6 credentials rotated (Anthropic, GitHub, Database, Linear, Slack Bot, Slack Signing Secret)
- [ ] New credentials stored in Azure Key Vault
- [ ] Old credentials revoked in all services
- [ ] .env file removed from git history using git-filter-repo
- [ ] .env added to .gitignore
- [ ] Verified old credentials no longer work

**Technical Details**:
```bash
# Credentials to rotate:
1. ANTHROPIC_API_KEY (https://console.anthropic.com/settings/keys)
2. GITHUB_TOKEN (https://github.com/settings/tokens)
3. DATABASE_PASSWORD (Azure PostgreSQL admin password)
4. LINEAR_API_KEY (https://linear.app/settings/api)
5. SLACK_BOT_TOKEN (https://api.slack.com/apps)
6. SLACK_SIGNING_SECRET (https://api.slack.com/apps)

# Storage: Azure Key Vault (nomark-kv-*)
# Git cleanup: git filter-repo --invert-paths --path .env
```

**Risks**:
- Brief service interruption during credential rotation (~5 minutes)
- Git force push required (coordinate with team)

---

#### Story 1.2: Fix SQL Injection Vulnerabilities
**Priority**: P0 - CRITICAL
**Effort**: 1 hour

**As a** security engineer
**I want to** fix SQL injection vulnerabilities in supabase_tools.py
**So that** attackers cannot execute arbitrary SQL or steal database data

**Acceptance Criteria**:
- [ ] `list_tables()` function uses whitelist validation (no string concatenation)
- [ ] `get_table_schema()` function uses regex validation for table names
- [ ] Unit tests added to verify SQL injection is blocked
- [ ] All existing functionality still works
- [ ] Code review completed and approved

**Technical Details**:
```python
# Files to modify:
- devops-mcp/devops_mcp/tools/supabase_tools.py (lines 335-358)

# Changes:
1. Replace f-string queries with parameterized queries or PostgREST filters
2. Add whitelist validation for schema names: ['public', 'auth', 'storage', 'extensions']
3. Add regex validation for table names: ^[a-zA-Z_][a-zA-Z0-9_]*$
4. Raise ValueError for invalid inputs
5. Add unit tests in tests/test_supabase_tools.py
```

**Test Cases**:
```python
# Should block:
list_tables("public'; DROP TABLE users; --")  # SQL injection
get_table_schema("users'; DROP TABLE --")      # SQL injection
get_table_schema("../../../etc/passwd")        # Path traversal

# Should allow:
list_tables("public")                          # Valid
get_table_schema("dev_tasks")                  # Valid
```

---

#### Story 1.3: Restrict SSH Access to Specific IPs
**Priority**: P0 - CRITICAL
**Effort**: 30 minutes

**As a** security engineer
**I want to** restrict SSH access to specific IP addresses only
**So that** attackers cannot brute-force SSH credentials

**Acceptance Criteria**:
- [ ] Terraform variable `allowed_ssh_ips` requires explicit configuration
- [ ] Validation prevents 0.0.0.0/0 from being used
- [ ] NSG rule updated to only allow specified IPs
- [ ] Terraform apply successful
- [ ] Verified SSH access works from allowed IPs
- [ ] Verified SSH access blocked from other IPs

**Technical Details**:
```hcl
# File: devops-agent/terraform/main.tf

# Update variable with validation:
variable "allowed_ssh_ips" {
  type        = list(string)
  default     = []
  description = "IP addresses allowed to SSH (must be specified)"

  validation {
    condition     = length(var.allowed_ssh_ips) > 0 && !contains(var.allowed_ssh_ips, "0.0.0.0/0")
    error_message = "SSH access must be restricted to specific IPs. 0.0.0.0/0 is not allowed."
  }
}

# Apply with:
terraform apply -var='allowed_ssh_ips=["YOUR_IP/32"]'
```

**Configuration Required**:
- User must provide their home IP and office IP
- Format: CIDR notation (e.g., "203.123.45.67/32")

---

#### Story 1.4: Restrict PostgreSQL to Private Access
**Priority**: P0 - CRITICAL
**Effort**: 30 minutes

**As a** security engineer
**I want to** restrict PostgreSQL access to only the DevOps VM
**So that** database cannot be accessed from the public internet

**Acceptance Criteria**:
- [ ] Removed firewall rule allowing 0.0.0.0/0 (AllowAllAzureServices)
- [ ] Added firewall rule for DevOps VM IP only
- [ ] Added firewall rule for admin management IP
- [ ] Verified application can still connect from VM
- [ ] Verified database connection fails from unauthorized IPs

**Technical Details**:
```bash
# Commands:
1. Remove public access rule
2. Get VM public IP
3. Add VM-specific firewall rule
4. Add admin management IP
5. Test connectivity from VM
6. Test block from external IP
```

---

#### Story 1.5: Secure Webhook Endpoint
**Priority**: P0 - CRITICAL
**Effort**: 1 hour

**As a** security engineer
**I want to** add authentication to the webhook endpoint on port 9000
**So that** unauthorized requests cannot trigger webhook actions

**Acceptance Criteria**:
- [ ] HMAC signature verification implemented
- [ ] Webhook secret generated and stored in Key Vault
- [ ] n8n configured to send HMAC signature header
- [ ] Requests without valid signature return 401
- [ ] Existing n8n workflows still work with authentication
- [ ] Alternative: Port 9000 blocked in NSG if webhook not needed

**Technical Details**:
```python
# Option 1: Add HMAC authentication
- Generate WEBHOOK_SECRET
- Store in Key Vault
- Implement verify_webhook_signature() function
- Verify X-N8N-Signature header
- Return 401 if invalid

# Option 2: Block port 9000 entirely
az network nsg rule delete --name Webhook ...
```

---

#### Story 1.6: Enable HTTPS-Only on Azure Function
**Priority**: P1 - HIGH
**Effort**: 15 minutes

**As a** security engineer
**I want to** enforce HTTPS-only on the VM starter Azure Function
**So that** Slack tokens cannot be intercepted via HTTP

**Acceptance Criteria**:
- [ ] Azure Function httpsOnly set to true
- [ ] Minimum TLS version set to 1.2
- [ ] HTTP requests automatically redirect to HTTPS
- [ ] Slack bot can still trigger VM start successfully

**Technical Details**:
```bash
az functionapp update --name nomark-vm-starter --set httpsOnly=true
az functionapp config set --min-tls-version 1.2
```

---

### Epic 2: Essential Infrastructure (Phase 2)

#### Story 2.1: Enable Application Insights Monitoring
**Priority**: P1 - HIGH
**Effort**: 2 hours

**As a** DevOps engineer
**I want to** enable Application Insights on all services
**So that** I can monitor performance, errors, and usage patterns

**Acceptance Criteria**:
- [ ] Application Insights instance created
- [ ] Instrumentation key stored in Key Vault
- [ ] Python applications instrumented with opencensus-ext-azure
- [ ] Custom metrics tracked (task count, task duration)
- [ ] Logs flowing to Application Insights
- [ ] Basic queries working in Log Analytics

**Technical Details**:
```python
# Dependencies:
opencensus-ext-azure==1.1.13
opencensus-ext-flask==0.8.2

# Metrics to track:
- tasks_started (count)
- tasks_completed (count)
- tasks_failed (count)
- task_duration_ms (distribution)
- api_calls (count by service)
```

**Cost**: ~$10/month (free tier includes 5GB/month)

---

#### Story 2.2: Configure Monitoring Alerts
**Priority**: P1 - HIGH
**Effort**: 2 hours

**As a** DevOps engineer
**I want to** receive alerts for critical system issues
**So that** I can respond before users are impacted

**Acceptance Criteria**:
- [ ] Alert: VM CPU > 80% for 5 minutes
- [ ] Alert: Database connection failure
- [ ] Alert: Disk space < 10%
- [ ] Alert: VM stopped/deallocated
- [ ] Action group created with email and SMS
- [ ] Test alerts successfully delivered
- [ ] Alert runbook links included

**Technical Details**:
```bash
# Alerts to create:
1. VM High CPU (threshold: 80%, window: 5min)
2. Database Connection Failure (active_connections < 1)
3. VM Low Disk Space (available < 10GB)
4. VM Power State != Running

# Action group:
- Email: admin@example.com
- SMS: +61 XXX XXX XXX
```

**Configuration Required**:
- Email address for alerts
- SMS number for critical alerts (optional)

---

#### Story 2.3: Enable Database Backups
**Priority**: P0 - CRITICAL
**Effort**: 2 hours

**As a** DevOps engineer
**I want to** enable automated daily database backups
**So that** we can recover from data corruption or accidental deletion

**Acceptance Criteria**:
- [ ] PostgreSQL automated backups enabled (7-day retention)
- [ ] Manual backup script created and tested
- [ ] Backup uploaded to Azure Blob Storage
- [ ] Cron job scheduled for daily backups (2 AM)
- [ ] Backup monitoring alert configured
- [ ] Successful test restore completed
- [ ] Documented restore procedure

**Technical Details**:
```bash
# Azure automated backups (free):
az postgres flexible-server update \
  --backup-retention 7 \
  --geo-redundant-backup Disabled  # Local only to save cost

# Manual backup script:
- pg_dump with compression
- Upload to Azure Blob Storage (backups container)
- Keep last 7 local backups
- Cron: 0 2 * * *

# Storage cost: ~$10/month for 100GB
```

**Recovery Testing**:
- Restore to test database
- Verify data integrity
- Document recovery time (target: <20 minutes)

---

#### Story 2.4: Add Database Performance Indexes
**Priority**: P1 - HIGH
**Effort**: 1 hour

**As a** backend developer
**I want to** add essential database indexes
**So that** queries run faster and reduce database load

**Acceptance Criteria**:
- [ ] Composite index on dev_tasks(status, created_at)
- [ ] Index on dev_tasks(slack_channel_id, slack_thread_ts)
- [ ] Index on dev_task_logs(task_id, timestamp)
- [ ] All indexes created with CONCURRENTLY (no downtime)
- [ ] Query performance improved by >10x
- [ ] ANALYZE run on all tables

**Technical Details**:
```sql
-- File: devops-agent/scripts/002-essential-indexes.sql

CREATE INDEX CONCURRENTLY idx_dev_tasks_status_created
ON dev_tasks(status, created_at DESC)
WHERE status IN ('queued', 'running', 'starting');

CREATE INDEX CONCURRENTLY idx_dev_tasks_slack_thread
ON dev_tasks(slack_channel_id, slack_thread_ts)
WHERE slack_thread_ts IS NOT NULL;

CREATE INDEX CONCURRENTLY idx_dev_task_logs_task_timestamp
ON dev_task_logs(task_id, timestamp DESC);

ANALYZE dev_tasks;
ANALYZE dev_task_logs;
```

**Performance Target**:
- Task list query: <50ms (from ~500ms)
- Slack thread lookup: <10ms (from ~100ms)

---

#### Story 2.5: Deploy Redis Cache
**Priority**: P2 - MEDIUM
**Effort**: 2 hours

**As a** backend developer
**I want to** add Redis caching for expensive queries
**So that** database load is reduced and response times improve

**Acceptance Criteria**:
- [ ] Redis Basic C0 instance created ($10/month)
- [ ] Connection string stored in Key Vault
- [ ] Cache manager class implemented
- [ ] Cached decorator for expensive functions
- [ ] list_tables() and get_table_schema() use cache (TTL: 5-10min)
- [ ] Cache invalidation on data mutations
- [ ] Graceful fallback if Redis unavailable

**Technical Details**:
```python
# File: devops-mcp/devops_mcp/cache.py

class SimpleCache:
    def __init__(self):
        self.redis = redis.from_url(os.environ.get("REDIS_URL"))

    def get(self, key): ...
    def set(self, key, value, ttl=300): ...
    def delete(self, pattern): ...

@cached(ttl=300)
async def list_tables(schema="public"):
    # Cached for 5 minutes
```

**Cost**: $10/month (Basic C0 - 250MB)

---

#### Story 2.6: Implement Audit Logging
**Priority**: P1 - HIGH
**Effort**: 3 hours

**As a** compliance officer
**I want to** track all data changes in an audit log
**So that** we can investigate incidents and meet compliance requirements

**Acceptance Criteria**:
- [ ] audit_logs table created
- [ ] Audit trigger function captures INSERT/UPDATE/DELETE
- [ ] Triggers added to dev_tasks and dev_prd_configs tables
- [ ] Audit log includes: timestamp, user_id, operation, old_values, new_values
- [ ] Indexes on timestamp and user_id for fast queries
- [ ] Test audit logging with sample operations
- [ ] Documented audit log retention (90 days)

**Technical Details**:
```sql
-- File: devops-agent/scripts/003-basic-audit-logging.sql

CREATE TABLE audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    timestamp TIMESTAMPTZ DEFAULT NOW(),
    user_id TEXT,
    table_name TEXT NOT NULL,
    operation TEXT NOT NULL,
    record_id UUID,
    changes JSONB
);

CREATE FUNCTION simple_audit_trigger() RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO audit_logs ...
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER audit_dev_tasks ...
```

**Compliance**: Supports SOC 2, GDPR audit requirements

---

#### Story 2.7: Migrate Secrets to Key Vault
**Priority**: P0 - CRITICAL
**Effort**: 4 hours

**As a** security engineer
**I want to** migrate all application secrets to Azure Key Vault
**So that** secrets are centrally managed and automatically rotated

**Acceptance Criteria**:
- [ ] SecretsManager class implemented with Key Vault client
- [ ] All applications use get_secret() instead of os.environ
- [ ] VM managed identity granted Key Vault access
- [ ] Local caching of secrets (reduce API calls)
- [ ] Fallback to environment variables for local development
- [ ] All 6 secrets migrated to Key Vault
- [ ] No secrets in environment variables or .env files
- [ ] Verified application works with Key Vault

**Technical Details**:
```python
# File: devops-mcp/devops_mcp/secrets.py

from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient

class SecretsManager:
    def __init__(self):
        credential = DefaultAzureCredential()
        self.client = SecretClient(vault_url=vault_url, credential=credential)
        self._cache = {}

    def get_secret(self, name):
        if name in self._cache:
            return self._cache[name]
        secret = self.client.get_secret(name)
        self._cache[name] = secret.value
        return secret.value

# Usage:
# OLD: os.environ.get("ANTHROPIC_API_KEY")
# NEW: get_secret("ANTHROPIC-API-KEY")
```

**Migration Path**:
1. Create SecretsManager class
2. Update one service at a time
3. Test each service
4. Remove environment variables

---

### Epic 3: CI/CD & Automated Testing (Phase 3)

#### Story 3.1: Create GitHub Actions CI/CD Pipeline
**Priority**: P1 - HIGH
**Effort**: 4 hours

**As a** DevOps engineer
**I want to** automate build, test, and deployment processes
**So that** code changes are validated before reaching production

**Acceptance Criteria**:
- [ ] CI workflow runs on every push and PR
- [ ] Lint job: Black, Flake8 formatting checks
- [ ] Security job: Bandit, Safety dependency scanning
- [ ] Test job: Pytest with coverage report (when tests exist)
- [ ] Deploy job: Automated deployment to production (main branch only)
- [ ] Manual approval required for production deployment
- [ ] Slack notification on deployment success/failure
- [ ] All jobs pass on main branch

**Technical Details**:
```yaml
# File: .github/workflows/ci-cd.yml

jobs:
  lint-and-scan:
    - Black, Flake8, Bandit, Safety

  test:
    - pytest with coverage
    - Minimum 60% coverage

  deploy-production:
    - Azure login
    - Deploy to VM via SSH
    - Health check verification
    - Slack notification
```

**Cost**: Free (GitHub Actions 2000 minutes/month free for private repos)

---

#### Story 3.2: Enable Branch Protection
**Priority**: P1 - HIGH
**Effort**: 30 minutes

**As a** engineering manager
**I want to** enforce code review and CI checks before merging
**So that** only validated code reaches production

**Acceptance Criteria**:
- [ ] Branch protection enabled on 'main' branch
- [ ] Require 1 pull request approval before merging
- [ ] Require status checks to pass (lint-and-scan, test)
- [ ] Require branches to be up to date
- [ ] Include administrators in restrictions
- [ ] Prevent force pushes to main
- [ ] Prevent deletion of main branch
- [ ] Test: Cannot merge PR without approval
- [ ] Test: Cannot merge PR with failing tests

**Configuration**:
```
Settings → Branches → Add rule for 'main':
✅ Require pull request reviews (1 approval)
✅ Require status checks to pass
   - lint-and-scan
   - test
✅ Require branches up to date
✅ Include administrators
❌ Allow force pushes
❌ Allow deletions
```

---

#### Story 3.3: Enable Dependabot Security Updates
**Priority**: P1 - HIGH
**Effort**: 15 minutes

**As a** security engineer
**I want to** automatically detect vulnerable dependencies
**So that** security patches are applied promptly

**Acceptance Criteria**:
- [ ] Dependabot.yml configuration created
- [ ] Weekly scans for Python dependencies
- [ ] Weekly scans for GitHub Actions
- [ ] PRs automatically created for security updates
- [ ] PRs labeled with "dependencies" and "security"
- [ ] Open PR limit set to 5
- [ ] Test: Dependabot creates PR for known vulnerable package

**Technical Details**:
```yaml
# File: .github/dependabot.yml

version: 2
updates:
  - package-ecosystem: "pip"
    directory: "/"
    schedule:
      interval: "weekly"
    open-pull-requests-limit: 5
    labels: ["dependencies", "security"]
```

**Cost**: Free (GitHub Dependabot included)

---

#### Story 3.4: Enable CodeQL Security Scanning
**Priority**: P1 - HIGH
**Effort**: 30 minutes

**As a** security engineer
**I want to** automatically scan code for security vulnerabilities
**So that** common vulnerabilities are caught before deployment

**Acceptance Criteria**:
- [ ] CodeQL workflow configured for Python and JavaScript
- [ ] Scans run on push to main and all PRs
- [ ] Weekly scheduled scans
- [ ] Security alerts appear in GitHub Security tab
- [ ] Test: CodeQL detects SQL injection test case
- [ ] Test: CodeQL detects hardcoded secret test case

**Technical Details**:
```yaml
# File: .github/workflows/codeql-analysis.yml

jobs:
  analyze:
    strategy:
      matrix:
        language: ['python', 'javascript']
    steps:
      - Initialize CodeQL
      - Autobuild
      - Perform CodeQL Analysis
```

**Cost**: Free for public repos; free for private repos (GitHub Advanced Security on request)

---

#### Story 3.5: Add Unit Tests (60% Coverage)
**Priority**: P1 - HIGH
**Effort**: 8 hours

**As a** software engineer
**I want to** add comprehensive unit tests
**So that** bugs are caught before reaching production

**Acceptance Criteria**:
- [ ] pytest framework configured
- [ ] Tests for SQL injection prevention (supabase_tools.py)
- [ ] Tests for secrets management (secrets.py)
- [ ] Tests for cache functionality (cache.py)
- [ ] Tests for webhook authentication
- [ ] Overall code coverage ≥60%
- [ ] All tests pass in CI pipeline
- [ ] Coverage report generated in HTML

**Test Coverage Targets**:
```
supabase_tools.py:     80% (security-critical)
secrets.py:            80% (security-critical)
cache.py:              70%
webhook handlers:      70%
utility functions:     60%
Overall:               60%
```

**Technical Details**:
```python
# File: tests/test_supabase_tools.py

def test_list_tables_validates_schema():
    # Valid schema should work
    result = supabase_tools.list_tables("public")
    assert "data" in result

    # Invalid schema should raise ValueError
    with pytest.raises(ValueError):
        supabase_tools.list_tables("'; DROP TABLE users; --")

def test_get_table_schema_prevents_sql_injection():
    # Test various injection attempts
    with pytest.raises(ValueError):
        supabase_tools.get_table_schema("users'; DROP TABLE --")
    with pytest.raises(ValueError):
        supabase_tools.get_table_schema("../../../etc/passwd")
```

**Pytest Configuration**:
```ini
# pytest.ini
[pytest]
testpaths = tests
addopts = -v --cov=. --cov-report=term-missing --cov-report=html --cov-fail-under=60
```

---

#### Story 3.6: Add Pre-commit Hooks
**Priority**: P2 - MEDIUM
**Effort**: 1 hour

**As a** software engineer
**I want to** automatically check code quality before committing
**So that** I catch issues before pushing to remote

**Acceptance Criteria**:
- [ ] pre-commit framework installed
- [ ] Hooks configured: trailing-whitespace, end-of-file-fixer, check-yaml, detect-private-key
- [ ] Black formatter enforced
- [ ] Flake8 linting enforced
- [ ] Bandit security scanning enforced
- [ ] detect-secrets with baseline generated
- [ ] All team members install hooks (git hook install instructions in README)
- [ ] Test: Commit with trailing whitespace is rejected
- [ ] Test: Commit with exposed secret is rejected

**Technical Details**:
```yaml
# File: .pre-commit-config.yaml

repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    hooks:
      - trailing-whitespace
      - end-of-file-fixer
      - check-yaml
      - check-added-large-files
      - detect-private-key

  - repo: https://github.com/psf/black
    hooks:
      - black

  - repo: https://github.com/Yelp/detect-secrets
    hooks:
      - detect-secrets
```

**Installation**:
```bash
pip install pre-commit
pre-commit install
detect-secrets scan > .secrets.baseline
```

---

### Epic 4: Incident Response Procedures (Phase 4)

#### Story 4.1: Create Incident Response Runbooks
**Priority**: P1 - HIGH
**Effort**: 6 hours

**As an** on-call engineer
**I want to** have step-by-step runbooks for common incidents
**So that** I can quickly resolve issues without escalation

**Acceptance Criteria**:
- [ ] Runbook 1: Service Outage / VM Unresponsive
- [ ] Runbook 2: Database Connection Failure
- [ ] Runbook 3: Slack Bot Not Responding
- [ ] Runbook 4: Claude API Errors / Rate Limiting
- [ ] Runbook 5: Disk Space Critical
- [ ] Each runbook includes: symptoms, diagnosis steps, resolution steps, escalation criteria
- [ ] All commands tested and verified
- [ ] Runbooks stored in OPERATIONAL_RUNBOOKS/ directory
- [ ] Links added to monitoring alerts

**Runbook Template**:
```markdown
# Runbook: [Incident Type]
## Severity: [P0/P1/P2/P3]
## SLA: [Response time, Resolution target]

## Symptoms
- [Observable issue 1]
- [Observable issue 2]

## Diagnosis Steps
1. [Check X]
2. [Check Y]

## Resolution Steps
1. [Action 1 with command]
2. [Action 2 with command]

## Post-Incident
- [ ] Update incident log
- [ ] Document root cause
- [ ] Create prevention task

## Escalation
[When to escalate and to whom]
```

**Testing**: Each runbook tested in staging/non-prod environment

---

#### Story 4.2: Document On-Call Procedures
**Priority**: P1 - HIGH
**Effort**: 2 hours

**As an** engineering manager
**I want to** define on-call responsibilities and procedures
**So that** incidents are handled consistently and efficiently

**Acceptance Criteria**:
- [ ] On-call schedule defined (weekly rotation)
- [ ] Incident severity classification (P0-P3)
- [ ] Response SLAs documented (P0: 15min, P1: 30min, P2: 2hr, P3: next day)
- [ ] Alert channels documented (Azure Monitor, App Insights, Slack)
- [ ] Escalation path documented
- [ ] On-call responsibilities checklist
- [ ] Handoff checklist for rotation changes
- [ ] Emergency contact information
- [ ] Procedures stored in ON_CALL_PROCEDURES.md

**Severity Classification**:
```
P0 - Critical:
- Complete service outage
- Data loss occurring
- Security breach
- Response: 15min, Resolution: 1hr

P1 - High:
- Partial degradation
- Backup failure
- Critical alerts
- Response: 30min, Resolution: 4hr

P2 - Medium:
- Minor issues
- Non-critical alerts
- Response: 2hr, Resolution: 1 day

P3 - Low:
- Documentation
- Feature requests
- Response: Best effort
```

---

#### Story 4.3: Create Database Recovery Procedures
**Priority**: P0 - CRITICAL
**Effort**: 4 hours

**As a** database administrator
**I want to** documented and tested recovery procedures
**So that** I can restore data quickly after corruption or deletion

**Acceptance Criteria**:
- [ ] Procedure 1: Restore from Azure automated backup (PITR)
- [ ] Procedure 2: Restore from manual backup (daily snapshots)
- [ ] Procedure 3: Recover from VM complete failure
- [ ] Each procedure includes: estimated recovery time, step-by-step commands, verification steps
- [ ] All procedures tested in non-production environment
- [ ] Recovery time measured and documented
- [ ] Procedures stored in RECOVERY_PROCEDURES.md
- [ ] RTO/RPO documented (RTO: 30min, RPO: 24hr)

**Recovery Scenarios**:
```
Scenario 1: Point-in-time restore (last 7 days)
- Recovery Time: 15-30 minutes
- Steps: az postgres flexible-server restore --restore-point-in-time

Scenario 2: Manual backup restore (daily at 2 AM)
- Recovery Time: 10-20 minutes
- Steps: Download from blob storage, pg_restore

Scenario 3: VM complete failure
- Recovery Time: 30-60 minutes
- Steps: Terraform apply, restore code, restore config
```

**Testing**: Complete recovery drill performed and documented

---

#### Story 4.4: Conduct Disaster Recovery Drill
**Priority**: P1 - HIGH
**Effort**: 4 hours

**As a** technical lead
**I want to** perform a complete disaster recovery drill
**So that** recovery procedures are validated and team is prepared

**Acceptance Criteria**:
- [ ] Scenario selected: Database corruption + data loss
- [ ] Pre-drill checklist completed
- [ ] Drill executed following RECOVERY_PROCEDURES.md
- [ ] Recovery time measured (target: <30 minutes)
- [ ] Data integrity verified post-recovery
- [ ] Drill documented with lessons learned
- [ ] Gaps identified and remediation tasks created
- [ ] Team debriefing completed

**Drill Steps**:
1. Backup current production data
2. Simulate data loss (controlled environment)
3. Follow recovery procedure
4. Measure recovery time
5. Verify data integrity
6. Document findings
7. Update procedures based on learnings

**Success Criteria**:
- Recovery completed within RTO (30 minutes)
- Zero data loss within RPO (24 hours)
- All team members understand procedure

---

## Technical Architecture

### System Context
```
┌─────────────────────────────────────────────────────────────┐
│                    NOMARK DevOps System                      │
│                                                              │
│  ┌──────────┐    ┌──────────┐    ┌──────────────┐          │
│  │  Slack   │───▶│   VM     │───▶│  PostgreSQL  │          │
│  │  Users   │    │ (Ubuntu) │    │   Database   │          │
│  └──────────┘    └──────────┘    └──────────────┘          │
│                        │                                     │
│                        ▼                                     │
│                  ┌──────────┐                               │
│                  │  Claude  │                               │
│                  │   Code   │                               │
│                  └──────────┘                               │
└─────────────────────────────────────────────────────────────┘

Security Layers (New):
┌─────────────────────────────────────────────────────────────┐
│  1. Network Security: NSG with IP whitelisting              │
│  2. Authentication: Azure Key Vault for secrets             │
│  3. Authorization: PostgreSQL firewall rules                │
│  4. Monitoring: Application Insights + Alerts               │
│  5. Audit: Database audit logging                           │
│  6. Backup: Daily automated backups                         │
│  7. CI/CD: GitHub Actions with security scanning            │
└─────────────────────────────────────────────────────────────┘
```

### Component Changes

#### New Components
1. **Azure Key Vault**: Centralized secret management
2. **Application Insights**: Monitoring and observability
3. **Redis Cache**: Query result caching (C0 tier)
4. **GitHub Actions**: CI/CD automation
5. **Audit Logging**: Database change tracking

#### Modified Components
1. **supabase_tools.py**: SQL injection fixes, input validation
2. **All Python services**: Key Vault integration via SecretsManager
3. **Terraform configuration**: NSG restrictions, validation rules
4. **PostgreSQL**: Indexes, backup configuration, firewall rules

#### Removed Components
- None (additive changes only)

### Data Flow Changes

**Before (Insecure)**:
```
User → Slack → Webhook (no auth) → VM (open SSH) → Database (public)
                                        ↓
                                 .env file (exposed secrets)
```

**After (Secure)**:
```
User → Slack → Webhook (HMAC auth) → VM (IP restricted) → Database (private)
                            ↓                                      ↓
                     Key Vault (secrets) ← Managed Identity       Backups
                            ↓                                      ↓
                   App Insights (monitoring)               Blob Storage
```

### Security Controls

| Control | Before | After |
|---------|--------|-------|
| Secrets Management | .env files | Azure Key Vault |
| Network Access | Public (0.0.0.0/0) | IP whitelisted |
| SQL Injection | Vulnerable | Input validated |
| Backups | None | Daily automated |
| Monitoring | None | App Insights + alerts |
| Audit Logging | None | Database triggers |
| CI/CD | Manual | Automated with security scanning |
| Code Review | Optional | Enforced via branch protection |

---

## Dependencies & Prerequisites

### Azure Resources Required
- [x] Azure subscription with active credits
- [x] Resource group: nomark-devops-rg
- [x] VM: nomark-devops-vm (Ubuntu)
- [x] PostgreSQL: nomark-devops-db (Flexible Server)
- [x] Azure Function: nomark-vm-starter
- [ ] Azure Key Vault: nomark-kv-* (to be created)
- [ ] Application Insights: nomark-devops-insights (to be created)
- [ ] Redis Cache: nomark-devops-cache (to be created)
- [ ] Storage Account: Blob container for backups

### Access & Permissions
- [x] Azure CLI authenticated
- [x] Terraform configured
- [x] GitHub repository access
- [x] VM SSH access
- [ ] Azure Key Vault contributor role
- [ ] GitHub Actions secrets configured

### External Services
- [x] Anthropic API account
- [x] GitHub account with Actions enabled
- [x] Slack workspace with bot configured
- [x] Linear workspace
- [ ] Email/SMS for alerts (configure)

### Development Tools
- [x] Python 3.11+
- [x] Terraform 1.5+
- [x] Azure CLI 2.50+
- [ ] git-filter-repo (for git history cleanup)
- [ ] pre-commit (for commit hooks)
- [ ] pytest (for testing)

---

## Risks & Mitigation

### High Risk

**Risk 1: Service Disruption During Credential Rotation**
- **Impact**: 5-10 minute service interruption
- **Probability**: High (planned activity)
- **Mitigation**:
  - Schedule during low-usage window
  - Pre-communicate downtime to users
  - Have rollback plan ready
  - Complete rotation in <10 minutes

**Risk 2: Git Force Push Breaks Workflow**
- **Impact**: Team members need to re-clone repository
- **Probability**: Medium
- **Mitigation**:
  - Coordinate with all team members
  - Document re-clone steps
  - Schedule during off-hours
  - Create backup branch before force push

**Risk 3: Key Vault Access Issues**
- **Impact**: Applications cannot start if Key Vault unreachable
- **Probability**: Low
- **Mitigation**:
  - Implement local caching of secrets
  - Fallback to environment variables in dev
  - Monitor Key Vault availability
  - Have manual override procedure

### Medium Risk

**Risk 4: Test Coverage Takes Longer Than Estimated**
- **Impact**: Phase 3 extends beyond 2 weeks
- **Probability**: Medium
- **Mitigation**:
  - Start with critical paths first (60% minimum)
  - Can continue adding tests after Phase 3 complete
  - Don't block deployment on 100% coverage

**Risk 5: Azure Costs Exceed Budget**
- **Impact**: Monthly costs >$35
- **Probability**: Low
- **Mitigation**:
  - Use cost calculator before creating resources
  - Set up cost alerts at $30, $40, $50
  - Monitor usage in first month
  - Can downgrade Redis tier if needed

### Low Risk

**Risk 6: CI/CD Pipeline Failures**
- **Impact**: Cannot merge PRs until fixed
- **Probability**: Medium initially
- **Mitigation**:
  - Allow continue-on-error for non-critical checks initially
  - Gradually enforce stricter rules
  - Document troubleshooting steps

---

## Success Metrics & KPIs

### Security Metrics

| Metric | Baseline | Target | Measurement |
|--------|----------|--------|-------------|
| Security Score | 16/100 | 70/100 | Manual audit |
| Exposed Credentials | 6 | 0 | Git scan |
| SQL Injection Vulnerabilities | 2 | 0 | CodeQL scan |
| Open Network Ports | All IPs | Specific IPs only | NSG audit |
| Secrets in Code | Yes | No | detect-secrets |
| Backup Success Rate | 0% | 100% | Monitoring |

### DevOps Metrics (DORA)

| Metric | Baseline | Target | Measurement |
|--------|----------|--------|-------------|
| Deployment Frequency | 1/week | 5+/week | GitHub Actions |
| Lead Time for Changes | 3 days | <4 hours | PR metrics |
| Change Failure Rate | ~25% | <5% | Deployment logs |
| Mean Time to Recovery | 30 min | <5 min | Incident logs |
| Mean Time to Detect | 6+ hours | <1 min | Monitoring alerts |

### Quality Metrics

| Metric | Baseline | Target | Measurement |
|--------|----------|--------|-------------|
| Code Coverage | 0% | 60%+ | pytest-cov |
| Linting Pass Rate | Unknown | 100% | Flake8/Black |
| Security Scan Pass Rate | Unknown | 100% | Bandit/CodeQL |
| Dependency Vulnerabilities | Unknown | 0 critical/high | Dependabot |

### Operational Metrics

| Metric | Baseline | Target | Measurement |
|--------|----------|--------|-------------|
| Uptime | Unknown | 99.5% | App Insights |
| API Error Rate | Unknown | <1% | App Insights |
| P0 Incident Response Time | Unknown | <15 min | Incident logs |
| Backup Restore Test Success | 0% | 100% | Quarterly drill |

---

## Implementation Timeline

### Week 1: Critical Security (Phase 1)
**Duration**: 6 hours
**Owner**: Security Engineer + DevOps Engineer

- **Day 1** (3 hours):
  - [ ] Story 1.1: Rotate credentials (2h)
  - [ ] Story 1.2: Fix SQL injection (1h)

- **Day 2** (2 hours):
  - [ ] Story 1.3: Restrict SSH (30min)
  - [ ] Story 1.4: Restrict PostgreSQL (30min)
  - [ ] Story 1.5: Secure webhook (1h)

- **Day 3** (1 hour):
  - [ ] Story 1.6: HTTPS-only (15min)
  - [ ] Verification testing (45min)

**Deliverables**: Zero exposed credentials, SQL injection fixed, network hardened

---

### Week 1-2: Essential Infrastructure (Phase 2)
**Duration**: 16 hours
**Owner**: DevOps Engineer

- **Days 4-5** (6 hours):
  - [ ] Story 2.1: Application Insights (2h)
  - [ ] Story 2.2: Monitoring alerts (2h)
  - [ ] Story 2.3: Database backups (2h)

- **Days 6-7** (6 hours):
  - [ ] Story 2.4: Database indexes (1h)
  - [ ] Story 2.5: Redis cache (2h)
  - [ ] Story 2.6: Audit logging (3h)

- **Days 8-10** (4 hours):
  - [ ] Story 2.7: Key Vault migration (4h)

**Deliverables**: Monitoring, backups, caching, audit logging, Key Vault

---

### Week 2-3: CI/CD & Testing (Phase 3)
**Duration**: 24 hours
**Owner**: DevOps Engineer + Software Engineers

- **Week 2** (12 hours):
  - [ ] Story 3.1: GitHub Actions pipeline (4h)
  - [ ] Story 3.2: Branch protection (30min)
  - [ ] Story 3.3: Dependabot (15min)
  - [ ] Story 3.4: CodeQL scanning (30min)
  - [ ] Story 3.5: Unit tests - Part 1 (6h)

- **Week 3** (12 hours):
  - [ ] Story 3.5: Unit tests - Part 2 (7h)
  - [ ] Story 3.6: Pre-commit hooks (1h)
  - [ ] Testing and refinement (4h)

**Deliverables**: Automated CI/CD, 60% test coverage, security scanning

---

### Week 4: Incident Response (Phase 4)
**Duration**: 12 hours
**Owner**: DevOps Engineer + Engineering Manager

- **Days 1-3** (6 hours):
  - [ ] Story 4.1: Incident runbooks (6h)

- **Day 4** (2 hours):
  - [ ] Story 4.2: On-call procedures (2h)

- **Days 5-6** (4 hours):
  - [ ] Story 4.3: Recovery procedures (4h)
  - [ ] Story 4.4: DR drill (included in 4.3)

**Deliverables**: Complete incident response framework, tested DR procedures

---

## Cost Breakdown

### One-Time Costs
| Item | Cost |
|------|------|
| git-filter-repo tool | $0 (open source) |
| Development/testing time | Labor only |
| **Total One-Time** | **$0** |

### Recurring Monthly Costs
| Item | Monthly Cost | Annual Cost |
|------|--------------|-------------|
| Azure Key Vault (operations) | $5 | $60 |
| PostgreSQL backup storage (100GB) | $10 | $120 |
| Application Insights (basic) | $10 | $120 |
| Redis Cache (Basic C0) | $10 | $120 |
| **Total Recurring** | **$35** | **$420** |

### Labor Costs (Internal)
| Phase | Hours | Cost @ $150/hr |
|-------|-------|----------------|
| Phase 1 | 6 | $900 |
| Phase 2 | 16 | $2,400 |
| Phase 3 | 24 | $3,600 |
| Phase 4 | 12 | $1,800 |
| **Total Labor** | **58** | **$8,700** |

### Total First Year Cost
- Setup (labor): $8,700
- Recurring (12 months): $420
- **Total**: $9,120

### ROI Analysis
- Risk exposure eliminated: ~$360,000/year
- Investment: $9,120 first year
- **ROI**: 3,847% in first year
- **Payback period**: ~10 days

---

## Acceptance Criteria (PRD Level)

### Phase 1 Complete When:
- [ ] All 6 credentials rotated and old ones revoked
- [ ] Zero secrets in git history (verified with detect-secrets)
- [ ] SQL injection vulnerabilities fixed (verified with CodeQL)
- [ ] SSH accessible only from whitelisted IPs
- [ ] PostgreSQL accessible only from VM and admin IP
- [ ] Webhook endpoint authenticated or disabled
- [ ] Azure Function HTTPS-only enabled
- [ ] Security scan shows 0 critical vulnerabilities

### Phase 2 Complete When:
- [ ] Application Insights collecting metrics
- [ ] 4+ monitoring alerts configured and tested
- [ ] Daily database backups running successfully
- [ ] At least 1 successful backup restore test
- [ ] Database query performance improved >10x
- [ ] Redis cache deployed and functional
- [ ] Audit logging capturing all data changes
- [ ] All secrets migrated to Key Vault
- [ ] Applications using SecretsManager class

### Phase 3 Complete When:
- [ ] CI/CD pipeline running on all PRs
- [ ] Branch protection enforced on main
- [ ] Dependabot creating security update PRs
- [ ] CodeQL scanning enabled
- [ ] Test coverage ≥60% (measured by pytest-cov)
- [ ] All tests passing in CI
- [ ] Pre-commit hooks installed and working
- [ ] At least 1 successful automated deployment

### Phase 4 Complete When:
- [ ] 5 incident runbooks created and tested
- [ ] On-call procedures documented
- [ ] Recovery procedures documented for 3 scenarios
- [ ] Successful disaster recovery drill completed
- [ ] RTO/RPO documented (RTO: 30min, RPO: 24hr)
- [ ] All runbooks tested in non-production
- [ ] Team trained on incident response

### Overall PRD Complete When:
- [ ] Security score improved from 16/100 to 70/100
- [ ] Zero exposed credentials
- [ ] Zero critical security vulnerabilities
- [ ] All 4 phases complete
- [ ] All acceptance criteria met
- [ ] Documentation complete
- [ ] Team trained
- [ ] Metrics dashboard operational

---

## Appendices

### Appendix A: Related Audit Documents
- EXECUTIVE_SUMMARY_GAPS.md
- BUSINESS_CONTINUITY_GAPS_ANALYSIS.md
- CRITICAL_GAPS_IMPLEMENTATION_ROADMAP.md
- AZURE_NETWORK_SECURITY_AUDIT.md
- COST_OPTIMIZED_REMEDIATION_PLAN.md

### Appendix B: Repository Structure
```
DEVOPS_NOMARK/
├── .github/
│   ├── workflows/
│   │   ├── ci-cd.yml (new)
│   │   └── codeql-analysis.yml (new)
│   └── dependabot.yml (new)
├── devops-agent/
│   ├── scripts/
│   │   ├── 002-essential-indexes.sql (new)
│   │   └── 003-basic-audit-logging.sql (new)
│   └── terraform/
│       └── main.tf (modified - validation added)
├── devops-mcp/
│   └── devops_mcp/
│       ├── secrets.py (new)
│       ├── cache.py (new)
│       └── tools/
│           └── supabase_tools.py (modified - SQL injection fix)
├── tests/ (new)
│   ├── test_supabase_tools.py
│   ├── test_secrets.py
│   └── test_cache.py
├── OPERATIONAL_RUNBOOKS/ (new)
│   ├── 01-service-outage.md
│   ├── 02-database-connection-failure.md
│   ├── 03-slack-bot-not-responding.md
│   ├── 04-claude-api-errors.md
│   └── 05-disk-space-critical.md
├── ON_CALL_PROCEDURES.md (new)
├── RECOVERY_PROCEDURES.md (new)
├── .pre-commit-config.yaml (new)
├── pytest.ini (new)
└── PRD_SECURITY_REMEDIATION.md (this file)
```

### Appendix C: Key Vault Secret Names
```
ANTHROPIC-API-KEY          # Anthropic Claude API key
GITHUB-TOKEN               # GitHub personal access token
DATABASE-PASSWORD          # PostgreSQL admin password
LINEAR-API-KEY             # Linear API key
SLACK-BOT-TOKEN           # Slack bot OAuth token
SLACK-SIGNING-SECRET      # Slack webhook signing secret
WEBHOOK-SECRET            # n8n webhook HMAC secret (if used)
REDIS-CONNECTION-STRING   # Redis cache connection string
APPINSIGHTS-INSTRUMENTATION-KEY  # Application Insights key
```

### Appendix D: Monitoring Alert Thresholds
```
CPU Usage:            >80% for 5 minutes
Memory Available:     <2GB for 5 minutes
Disk Space:           <10GB remaining
Database Connections: <1 active connection
HTTP Error Rate:      >5% for 10 minutes
Response Time:        >5 seconds average for 5 minutes
Backup Failure:       Any failed backup job
VM Power State:       Stopped or deallocated
```

### Appendix E: Test Commands
```bash
# Verify secrets rotation
az keyvault secret list --vault-name nomark-kv-XXXXX
curl https://api.anthropic.com/v1/messages -H "x-api-key: OLD_KEY"  # Should fail

# Verify SQL injection fix
pytest tests/test_supabase_tools.py::test_list_tables_validates_schema -v

# Verify network restrictions
ssh devops@VM_IP  # From unauthorized IP - should fail
psql -h nomark-devops-db.postgres.database.azure.com -U devops_admin  # From external - should fail

# Verify backup
az postgres flexible-server backup list --resource-group nomark-devops-rg --name nomark-devops-db

# Verify CI/CD
git push origin feature-branch  # Should trigger CI
gh pr create  # Should require checks to pass

# Verify monitoring
az monitor metrics list --resource VM_RESOURCE_ID --metric "Percentage CPU"
```

---

**Document Version**: 1.0
**Last Updated**: 2026-02-08
**Next Review**: 2026-03-08 (post-implementation)
