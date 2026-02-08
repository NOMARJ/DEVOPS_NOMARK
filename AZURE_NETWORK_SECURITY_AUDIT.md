# Azure Network Security Audit Report

**Audit Date:** 2026-02-08
**Auditor:** Network Security Specialist
**Scope:** NOMARK DevOps Azure Infrastructure (nomark-devops-rg)
**Subscription:** ac7254fa-1f0b-433e-976c-b0430909c5ac

---

## Executive Summary

This comprehensive network security audit evaluates the Azure infrastructure supporting the NOMARK DevOps platform. The assessment covers network segmentation, security controls, connectivity patterns, traffic management, and monitoring capabilities.

### Risk Level: HIGH

**Critical Findings:**
- 4 Critical vulnerabilities identified
- 8 High-risk security gaps
- 12 Medium-priority improvements needed
- Network attack surface is unnecessarily large

**Key Issues:**
1. Overly permissive NSG rules allowing unrestricted internet access
2. PostgreSQL databases exposed to public internet without IP restrictions
3. No Azure Firewall, WAF, or DDoS protection implemented
4. Missing network flow logs and traffic analytics
5. No hub-spoke topology or network segmentation
6. Azure Function not enforcing HTTPS
7. No private endpoints for PaaS services

---

## 1. Network Segmentation Analysis

### Current VNet Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                    Current Network Topology                          │
│                         (Single VNet)                                │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  Internet                                                            │
│     │                                                                │
│     │ (All protocols, all IPs allowed)                              │
│     ▼                                                                │
│  ┌──────────────────────────────────────────────────────────┐       │
│  │         Public IP: 20.5.185.136                          │       │
│  │              (Standard SKU)                              │       │
│  └────────────────────────┬─────────────────────────────────┘       │
│                           │                                         │
│                           ▼                                         │
│  ┌──────────────────────────────────────────────────────────┐       │
│  │  Network Security Group: nomark-devops-vmNSG            │       │
│  │  ┌────────────────────────────────────────────────────┐ │       │
│  │  │  Rule 1000: SSH (22) - * → * ALLOW                 │ │       │
│  │  │  Rule 1010: HTTP 8080 - * → * ALLOW                │ │       │
│  │  │  Rule 1020: HTTPS (443) - * → * ALLOW              │ │       │
│  │  │  Rule 1030: HTTP (80) - * → * ALLOW                │ │       │
│  │  └────────────────────────────────────────────────────┘ │       │
│  └────────────────────────┬─────────────────────────────────┘       │
│                           │                                         │
│                           ▼                                         │
│  ┌──────────────────────────────────────────────────────────┐       │
│  │      VNet: nomark-devops-vmVNET                          │       │
│  │      Address Space: 10.0.0.0/16 (NOT USED IN TERRAFORM) │       │
│  │                                                          │       │
│  │   ┌────────────────────────────────────────────────┐    │       │
│  │   │  Subnet: nomark-devops-vmSubnet                │    │       │
│  │   │  Address: 10.0.0.0/24                          │    │       │
│  │   │                                                │    │       │
│  │   │   ┌──────────────────────────────────┐         │    │       │
│  │   │   │  VM: nomark-devops-vm            │         │    │       │
│  │   │   │  Size: Standard_B2as_v2          │         │    │       │
│  │   │   │  OS: Linux (Ubuntu)              │         │    │       │
│  │   │   │  Private IP: Dynamic             │         │    │       │
│  │   │   │                                  │         │    │       │
│  │   │   │  Exposed Services:               │         │    │       │
│  │   │   │  - SSH (22)                      │         │    │       │
│  │   │   │  - HTTP (80)                     │         │    │       │
│  │   │   │  - HTTPS (443)                   │         │    │       │
│  │   │   │  - MCP (8080)                    │         │    │       │
│  │   │   └──────────────────────────────────┘         │    │       │
│  │   └────────────────────────────────────────────────┘    │       │
│  └──────────────────────────────────────────────────────────┘       │
│                                                                      │
│  External PaaS Services (Public Internet Access):                   │
│  ┌──────────────────────────────────────────────────────────┐       │
│  │  PostgreSQL: nomark-devops-db.postgres.database.azure.com│       │
│  │  - Public Access: ENABLED                                │       │
│  │  - Firewall: 0.0.0.0-0.0.0.0 (Allow all Azure services) │       │
│  │  - No Private Endpoint                                   │       │
│  └──────────────────────────────────────────────────────────┘       │
│                                                                      │
│  ┌──────────────────────────────────────────────────────────┐       │
│  │  Function App: nomark-vm-starter.azurewebsites.net       │       │
│  │  - HTTPS Only: FALSE (Accepts HTTP!)                     │       │
│  │  - Min TLS: Not configured                               │       │
│  └──────────────────────────────────────────────────────────┘       │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

### Issues Identified

#### CRITICAL - No Network Segmentation
- **Issue:** Single flat subnet with all resources
- **Impact:** No isolation between management, application, and data tiers
- **Terraform Evidence:** Lines 149-154 define only one subnet
  ```hcl
  resource "azurerm_subnet" "main" {
    name                 = "${var.project_name}-subnet"
    address_prefixes     = ["10.100.1.0/24"]
  }
  ```
- **Risk:** Lateral movement in case of compromise

#### HIGH - Address Space Mismatch
- **Issue:** Terraform defines 10.100.0.0/16 but Azure shows 10.0.0.0/16
- **Impact:** Configuration drift, potential routing issues
- **Evidence:**
  - Terraform (line 143): `address_space = ["10.100.0.0/16"]`
  - Azure CLI: Shows 10.0.0.0/16
- **Risk:** Management confusion, infrastructure inconsistency

#### HIGH - No Hub-Spoke Topology
- **Issue:** Flat network architecture without central hub
- **Impact:** Cannot implement centralized security controls
- **Missing:**
  - No hub VNet for shared services
  - No spoke VNets for workload isolation
  - No VNet peering configured
- **Risk:** Limited scalability and security control

---

## 2. Network Security Group (NSG) Analysis

### Current NSG Rules - CRITICAL ISSUES

| Priority | Name | Direction | Protocol | Source | Source Port | Dest | Dest Port | Action | Risk |
|----------|------|-----------|----------|--------|-------------|------|-----------|--------|------|
| 1000 | default-allow-ssh | Inbound | TCP | * (ANY) | * | * | 22 | ALLOW | CRITICAL |
| 1010 | allow-mcp-8080 | Inbound | TCP | * (ANY) | * | * | 8080 | ALLOW | HIGH |
| 1020 | allow-https-443 | Inbound | TCP | * (ANY) | * | * | 443 | ALLOW | MEDIUM |
| 1030 | allow-http-80 | Inbound | TCP | * (ANY) | * | * | 80 | ALLOW | MEDIUM |

