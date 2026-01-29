"""
n8n Tools for DevOps MCP
========================
Tools for managing n8n workflows and executions.
"""

import os
import httpx
from typing import Any, Optional


class N8nTools:
    """n8n workflow management tools."""
    
    def __init__(self):
        self.base_url = os.environ.get("N8N_URL", "").rstrip("/")
        self.api_key = os.environ.get("N8N_API_KEY")
    
    def is_configured(self) -> bool:
        return bool(self.base_url and self.api_key)
    
    def _headers(self):
        return {"X-N8N-API-KEY": self.api_key}
    
    def get_tools(self) -> dict[str, dict]:
        return {
            "n8n_workflow_list": {
                "description": "List all n8n workflows",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "active": {"type": "boolean", "description": "Filter by active status"},
                        "tags": {"type": "array", "items": {"type": "string"}, "description": "Filter by tags"},
                    },
                },
                "handler": self.list_workflows,
            },
            "n8n_workflow_get": {
                "description": "Get a workflow by ID",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "workflow_id": {"type": "string", "description": "Workflow ID"},
                    },
                    "required": ["workflow_id"],
                },
                "handler": self.get_workflow,
            },
            "n8n_workflow_activate": {
                "description": "Activate a workflow",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "workflow_id": {"type": "string", "description": "Workflow ID"},
                    },
                    "required": ["workflow_id"],
                },
                "handler": self.activate_workflow,
            },
            "n8n_workflow_deactivate": {
                "description": "Deactivate a workflow",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "workflow_id": {"type": "string", "description": "Workflow ID"},
                    },
                    "required": ["workflow_id"],
                },
                "handler": self.deactivate_workflow,
            },
            "n8n_workflow_execute": {
                "description": "Execute a workflow manually",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "workflow_id": {"type": "string", "description": "Workflow ID"},
                        "data": {"type": "object", "description": "Input data for the workflow"},
                    },
                    "required": ["workflow_id"],
                },
                "handler": self.execute_workflow,
            },
            "n8n_execution_list": {
                "description": "List workflow executions",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "workflow_id": {"type": "string", "description": "Filter by workflow ID"},
                        "status": {"type": "string", "enum": ["success", "error", "waiting"]},
                        "limit": {"type": "integer", "default": 20},
                    },
                },
                "handler": self.list_executions,
            },
            "n8n_execution_get": {
                "description": "Get execution details",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "execution_id": {"type": "string", "description": "Execution ID"},
                    },
                    "required": ["execution_id"],
                },
                "handler": self.get_execution,
            },
            "n8n_webhook_trigger": {
                "description": "Trigger a webhook workflow",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "webhook_path": {"type": "string", "description": "Webhook path (after /webhook/)"},
                        "method": {"type": "string", "enum": ["GET", "POST"], "default": "POST"},
                        "data": {"type": "object", "description": "Data to send"},
                    },
                    "required": ["webhook_path"],
                },
                "handler": self.trigger_webhook,
            },
            "n8n_credentials_list": {
                "description": "List available credentials",
                "input_schema": {
                    "type": "object",
                    "properties": {},
                },
                "handler": self.list_credentials,
            },
        }
    
    async def list_workflows(self, active: Optional[bool] = None, tags: Optional[list] = None) -> dict:
        params = {}
        if active is not None:
            params["active"] = active
        if tags:
            params["tags"] = ",".join(tags)
        
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self.base_url}/api/v1/workflows",
                headers=self._headers(),
                params=params,
            )
            data = resp.json()
        
        return {
            "workflows": [
                {
                    "id": w["id"],
                    "name": w["name"],
                    "active": w["active"],
                    "tags": [t["name"] for t in w.get("tags", [])],
                    "updated_at": w.get("updatedAt"),
                }
                for w in data.get("data", [])
            ]
        }
    
    async def get_workflow(self, workflow_id: str) -> dict:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self.base_url}/api/v1/workflows/{workflow_id}",
                headers=self._headers(),
            )
            data = resp.json()
        
        return {
            "id": data["id"],
            "name": data["name"],
            "active": data["active"],
            "nodes": len(data.get("nodes", [])),
            "connections": data.get("connections", {}),
        }
    
    async def activate_workflow(self, workflow_id: str) -> dict:
        async with httpx.AsyncClient() as client:
            resp = await client.patch(
                f"{self.base_url}/api/v1/workflows/{workflow_id}/activate",
                headers=self._headers(),
            )
        
        return {"workflow_id": workflow_id, "status": "activated"}
    
    async def deactivate_workflow(self, workflow_id: str) -> dict:
        async with httpx.AsyncClient() as client:
            resp = await client.patch(
                f"{self.base_url}/api/v1/workflows/{workflow_id}/deactivate",
                headers=self._headers(),
            )
        
        return {"workflow_id": workflow_id, "status": "deactivated"}
    
    async def execute_workflow(self, workflow_id: str, data: Optional[dict] = None) -> dict:
        body = {}
        if data:
            body["data"] = data
        
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self.base_url}/api/v1/workflows/{workflow_id}/run",
                headers=self._headers(),
                json=body,
            )
            result = resp.json()
        
        return {
            "execution_id": result.get("data", {}).get("executionId"),
            "status": "started",
        }
    
    async def list_executions(
        self,
        workflow_id: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 20,
    ) -> dict:
        params = {"limit": limit}
        if workflow_id:
            params["workflowId"] = workflow_id
        if status:
            params["status"] = status
        
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self.base_url}/api/v1/executions",
                headers=self._headers(),
                params=params,
            )
            data = resp.json()
        
        return {
            "executions": [
                {
                    "id": e["id"],
                    "workflow_id": e.get("workflowId"),
                    "status": e.get("status"),
                    "started_at": e.get("startedAt"),
                    "finished_at": e.get("stoppedAt"),
                }
                for e in data.get("data", [])
            ]
        }
    
    async def get_execution(self, execution_id: str) -> dict:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self.base_url}/api/v1/executions/{execution_id}",
                headers=self._headers(),
            )
            data = resp.json()
        
        return {
            "id": data["id"],
            "workflow_id": data.get("workflowId"),
            "status": data.get("status"),
            "started_at": data.get("startedAt"),
            "finished_at": data.get("stoppedAt"),
            "data": data.get("data"),
        }
    
    async def trigger_webhook(self, webhook_path: str, method: str = "POST", data: Optional[dict] = None) -> dict:
        url = f"{self.base_url}/webhook/{webhook_path}"
        
        async with httpx.AsyncClient() as client:
            if method == "GET":
                resp = await client.get(url, params=data or {})
            else:
                resp = await client.post(url, json=data or {})
            
            try:
                result = resp.json()
            except:
                result = {"response": resp.text}
        
        return {
            "status": resp.status_code,
            "response": result,
        }
    
    async def list_credentials(self) -> dict:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self.base_url}/api/v1/credentials",
                headers=self._headers(),
            )
            data = resp.json()
        
        return {
            "credentials": [
                {
                    "id": c["id"],
                    "name": c["name"],
                    "type": c["type"],
                }
                for c in data.get("data", [])
            ]
        }
