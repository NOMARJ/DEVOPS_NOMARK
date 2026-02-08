# Security Remediation Implementation Guide
## START HERE - Step-by-Step Execution Plan

**Created**: 2026-02-08
**Based on**: PRD_SECURITY_REMEDIATION.md
**Estimated Time**: 58 hours over 4 weeks
**Monthly Cost**: $35

---

## ⚠️ CRITICAL: Read This First

This security remediation project cannot be fully automated with Ralph because it requires:
- Manual rotation of credentials on external platforms (Anthropic, GitHub, Linear, Slack)
- Azure CLI commands requiring authentication
- Security verification and testing
- Coordination across multiple systems

**This guide provides a step-by-step manual implementation path.**

---

## 🚀 Quick Start: Phase 1 (TODAY - 6 Hours)

### Prerequisites Checklist
- [ ] Azure CLI installed and authenticated (`az login`)
- [ ] git-filter-repo installed (`brew install git-filter-repo` or `pip install git-filter-repo`)
- [ ] SSH access to DevOps VM
- [ ] Admin access to: Anthropic, GitHub, Linear, Slack
- [ ] Backup of current .env file saved securely offline

---

## Phase 1: Eliminate Active Security Threats (6 hours)

### Task 1.1: Rotate All Exposed Credentials (2 hours)

**⚠️ CRITICAL: This will cause ~5 minutes of service downtime**

#### Step 1: Create Azure Key Vault (15 minutes)
```bash
# Create Key Vault with unique name
VAULT_NAME="nomark-kv-$(date +%s)"
az keyvault create \
  --name "$VAULT_NAME" \
  --resource-group nomark-devops-rg \
  --location australiaeast \
  --enable-rbac-authorization false

# Save vault name for later
echo "AZURE_KEY_VAULT_URL=https://$VAULT_NAME.vault.azure.net" >> ~/vault-config.txt
echo "Key Vault created: $VAULT_NAME"
```

#### Step 2: Rotate Anthropic API Key (15 minutes)
```bash
# 1. Go to https://console.anthropic.com/settings/keys
# 2. Click "Create Key"
# 3. Name it "NOMARK-DEVOPS-PROD"
# 4. Copy the new key (starts with sk-ant-api03-)

# 5. Store in Key Vault
read -sp "Paste NEW Anthropic API key: " NEW_ANTHROPIC_KEY
echo
az keyvault secret set \
  --vault-name "$VAULT_NAME" \
  --name "ANTHROPIC-API-KEY" \
  --value "$NEW_ANTHROPIC_KEY"

# 6. Test new key works
curl -X POST https://api.anthropic.com/v1/messages \
  -H "x-api-key: $NEW_ANTHROPIC_KEY" \
  -H "anthropic-version: 2023-06-01" \
  -H "content-type: application/json" \
  -d '{"model":"claude-3-5-sonnet-20241022","max_tokens":10,"messages":[{"role":"user","content":"test"}]}'

# Expected: Should return a valid response, not 401

# 7. AFTER verifying new key works, delete old key in Anthropic console
```

#### Step 3: Rotate GitHub Token (15 minutes)
```bash
# 1. Go to https://github.com/settings/tokens
# 2. Click "Generate new token (fine-grained)"
# 3. Repository access: Select your DEVOPS_NOMARK repo
# 4. Permissions:
#    - Contents: Read and write
#    - Pull requests: Read and write
#    - Issues: Read and write (if using)
# 5. Copy the new token (starts with ghp_)

# 6. Store in Key Vault
read -sp "Paste NEW GitHub token: " NEW_GITHUB_TOKEN
echo
az keyvault secret set \
  --vault-name "$VAULT_NAME" \
  --name "GITHUB-TOKEN" \
  --value "$NEW_GITHUB_TOKEN"

# 7. Test new token works
curl -H "Authorization: token $NEW_GITHUB_TOKEN" \
  https://api.github.com/user

# Expected: Should return your GitHub user info, not 401

# 8. AFTER verifying, delete old token in GitHub settings
```

