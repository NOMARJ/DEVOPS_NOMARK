# ============================================================================
# DevOps Agent - Autonomous Development VM
# ============================================================================
# A standalone, event-driven development agent that runs Claude Code
# autonomously via Slack commands and n8n orchestration.
#
# Usage:
#   terraform init
#   terraform plan -var-file="secrets.tfvars"
#   terraform apply -var-file="secrets.tfvars"
# ============================================================================

terraform {
  required_version = ">= 1.0"
  
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.80"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.5"
    }
  }
  
  # Optional: Store state in Azure Storage
  # backend "azurerm" {
  #   resource_group_name  = "devops-tfstate"
  #   storage_account_name = "devopstfstate"
  #   container_name       = "tfstate"
  #   key                  = "devops-agent.tfstate"
  # }
}

provider "azurerm" {
  features {
    resource_group {
      prevent_deletion_if_contains_resources = false
    }
  }
}

# ============================================================================
# Variables
# ============================================================================

variable "project_name" {
  description = "Project name prefix for all resources"
  type        = string
  default     = "devops-agent"
}

variable "location" {
  description = "Azure region"
  type        = string
  default     = "australiaeast"
}

variable "vm_size" {
  description = "Azure VM size"
  type        = string
  default     = "Standard_B4ms"  # 4 vCPU, 16GB RAM, burstable
}

variable "admin_username" {
  description = "Admin username for the VM"
  type        = string
  default     = "devops"
}

variable "ssh_public_key" {
  description = "SSH public key for VM access"
  type        = string
}

variable "anthropic_api_key" {
  description = "Anthropic API key for Claude Code"
  type        = string
  sensitive   = true
}

variable "github_token" {
  description = "GitHub Personal Access Token for repo access"
  type        = string
  sensitive   = true
}

variable "n8n_webhook_base_url" {
  description = "Base URL for n8n webhooks (e.g., https://n8n.yourdomain.com/webhook)"
  type        = string
}

variable "devops_agent_repo" {
  description = "URL of the devops-agent repo (for syncing skills)"
  type        = string
  default     = ""
}

variable "default_repo_url" {
  description = "Default repository URL for development tasks"
  type        = string
}

variable "allowed_ssh_ips" {
  description = "List of IPs allowed to SSH (CIDR notation)"
  type        = list(string)
  default     = ["0.0.0.0/0"]  # Restrict in production!
}

variable "auto_shutdown_time" {
  description = "Daily auto-shutdown time in UTC (HH:MM)"
  type        = string
  default     = "1900"  # 7 PM UTC = 5 AM AEST next day
}

variable "tags" {
  description = "Tags to apply to all resources"
  type        = map(string)
  default = {
    Environment = "development"
    Purpose     = "autonomous-dev-agent"
    ManagedBy   = "terraform"
  }
}

# ============================================================================
# Resource Group
# ============================================================================

resource "azurerm_resource_group" "main" {
  name     = "${var.project_name}-rg"
  location = var.location
  tags     = var.tags
}

# ============================================================================
# Networking
# ============================================================================

resource "azurerm_virtual_network" "main" {
  name                = "${var.project_name}-vnet"
  address_space       = ["10.100.0.0/16"]
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  tags                = var.tags
}

resource "azurerm_subnet" "main" {
  name                 = "${var.project_name}-subnet"
  resource_group_name  = azurerm_resource_group.main.name
  virtual_network_name = azurerm_virtual_network.main.name
  address_prefixes     = ["10.100.1.0/24"]
}

resource "azurerm_public_ip" "main" {
  name                = "${var.project_name}-pip"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  allocation_method   = "Static"
  sku                 = "Standard"
  tags                = var.tags
}

resource "azurerm_network_security_group" "main" {
  name                = "${var.project_name}-nsg"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  tags                = var.tags

  # SSH access
  security_rule {
    name                       = "SSH"
    priority                   = 100
    direction                  = "Inbound"
    access                     = "Allow"
    protocol                   = "Tcp"
    source_port_range          = "*"
    destination_port_range     = "22"
    source_address_prefixes    = var.allowed_ssh_ips
    destination_address_prefix = "*"
  }

  # Webhook listener (for n8n triggers)
  security_rule {
    name                       = "Webhook"
    priority                   = 110
    direction                  = "Inbound"
    access                     = "Allow"
    protocol                   = "Tcp"
    source_port_range          = "*"
    destination_port_range     = "9000"
    source_address_prefix      = "*"
    destination_address_prefix = "*"
  }
}