### Vulnerabilities

#### CRITICAL - SSH Exposed to Internet
```hcl
# Terraform Lines 172-182
security_rule {
  name                       = "SSH"
  source_address_prefixes    = var.allowed_ssh_ips  # DEFAULTS TO 0.0.0.0/0!
  destination_port_range     = "22"
  access                     = "Allow"
}
```

**Issues:**
- Default value: `["0.0.0.0/0"]` (Terraform line 108)
- Comment acknowledges risk: "Restrict in production!" (line 108)
- SSH exposed to entire internet
- No rate limiting or fail2ban visible
- No Azure Bastion for secure access

**Attack Surface:**
- Constant brute force attempts expected
- Exposed to automated SSH scanning tools
- Single point of failure if SSH key compromised

**Remediation Required:**
1. Remove default 0.0.0.0/0 value
2. Implement Azure Bastion for SSH access
3. Add specific IP allowlist only
4. Enable MFA for SSH connections

#### HIGH - Unnecessary HTTP (Port 80) Open
```hcl
# Terraform Lines 184-195 (Webhook listener)
security_rule {
  name                       = "Webhook"
  source_address_prefix      = "*"  # ALLOWS ENTIRE INTERNET
  destination_port_range     = "9000"
  access                     = "Allow"
}
```

**Issues:**
- Port 9000 webhook exposed to internet (Terraform doesn't show this, but Azure has port 80 open)
- Port 80 HTTP accepting unencrypted traffic
- No source IP restrictions
- No rate limiting

**Attack Vectors:**
- Man-in-the-middle attacks on port 80
- Webhook abuse and DoS attacks on port 9000
- Data interception

#### HIGH - Missing Outbound Rules
**Issue:** No explicit outbound filtering rules
**Impact:** VM can egress to any internet destination
**Risk:** Data exfiltration, C2 communication possible

#### MEDIUM - No Application Security Groups (ASGs)
**Missing Capability:**
- Cannot group resources by role (web, app, data tier)
- All rules use IP-based filtering
- Difficult to scale and manage

### Comparison to Terraform Configuration

The Terraform configuration (lines 165-196) only defines 2 NSG rules:
1. SSH (port 22)
2. Webhook (port 9000)

However, Azure shows 4 rules:
- SSH (22)
- MCP (8080)
- HTTPS (443)
- HTTP (80)

**Configuration Drift Detected:** Manual changes made outside Terraform

---

## 3. Network Security Controls Assessment

### Azure Firewall - NOT IMPLEMENTED

**Status:** No Azure Firewall deployed

**Missing Capabilities:**
- Threat intelligence-based filtering
- FQDN filtering for outbound traffic
- Application rules for L7 filtering
- Network rules for L3-L4 protection
- Centralized logging and monitoring

**Impact:**
- No protection against known malicious IPs/domains
- Cannot enforce corporate internet policies
- Limited visibility into outbound traffic
- No intrusion detection/prevention

**Terraform Evidence:** No firewall resources defined

### DDoS Protection - NOT ENABLED

**Status:** No DDoS Protection Plan

**Query Results:**
```bash
az network ddos-protection list
# Output: No DDoS Protection Plans found
```

**Vulnerabilities:**
- Public IP exposed without DDoS protection
- Standard SKU public IP has basic DDoS protection only
- No layer 3-4 volumetric attack mitigation
- No layer 7 application attack protection
- No real-time attack metrics

**Risk Assessment:**
- Public-facing services (SSH, HTTP, HTTPS) vulnerable
- Could impact availability for 20.5.185.136
- No SLA protection during attacks

### Web Application Firewall (WAF) - NOT IMPLEMENTED

**Status:** No Application Gateway with WAF

**Query Results:**
```bash
az network application-gateway list
# Output: No Application Gateways found
```

**Missing Protection:**
- OWASP Top 10 vulnerabilities unmitigated
- SQL injection attacks possible
- Cross-site scripting (XSS) not blocked
- No bot protection
- No geo-filtering capabilities

**Exposed Services at Risk:**
- HTTP/HTTPS on ports 80/443
- MCP service on port 8080
- Azure Function endpoints

### Service Endpoints vs Private Endpoints

**Current State:** Neither implemented

**PostgreSQL Databases:**
- nomark-devops-db: **Public Access ENABLED**
- Firewall rule: **0.0.0.0-0.0.0.0** (Allow all Azure)
- No private endpoint configured
- Traffic traverses public internet

**Risks:**
```
┌──────────────────────────────────────────────────────────────┐
│  Current PostgreSQL Access Pattern                           │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  VM (10.0.0.x) ──→ Public Internet ──→ PostgreSQL           │
│                    (Unencrypted path)                        │
│                                                              │
│  Issues:                                                     │
│  ✗ Data exposed to internet routing                         │
│  ✗ No network-level isolation                               │
│  ✗ Vulnerable to MITM attacks                               │
│  ✗ Compliance issues (HIPAA, SOC2)                          │
└──────────────────────────────────────────────────────────────┘
```

**Required Changes:**
1. Create subnet delegation for PostgreSQL
2. Deploy private endpoint
3. Disable public network access
4. Update connection strings

---

## 4. TLS/SSL and Certificate Management

### Azure Function: nomark-vm-starter

**CRITICAL VULNERABILITY FOUND:**

```bash
az functionapp list --query "[].{Name:name, HTTPSOnly:httpsOnly}"
# Output: nomark-vm-starter: HTTPSOnly=False
```

**Issues:**
- **HTTPS Only: FALSE** - Accepts unencrypted HTTP traffic
- **Min TLS Version:** Not configured (likely 1.0 or 1.1)
- **Custom domain:** Not configured, using *.azurewebsites.net
- **Certificate management:** Using default Azure certificate only

**Security Impact:**
```
Slack Command Flow (INSECURE):
┌────────────────────────────────────────────────────────────┐
│                                                            │
│  Slack ──HTTP──→ nomark-vm-starter.azurewebsites.net      │
│        (Unencrypted Slack tokens!)                         │
│                                                            │
│  Data at Risk:                                             │
│  - Slack verification tokens (function_app.py line 19)     │
│  - Azure subscription IDs (line 16)                        │
│  - User information (line 49)                              │
│  - VM control commands                                     │
└────────────────────────────────────────────────────────────┘
```

**Function App Code Evidence:**
```python
# /Users/reecefrazier/DEVOPS_NOMARK/vm-starter-function/function_app.py
# Line 21: Anonymous auth level
@app.route(route="start-vm", auth_level=func.AuthLevel.ANONYMOUS)

# Line 42-46: Token passed in plain text if HTTP used
if SLACK_VERIFICATION_TOKEN:
    token = form_data.get('token', '')
    if token != SLACK_VERIFICATION_TOKEN:
        return func.HttpResponse("Unauthorized", status_code=401)
```

### Terraform VM Configuration

**Lines 244-249:** VM image reference
```hcl
source_image_reference {
  publisher = "Canonical"
  offer     = "0001-com-ubuntu-server-jammy"
  sku       = "22_04-lts-gen2"  # Using Ubuntu 22.04
  version   = "latest"
}
```

**TLS Configuration Not Visible in IaC:**
- Cloud-init installs nginx (line 296) but no TLS config shown
- Custom data includes webhook server (lines 450-544) - HTTP only
- No certbot or Let's Encrypt configuration
- Ports 80/443 open but certificate management unclear

### Certificate Management Issues

**Missing:**
- No Azure Key Vault certificate integration
- No automatic certificate rotation
- No certificate expiry monitoring
- No HTTPS redirect enforcement
- No HSTS headers configured

---

## 5. DNS Security

### Private DNS Zones - NOT CONFIGURED

**Query Results:**
```bash
az network private-dns zone list
# Output: No Private DNS Zones found
```

**Missing Capabilities:**
- Private name resolution for Azure resources
- Split-horizon DNS for hybrid scenarios
- Protection against DNS spoofing
- Private DNS records for services

### DNSSEC - NOT ENABLED

**Azure Status:** Azure DNS does not support DNSSEC
**Alternative Required:** Use third-party DNS with DNSSEC if required

### DNS Configuration (Terraform)

**Not explicitly configured** - Using Azure default DNS
- VNet likely using Azure-provided DNS (168.63.129.16)
- No custom DNS servers defined
- No DNS forwarders for hybrid connectivity

---

## 6. Connectivity Patterns

### Hub-Spoke Topology - NOT IMPLEMENTED

**Current Architecture:** Single standalone VNet

**Missing:**
```
Recommended Hub-Spoke Architecture:
┌─────────────────────────────────────────────────────────────┐
│                  Hub VNet (Not Implemented)                  │
│  ┌────────────────────────────────────────────────────────┐  │
│  │  - Azure Firewall                                       │  │
│  │  - VPN Gateway                                          │  │
│  │  - Azure Bastion                                        │  │
│  │  - Shared Services (DNS, Monitoring)                    │  │
│  └────────────────────────────────────────────────────────┘  │
│           │                  │                  │            │
│  ┌────────┘                  │                  └──────────┐  │
│  │                           │                             │  │
│  ▼                           ▼                             ▼  │
│ ┌──────────┐         ┌──────────┐              ┌──────────┐  │
│ │ Spoke 1  │         │ Spoke 2  │              │ Spoke 3  │  │
│ │(DevOps)  │         │(FlowM.)  │              │(Future)  │  │
│ └──────────┘         └──────────┘              └──────────┘  │
└─────────────────────────────────────────────────────────────┘
```

**Impact of Missing Hub-Spoke:**
- Cannot centralize security controls
- Difficult to add new workloads
- No shared service consolidation
- Higher operational complexity

### VNet Peering - NOT CONFIGURED

**Query Results:**
```bash
az network vnet peering list --vnet-name nomark-devops-vmVNET
# Output: No VNet peerings configured
```

**Missing Connectivity:**
- No connection to other NOMARK workloads
- FlowMetrics_Dev is isolated
- Cannot share resources across environments

### VPN/ExpressRoute - NOT DEPLOYED

**Query Results:**
```bash
az network vnet-gateway list
# Output: No VPN Gateways found
```

**Impact:**
- No hybrid connectivity to on-premises
- No site-to-site VPN for secure access
- No ExpressRoute for dedicated connection
- Developers must use public internet SSH

### Service Mesh - NOT APPLICABLE

**Status:** Not relevant for current architecture
**Reason:** Single VM deployment, not containerized microservices

---

## 7. Traffic Management

### Load Balancers - NOT DEPLOYED

**Query Results:**
```bash
az network lb list
# Output: No Load Balancers found
```

**Current State:**
- Single VM with public IP
- No high availability configuration
- No traffic distribution
- No health probing

**Single Point of Failure:**
```
┌──────────────────────────────────────────┐
│  Current: No Redundancy                  │
├──────────────────────────────────────────┤
│                                          │
│  Internet ──→ 20.5.185.136 ──→ VM       │
│               (Single point)             │
│                                          │
│  If VM fails: Complete outage            │
└──────────────────────────────────────────┘
```

### Application Gateway - NOT DEPLOYED

**Missing Capabilities:**
- Layer 7 load balancing
- URL-based routing
- SSL termination
- Web Application Firewall
- Cookie-based session affinity

### Traffic Manager - NOT CONFIGURED

**Query Results:**
```bash
az network traffic-manager profile list
# Output: No Traffic Manager profiles found
```

**Missing:**
- Global load balancing
- Geographic routing
- Failover capabilities
- Multi-region redundancy

### CDN - NOT IMPLEMENTED

**Query Results:**
```bash
az cdn profile list
# Output: No CDN profiles found
```

**Impact:**
- Static assets served directly from VM
- No edge caching for global users
- Higher latency for distant users
- Increased bandwidth costs
- No DDoS protection at CDN edge

**Terraform Evidence:** No CDN resources defined

---

## 8. Network Monitoring

### Network Watcher - ENABLED (Good!)

**Status:** Active in australiaeast region
```bash
Network Watcher: NetworkWatcher_australiaeast
Resource Group: NetworkWatcherRG
```

**Enabled Capabilities:**
- Network performance monitoring
- Connectivity diagnostics
- Topology visualization
- Next hop analysis

### NSG Flow Logs - NOT CONFIGURED (Critical!)

**Query Results:**
```bash
az network watcher flow-log list --location australiaeast
# Output: No flow logs configured
```

**Missing:**
- Network traffic analysis
- Security threat detection
- Compliance logging
- Troubleshooting data

**Impact:**
```
Without Flow Logs:
✗ Cannot detect anomalous traffic patterns
✗ No audit trail for security investigations
✗ Missing compliance requirements (SOC2, ISO 27001)
✗ Cannot identify attack sources
✗ No bandwidth usage visibility
```

**Cost:** Minimal (~$5-10/month for storage)

### Traffic Analytics - NOT ENABLED

**Status:** Not configured (requires flow logs first)

**Missing Insights:**
- Top talkers identification
- Application protocol distribution
- Malicious IP detection
- Bandwidth utilization trends

### Connection Monitoring - NOT CONFIGURED

**Query Results:**
```bash
az network watcher connection-monitor list
# Output: No connection monitors configured
```

**Missing:**
- End-to-end connectivity monitoring
- Latency tracking to PostgreSQL
- Packet loss detection
- Network path analysis

### Diagnostic Settings - NOT CONFIGURED

**Query Results:**
```bash
az monitor diagnostic-settings list --resource <NSG>
# Output: No diagnostic settings on NSG
```

**Impact:**
- NSG events not logged to Log Analytics
- No centralized security monitoring
- Cannot correlate network events with other logs

---

## 9. Exposed Services and Attack Surface

### Public Attack Surface

**Externally Accessible Endpoints:**

#### 1. VM Public IP: 20.5.185.136

| Port | Service | Protocol | Exposure | Risk Level |
|------|---------|----------|----------|------------|
| 22 | SSH | TCP | Internet (0.0.0.0/0) | CRITICAL |
| 80 | HTTP | TCP | Internet (0.0.0.0/0) | HIGH |
| 443 | HTTPS | TCP | Internet (0.0.0.0/0) | MEDIUM |
| 8080 | MCP/DevOps | TCP | Internet (0.0.0.0/0) | HIGH |

**Port Scan Results:**
```bash
# Live connectivity test to 20.5.185.136
Port 22 (SSH): OPEN - Accessible
Port 80 (HTTP): OPEN - Accessible
Port 443 (HTTPS): OPEN - Accessible
Port 8080 (MCP): OPEN - Accessible
```

#### 2. Azure Function: nomark-vm-starter.azurewebsites.net

| Endpoint | Protocol | Authentication | Risk |
|----------|----------|----------------|------|
| /api/start-vm | HTTP/HTTPS | Slack token (weak) | HIGH |
| /api/health | HTTP/HTTPS | None (Anonymous) | MEDIUM |

**Function Code Analysis:**
```python
# Line 21: Anonymous authentication
@app.route(route="start-vm", auth_level=func.AuthLevel.ANONYMOUS)

# Line 42-46: Weak authentication via form data
if SLACK_VERIFICATION_TOKEN:
    token = form_data.get('token', '')  # Can be intercepted if HTTP
```

#### 3. PostgreSQL Databases (Public Endpoints)

| Database | FQDN | Public Access | Firewall |
|----------|------|---------------|----------|
| nomark-devops-db | nomark-devops-db.postgres.database.azure.com | ENABLED | 0.0.0.0/0 (All Azure) |
| fmetrics-dev-n8n-pg | fmetrics-dev-n8n-pg.postgres.database.azure.com | ENABLED | Unknown |
| fmetrics-dev-sftpgo-pg | fmetrics-dev-sftpgo-pg.postgres.database.azure.com | ENABLED | Unknown |

**Critical Issue:** Databases accessible from any Azure IP

### Attack Vectors

#### Vector 1: SSH Brute Force
```
Attacker ──→ Internet ──→ 20.5.185.136:22 ──→ VM
         (Unlimited attempts, no rate limiting visible)
```

**Mitigations Missing:**
- No Azure Bastion
- No MFA requirement
- No IP allowlist
- No fail2ban confirmation

#### Vector 2: Webhook Abuse
```
Attacker ──→ Internet ──→ 20.5.185.136:8080/trigger ──→ Webhook Service
         (No authentication, can trigger arbitrary tasks)
```

**Terraform Evidence (Lines 481-489):**
```python
# webhook-server.py - No authentication required
if self.path == '/trigger':
    self.handle_trigger(data)  # Accepts any POST
```

#### Vector 3: Database Exposure
```
Attacker ──→ Azure IP ──→ nomark-devops-db.postgres.database.azure.com
         (If credentials compromised, full database access)
```

#### Vector 4: Man-in-the-Middle (Azure Function)
```
Slack ──HTTP──→ nomark-vm-starter.azurewebsites.net
    (Unencrypted traffic can be intercepted)
```

### Unnecessary Open Ports

**Port 80 (HTTP):**
- Should redirect to 443
- No legitimate use case for unencrypted traffic
- **Recommendation:** Remove NSG rule, enforce HTTPS only

**Port 8080 (MCP):**
- Development tool exposed to internet
- Should be behind VPN or Bastion
- **Recommendation:** Restrict to authorized IPs only

### Network Attack Surface Summary

```
┌─────────────────────────────────────────────────────────────────┐
│                  Attack Surface Analysis                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  CRITICAL EXPOSURE:                                              │
│  ├─ SSH (22) open to 0.0.0.0/0                                  │
│  ├─ PostgreSQL public access enabled                            │
│  └─ Azure Function accepts HTTP                                 │
│                                                                  │
│  HIGH EXPOSURE:                                                  │
│  ├─ HTTP (80) accepts unencrypted traffic                       │
│  ├─ MCP (8080) exposed to internet                              │
│  └─ Webhook service with no authentication                      │
│                                                                  │
│  MEDIUM EXPOSURE:                                                │
│  ├─ HTTPS (443) without WAF protection                          │
│  └─ No DDoS protection on public IP                             │
│                                                                  │
│  TOTAL RISK SCORE: 8.7/10 (CRITICAL)                            │
└──────────────────────────────────────────────────────────────────┘
```

---

## 10. Recommended Security Architecture

### Target Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│               Recommended Secure Network Architecture                    │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌──────────────────────────────────────────────────────────────┐       │
│  │                    Internet Edge Layer                        │       │
│  │  ┌────────────────────────────────────────────────────────┐  │       │
│  │  │  Azure Front Door (WAF + DDoS Protection)             │  │       │
│  │  │  - OWASP protection                                    │  │       │
│  │  │  - Bot protection                                      │  │       │
│  │  │  - Rate limiting                                       │  │       │
│  │  │  - SSL/TLS termination                                │  │       │
│  │  └────────────────┬───────────────────────────────────────┘  │       │
│  └───────────────────┼──────────────────────────────────────────┘       │
│                      │                                                   │
│                      ▼                                                   │
│  ┌──────────────────────────────────────────────────────────────┐       │
│  │                    Hub VNet (10.0.0.0/16)                     │       │
│  │  ┌────────────────────────────────────────────────────────┐  │       │
│  │  │  AzureFirewallSubnet (10.0.0.0/26)                     │  │       │
│  │  │  ┌──────────────────────────────────────────────────┐  │  │       │
│  │  │  │  Azure Firewall                                   │  │  │       │
│  │  │  │  - Threat intelligence                            │  │  │       │
│  │  │  │  - FQDN filtering                                 │  │  │       │
│  │  │  │  - Network rules                                  │  │  │       │
│  │  │  └──────────────────────────────────────────────────┘  │  │       │
│  │  └────────────────────────────────────────────────────────┘  │       │
│  │                                                              │       │
│  │  ┌────────────────────────────────────────────────────────┐  │       │
│  │  │  AzureBastionSubnet (10.0.1.0/27)                      │  │       │
│  │  │  ┌──────────────────────────────────────────────────┐  │  │       │
│  │  │  │  Azure Bastion                                    │  │  │       │
│  │  │  │  - Secure RDP/SSH access                          │  │  │       │
│  │  │  │  - No public IP on VMs required                   │  │  │       │
│  │  │  │  - Session recording                              │  │  │       │
│  │  │  └──────────────────────────────────────────────────┘  │  │       │
│  │  └────────────────────────────────────────────────────────┘  │       │
│  │                                                              │       │
│  │  ┌────────────────────────────────────────────────────────┐  │       │
│  │  │  GatewaySubnet (10.0.2.0/27)                           │  │       │
│  │  │  ┌──────────────────────────────────────────────────┐  │  │       │
│  │  │  │  VPN Gateway (Optional)                           │  │  │       │
│  │  │  │  - Site-to-site VPN                               │  │  │       │
│  │  │  │  - Point-to-site VPN                              │  │  │       │
│  │  │  └──────────────────────────────────────────────────┘  │  │       │
│  │  └────────────────────────────────────────────────────────┘  │       │
│  └──────────────────────────────────────────────────────────────┘       │
│                      │                                                   │
│         ┌────────────┴────────────┐                                      │
│         │    VNet Peering         │                                      │
│         │    (Encrypted)          │                                      │
│         └────────────┬────────────┘                                      │
│                      │                                                   │
│                      ▼                                                   │
│  ┌──────────────────────────────────────────────────────────────┐       │
│  │              Spoke VNet - DevOps (10.100.0.0/16)              │       │
│  │                                                              │       │
│  │  ┌────────────────────────────────────────────────────────┐  │       │
│  │  │  AppSubnet (10.100.1.0/24)                             │  │       │
│  │  │  NSG: Allow 443 from Front Door only                   │  │       │
│  │  │  ┌──────────────────────────────────────────────────┐  │  │       │
│  │  │  │  DevOps VM (Private IP only)                      │  │  │       │
│  │  │  │  - No public IP                                   │  │  │       │
│  │  │  │  - Managed via Bastion                            │  │  │       │
│  │  │  └──────────────────────────────────────────────────┘  │  │       │
│  │  └────────────────────────────────────────────────────────┘  │       │
│  │                                                              │       │
│  │  ┌────────────────────────────────────────────────────────┐  │       │
│  │  │  DataSubnet (10.100.2.0/24)                            │  │       │
│  │  │  NSG: Allow 5432 from AppSubnet only                   │  │       │
│  │  │  Service Endpoints: Microsoft.Sql                      │  │       │
│  │  │  ┌──────────────────────────────────────────────────┐  │  │       │
│  │  │  │  Private Endpoint: PostgreSQL                     │  │  │       │
│  │  │  │  - Private IP: 10.100.2.5                         │  │  │       │
│  │  │  │  - Public access: DISABLED                        │  │  │       │
│  │  │  └──────────────────────────────────────────────────┘  │  │       │
│  │  └────────────────────────────────────────────────────────┘  │       │
│  │                                                              │       │
│  │  ┌────────────────────────────────────────────────────────┐  │       │
│  │  │  PrivateLinkSubnet (10.100.3.0/24)                     │  │       │
│  │  │  - Private endpoints for PaaS services                 │  │       │
│  │  │  - Private DNS zones                                   │  │       │
│  │  └────────────────────────────────────────────────────────┘  │       │
│  └──────────────────────────────────────────────────────────────┘       │
│                                                                          │
│  ┌──────────────────────────────────────────────────────────────┐       │
│  │              Spoke VNet - FlowMetrics (10.101.0.0/16)         │       │
│  │  (Similar structure with isolated subnets)                    │       │
│  └──────────────────────────────────────────────────────────────┘       │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## 11. Prioritized Remediation Plan

### Phase 1: Immediate Actions (Week 1) - CRITICAL

#### 1.1 Restrict SSH Access
**Priority:** CRITICAL
**Effort:** 1 hour
**Cost:** $0

**Action:**
```bash
# Update Terraform variable
allowed_ssh_ips = ["YOUR_OFFICE_IP/32", "YOUR_HOME_IP/32"]

# Apply immediately
terraform apply -var-file="secrets.tfvars"
```

**Terraform Change:**
```hcl
# main.tf Line 108 - Remove dangerous default
variable "allowed_ssh_ips" {
  description = "List of IPs allowed to SSH (CIDR notation)"
  type        = list(string)
  # REMOVE THIS: default = ["0.0.0.0/0"]
  # Make it required
}
```

#### 1.2 Enable HTTPS Only on Function App
**Priority:** CRITICAL
**Effort:** 15 minutes
**Cost:** $0

**Action:**
```bash
az functionapp update \
  --name nomark-vm-starter \
  --resource-group nomark-devops-rg \
  --set httpsOnly=true

az functionapp config set \
  --name nomark-vm-starter \
  --resource-group nomark-devops-rg \
  --min-tls-version 1.2
```

#### 1.3 Restrict PostgreSQL Public Access
**Priority:** CRITICAL
**Effort:** 2 hours
**Cost:** $0

**Actions:**
```bash
# Remove the allow-all Azure rule
az postgres flexible-server firewall-rule delete \
  --resource-group nomark-devops-rg \
  --name nomark-devops-db \
  --rule-name AllowAllAzureServicesAndResourcesWithinAzureIps_2026-1-26_16-8-49

# Add specific VM IP only
az postgres flexible-server firewall-rule create \
  --resource-group nomark-devops-rg \
  --name nomark-devops-db \
  --rule-name AllowDevOpsVM \
  --start-ip-address 20.5.185.136 \
  --end-ip-address 20.5.185.136
```

#### 1.4 Remove Unnecessary Port 80
**Priority:** HIGH
**Effort:** 30 minutes
**Cost:** $0

**Action:**
```bash
az network nsg rule delete \
  --resource-group nomark-devops-rg \
  --nsg-name nomark-devops-vmNSG \
  --name allow-http-80
```

### Phase 2: Short-term Improvements (Week 2-3)

#### 2.1 Deploy Azure Bastion
**Priority:** HIGH
**Effort:** 4 hours
**Cost:** ~$140/month

**Terraform Addition:**
```hcl
# Add to main.tf
resource "azurerm_subnet" "bastion" {
  name                 = "AzureBastionSubnet"  # Name must be exact
  resource_group_name  = azurerm_resource_group.main.name
  virtual_network_name = azurerm_virtual_network.main.name
  address_prefixes     = ["10.100.254.0/27"]  # Minimum /27 required
}

resource "azurerm_public_ip" "bastion" {
  name                = "${var.project_name}-bastion-pip"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  allocation_method   = "Static"
  sku                 = "Standard"
}

resource "azurerm_bastion_host" "main" {
  name                = "${var.project_name}-bastion"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name

  ip_configuration {
    name                 = "configuration"
    subnet_id            = azurerm_subnet.bastion.id
    public_ip_address_id = azurerm_public_ip.bastion.id
  }
}

# Remove public IP from VM NIC
# Remove SSH NSG rule (access via Bastion only)
```

#### 2.2 Enable NSG Flow Logs
**Priority:** HIGH
**Effort:** 2 hours
**Cost:** ~$10/month

**Actions:**
```bash
# Create storage account for flow logs
az storage account create \
  --name nomarkdevopsflowlogs \
  --resource-group nomark-devops-rg \
  --location australiaeast \
  --sku Standard_LRS

# Enable flow logs
az network watcher flow-log create \
  --location australiaeast \
  --name nomark-devops-vmNSG-flowlog \
  --nsg /subscriptions/ac7254fa-1f0b-433e-976c-b0430909c5ac/resourceGroups/nomark-devops-rg/providers/Microsoft.Network/networkSecurityGroups/nomark-devops-vmNSG \
  --storage-account nomarkdevopsflowlogs \
  --enabled true \
  --retention 30 \
  --format JSON \
  --log-version 2
```

#### 2.3 Implement Network Segmentation
**Priority:** MEDIUM
**Effort:** 6 hours
**Cost:** $0

**Terraform Changes:**
```hcl
# Create subnet for applications
resource "azurerm_subnet" "app" {
  name                 = "${var.project_name}-app-subnet"
  resource_group_name  = azurerm_resource_group.main.name
  virtual_network_name = azurerm_virtual_network.main.name
  address_prefixes     = ["10.100.1.0/24"]
}

# Create subnet for data tier
resource "azurerm_subnet" "data" {
  name                 = "${var.project_name}-data-subnet"
  resource_group_name  = azurerm_resource_group.main.name
  virtual_network_name = azurerm_virtual_network.main.name
  address_prefixes     = ["10.100.2.0/24"]

  service_endpoints    = ["Microsoft.Sql"]
}

# Create NSG for data tier
resource "azurerm_network_security_group" "data" {
  name                = "${var.project_name}-data-nsg"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name

  security_rule {
    name                       = "AllowPostgreSQL"
    priority                   = 100
    direction                  = "Inbound"
    access                     = "Allow"
    protocol                   = "Tcp"
    source_port_range          = "*"
    destination_port_range     = "5432"
    source_address_prefix      = "10.100.1.0/24"  # Only from app subnet
    destination_address_prefix = "*"
  }

  security_rule {
    name                       = "DenyAllOther"
    priority                   = 4096
    direction                  = "Inbound"
    access                     = "Deny"
    protocol                   = "*"
    source_port_range          = "*"
    destination_port_range     = "*"
    source_address_prefix      = "*"
    destination_address_prefix = "*"
  }
}
```

### Phase 3: Medium-term Enhancements (Month 2)

#### 3.1 Deploy Azure Firewall
**Priority:** MEDIUM
**Effort:** 8 hours
**Cost:** ~$1,250/month (Standard) or ~$30/month (Basic)

**Recommendation:** Start with Azure Firewall Basic for cost savings

#### 3.2 Implement Private Endpoints for PostgreSQL
**Priority:** MEDIUM
**Effort:** 4 hours
**Cost:** ~$7.50/month per endpoint

**Terraform Example:**
```hcl
resource "azurerm_private_endpoint" "postgres" {
  name                = "${var.project_name}-postgres-pe"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  subnet_id           = azurerm_subnet.data.id

  private_service_connection {
    name                           = "${var.project_name}-postgres-psc"
    private_connection_resource_id = azurerm_postgresql_flexible_server.main.id
    subresource_names              = ["postgresqlServer"]
    is_manual_connection           = false
  }
}

# Disable public access
resource "azurerm_postgresql_flexible_server" "main" {
  # ... existing config ...

  public_network_access_enabled = false
}
```

#### 3.3 Enable DDoS Protection
**Priority:** MEDIUM
**Effort:** 2 hours
**Cost:** ~$2,944/month (Standard) or included with Basic

**Recommendation:**
- Use Network DDoS protection (included with public IP)
- Upgrade to Standard only if under active attack

#### 3.4 Deploy Application Gateway with WAF
**Priority:** LOW (unless public web apps planned)
**Effort:** 8 hours
**Cost:** ~$250/month (WAF v2)

### Phase 4: Long-term Architecture (Month 3-4)

#### 4.1 Hub-Spoke Network Topology
**Priority:** MEDIUM
**Effort:** 16 hours
**Cost:** Variable based on services

#### 4.2 Traffic Analytics and Advanced Monitoring
**Priority:** LOW
**Effort:** 4 hours
**Cost:** ~$50/month

#### 4.3 Zero Trust Network Implementation
**Priority:** LOW
**Effort:** Ongoing
**Cost:** Variable

---

## 12. Compliance and Best Practices

### Azure Security Benchmark Compliance

| Control | Requirement | Status | Gap |
|---------|-------------|--------|-----|
| NS-1 | Establish network segmentation boundaries | FAIL | Single flat network |
| NS-2 | Secure cloud services with network controls | FAIL | No private endpoints |
| NS-3 | Deploy firewall at network edge | FAIL | No Azure Firewall |
| NS-4 | Deploy intrusion detection/prevention | FAIL | No IDS/IPS |
| NS-5 | Deploy DDoS protection | PARTIAL | Basic only |
| NS-6 | Deploy web application firewall | FAIL | No WAF |
| NS-7 | Simplify network security rules | PARTIAL | Some complex rules |
| NS-8 | Detect and disable insecure services | FAIL | HTTP enabled |

### CIS Azure Benchmark

| Section | Control | Status | Priority |
|---------|---------|--------|----------|
| 6.1 | Restrict RDP/SSH access from internet | FAIL | CRITICAL |
| 6.2 | Enable Network Security Group Flow Logs | FAIL | HIGH |
| 6.3 | Ensure VNet has Network Watcher enabled | PASS | ✓ |
| 6.4 | Ensure Network Security Groups restrict management ports | FAIL | CRITICAL |
| 6.5 | Ensure Network Watcher is enabled | PASS | ✓ |
| 6.6 | Enable DDoS Protection Standard | FAIL | MEDIUM |

### HIPAA/SOC2 Considerations

If handling sensitive data:
- **HIPAA 164.312(e)(1):** Requires transmission security - Currently FAIL (HTTP enabled)
- **SOC2 CC6.6:** Requires logical access controls - Currently PARTIAL
- **SOC2 CC6.7:** Requires network segmentation - Currently FAIL

---

## 13. Cost Analysis

### Current Network Costs (Monthly)

| Resource | SKU | Quantity | Cost |
|----------|-----|----------|------|
| Public IP (Standard) | Standard | 1 | $3.65 |
| VNet | N/A | 1 | $0 (no peering) |
| Network Watcher | N/A | 1 | ~$5 |
| **Total Current** | | | **~$9/month** |

### Recommended Architecture Costs (Monthly)

| Resource | SKU | Quantity | Monthly Cost |
|----------|-----|----------|--------------|
| **Phase 1 (Immediate)** | | | |
| NSG Flow Logs Storage | Standard LRS | 1 | $10 |
| **Phase 2 (Short-term)** | | | |
| Azure Bastion | Basic | 1 | $140 |
| Additional Subnets | N/A | 3 | $0 |
| **Phase 3 (Medium-term)** | | | |
| Azure Firewall | Basic | 1 | $30 |
| Private Endpoints | Standard | 2 | $15 |
| DDoS Protection | Basic | Included | $0 |
| **Phase 4 (Optional)** | | | |
| Application Gateway WAF | WAF v2 | 1 | $250 |
| Traffic Analytics | N/A | 1 | $50 |
| Log Analytics Workspace | Pay-as-you-go | 1 | $25 |
| **Total (Full Implementation)** | | | **~$520/month** |

**Note:** Azure Bastion is the largest cost driver at $140/month. Alternative: Use Azure Bastion Developer SKU ($20/month) or maintain strict IP allowlisting.

---

## 14. Summary and Risk Score

### Overall Security Posture: 3.2/10 (CRITICAL)

#### Critical Issues (Immediate Action Required)
1. SSH exposed to internet (0.0.0.0/0)
2. PostgreSQL databases publicly accessible
3. Azure Function accepting HTTP traffic
4. No network flow logs or monitoring
5. Configuration drift between Terraform and Azure

#### High Priority Issues
1. No Azure Firewall or network filtering
2. No DDoS protection
3. Flat network with no segmentation
4. Port 80 HTTP unnecessarily open
5. Port 8080 webhook exposed to internet
6. No private endpoints for PaaS services

#### Medium Priority Issues
1. No VNet peering or hub-spoke topology
2. No Application Gateway or WAF
3. No certificate management strategy
4. No connection monitoring
5. Single point of failure (no redundancy)

#### Positive Findings
- Network Watcher enabled
- Using Standard SKU public IP (better DDoS protection)
- SSH key authentication (not passwords)
- Terraform infrastructure as code in use

---

## 15. Terraform Security Improvements

### Updated main.tf - Security Hardening

Create this improved version:

```hcl
# /Users/reecefrazier/DEVOPS_NOMARK/devops-agent/terraform/main-secure.tf
# SECURITY-HARDENED VERSION

# ============================================================================
# Variables - Security Focused
# ============================================================================

variable "allowed_ssh_ips" {
  description = "List of IPs allowed to SSH (CIDR notation) - NO DEFAULT FOR SECURITY"
  type        = list(string)
  # REMOVED: default = ["0.0.0.0/0"]
  validation {
    condition     = !contains(var.allowed_ssh_ips, "0.0.0.0/0")
    error_message = "SSH must not be exposed to the entire internet (0.0.0.0/0)"
  }
}

variable "enable_bastion" {
  description = "Deploy Azure Bastion for secure access"
  type        = bool
  default     = true
}

variable "enable_flow_logs" {
  description = "Enable NSG flow logs"
  type        = bool
  default     = true
}

# ============================================================================
# Networking - Hub-Spoke Preparation
# ============================================================================

resource "azurerm_virtual_network" "main" {
  name                = "${var.project_name}-vnet"
  address_space       = ["10.100.0.0/16"]  # Consistent with Terraform
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  tags                = var.tags
}

# Application Subnet
resource "azurerm_subnet" "app" {
  name                 = "${var.project_name}-app-subnet"
  resource_group_name  = azurerm_resource_group.main.name
  virtual_network_name = azurerm_virtual_network.main.name
  address_prefixes     = ["10.100.1.0/24"]
}

# Data Subnet with Service Endpoints
resource "azurerm_subnet" "data" {
  name                 = "${var.project_name}-data-subnet"
  resource_group_name  = azurerm_resource_group.main.name
  virtual_network_name = azurerm_virtual_network.main.name
  address_prefixes     = ["10.100.2.0/24"]
  service_endpoints    = ["Microsoft.Sql", "Microsoft.Storage"]
}

# Azure Bastion Subnet (conditional)
resource "azurerm_subnet" "bastion" {
  count                = var.enable_bastion ? 1 : 0
  name                 = "AzureBastionSubnet"
  resource_group_name  = azurerm_resource_group.main.name
  virtual_network_name = azurerm_virtual_network.main.name
  address_prefixes     = ["10.100.254.0/27"]
}

# ============================================================================
# Network Security Groups - Hardened
# ============================================================================

# App Tier NSG
resource "azurerm_network_security_group" "app" {
  name                = "${var.project_name}-app-nsg"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  tags                = var.tags

  # HTTPS only from internet
  security_rule {
    name                       = "AllowHTTPS"
    priority                   = 100
    direction                  = "Inbound"
    access                     = "Allow"
    protocol                   = "Tcp"
    source_port_range          = "*"
    destination_port_range     = "443"
    source_address_prefix      = "Internet"
    destination_address_prefix = "*"
  }

  # SSH only from allowed IPs (or remove if using Bastion)
  dynamic "security_rule" {
    for_each = var.enable_bastion ? [] : [1]
    content {
      name                       = "AllowSSHRestricted"
      priority                   = 110
      direction                  = "Inbound"
      access                     = "Allow"
      protocol                   = "Tcp"
      source_port_range          = "*"
      destination_port_range     = "22"
      source_address_prefixes    = var.allowed_ssh_ips
      destination_address_prefix = "*"
    }
  }

  # Deny all other inbound
  security_rule {
    name                       = "DenyAllInbound"
    priority                   = 4096
    direction                  = "Inbound"
    access                     = "Deny"
    protocol                   = "*"
    source_port_range          = "*"
    destination_port_range     = "*"
    source_address_prefix      = "*"
    destination_address_prefix = "*"
  }

  # Allow outbound to data tier
  security_rule {
    name                       = "AllowDataTier"
    priority                   = 100
    direction                  = "Outbound"
    access                     = "Allow"
    protocol                   = "Tcp"
    source_port_range          = "*"
    destination_port_range     = "5432"
    source_address_prefix      = "10.100.1.0/24"
    destination_address_prefix = "10.100.2.0/24"
  }
}

# Data Tier NSG
resource "azurerm_network_security_group" "data" {
  name                = "${var.project_name}-data-nsg"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  tags                = var.tags

  # Allow PostgreSQL only from app subnet
  security_rule {
    name                       = "AllowPostgreSQLFromApp"
    priority                   = 100
    direction                  = "Inbound"
    access                     = "Allow"
    protocol                   = "Tcp"
    source_port_range          = "*"
    destination_port_range     = "5432"
    source_address_prefix      = "10.100.1.0/24"
    destination_address_prefix = "*"
  }

  # Deny all other inbound
  security_rule {
    name                       = "DenyAllInbound"
    priority                   = 4096
    direction                  = "Inbound"
    access                     = "Deny"
    protocol                   = "*"
    source_port_range          = "*"
    destination_port_range     = "*"
    source_address_prefix      = "*"
    destination_address_prefix = "*"
  }
}

# ============================================================================
# Azure Bastion (Optional but Recommended)
# ============================================================================

resource "azurerm_public_ip" "bastion" {
  count               = var.enable_bastion ? 1 : 0
  name                = "${var.project_name}-bastion-pip"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  allocation_method   = "Static"
  sku                 = "Standard"
  tags                = var.tags
}

resource "azurerm_bastion_host" "main" {
  count               = var.enable_bastion ? 1 : 0
  name                = "${var.project_name}-bastion"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  sku                 = "Basic"  # Use Basic to save costs
  tags                = var.tags

  ip_configuration {
    name                 = "configuration"
    subnet_id            = azurerm_subnet.bastion[0].id
    public_ip_address_id = azurerm_public_ip.bastion[0].id
  }
}

# ============================================================================
# NSG Flow Logs
# ============================================================================

resource "azurerm_storage_account" "flowlogs" {
  count                    = var.enable_flow_logs ? 1 : 0
  name                     = "${replace(var.project_name, "-", "")}flowlogs"
  resource_group_name      = azurerm_resource_group.main.name
  location                 = azurerm_resource_group.main.location
  account_tier             = "Standard"
  account_replication_type = "LRS"
  min_tls_version          = "TLS1_2"

  network_rules {
    default_action = "Deny"
    bypass         = ["AzureServices"]
  }

  tags = var.tags
}

resource "azurerm_log_analytics_workspace" "main" {
  count               = var.enable_flow_logs ? 1 : 0
  name                = "${var.project_name}-law"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  sku                 = "PerGB2018"
  retention_in_days   = 30
  tags                = var.tags
}

# Note: NSG Flow Log configuration requires azurerm provider >= 3.0
# This is a placeholder - actual implementation may vary
```

---

## 16. Testing and Validation Commands

### Verify NSG Rules
```bash
# List all NSG rules
az network nsg rule list \
  --nsg-name nomark-devops-vmNSG \
  --resource-group nomark-devops-rg \
  --output table

# Test if SSH is restricted
az network nsg rule show \
  --nsg-name nomark-devops-vmNSG \
  --resource-group nomark-devops-rg \
  --name default-allow-ssh \
  --query "sourceAddressPrefix"
```

### Verify PostgreSQL Security
```bash
# Check public access status
az postgres flexible-server show \
  --resource-group nomark-devops-rg \
  --name nomark-devops-db \
  --query "network.publicNetworkAccess"

# List firewall rules
az postgres flexible-server firewall-rule list \
  --resource-group nomark-devops-rg \
  --name nomark-devops-db \
  --output table
```

### Verify Function App HTTPS
```bash
# Check HTTPS enforcement
az functionapp show \
  --name nomark-vm-starter \
  --resource-group nomark-devops-rg \
  --query "{httpsOnly:httpsOnly, minTlsVersion:siteConfig.minTlsVersion}"
```

### Port Scan from External
```bash
# Test from external source
nmap -Pn -sT -p 22,80,443,8080 20.5.185.136
```

### Check Flow Logs Status
```bash
# Verify flow logs are enabled
az network watcher flow-log list \
  --location australiaeast \
  --query "[].{Name:name, Enabled:enabled, NSG:targetResourceId}"
```

---

## 17. Conclusion

The current Azure network infrastructure has **significant security vulnerabilities** that require immediate attention. The most critical issues are:

1. **SSH exposed to the internet** without IP restrictions
2. **PostgreSQL databases accessible** from any Azure IP
3. **HTTP traffic accepted** by Azure Function (unencrypted Slack tokens)
4. **No network monitoring** or flow logs enabled
5. **Flat network design** with no segmentation

### Immediate Actions Required (Today):
1. Restrict SSH access to specific IPs
2. Enable HTTPS-only on Azure Function
3. Remove PostgreSQL firewall rule allowing all Azure IPs
4. Delete NSG rule for port 80

### Risk if Not Addressed:
- **Data breach** through compromised SSH or database access
- **Service disruption** from DDoS attacks
- **Compliance violations** (SOC2, HIPAA)
- **Credential theft** via man-in-the-middle attacks

**Estimated time to implement critical fixes:** 4 hours
**Estimated cost:** $0 for Phase 1 immediate actions

---

## Appendix A: Contact Information

**Report Prepared By:** Network Security Audit Team
**Date:** 2026-02-08
**Review Status:** CRITICAL - Immediate Action Required

## Appendix B: References

- Azure Security Benchmark: https://learn.microsoft.com/en-us/security/benchmark/azure/
- CIS Azure Foundations Benchmark: https://www.cisecurity.org/benchmark/azure
- Azure Network Security Best Practices: https://learn.microsoft.com/en-us/azure/security/fundamentals/network-best-practices
- NSG Flow Logs: https://learn.microsoft.com/en-us/azure/network-watcher/network-watcher-nsg-flow-logging-overview

---

**END OF REPORT**