#### Step 4: Rotate Database Password (15 minutes)
```bash
# Generate strong password
NEW_DB_PASSWORD=$(openssl rand -base64 32 | tr -d "=+/" | cut -c1-32)

# Store in Key Vault first
az keyvault secret set \
  --vault-name "$VAULT_NAME" \
  --name "DATABASE-PASSWORD" \
  --value "$NEW_DB_PASSWORD"

# Update PostgreSQL password
az postgres flexible-server update \
  --resource-group nomark-devops-rg \
  --name nomark-devops-db \
  --admin-password "$NEW_DB_PASSWORD"

# Test connection
psql "postgresql://devops_admin:$NEW_DB_PASSWORD@nomark-devops-db.postgres.database.azure.com:5432/devops?sslmode=require" \
  -c "SELECT 1;"

# Expected: Should connect successfully
```

#### Step 5: Rotate Linear API Key (10 minutes)
```bash
# 1. Go to https://linear.app/settings/api
# 2. Click "Create new personal API key"
# 3. Name it "NOMARK-DEVOPS-PROD"
# 4. Copy the new key (starts with lin_api_)

# 5. Store in Key Vault
read -sp "Paste NEW Linear API key: " NEW_LINEAR_KEY
echo
az keyvault secret set \
  --vault-name "$VAULT_NAME" \
  --name "LINEAR-API-KEY" \
  --value "$NEW_LINEAR_KEY"

# 6. Test new key works
curl https://api.linear.app/graphql \
  -H "Authorization: $NEW_LINEAR_KEY" \
  -H "Content-Type: application/json" \
  -d '{"query":"{ viewer { name } }"}'

# Expected: Should return your name, not authentication error

# 7. AFTER verifying, delete old key in Linear settings
```

#### Step 6: Rotate Slack Tokens (20 minutes)
```bash
# 1. Go to https://api.slack.com/apps
# 2. Select your NOMARK DevOps app
# 3. Go to "Settings" → "Install App"
# 4. Click "Regenerate" for Bot User OAuth Token
# 5. Copy the new token (starts with xoxb-)

# 6. Store bot token in Key Vault
read -sp "Paste NEW Slack Bot Token: " NEW_SLACK_BOT_TOKEN
echo
az keyvault secret set \
  --vault-name "$VAULT_NAME" \
  --name "SLACK-BOT-TOKEN" \
  --value "$NEW_SLACK_BOT_TOKEN"

# 7. Go to "Basic Information" → "App Credentials"
# 8. Click "Regenerate" for Signing Secret
# 9. Copy the new signing secret

# 10. Store signing secret in Key Vault
read -sp "Paste NEW Slack Signing Secret: " NEW_SLACK_SIGNING_SECRET
echo
az keyvault secret set \
  --vault-name "$VAULT_NAME" \
  --name "SLACK-SIGNING-SECRET" \
  --value "$NEW_SLACK_SIGNING_SECRET"

# 11. Test bot token works
curl -X POST https://slack.com/api/auth.test \
  -H "Authorization: Bearer $NEW_SLACK_BOT_TOKEN"

# Expected: "ok": true
```

#### Step 7: Remove .env from Git History (30 minutes)
```bash
# ⚠️ WARNING: This requires force push and team coordination

# 1. Backup current .env file to safe location (NOT in repo)
cp .env ~/.env.backup.$(date +%Y%m%d_%H%M%S)

# 2. Install git-filter-repo if not already installed
# macOS: brew install git-filter-repo
# Linux: pip install git-filter-repo

# 3. Remove .env from all git history
cd /Users/reecefrazier/DEVOPS_NOMARK
git filter-repo --invert-paths --path .env --force

# 4. Add .env to .gitignore (if not already)
if ! grep -q "^\.env$" .gitignore; then
    echo ".env" >> .gitignore
    git add .gitignore
    git commit -m "security: ensure .env is never committed"
fi

# 5. Force push to remote (⚠️ Coordinate with team first!)
git push origin --force --all
git push origin --force --tags

# 6. Notify team members to re-clone repository:
echo "IMPORTANT: All team members must now run:"
echo "  git fetch origin"
echo "  git reset --hard origin/main"
```

