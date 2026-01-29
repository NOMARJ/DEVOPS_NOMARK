"""
Supabase Tools for DevOps MCP
=============================
Tools for managing Supabase databases, auth, and storage.
"""

import os
import json
from typing import Any, Optional, List


class SupabaseTools:
    """Supabase management tools."""
    
    def __init__(self):
        self.url = os.environ.get("SUPABASE_URL")
        self.service_key = os.environ.get("SUPABASE_SERVICE_KEY")
        self._client = None
    
    def is_configured(self) -> bool:
        """Check if Supabase is properly configured."""
        return bool(self.url and self.service_key)
    
    def _get_client(self):
        """Get Supabase client (lazy loaded)."""
        if self._client is None:
            from supabase import create_client
            self._client = create_client(self.url, self.service_key)
        return self._client
    
    def get_tools(self) -> dict[str, dict]:
        """Return all Supabase tools."""
        return {
            "supabase_query": {
                "description": "Execute a SELECT query on a Supabase table",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "table": {"type": "string", "description": "Table name"},
                        "select": {"type": "string", "description": "Columns to select (default: *)", "default": "*"},
                        "filters": {
                            "type": "array",
                            "description": "Filters as [{column, operator, value}]",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "column": {"type": "string"},
                                    "operator": {"type": "string", "enum": ["eq", "neq", "gt", "gte", "lt", "lte", "like", "ilike", "in"]},
                                    "value": {},
                                },
                            },
                        },
                        "limit": {"type": "integer", "description": "Max rows to return", "default": 100},
                        "order_by": {"type": "string", "description": "Column to order by"},
                        "ascending": {"type": "boolean", "description": "Sort ascending", "default": True},
                    },
                    "required": ["table"],
                },
                "handler": self.query,
            },
            "supabase_insert": {
                "description": "Insert rows into a Supabase table",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "table": {"type": "string", "description": "Table name"},
                        "data": {
                            "description": "Row data (object) or array of objects",
                        },
                        "upsert": {"type": "boolean", "description": "Upsert mode (update if exists)", "default": False},
                    },
                    "required": ["table", "data"],
                },
                "handler": self.insert,
            },
            "supabase_update": {
                "description": "Update rows in a Supabase table",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "table": {"type": "string", "description": "Table name"},
                        "data": {"type": "object", "description": "Fields to update"},
                        "filters": {
                            "type": "array",
                            "description": "Filters to identify rows",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "column": {"type": "string"},
                                    "operator": {"type": "string"},
                                    "value": {},
                                },
                            },
                        },
                    },
                    "required": ["table", "data", "filters"],
                },
                "handler": self.update,
            },
            "supabase_delete": {
                "description": "Delete rows from a Supabase table",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "table": {"type": "string", "description": "Table name"},
                        "filters": {
                            "type": "array",
                            "description": "Filters to identify rows to delete",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "column": {"type": "string"},
                                    "operator": {"type": "string"},
                                    "value": {},
                                },
                            },
                        },
                    },
                    "required": ["table", "filters"],
                },
                "handler": self.delete,
            },
            "supabase_rpc": {
                "description": "Call a Supabase RPC function",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "function_name": {"type": "string", "description": "Function name"},
                        "params": {"type": "object", "description": "Function parameters", "default": {}},
                    },
                    "required": ["function_name"],
                },
                "handler": self.rpc,
            },
            "supabase_list_tables": {
                "description": "List all tables in the database",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "schema": {"type": "string", "description": "Schema name", "default": "public"},
                    },
                },
                "handler": self.list_tables,
            },
            "supabase_table_schema": {
                "description": "Get schema/columns for a table",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "table": {"type": "string", "description": "Table name"},
                    },
                    "required": ["table"],
                },
                "handler": self.get_table_schema,
            },
            "supabase_run_sql": {
                "description": "Run raw SQL query (use with caution)",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "SQL query"},
                    },
                    "required": ["query"],
                },
                "handler": self.run_sql,
            },
            "supabase_storage_list": {
                "description": "List files in a storage bucket",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "bucket": {"type": "string", "description": "Bucket name"},
                        "path": {"type": "string", "description": "Folder path", "default": ""},
                        "limit": {"type": "integer", "description": "Max files to return", "default": 100},
                    },
                    "required": ["bucket"],
                },
                "handler": self.storage_list,
            },
            "supabase_storage_upload": {
                "description": "Upload a file to storage",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "bucket": {"type": "string", "description": "Bucket name"},
                        "path": {"type": "string", "description": "Destination path"},
                        "file_path": {"type": "string", "description": "Local file path"},
                        "content_type": {"type": "string", "description": "MIME type"},
                    },
                    "required": ["bucket", "path", "file_path"],
                },
                "handler": self.storage_upload,
            },
            "supabase_storage_download": {
                "description": "Download a file from storage",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "bucket": {"type": "string", "description": "Bucket name"},
                        "path": {"type": "string", "description": "File path in bucket"},
                        "local_path": {"type": "string", "description": "Local destination path"},
                    },
                    "required": ["bucket", "path", "local_path"],
                },
                "handler": self.storage_download,
            },
        }
    
    async def query(
        self,
        table: str,
        select: str = "*",
        filters: Optional[List[dict]] = None,
        limit: int = 100,
        order_by: Optional[str] = None,
        ascending: bool = True,
    ) -> dict:
        """Execute a SELECT query."""
        client = self._get_client()
        
        query = client.table(table).select(select)
        
        # Apply filters
        if filters:
            for f in filters:
                col = f["column"]
                op = f["operator"]
                val = f["value"]
                
                if op == "eq":
                    query = query.eq(col, val)
                elif op == "neq":
                    query = query.neq(col, val)
                elif op == "gt":
                    query = query.gt(col, val)
                elif op == "gte":
                    query = query.gte(col, val)
                elif op == "lt":
                    query = query.lt(col, val)
                elif op == "lte":
                    query = query.lte(col, val)
                elif op == "like":
                    query = query.like(col, val)
                elif op == "ilike":
                    query = query.ilike(col, val)
                elif op == "in":
                    query = query.in_(col, val)
        
        # Apply ordering
        if order_by:
            query = query.order(order_by, desc=not ascending)
        
        # Apply limit
        query = query.limit(limit)
        
        result = query.execute()
        
        return {
            "data": result.data,
            "count": len(result.data),
        }
    
    async def insert(self, table: str, data: Any, upsert: bool = False) -> dict:
        """Insert rows into a table."""
        client = self._get_client()
        
        if upsert:
            result = client.table(table).upsert(data).execute()
        else:
            result = client.table(table).insert(data).execute()
        
        return {
            "status": "inserted",
            "data": result.data,
            "count": len(result.data) if isinstance(result.data, list) else 1,
        }
    
    async def update(self, table: str, data: dict, filters: List[dict]) -> dict:
        """Update rows in a table."""
        client = self._get_client()
        
        query = client.table(table).update(data)
        
        for f in filters:
            col = f["column"]
            op = f.get("operator", "eq")
            val = f["value"]
            
            if op == "eq":
                query = query.eq(col, val)
            # Add other operators as needed
        
        result = query.execute()
        
        return {
            "status": "updated",
            "data": result.data,
            "count": len(result.data) if result.data else 0,
        }
    
    async def delete(self, table: str, filters: List[dict]) -> dict:
        """Delete rows from a table."""
        client = self._get_client()
        
        query = client.table(table).delete()
        
        for f in filters:
            col = f["column"]
            op = f.get("operator", "eq")
            val = f["value"]
            
            if op == "eq":
                query = query.eq(col, val)
        
        result = query.execute()
        
        return {
            "status": "deleted",
            "count": len(result.data) if result.data else 0,
        }
    
    async def rpc(self, function_name: str, params: dict = None) -> dict:
        """Call an RPC function."""
        client = self._get_client()
        
        result = client.rpc(function_name, params or {}).execute()
        
        return {
            "data": result.data,
        }
    
    async def list_tables(self, schema: str = "public") -> dict:
        """List all tables in a schema."""
        # Use information_schema to get tables
        query = f"""
        SELECT table_name, table_type
        FROM information_schema.tables
        WHERE table_schema = '{schema}'
        ORDER BY table_name
        """
        
        return await self.run_sql(query)
    
    async def get_table_schema(self, table: str) -> dict:
        """Get column information for a table."""
        query = f"""
        SELECT 
            column_name,
            data_type,
            is_nullable,
            column_default,
            character_maximum_length
        FROM information_schema.columns
        WHERE table_name = '{table}'
        ORDER BY ordinal_position
        """
        
        return await self.run_sql(query)
    
    async def run_sql(self, query: str) -> dict:
        """Run raw SQL query."""
        client = self._get_client()
        
        # Use Supabase's sql function (requires service role)
        result = client.rpc("exec_sql", {"query": query}).execute()
        
        return {
            "data": result.data,
        }
    
    async def storage_list(self, bucket: str, path: str = "", limit: int = 100) -> dict:
        """List files in a storage bucket."""
        client = self._get_client()
        
        result = client.storage.from_(bucket).list(path, {"limit": limit})
        
        return {
            "bucket": bucket,
            "path": path,
            "files": result,
            "count": len(result),
        }
    
    async def storage_upload(
        self,
        bucket: str,
        path: str,
        file_path: str,
        content_type: Optional[str] = None,
    ) -> dict:
        """Upload a file to storage."""
        client = self._get_client()
        
        with open(file_path, "rb") as f:
            file_data = f.read()
        
        options = {}
        if content_type:
            options["content-type"] = content_type
        
        result = client.storage.from_(bucket).upload(path, file_data, options)
        
        return {
            "status": "uploaded",
            "bucket": bucket,
            "path": path,
        }
    
    async def storage_download(self, bucket: str, path: str, local_path: str) -> dict:
        """Download a file from storage."""
        client = self._get_client()
        
        result = client.storage.from_(bucket).download(path)
        
        with open(local_path, "wb") as f:
            f.write(result)
        
        return {
            "status": "downloaded",
            "bucket": bucket,
            "path": path,
            "local_path": local_path,
        }
