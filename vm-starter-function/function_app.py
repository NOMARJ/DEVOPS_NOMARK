"""
Azure Function to start the DevOps VM from Slack.
Responds to Slack slash command: /nomark-start
"""

import azure.functions as func
import logging
import os
import json
from azure.identity import DefaultAzureCredential
from azure.mgmt.compute import ComputeManagementClient

app = func.FunctionApp()

# Azure configuration
SUBSCRIPTION_ID = os.environ.get("AZURE_SUBSCRIPTION_ID")
RESOURCE_GROUP = os.environ.get("AZURE_RESOURCE_GROUP", "nomark-devops-rg")
VM_NAME = os.environ.get("AZURE_VM_NAME", "nomark-devops-vm")
SLACK_VERIFICATION_TOKEN = os.environ.get("SLACK_VERIFICATION_TOKEN")

@app.route(route="start-vm", auth_level=func.AuthLevel.ANONYMOUS)
def start_vm(req: func.HttpRequest) -> func.HttpResponse:
    """
    HTTP endpoint to start the VM.
    Responds to Slack slash command.
    """
    logging.info('VM start request received')

    # Verify Slack token
    form_data = {}
    try:
        body = req.get_body().decode('utf-8')
        for item in body.split('&'):
            if '=' in item:
                key, value = item.split('=', 1)
                form_data[key] = value
    except Exception as e:
        logging.error(f"Failed to parse form data: {e}")
        return func.HttpResponse("Invalid request", status_code=400)

    # Check verification token
    if SLACK_VERIFICATION_TOKEN:
        token = form_data.get('token', '')
        if token != SLACK_VERIFICATION_TOKEN:
            logging.warning(f"Invalid Slack token: {token}")
            return func.HttpResponse("Unauthorized", status_code=401)

    # Get user who triggered the command
    user_name = form_data.get('user_name', 'unknown')
    logging.info(f"VM start requested by Slack user: {user_name}")

    try:
        # Initialize Azure credentials
        credential = DefaultAzureCredential()
        compute_client = ComputeManagementClient(credential, SUBSCRIPTION_ID)

        # Check VM status
        vm = compute_client.virtual_machines.instance_view(RESOURCE_GROUP, VM_NAME)
        statuses = vm.statuses

        power_state = None
        for status in statuses:
            if status.code.startswith('PowerState/'):
                power_state = status.code.split('/')[-1]
                break

        if power_state == 'running':
            # VM is already running
            response = {
                "response_type": "in_channel",
                "text": "✅ VM is already running",
                "attachments": [{
                    "color": "good",
                    "fields": [
                        {"title": "Status", "value": "Running", "short": True},
                        {"title": "IP", "value": "20.5.185.136", "short": True},
                        {"title": "MCP URL", "value": "https://20-5-185-136.sslip.io", "short": False}
                    ]
                }]
            }
            return func.HttpResponse(
                json.dumps(response),
                mimetype="application/json",
                status_code=200
            )

        # Start the VM (async operation)
        logging.info(f"Starting VM: {VM_NAME}")
        async_vm_start = compute_client.virtual_machines.begin_start(RESOURCE_GROUP, VM_NAME)

        # Return immediate response to Slack
        response = {
            "response_type": "in_channel",
            "text": f"🚀 Starting VM `{VM_NAME}`...",
            "attachments": [{
                "color": "warning",
                "text": "This will take 1-2 minutes. The Slack bot will be available shortly.",
                "fields": [
                    {"title": "Requested by", "value": f"@{user_name}", "short": True},
                    {"title": "Expected time", "value": "~90 seconds", "short": True}
                ]
            }]
        }

        return func.HttpResponse(
            json.dumps(response),
            mimetype="application/json",
            status_code=200
        )

    except Exception as e:
        logging.error(f"Error starting VM: {str(e)}")
        response = {
            "response_type": "ephemeral",
            "text": f"❌ Error starting VM: {str(e)}"
        }
        return func.HttpResponse(
            json.dumps(response),
            mimetype="application/json",
            status_code=200
        )


@app.route(route="health", auth_level=func.AuthLevel.ANONYMOUS)
def health(req: func.HttpRequest) -> func.HttpResponse:
    """Health check endpoint."""
    return func.HttpResponse(
        json.dumps({"status": "healthy", "service": "vm-starter"}),
        mimetype="application/json",
        status_code=200
    )