#### Step 8: Verify Credential Rotation (10 minutes)
```bash
# Test that OLD credentials no longer work
# (Use old values from your backup .env file)

# Test old Anthropic key (should FAIL)
curl -X POST https://api.anthropic.com/v1/messages \
  -H "x-api-key: sk-ant-OLD-KEY-FROM-BACKUP" \
  -H "anthropic-version: 2023-06-01" \
  -H "content-type: application/json" \
  -d '{"model":"claude-3-5-sonnet-20241022","max_tokens":10,"messages":[{"role":"user","content":"test"}]}'

# Expected: Should return 401 Unauthorized

# Verify all new credentials are in Key Vault
az keyvault secret list --vault-name "$VAULT_NAME" --query "[].name" -o table

# Expected output:
# ANTHROPIC-API-KEY
# GITHUB-TOKEN
# DATABASE-PASSWORD
# LINEAR-API-KEY
# SLACK-BOT-TOKEN
# SLACK-SIGNING-SECRET
```

**✅ Task 1.1 Complete**: All credentials rotated and secured in Key Vault

---

### Task 1.2: Fix SQL Injection Vulnerabilities (1 hour)

#### Step 1: Fix list_tables() Function (20 minutes)
```bash
# Edit the file
code devops-mcp/devops_mcp/tools/supabase_tools.py

# Replace lines ~335-350 with:
```

```python
async def list_tables(self, schema: str = "public") -> dict:
    """List all tables with SQL injection protection.

    Args:
        schema: Schema name (must be in whitelist)

    Returns:
        dict with 'data' key containing list of tables

    Raises:
        ValueError: If schema name is not in whitelist
    """
    # Whitelist validation to prevent SQL injection
    ALLOWED_SCHEMAS = ['public', 'auth', 'storage', 'extensions']
    if schema not in ALLOWED_SCHEMAS:
        raise ValueError(
            f"Invalid schema name: {schema}. "
            f"Must be one of: {', '.join(ALLOWED_SCHEMAS)}"
        )

    # Use PostgREST filter instead of raw SQL to avoid injection
    client = self._get_client()
    try:
        result = client.table('information_schema.tables') \
            .select('table_name, table_type') \
            .eq('table_schema', schema) \
            .order('table_name') \
            .execute()

        return {"data": result.data}
    except Exception as e:
        return {"error": str(e), "data": []}
```

#### Step 2: Fix get_table_schema() Function (20 minutes)
```python
async def get_table_schema(self, table: str) -> dict:
    """Get table schema with SQL injection protection.

    Args:
        table: Table name (must match regex pattern)

    Returns:
        dict with 'data' key containing column information

    Raises:
        ValueError: If table name contains invalid characters
    """
    import re

    # Strict validation: only alphanumeric and underscore, must start with letter/underscore
    if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', table):
        raise ValueError(
            f"Invalid table name: {table}. "
            f"Table names must start with a letter or underscore, "
            f"and contain only letters, numbers, and underscores."
        )

    # Additional length check
    if len(table) > 63:  # PostgreSQL identifier limit
        raise ValueError(f"Table name too long: {table} (max 63 characters)")

    # Use PostgREST filter for safety
    client = self._get_client()
    try:
        result = client.table('information_schema.columns') \
            .select('column_name, data_type, is_nullable, column_default, character_maximum_length') \
            .eq('table_name', table) \
            .order('ordinal_position') \
            .execute()

        return {"data": result.data}
    except Exception as e:
        return {"error": str(e), "data": []}
```

