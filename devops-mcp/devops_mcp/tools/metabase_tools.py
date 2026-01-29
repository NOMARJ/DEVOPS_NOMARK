"""
Metabase Tools for DevOps MCP
=============================
Tools for interacting with self-hosted Metabase - dashboards, questions, and embeds.
"""

import os
import json
import httpx
from typing import Any, Optional, List
from datetime import datetime


class MetabaseTools:
    """Metabase analytics and embedding tools."""
    
    def __init__(self):
        self.base_url = os.environ.get("METABASE_URL", "").rstrip("/")
        self.username = os.environ.get("METABASE_USERNAME")
        self.password = os.environ.get("METABASE_PASSWORD")
        self.secret_key = os.environ.get("METABASE_SECRET_KEY")  # For signed embeds
        self._session_token = None
    
    def is_configured(self) -> bool:
        return bool(self.base_url and (self.username or self.secret_key))
    
    async def _get_session(self) -> str:
        """Get or refresh session token."""
        if self._session_token:
            return self._session_token
        
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self.base_url}/api/session",
                json={"username": self.username, "password": self.password}
            )
            data = resp.json()
            self._session_token = data.get("id")
        
        return self._session_token
    
    def _headers(self, token: str) -> dict:
        return {"X-Metabase-Session": token}
    
    def get_tools(self) -> dict[str, dict]:
        return {
            "metabase_dashboard_list": {
                "description": "List all Metabase dashboards",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "collection_id": {"type": "integer", "description": "Filter by collection ID"},
                    },
                },
                "handler": self.list_dashboards,
            },
            "metabase_dashboard_get": {
                "description": "Get dashboard details and cards",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "dashboard_id": {"type": "integer", "description": "Dashboard ID"},
                    },
                    "required": ["dashboard_id"],
                },
                "handler": self.get_dashboard,
            },
            "metabase_question_list": {
                "description": "List saved questions (cards)",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "collection_id": {"type": "integer", "description": "Filter by collection ID"},
                    },
                },
                "handler": self.list_questions,
            },
            "metabase_question_run": {
                "description": "Execute a saved question and get results",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "question_id": {"type": "integer", "description": "Question/Card ID"},
                        "parameters": {"type": "object", "description": "Filter parameters"},
                    },
                    "required": ["question_id"],
                },
                "handler": self.run_question,
            },
            "metabase_query_run": {
                "description": "Run an ad-hoc SQL query",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "database_id": {"type": "integer", "description": "Database ID"},
                        "query": {"type": "string", "description": "SQL query"},
                    },
                    "required": ["database_id", "query"],
                },
                "handler": self.run_query,
            },
            "metabase_embed_url": {
                "description": "Generate a signed embed URL for a dashboard or question",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "resource_type": {"type": "string", "enum": ["dashboard", "question"]},
                        "resource_id": {"type": "integer", "description": "Dashboard or Question ID"},
                        "params": {"type": "object", "description": "Locked parameters for the embed"},
                        "expiry_minutes": {"type": "integer", "default": 60},
                    },
                    "required": ["resource_type", "resource_id"],
                },
                "handler": self.generate_embed_url,
            },
            "metabase_collection_list": {
                "description": "List collections (folders)",
                "input_schema": {
                    "type": "object",
                    "properties": {},
                },
                "handler": self.list_collections,
            },
            "metabase_database_list": {
                "description": "List connected databases",
                "input_schema": {
                    "type": "object",
                    "properties": {},
                },
                "handler": self.list_databases,
            },
            "metabase_table_metadata": {
                "description": "Get table schema/metadata",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "table_id": {"type": "integer", "description": "Table ID"},
                    },
                    "required": ["table_id"],
                },
                "handler": self.get_table_metadata,
            },
            "metabase_pulse_list": {
                "description": "List scheduled reports (pulses)",
                "input_schema": {
                    "type": "object",
                    "properties": {},
                },
                "handler": self.list_pulses,
            },
            "metabase_pulse_trigger": {
                "description": "Manually trigger a pulse/subscription",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "pulse_id": {"type": "integer", "description": "Pulse ID"},
                    },
                    "required": ["pulse_id"],
                },
                "handler": self.trigger_pulse,
            },
        }
    
    async def list_dashboards(self, collection_id: Optional[int] = None) -> dict:
        """List dashboards."""
        token = await self._get_session()
        
        async with httpx.AsyncClient() as client:
            if collection_id:
                resp = await client.get(
                    f"{self.base_url}/api/collection/{collection_id}/items",
                    headers=self._headers(token),
                    params={"models": "dashboard"}
                )
            else:
                resp = await client.get(
                    f"{self.base_url}/api/dashboard",
                    headers=self._headers(token),
                )
            data = resp.json()
        
        dashboards = data if isinstance(data, list) else data.get("data", [])
        
        return {
            "dashboards": [
                {
                    "id": d.get("id"),
                    "name": d.get("name"),
                    "description": d.get("description"),
                    "collection_id": d.get("collection_id"),
                }
                for d in dashboards
            ]
        }
    
    async def get_dashboard(self, dashboard_id: int) -> dict:
        """Get dashboard details."""
        token = await self._get_session()
        
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self.base_url}/api/dashboard/{dashboard_id}",
                headers=self._headers(token),
            )
            data = resp.json()
        
        return {
            "id": data.get("id"),
            "name": data.get("name"),
            "description": data.get("description"),
            "parameters": data.get("parameters", []),
            "cards": [
                {
                    "id": c.get("id"),
                    "card_id": c.get("card_id"),
                    "name": c.get("card", {}).get("name"),
                    "visualization": c.get("card", {}).get("display"),
                }
                for c in data.get("dashcards", [])
            ],
        }
    
    async def list_questions(self, collection_id: Optional[int] = None) -> dict:
        """List saved questions."""
        token = await self._get_session()
        
        async with httpx.AsyncClient() as client:
            if collection_id:
                resp = await client.get(
                    f"{self.base_url}/api/collection/{collection_id}/items",
                    headers=self._headers(token),
                    params={"models": "card"}
                )
                data = resp.json()
                questions = data.get("data", [])
            else:
                resp = await client.get(
                    f"{self.base_url}/api/card",
                    headers=self._headers(token),
                )
                questions = resp.json()
        
        return {
            "questions": [
                {
                    "id": q.get("id"),
                    "name": q.get("name"),
                    "description": q.get("description"),
                    "display": q.get("display"),
                    "collection_id": q.get("collection_id"),
                }
                for q in questions
            ]
        }
    
    async def run_question(self, question_id: int, parameters: Optional[dict] = None) -> dict:
        """Execute a saved question."""
        token = await self._get_session()
        
        body = {}
        if parameters:
            body["parameters"] = [
                {"type": k, "value": v} for k, v in parameters.items()
            ]
        
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                f"{self.base_url}/api/card/{question_id}/query",
                headers=self._headers(token),
                json=body,
            )
            data = resp.json()
        
        result_data = data.get("data", {})
        
        return {
            "columns": [c.get("display_name") or c.get("name") for c in result_data.get("cols", [])],
            "rows": result_data.get("rows", [])[:100],  # Limit rows
            "row_count": len(result_data.get("rows", [])),
            "truncated": len(result_data.get("rows", [])) > 100,
        }
    
    async def run_query(self, database_id: int, query: str) -> dict:
        """Run ad-hoc SQL query."""
        token = await self._get_session()
        
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                f"{self.base_url}/api/dataset",
                headers=self._headers(token),
                json={
                    "database": database_id,
                    "native": {"query": query},
                    "type": "native",
                },
            )
            data = resp.json()
        
        result_data = data.get("data", {})
        
        return {
            "columns": [c.get("display_name") or c.get("name") for c in result_data.get("cols", [])],
            "rows": result_data.get("rows", [])[:100],
            "row_count": len(result_data.get("rows", [])),
        }
    
    async def generate_embed_url(
        self,
        resource_type: str,
        resource_id: int,
        params: Optional[dict] = None,
        expiry_minutes: int = 60,
    ) -> dict:
        """Generate signed embed URL."""
        import jwt
        import time
        
        if not self.secret_key:
            return {"error": "METABASE_SECRET_KEY not configured"}
        
        payload = {
            "resource": {resource_type: resource_id},
            "params": params or {},
            "exp": int(time.time()) + (expiry_minutes * 60),
        }
        
        token = jwt.encode(payload, self.secret_key, algorithm="HS256")
        
        embed_url = f"{self.base_url}/embed/{resource_type}/{token}"
        
        return {
            "embed_url": embed_url,
            "expires_in_minutes": expiry_minutes,
            "resource_type": resource_type,
            "resource_id": resource_id,
        }
    
    async def list_collections(self) -> dict:
        """List collections."""
        token = await self._get_session()
        
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self.base_url}/api/collection",
                headers=self._headers(token),
            )
            data = resp.json()
        
        return {
            "collections": [
                {
                    "id": c.get("id"),
                    "name": c.get("name"),
                    "location": c.get("location"),
                }
                for c in data
            ]
        }
    
    async def list_databases(self) -> dict:
        """List connected databases."""
        token = await self._get_session()
        
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self.base_url}/api/database",
                headers=self._headers(token),
            )
            data = resp.json()
        
        db_list = data if isinstance(data, list) else data.get("data", [])
        return {
            "databases": [
                {
                    "id": d.get("id"),
                    "name": d.get("name"),
                    "engine": d.get("engine"),
                    "tables": d.get("tables", []),
                }
                for d in db_list
            ]
        }
    
    async def get_table_metadata(self, table_id: int) -> dict:
        """Get table schema."""
        token = await self._get_session()
        
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self.base_url}/api/table/{table_id}/query_metadata",
                headers=self._headers(token),
            )
            data = resp.json()
        
        return {
            "id": data.get("id"),
            "name": data.get("name"),
            "schema": data.get("schema"),
            "fields": [
                {
                    "id": f.get("id"),
                    "name": f.get("name"),
                    "display_name": f.get("display_name"),
                    "base_type": f.get("base_type"),
                    "semantic_type": f.get("semantic_type"),
                }
                for f in data.get("fields", [])
            ],
        }
    
    async def list_pulses(self) -> dict:
        """List scheduled reports."""
        token = await self._get_session()
        
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self.base_url}/api/pulse",
                headers=self._headers(token),
            )
            data = resp.json()
        
        return {
            "pulses": [
                {
                    "id": p.get("id"),
                    "name": p.get("name"),
                    "cards": [c.get("name") for c in p.get("cards", [])],
                    "channels": [c.get("channel_type") for c in p.get("channels", [])],
                }
                for p in data
            ]
        }
    
    async def trigger_pulse(self, pulse_id: int) -> dict:
        """Manually send a pulse."""
        token = await self._get_session()
        
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self.base_url}/api/pulse/{pulse_id}/test",
                headers=self._headers(token),
            )
        
        return {
            "status": "triggered" if resp.status_code == 200 else "failed",
            "pulse_id": pulse_id,
        }