resource "azurerm_network_interface" "main" {
  name                = "${var.project_name}-nic"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  tags                = var.tags

  ip_configuration {
    name                          = "internal"
    subnet_id                     = azurerm_subnet.main.id
    private_ip_address_allocation = "Dynamic"
    public_ip_address_id          = azurerm_public_ip.main.id
  }
}

resource "azurerm_network_interface_security_group_association" "main" {
  network_interface_id      = azurerm_network_interface.main.id
  network_security_group_id = azurerm_network_security_group.main.id
}

# ============================================================================
# Virtual Machine
# ============================================================================

resource "azurerm_linux_virtual_machine" "main" {
  name                = "${var.project_name}-vm"
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  size                = var.vm_size
  admin_username      = var.admin_username
  tags                = var.tags

  network_interface_ids = [
    azurerm_network_interface.main.id
  ]

  admin_ssh_key {
    username   = var.admin_username
    public_key = var.ssh_public_key
  }

  os_disk {
    caching              = "ReadWrite"
    storage_account_type = "Premium_LRS"
    disk_size_gb         = 128
  }

  source_image_reference {
    publisher = "Canonical"
    offer     = "0001-com-ubuntu-server-jammy"
    sku       = "22_04-lts-gen2"
    version   = "latest"
  }

  custom_data = base64encode(local.cloud_init_config)

  identity {
    type = "SystemAssigned"
  }
}

# Auto-shutdown schedule (cost savings)
resource "azurerm_dev_test_global_vm_shutdown_schedule" "main" {
  virtual_machine_id = azurerm_linux_virtual_machine.main.id
  location           = azurerm_resource_group.main.location
  enabled            = true

  daily_recurrence_time = var.auto_shutdown_time
  timezone              = "UTC"

  notification_settings {
    enabled = false
  }

  tags = var.tags
}

# ============================================================================
# Cloud-Init Configuration
# ============================================================================