#### Step 3: Create Unit Tests (20 minutes)
```bash
# Create tests directory if it doesn't exist
mkdir -p tests

# Create test file
cat > tests/test_supabase_tools.py << 'EOF'
import pytest
from devops_mcp.tools.supabase_tools import SupabaseTools

class TestSupabaseToolsSecurity:
    """Security tests for SQL injection prevention."""

    @pytest.fixture
    def supabase_tools(self):
        return SupabaseTools()

    def test_list_tables_blocks_sql_injection(self, supabase_tools):
        """Test that list_tables blocks SQL injection attempts."""
        injection_attempts = [
            "public'; DROP TABLE users; --",
            "public' OR '1'='1",
            "public; DELETE FROM users;",
            "../../../etc/passwd",
            "public`; DROP TABLE users;`",
        ]

        for attempt in injection_attempts:
            with pytest.raises(ValueError, match="Invalid schema name"):
                supabase_tools.list_tables(attempt)

    def test_list_tables_allows_valid_schemas(self, supabase_tools):
        """Test that list_tables allows whitelisted schemas."""
        valid_schemas = ['public', 'auth', 'storage', 'extensions']

        for schema in valid_schemas:
            # Should not raise ValueError
            result = supabase_tools.list_tables(schema)
            assert "data" in result or "error" in result

    def test_get_table_schema_blocks_sql_injection(self, supabase_tools):
        """Test that get_table_schema blocks SQL injection attempts."""
        injection_attempts = [
            "users'; DROP TABLE users; --",
            "users' OR '1'='1",
            "../../../etc/passwd",
            "users; DELETE FROM data;",
            "'; DROP TABLE users CASCADE; --",
            "users`; TRUNCATE users;`",
        ]

        for attempt in injection_attempts:
            with pytest.raises(ValueError, match="Invalid table name"):
                supabase_tools.get_table_schema(attempt)

    def test_get_table_schema_allows_valid_names(self, supabase_tools):
        """Test that get_table_schema allows valid table names."""
        valid_names = [
            "users",
            "dev_tasks",
            "audit_logs",
            "_internal_table",
            "Table123",
        ]

        for name in valid_names:
            # Should not raise ValueError
            result = supabase_tools.get_table_schema(name)
            assert "data" in result or "error" in result

    def test_get_table_schema_blocks_long_names(self, supabase_tools):
        """Test that table names over 63 chars are rejected."""
        long_name = "a" * 64
        with pytest.raises(ValueError, match="Table name too long"):
            supabase_tools.get_table_schema(long_name)

EOF

# Create pytest configuration
cat > pytest.ini << 'EOF'
[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = -v
EOF
```

#### Step 4: Run Tests (10 minutes)
```bash
# Install pytest if not already installed
pip install pytest pytest-asyncio

# Run security tests
pytest tests/test_supabase_tools.py -v

# Expected: All tests should PASS

# Run with coverage (optional)
pip install pytest-cov
pytest tests/test_supabase_tools.py -v --cov=devops_mcp/tools/supabase_tools.py --cov-report=term-missing
```

**✅ Task 1.2 Complete**: SQL injection vulnerabilities fixed and tested

---

### Task 1.3: Restrict SSH Access (30 minutes)

#### Step 1: Get Your IP Address
```bash
# Get your current public IP
MY_IP=$(curl -s https://api.ipify.org)
echo "Your public IP: $MY_IP"

# If you have multiple locations (home, office), get both:
# Home IP: (run from home network)
# Office IP: (run from office network)
```

#### Step 2: Update Terraform Configuration
```bash
# Edit terraform file
code devops-agent/terraform/main.tf

# Find the variable "allowed_ssh_ips" (around line 108)
# Replace with:
```

```hcl
variable "allowed_ssh_ips" {
  type        = list(string)
  default     = []  # Force explicit configuration
  description = "IP addresses allowed to SSH (must be specified in CIDR notation)"

  validation {
    condition     = length(var.allowed_ssh_ips) > 0 && !contains(var.allowed_ssh_ips, "0.0.0.0/0")
    error_message = "SSH access must be restricted to specific IPs. 0.0.0.0/0 is not allowed."
  }
}
```

#### Step 3: Apply Terraform Changes
```bash
cd devops-agent/terraform

# Apply with your IP (replace with your actual IP)
terraform apply -var='allowed_ssh_ips=["YOUR_IP/32"]'

# If you have multiple IPs:
# terraform apply -var='allowed_ssh_ips=["HOME_IP/32", "OFFICE_IP/32"]'

# Type 'yes' when prompted

# Verify NSG rule updated
az network nsg rule show \
  --resource-group nomark-devops-rg \
  --nsg-name nomark-devops-nsg \
  --name SSH \
  --query "sourceAddressPrefixes"

# Expected: Should show only your IP(s), not 0.0.0.0/0
```

#### Step 4: Test SSH Access
```bash
# From allowed IP - should WORK
ssh devops@VM_PUBLIC_IP

# From unauthorized IP (use phone hotspot or VPN) - should FAIL
# ssh devops@VM_PUBLIC_IP
# Expected: Connection timeout or connection refused
```

**✅ Task 1.3 Complete**: SSH access restricted to specific IPs

---

### Task 1.4: Restrict PostgreSQL Access (30 minutes)

#### Step 1: Get VM Public IP
```bash
VM_PUBLIC_IP=$(az vm show -d \
  --resource-group nomark-devops-rg \
  --name nomark-devops-vm \
  --query publicIps -o tsv)

echo "VM Public IP: $VM_PUBLIC_IP"
```

