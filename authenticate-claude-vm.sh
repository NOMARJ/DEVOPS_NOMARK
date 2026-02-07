#!/bin/bash
#
# Authenticate Claude CLI on Azure VM with your Claude Max subscription
# This will allow the Slack bot to use your Claude Max instead of API credits
#

set -e

VM_IP="20.5.185.136"
VM_USER="devops"

echo "=========================================="
echo "Claude Max Authentication Setup"
echo "=========================================="
echo ""
echo "This will authenticate the Claude CLI on your Azure VM"
echo "with your Claude Max subscription."
echo ""
echo "VM: $VM_USER@$VM_IP"
echo ""

read -p "Continue? (y/n): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Cancelled"
    exit 0
fi

echo ""
echo "Step 1: Opening SSH session to VM..."
echo "You will be prompted to run 'claude auth login' on the VM"
echo ""
echo "Instructions:"
echo "  1. When prompted, run: claude auth login"
echo "  2. The CLI will show a URL and code"
echo "  3. Open the URL in your browser"
echo "  4. Log in with your Claude.ai account (with Claude Max)"
echo "  5. Enter the code shown by the CLI"
echo "  6. Wait for 'Authentication successful!'"
echo "  7. Type 'exit' to return to your local machine"
echo ""

read -p "Press Enter to connect to VM..."

# SSH to VM with instructions
ssh -t "$VM_USER@$VM_IP" << 'ENDSSH'
echo "=========================================="
echo "You are now connected to the Azure VM"
echo "=========================================="
echo ""

# Check current status
echo "Current Claude CLI status:"
claude auth status 2>&1 || echo "Not authenticated"
echo ""

# Prompt for authentication
echo "Step 1: Authenticate with your Claude Max account"
echo "Run this command:"
echo ""
echo "  claude auth login"
echo ""
echo "Then follow the browser prompts."
echo ""

# Keep shell open for user to authenticate
echo "When done, verify with: claude auth status"
echo "Then type: exit"
echo ""

exec bash
ENDSSH

echo ""
echo "=========================================="
echo "Verification"
echo "=========================================="
echo ""

# Verify authentication
echo "Checking if Claude CLI is now authenticated..."
ssh "$VM_USER@$VM_IP" "claude auth status" 2>&1

echo ""
echo "Testing Claude CLI..."
ssh "$VM_USER@$VM_IP" 'claude "respond with exactly: Test successful"' 2>&1

echo ""
echo "=========================================="
echo "✓ Setup Complete!"
echo "=========================================="
echo ""
echo "Your Slack bot will now use Claude Max instead of API credits."
echo ""
echo "Test it from Slack:"
echo "  @DevOps task inhhale-v2 complete the iOS audit"
echo ""