locals {
  cloud_init_config = <<-EOF
#cloud-config
package_update: true
package_upgrade: true

packages:
  - git
  - curl
  - wget
  - jq
  - tmux
  - htop
  - unzip
  - build-essential
  - python3
  - python3-pip
  - python3-venv
  - nginx  # For webhook listener

# Create user directories
runcmd:
  # Install Node.js 20 LTS
  - curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
  - apt-get install -y nodejs
  
  # Install pnpm
  - npm install -g pnpm
  
  # Install Claude Code CLI
  - npm install -g @anthropic-ai/claude-code
  
  # Create directories
  - mkdir -p /home/${var.admin_username}/{repos,logs,scripts}
  - chown -R ${var.admin_username}:${var.admin_username} /home/${var.admin_username}
  
  # Set up environment
  - |
    cat > /home/${var.admin_username}/.devops-env << 'ENVFILE'
    export ANTHROPIC_API_KEY="${var.anthropic_api_key}"
    export GITHUB_TOKEN="${var.github_token}"
    export N8N_WEBHOOK_BASE_URL="${var.n8n_webhook_base_url}"
    export REPOS_DIR="/home/${var.admin_username}/repos"
    export LOGS_DIR="/home/${var.admin_username}/logs"
    ENVFILE
  - chown ${var.admin_username}:${var.admin_username} /home/${var.admin_username}/.devops-env
  - chmod 600 /home/${var.admin_username}/.devops-env
  
  # Add to bashrc
  - echo 'source ~/.devops-env' >> /home/${var.admin_username}/.bashrc
  
  # Set up Git
  - |
    su - ${var.admin_username} -c "git config --global credential.helper store"
    su - ${var.admin_username} -c "git config --global user.email 'devops-agent@flowmetrics.io'"
    su - ${var.admin_username} -c "git config --global user.name 'DevOps Agent'"
  
  # Configure Git to use token
  - |
    echo "https://${var.github_token}@github.com" > /home/${var.admin_username}/.git-credentials
    chown ${var.admin_username}:${var.admin_username} /home/${var.admin_username}/.git-credentials
    chmod 600 /home/${var.admin_username}/.git-credentials
  
  # Set up webhook listener service
  - systemctl daemon-reload
  - systemctl enable devops-webhook
  - systemctl start devops-webhook
  
  # Signal completion
  - curl -s -X POST "${var.n8n_webhook_base_url}/vm-ready" -H "Content-Type: application/json" -d '{"status":"ready","vm":"${var.project_name}"}' || true

write_files:
  # Main task runner script
  - path: /home/${var.admin_username}/scripts/run-task.sh
    permissions: '0755'
    owner: ${var.admin_username}:${var.admin_username}
    content: |
      #!/bin/bash
      # =======================================================================
      # DevOps Agent Task Runner
      # Executes Claude Code with Ralph orchestration
      # =======================================================================
      
      set -e
      source /home/${var.admin_username}/.devops-env
      
      # Arguments
      TASK_ID="$${1:-$(date +%s)}"
      REPO_URL="$${2}"
      REPO_BRANCH="$${3:-main}"
      PRD_PATH="$${4:-ralph/scripts/ralph}"
      STORY_COUNT="$${5:-5}"
      
      LOG_FILE="$LOGS_DIR/task-$TASK_ID.log"
      
      log() {
        echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] $1" | tee -a "$LOG_FILE"
      }
      
      notify() {
        local status="$1"
        local message="$2"
        local extra="$${3:-{}}"
        
        curl -s -X POST "$N8N_WEBHOOK_BASE_URL/task-progress" \
          -H "Content-Type: application/json" \
          -d "{
            \"task_id\": \"$TASK_ID\",
            \"status\": \"$status\",
            \"message\": \"$message\",
            \"timestamp\": \"$(date -u +%Y-%m-%dT%H:%M:%SZ)\",
            \"extra\": $extra
          }" || true
      }
      
      # Extract repo name from URL
      REPO_NAME=$(basename "$REPO_URL" .git)
      REPO_DIR="$REPOS_DIR/$REPO_NAME"
      
      log "Starting task $TASK_ID"
      log "Repo: $REPO_URL (branch: $REPO_BRANCH)"
      log "PRD Path: $PRD_PATH"
      log "Stories: $STORY_COUNT"
      
      notify "started" "Task started" "{\"repo\": \"$REPO_NAME\", \"stories\": $STORY_COUNT}"
      
      # Clone or update repo
      if [ -d "$REPO_DIR" ]; then
        log "Updating existing repo..."
        cd "$REPO_DIR"
        git fetch origin
        git checkout "$REPO_BRANCH"
        git pull origin "$REPO_BRANCH"
      else
        log "Cloning repo..."
        git clone --branch "$REPO_BRANCH" "$REPO_URL" "$REPO_DIR"
        cd "$REPO_DIR"
      fi
      
      # Check if Ralph exists
      RALPH_SCRIPT="$REPO_DIR/$PRD_PATH/ralph.sh"
      if [ ! -f "$RALPH_SCRIPT" ]; then
        log "ERROR: Ralph script not found at $RALPH_SCRIPT"
        notify "error" "Ralph script not found" "{\"path\": \"$RALPH_SCRIPT\"}"
        exit 1
      fi
      
      # Make Ralph executable
      chmod +x "$RALPH_SCRIPT"
      
      # Run Ralph with Claude Code
      log "Running Ralph..."
      notify "running" "Executing stories..."
      
      cd "$(dirname "$RALPH_SCRIPT")/.."
      
      # Run Ralph and capture output
      export TASK_ID
      export N8N_WEBHOOK_BASE_URL
      
      if ./scripts/ralph/ralph.sh --tool claude "$STORY_COUNT" 2>&1 | tee -a "$LOG_FILE"; then
        log "Ralph completed successfully"
        notify "completed" "All stories completed" "{\"stories_completed\": $STORY_COUNT}"
      else
        log "Ralph failed"
        notify "error" "Ralph execution failed" "{\"log\": \"$LOG_FILE\"}"
        exit 1
      fi
      
      log "Task $TASK_ID finished"

  # Webhook listener using Python (simple HTTP server)
  - path: /home/${var.admin_username}/scripts/webhook-server.py
    permissions: '0755'
    owner: ${var.admin_username}:${var.admin_username}
    content: |
      #!/usr/bin/env python3
      """
      Simple webhook server for receiving task triggers from n8n.
      Listens on port 9000 and spawns task runner processes.
      """
      
      import json
      import subprocess
      import os
      from http.server import HTTPServer, BaseHTTPRequestHandler
      from urllib.parse import parse_qs
      import threading
      
      PORT = 9000
      SCRIPTS_DIR = os.path.expanduser("~/scripts")
      
      class WebhookHandler(BaseHTTPRequestHandler):
          def do_POST(self):
              content_length = int(self.headers.get('Content-Length', 0))
              body = self.rfile.read(content_length).decode('utf-8')
              
              try:
                  data = json.loads(body) if body else {}
              except json.JSONDecodeError:
                  self.send_error(400, "Invalid JSON")
                  return
              
              if self.path == '/trigger':
                  self.handle_trigger(data)
              elif self.path == '/health':
                  self.send_json({"status": "healthy"})
              else:
                  self.send_error(404, "Not found")
          
          def do_GET(self):
              if self.path == '/health':
                  self.send_json({"status": "healthy"})
              else:
                  self.send_error(404, "Not found")
          
          def handle_trigger(self, data):
              task_id = data.get('task_id', 'unknown')
              repo_url = data.get('repo_url')
              repo_branch = data.get('repo_branch', 'main')
              prd_path = data.get('prd_path', 'ralph/scripts/ralph')
              story_count = data.get('story_count', 5)
              
              if not repo_url:
                  self.send_error(400, "repo_url is required")
                  return
              
              # Run task in background
              cmd = [
                  f"{SCRIPTS_DIR}/run-task.sh",
                  str(task_id),
                  repo_url,
                  repo_branch,
                  prd_path,
                  str(story_count)
              ]
              
              def run_task():
                  subprocess.Popen(
                      cmd,
                      stdout=open(f"/home/${var.admin_username}/logs/task-{task_id}.log", 'a'),
                      stderr=subprocess.STDOUT,
                      start_new_session=True
                  )
              
              thread = threading.Thread(target=run_task)
              thread.start()
              
              self.send_json({
                  "status": "accepted",
                  "task_id": task_id,
                  "message": "Task queued for execution"
              })
          
          def send_json(self, data):
              self.send_response(200)
              self.send_header('Content-Type', 'application/json')
              self.end_headers()
              self.wfile.write(json.dumps(data).encode())
          
          def log_message(self, format, *args):
              pass  # Suppress default logging
      
      if __name__ == '__main__':
          server = HTTPServer(('0.0.0.0', PORT), WebhookHandler)
          print(f"Webhook server running on port {PORT}")
          server.serve_forever()

  # Systemd service for webhook listener
  - path: /etc/systemd/system/devops-webhook.service
    permissions: '0644'
    content: |
      [Unit]
      Description=DevOps Agent Webhook Listener
      After=network.target
      
      [Service]
      Type=simple
      User=${var.admin_username}
      WorkingDirectory=/home/${var.admin_username}
      ExecStart=/usr/bin/python3 /home/${var.admin_username}/scripts/webhook-server.py
      Restart=always
      RestartSec=10
      Environment="HOME=/home/${var.admin_username}"
      
      [Install]
      WantedBy=multi-user.target

  # Health check script
  - path: /home/${var.admin_username}/scripts/health-check.sh
    permissions: '0755'
    owner: ${var.admin_username}:${var.admin_username}
    content: |
      #!/bin/bash
      # Quick health check
      
      echo "=== DevOps Agent Health Check ==="
      echo "Hostname: $(hostname)"
      echo "Uptime: $(uptime -p)"
      echo "Memory: $(free -h | grep Mem | awk '{print $3 "/" $2}')"
      echo "Disk: $(df -h / | tail -1 | awk '{print $3 "/" $2 " (" $5 " used)"}')"
      echo ""
      echo "Services:"
      systemctl is-active devops-webhook && echo "  ✅ Webhook listener running" || echo "  ❌ Webhook listener stopped"
      echo ""
      echo "Tools:"
      node --version && echo "  ✅ Node.js installed"
      claude --version 2>/dev/null && echo "  ✅ Claude Code installed" || echo "  ❌ Claude Code not found"
      git --version && echo "  ✅ Git installed"
EOF
}

# ============================================================================
# Outputs
# ============================================================================

output "resource_group_name" {
  value = azurerm_resource_group.main.name
}

output "vm_name" {
  value = azurerm_linux_virtual_machine.main.name
}

output "vm_public_ip" {
  value = azurerm_public_ip.main.ip_address
}

output "ssh_command" {
  value = "ssh ${var.admin_username}@${azurerm_public_ip.main.ip_address}"
}

output "webhook_url" {
  value = "http://${azurerm_public_ip.main.ip_address}:9000/trigger"
}

output "health_check_url" {
  value = "http://${azurerm_public_ip.main.ip_address}:9000/health"
}

output "vm_start_command" {
  value = "az vm start --resource-group ${azurerm_resource_group.main.name} --name ${azurerm_linux_virtual_machine.main.name}"
}

output "vm_stop_command" {
  value = "az vm deallocate --resource-group ${azurerm_resource_group.main.name} --name ${azurerm_linux_virtual_machine.main.name}"
}