#### Step 2: Remove Public Access Rules
```bash
# List current firewall rules
az postgres flexible-server firewall-rule list \
  --resource-group nomark-devops-rg \
  --name nomark-devops-db \
  --output table

# Delete the rule allowing all Azure services (if exists)
az postgres flexible-server firewall-rule delete \
  --resource-group nomark-devops-rg \
  --name nomark-devops-db \
  --rule-name AllowAllAzureServices \
  --yes

# Delete any other overly permissive rules (0.0.0.0 - 255.255.255.255)
# Replace RULE_NAME with actual name from list above
# az postgres flexible-server firewall-rule delete \
#   --resource-group nomark-devops-rg \
#   --name nomark-devops-db \
#   --rule-name RULE_NAME \
#   --yes
```

#### Step 3: Add VM-Specific Firewall Rule
```bash
# Allow only the DevOps VM
az postgres flexible-server firewall-rule create \
  --resource-group nomark-devops-rg \
  --name nomark-devops-db \
  --rule-name AllowDevOpsVM \
  --start-ip-address $VM_PUBLIC_IP \
  --end-ip-address $VM_PUBLIC_IP
```

#### Step 4: Add Admin Access (Optional)
```bash
# If you need admin access from your machine
MY_IP=$(curl -s https://api.ipify.org)

az postgres flexible-server firewall-rule create \
  --resource-group nomark-devops-rg \
  --name nomark-devops-db \
  --rule-name AllowAdminAccess \
  --start-ip-address $MY_IP \
  --end-ip-address $MY_IP
```

#### Step 5: Test Database Connectivity
```bash
# From VM - should WORK
ssh devops@$VM_PUBLIC_IP "psql '$DATABASE_URL' -c 'SELECT 1;'"

# From your machine (if you added admin rule) - should WORK
psql "postgresql://devops_admin:PASSWORD@nomark-devops-db.postgres.database.azure.com:5432/devops?sslmode=require" -c "SELECT 1;"

# From unauthorized IP (phone hotspot) - should FAIL
# Expected: Connection timeout or access denied
```

**✅ Task 1.4 Complete**: PostgreSQL access restricted to VM and admin only

---

### Task 1.5: Secure Webhook Endpoint (1 hour)

#### Option A: Add HMAC Authentication (Recommended if using webhooks)

**Step 1: Generate Webhook Secret**
```bash
# Generate strong secret
WEBHOOK_SECRET=$(openssl rand -hex 32)

# Store in Key Vault
az keyvault secret set \
  --vault-name "$VAULT_NAME" \
  --name "WEBHOOK-SECRET" \
  --value "$WEBHOOK_SECRET"

echo "Webhook secret generated and stored"
```

**Step 2: Implement HMAC Verification**
```python
# Create webhook authentication module
cat > nomark-method/scripts/webhook_auth.py << 'EOF'
import hmac
import hashlib
import os
from flask import request, jsonify

def get_webhook_secret():
    """Get webhook secret from Key Vault."""
    from devops_mcp.secrets import get_secret
    return get_secret("WEBHOOK-SECRET")

def verify_webhook_signature(request):
    """Verify HMAC signature from n8n webhook.

    Args:
        request: Flask request object

    Returns:
        bool: True if signature is valid, False otherwise
    """
    signature = request.headers.get('X-N8N-Signature')
    if not signature:
        return False

    # Get request body
    body = request.get_data()

    # Calculate expected signature
    secret = get_webhook_secret()
    expected_sig = hmac.new(
        secret.encode(),
        body,
        hashlib.sha256
    ).hexdigest()

    # Constant-time comparison to prevent timing attacks
    return hmac.compare_digest(signature, expected_sig)

def require_webhook_auth(f):
    """Decorator to require webhook authentication."""
    from functools import wraps

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not verify_webhook_signature(request):
            return jsonify({"error": "Invalid signature"}), 401
        return f(*args, **kwargs)

    return decorated_function

EOF
```

**Step 3: Update Webhook Handler**
```python
# Add to your webhook endpoint file
# Example: nomark-method/scripts/webhook-server.py

from webhook_auth import require_webhook_auth

@app.route('/webhook', methods=['POST'])
@require_webhook_auth  # Add this decorator
def webhook():
    # Your existing webhook code
    data = request.json
    # ... process webhook ...
    return jsonify({"status": "success"})
```

