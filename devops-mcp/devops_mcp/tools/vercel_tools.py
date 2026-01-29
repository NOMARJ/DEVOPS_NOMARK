"""
Vercel Tools for DevOps MCP
===========================
Tools for managing Vercel deployments and projects.
"""

import os
import httpx
from typing import Any, Optional


class VercelTools:
    """Vercel deployment management tools."""
    
    def __init__(self):
        self.token = os.environ.get("VERCEL_TOKEN")
        self.team_id = os.environ.get("VERCEL_TEAM_ID")
        self.base_url = "https://api.vercel.com"
    
    def is_configured(self) -> bool:
        return bool(self.token)
    
    def _headers(self):
        return {"Authorization": f"Bearer {self.token}"}
    
    def _params(self):
        return {"teamId": self.team_id} if self.team_id else {}
    
    def get_tools(self) -> dict[str, dict]:
        return {
            "vercel_project_list": {
                "description": "List Vercel projects",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "limit": {"type": "integer", "default": 20},
                    },
                },
                "handler": self.list_projects,
            },
            "vercel_deployment_list": {
                "description": "List deployments for a project",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "project": {"type": "string", "description": "Project name or ID"},
                        "state": {"type": "string", "enum": ["BUILDING", "ERROR", "INITIALIZING", "QUEUED", "READY", "CANCELED"]},
                        "limit": {"type": "integer", "default": 10},
                    },
                    "required": ["project"],
                },
                "handler": self.list_deployments,
            },
            "vercel_deployment_create": {
                "description": "Create a new deployment (redeploy)",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "project": {"type": "string", "description": "Project name or ID"},
                        "target": {"type": "string", "enum": ["production", "preview"], "default": "preview"},
                        "ref": {"type": "string", "description": "Git ref to deploy"},
                    },
                    "required": ["project"],
                },
                "handler": self.create_deployment,
            },
            "vercel_deployment_cancel": {
                "description": "Cancel a deployment",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "deployment_id": {"type": "string", "description": "Deployment ID"},
                    },
                    "required": ["deployment_id"],
                },
                "handler": self.cancel_deployment,
            },
            "vercel_env_list": {
                "description": "List environment variables for a project",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "project": {"type": "string", "description": "Project name or ID"},
                    },
                    "required": ["project"],
                },
                "handler": self.list_env_vars,
            },
            "vercel_env_set": {
                "description": "Set an environment variable",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "project": {"type": "string", "description": "Project name or ID"},
                        "key": {"type": "string", "description": "Variable name"},
                        "value": {"type": "string", "description": "Variable value"},
                        "target": {"type": "array", "items": {"type": "string", "enum": ["production", "preview", "development"]}, "default": ["production", "preview"]},
                    },
                    "required": ["project", "key", "value"],
                },
                "handler": self.set_env_var,
            },
        }
    
    async def list_projects(self, limit: int = 20) -> dict:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self.base_url}/v9/projects",
                headers=self._headers(),
                params={**self._params(), "limit": limit},
            )
            data = resp.json()
        
        return {
            "projects": [
                {
                    "id": p["id"],
                    "name": p["name"],
                    "framework": p.get("framework"),
                    "updated_at": p.get("updatedAt"),
                }
                for p in data.get("projects", [])
            ]
        }
    
    async def list_deployments(self, project: str, state: Optional[str] = None, limit: int = 10) -> dict:
        params = {**self._params(), "projectId": project, "limit": limit}
        if state:
            params["state"] = state
        
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self.base_url}/v6/deployments",
                headers=self._headers(),
                params=params,
            )
            data = resp.json()
        
        return {
            "deployments": [
                {
                    "id": d["uid"],
                    "url": d.get("url"),
                    "state": d.get("state"),
                    "target": d.get("target"),
                    "created_at": d.get("created"),
                }
                for d in data.get("deployments", [])
            ]
        }
    
    async def create_deployment(self, project: str, target: str = "preview", ref: Optional[str] = None) -> dict:
        body = {"name": project, "target": target}
        if ref:
            body["gitSource"] = {"ref": ref}
        
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self.base_url}/v13/deployments",
                headers=self._headers(),
                params=self._params(),
                json=body,
            )
            data = resp.json()
        
        return {
            "id": data.get("id"),
            "url": data.get("url"),
            "status": "created",
        }
    
    async def cancel_deployment(self, deployment_id: str) -> dict:
        async with httpx.AsyncClient() as client:
            resp = await client.patch(
                f"{self.base_url}/v12/deployments/{deployment_id}/cancel",
                headers=self._headers(),
                params=self._params(),
            )
        
        return {"status": "canceled", "deployment_id": deployment_id}
    
    async def list_env_vars(self, project: str) -> dict:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self.base_url}/v9/projects/{project}/env",
                headers=self._headers(),
                params=self._params(),
            )
            data = resp.json()
        
        return {
            "env_vars": [
                {
                    "key": e["key"],
                    "target": e.get("target"),
                    "type": e.get("type"),
                }
                for e in data.get("envs", [])
            ]
        }
    
    async def set_env_var(self, project: str, key: str, value: str, target: list = None) -> dict:
        body = {
            "key": key,
            "value": value,
            "target": target or ["production", "preview"],
            "type": "encrypted",
        }
        
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self.base_url}/v10/projects/{project}/env",
                headers=self._headers(),
                params=self._params(),
                json=body,
            )
        
        return {"status": "created", "key": key}
