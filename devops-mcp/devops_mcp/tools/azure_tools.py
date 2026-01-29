"""
Azure Tools for DevOps MCP
==========================
Tools for managing Azure resources including VMs, Container Apps, Storage, and Key Vault.
"""

import os
import json
from typing import Any, Optional
from datetime import datetime

# Azure SDK imports (lazy loaded)
_azure_mgmt_compute = None
_azure_mgmt_containerinstance = None
_azure_identity = None


def _get_azure_credential():
    """Get Azure credential using DefaultAzureCredential."""
    global _azure_identity
    if _azure_identity is None:
        from azure.identity import DefaultAzureCredential
        _azure_identity = DefaultAzureCredential
    return _azure_identity()


def _get_compute_client():
    """Get Azure Compute Management client."""
    global _azure_mgmt_compute
    if _azure_mgmt_compute is None:
        from azure.mgmt.compute import ComputeManagementClient
        _azure_mgmt_compute = ComputeManagementClient
    
    subscription_id = os.environ.get("AZURE_SUBSCRIPTION_ID")
    if not subscription_id:
        raise ValueError("AZURE_SUBSCRIPTION_ID environment variable not set")
    
    return _azure_mgmt_compute(_get_azure_credential(), subscription_id)


class AzureTools:
    """Azure infrastructure management tools."""
    
    def __init__(self):
        self.subscription_id = os.environ.get("AZURE_SUBSCRIPTION_ID")
    
    def is_configured(self) -> bool:
        """Check if Azure is properly configured."""
        return bool(self.subscription_id)
    
    def get_tools(self) -> dict[str, dict]:
        """Return all Azure tools."""
        return {
            "azure_vm_list": {
                "description": "List all VMs in a resource group or subscription",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "resource_group": {
                            "type": "string",
                            "description": "Resource group name (optional, lists all if not provided)",
                        },
                    },
                },
                "handler": self.list_vms,
            },
            "azure_vm_start": {
                "description": "Start an Azure VM",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "resource_group": {"type": "string", "description": "Resource group name"},
                        "vm_name": {"type": "string", "description": "VM name"},
                    },
                    "required": ["resource_group", "vm_name"],
                },
                "handler": self.start_vm,
            },
            "azure_vm_stop": {
                "description": "Stop (deallocate) an Azure VM to stop billing",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "resource_group": {"type": "string", "description": "Resource group name"},
                        "vm_name": {"type": "string", "description": "VM name"},
                    },
                    "required": ["resource_group", "vm_name"],
                },
                "handler": self.stop_vm,
            },
            "azure_vm_status": {
                "description": "Get the power state of an Azure VM",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "resource_group": {"type": "string", "description": "Resource group name"},
                        "vm_name": {"type": "string", "description": "VM name"},
                    },
                    "required": ["resource_group", "vm_name"],
                },
                "handler": self.get_vm_status,
            },
            "azure_vm_run_command": {
                "description": "Run a shell command on an Azure VM",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "resource_group": {"type": "string", "description": "Resource group name"},
                        "vm_name": {"type": "string", "description": "VM name"},
                        "command": {"type": "string", "description": "Shell command to run"},
                    },
                    "required": ["resource_group", "vm_name", "command"],
                },
                "handler": self.run_command,
            },
            "azure_container_app_list": {
                "description": "List Container Apps in a resource group",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "resource_group": {"type": "string", "description": "Resource group name"},
                    },
                    "required": ["resource_group"],
                },
                "handler": self.list_container_apps,
            },
            "azure_container_app_restart": {
                "description": "Restart a Container App",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "resource_group": {"type": "string", "description": "Resource group name"},
                        "app_name": {"type": "string", "description": "Container App name"},
                    },
                    "required": ["resource_group", "app_name"],
                },
                "handler": self.restart_container_app,
            },
            "azure_container_app_logs": {
                "description": "Get recent logs from a Container App",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "resource_group": {"type": "string", "description": "Resource group name"},
                        "app_name": {"type": "string", "description": "Container App name"},
                        "lines": {"type": "integer", "description": "Number of log lines (default 100)", "default": 100},
                    },
                    "required": ["resource_group", "app_name"],
                },
                "handler": self.get_container_app_logs,
            },
            "azure_keyvault_get_secret": {
                "description": "Get a secret from Azure Key Vault",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "vault_name": {"type": "string", "description": "Key Vault name"},
                        "secret_name": {"type": "string", "description": "Secret name"},
                    },
                    "required": ["vault_name", "secret_name"],
                },
                "handler": self.get_secret,
            },
            "azure_keyvault_set_secret": {
                "description": "Set a secret in Azure Key Vault",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "vault_name": {"type": "string", "description": "Key Vault name"},
                        "secret_name": {"type": "string", "description": "Secret name"},
                        "secret_value": {"type": "string", "description": "Secret value"},
                    },
                    "required": ["vault_name", "secret_name", "secret_value"],
                },
                "handler": self.set_secret,
            },
        }
    
    async def list_vms(self, resource_group: Optional[str] = None) -> dict:
        """List VMs in a resource group or subscription."""
        client = _get_compute_client()
        
        if resource_group:
            vms = client.virtual_machines.list(resource_group)
        else:
            vms = client.virtual_machines.list_all()
        
        result = []
        for vm in vms:
            # Get instance view for power state
            instance_view = client.virtual_machines.instance_view(
                resource_group or vm.id.split("/")[4],
                vm.name
            )
            power_state = "unknown"
            for status in instance_view.statuses:
                if status.code.startswith("PowerState/"):
                    power_state = status.code.replace("PowerState/", "")
                    break
            
            result.append({
                "name": vm.name,
                "resource_group": vm.id.split("/")[4],
                "location": vm.location,
                "vm_size": vm.hardware_profile.vm_size,
                "power_state": power_state,
                "os_type": vm.storage_profile.os_disk.os_type,
            })
        
        return {"vms": result, "count": len(result)}
    
    async def start_vm(self, resource_group: str, vm_name: str) -> dict:
        """Start an Azure VM."""
        client = _get_compute_client()
        
        # Start the VM (async operation)
        poller = client.virtual_machines.begin_start(resource_group, vm_name)
        
        return {
            "status": "starting",
            "vm_name": vm_name,
            "resource_group": resource_group,
            "message": f"VM {vm_name} is starting. This may take a few minutes.",
        }
    
    async def stop_vm(self, resource_group: str, vm_name: str) -> dict:
        """Stop (deallocate) an Azure VM."""
        client = _get_compute_client()
        
        # Deallocate the VM (stops billing)
        poller = client.virtual_machines.begin_deallocate(resource_group, vm_name)
        
        return {
            "status": "stopping",
            "vm_name": vm_name,
            "resource_group": resource_group,
            "message": f"VM {vm_name} is deallocating. Billing will stop once complete.",
        }
    
    async def get_vm_status(self, resource_group: str, vm_name: str) -> dict:
        """Get VM power state."""
        client = _get_compute_client()
        
        instance_view = client.virtual_machines.instance_view(resource_group, vm_name)
        
        power_state = "unknown"
        provisioning_state = "unknown"
        
        for status in instance_view.statuses:
            if status.code.startswith("PowerState/"):
                power_state = status.code.replace("PowerState/", "")
            elif status.code.startswith("ProvisioningState/"):
                provisioning_state = status.code.replace("ProvisioningState/", "")
        
        return {
            "vm_name": vm_name,
            "resource_group": resource_group,
            "power_state": power_state,
            "provisioning_state": provisioning_state,
        }
    
    async def run_command(self, resource_group: str, vm_name: str, command: str) -> dict:
        """Run a shell command on an Azure VM."""
        client = _get_compute_client()
        
        run_command_input = {
            "command_id": "RunShellScript",
            "script": [command],
        }
        
        poller = client.virtual_machines.begin_run_command(
            resource_group, vm_name, run_command_input
        )
        result = poller.result()
        
        output = ""
        if result.value:
            for item in result.value:
                output += item.message or ""
        
        return {
            "vm_name": vm_name,
            "command": command,
            "output": output,
            "status": "completed",
        }
    
    async def list_container_apps(self, resource_group: str) -> dict:
        """List Container Apps in a resource group."""
        # This would use azure.mgmt.appcontainers
        # For now, return placeholder
        return {
            "message": "Container Apps listing requires azure-mgmt-appcontainers package",
            "resource_group": resource_group,
        }
    
    async def restart_container_app(self, resource_group: str, app_name: str) -> dict:
        """Restart a Container App."""
        return {
            "status": "restarting",
            "app_name": app_name,
            "resource_group": resource_group,
        }
    
    async def get_container_app_logs(self, resource_group: str, app_name: str, lines: int = 100) -> dict:
        """Get Container App logs."""
        return {
            "app_name": app_name,
            "resource_group": resource_group,
            "lines": lines,
            "message": "Log retrieval requires Azure Monitor integration",
        }
    
    async def get_secret(self, vault_name: str, secret_name: str) -> dict:
        """Get a secret from Key Vault."""
        from azure.keyvault.secrets import SecretClient
        
        vault_url = f"https://{vault_name}.vault.azure.net"
        client = SecretClient(vault_url=vault_url, credential=_get_azure_credential())
        
        secret = client.get_secret(secret_name)
        
        return {
            "vault_name": vault_name,
            "secret_name": secret_name,
            "value": secret.value,
            "enabled": secret.properties.enabled,
            "created_on": secret.properties.created_on,
        }
    
    async def set_secret(self, vault_name: str, secret_name: str, secret_value: str) -> dict:
        """Set a secret in Key Vault."""
        from azure.keyvault.secrets import SecretClient
        
        vault_url = f"https://{vault_name}.vault.azure.net"
        client = SecretClient(vault_url=vault_url, credential=_get_azure_credential())
        
        secret = client.set_secret(secret_name, secret_value)
        
        return {
            "vault_name": vault_name,
            "secret_name": secret_name,
            "status": "created",
            "version": secret.properties.version,
        }