**Step 4: Configure n8n to Send Signature**
```
In your n8n workflow:
1. Before the HTTP Request node, add a Function node:

// Calculate HMAC signature
const crypto = require('crypto');
const body = JSON.stringify($json);
const secret = 'YOUR_WEBHOOK_SECRET';  // From Key Vault
const signature = crypto
  .createHmac('sha256', secret)
  .update(body)
  .digest('hex');

// Add to headers
return {
  json: $json,
  headers: {
    'X-N8N-Signature': signature
  }
};

2. In HTTP Request node, use the output from Function node
```

#### Option B: Block Port 9000 Entirely (If webhook not needed)

```bash
# Delete webhook NSG rule
az network nsg rule delete \
  --resource-group nomark-devops-rg \
  --nsg-name nomark-devops-nsg \
  --name Webhook \
  --yes

echo "Webhook port 9000 blocked"
```

**✅ Task 1.5 Complete**: Webhook endpoint secured

---

### Task 1.6: Enable HTTPS-Only on Azure Function (15 minutes)

```bash
# Enable HTTPS-only
az functionapp update \
  --name nomark-vm-starter \
  --resource-group nomark-devops-rg \
  --set httpsOnly=true

# Set minimum TLS version
az functionapp config set \
  --name nomark-vm-starter \
  --resource-group nomark-devops-rg \
  --min-tls-version 1.2

# Verify settings
az functionapp show \
  --name nomark-vm-starter \
  --resource-group nomark-devops-rg \
  --query "{httpsOnly:httpsOnly, minTlsVersion:siteConfig.minTlsVersion}"

# Expected: httpsOnly: true, minTlsVersion: "1.2"

# Test that HTTP redirects to HTTPS
HTTP_URL=$(az functionapp show \
  --name nomark-vm-starter \
  --resource-group nomark-devops-rg \
  --query defaultHostName -o tsv)

curl -I "http://$HTTP_URL"
# Expected: HTTP 307 redirect to HTTPS
```

**✅ Task 1.6 Complete**: Azure Function HTTPS-only enabled

---

## ✅ Phase 1 Complete Checklist

Verify all tasks completed:

- [ ] All 6 credentials rotated and stored in Azure Key Vault
- [ ] Old credentials verified as revoked
- [ ] .env file removed from git history
- [ ] SQL injection vulnerabilities fixed in supabase_tools.py
- [ ] Unit tests passing for SQL injection prevention
- [ ] SSH access restricted to specific IPs only
- [ ] PostgreSQL access restricted to VM and admin only
- [ ] Webhook endpoint secured (authenticated or blocked)
- [ ] Azure Function HTTPS-only enabled
- [ ] All services still functional

**Security Improvement**: **16/100 → 56/100 (+40 points)**

---

## 📋 Next Steps

**Phase 2 starts next** (Week 1, 16 hours):
- Enable Application Insights monitoring
- Configure monitoring alerts
- Enable database backups
- Add database indexes
- Deploy Redis cache
- Implement audit logging
- Complete Key Vault migration

Continue to [IMPLEMENTATION_GUIDE_PHASE2.md](IMPLEMENTATION_GUIDE_PHASE2.md) when ready.

---

## 🆘 Troubleshooting

### Issue: Key Vault creation fails
```bash
# Try a different vault name (must be globally unique)
VAULT_NAME="nomark-devops-kv-$(whoami)-$(date +%s)"
# Retry creation command
```

### Issue: Cannot connect to database after password rotation
```bash
# Verify password was updated
az postgres flexible-server show \
  --resource-group nomark-devops-rg \
  --name nomark-devops-db \
  --query administratorLogin

# Reset password if needed
az postgres flexible-server update \
  --resource-group nomark-devops-rg \
  --name nomark-devops-db \
  --admin-password "NEW_PASSWORD"
```

### Issue: SSH blocked after Terraform apply
```bash
# Check your current IP
curl https://api.ipify.org

# Re-apply with correct IP
terraform apply -var='allowed_ssh_ips=["CORRECT_IP/32"]'
```

### Issue: Git force push rejected
```bash
# If you have branch protection rules, temporarily disable them
# Then retry force push
git push origin --force --all
```

---

**Document Version**: 1.0
**Last Updated**: 2026-02-08
**Estimated Completion Time**: 6 hours for Phase 1
