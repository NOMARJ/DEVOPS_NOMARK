"""
Carbone Tools for DevOps MCP
============================
Tools for generating documents from templates using Carbone.
Supports Word, Excel, PowerPoint, PDF, and more.
"""

import os
import json
import base64
import httpx
from pathlib import Path
from typing import Any, Optional


class CarboneTools:
    """Carbone document generation tools."""
    
    def __init__(self):
        # Carbone can be self-hosted or use cloud API
        self.api_url = os.environ.get("CARBONE_API_URL", "https://api.carbone.io")
        self.api_key = os.environ.get("CARBONE_API_KEY")
        self.templates_dir = os.environ.get("CARBONE_TEMPLATES_DIR", "./templates")
    
    def is_configured(self) -> bool:
        return bool(self.api_key) or os.path.exists(self.templates_dir)
    
    def _headers(self):
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers
    
    def get_tools(self) -> dict[str, dict]:
        return {
            "carbone_render": {
                "description": "Render a document from a Carbone template with data",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "template": {"type": "string", "description": "Template name or path"},
                        "data": {"type": "object", "description": "Data to inject into template"},
                        "output_format": {
                            "type": "string",
                            "description": "Output format",
                            "enum": ["pdf", "docx", "xlsx", "pptx", "odt", "ods", "odp", "html", "txt"],
                            "default": "pdf"
                        },
                        "output_path": {"type": "string", "description": "Where to save the output file"},
                    },
                    "required": ["template", "data"],
                },
                "handler": self.render,
            },
            "carbone_template_list": {
                "description": "List available Carbone templates",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "category": {"type": "string", "description": "Filter by category/folder"},
                    },
                },
                "handler": self.list_templates,
            },
            "carbone_template_upload": {
                "description": "Upload a new template to Carbone",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "file_path": {"type": "string", "description": "Local path to template file"},
                        "template_name": {"type": "string", "description": "Name for the template"},
                    },
                    "required": ["file_path"],
                },
                "handler": self.upload_template,
            },
            "carbone_render_report": {
                "description": "Render a FlowMetrics report (pre-configured templates)",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "report_type": {
                            "type": "string",
                            "description": "Type of report",
                            "enum": [
                                "monthly_flows",
                                "quarterly_summary",
                                "platform_comparison",
                                "client_board_pack",
                                "data_quality"
                            ]
                        },
                        "client_id": {"type": "string", "description": "Client ID"},
                        "period": {"type": "string", "description": "Report period (e.g., '2024-01', '2024-Q1')"},
                        "data": {"type": "object", "description": "Additional data overrides"},
                        "output_format": {"type": "string", "default": "pdf"},
                    },
                    "required": ["report_type", "client_id", "period"],
                },
                "handler": self.render_report,
            },
            "carbone_batch_render": {
                "description": "Render multiple documents from same template with different data",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "template": {"type": "string", "description": "Template name"},
                        "data_list": {
                            "type": "array",
                            "description": "Array of data objects",
                            "items": {"type": "object"}
                        },
                        "output_format": {"type": "string", "default": "pdf"},
                        "output_dir": {"type": "string", "description": "Output directory"},
                        "filename_template": {
                            "type": "string",
                            "description": "Filename template using {field} placeholders",
                            "default": "document_{index}"
                        },
                    },
                    "required": ["template", "data_list"],
                },
                "handler": self.batch_render,
            },
        }
    
    async def render(
        self,
        template: str,
        data: dict,
        output_format: str = "pdf",
        output_path: Optional[str] = None,
    ) -> dict:
        """Render a document from template."""
        
        # Find template file
        template_path = self._find_template(template)
        if not template_path:
            return {"error": f"Template not found: {template}"}
        
        # Read template
        with open(template_path, "rb") as f:
            template_content = base64.b64encode(f.read()).decode()
        
        # If using Carbone Cloud API
        if self.api_key:
            return await self._render_cloud(template_content, data, output_format, output_path)
        
        # If using local Carbone (carbone-copy-paste or carbone CLI)
        return await self._render_local(template_path, data, output_format, output_path)
    
    async def _render_cloud(
        self,
        template_base64: str,
        data: dict,
        output_format: str,
        output_path: Optional[str],
    ) -> dict:
        """Render using Carbone Cloud API."""
        
        async with httpx.AsyncClient() as client:
            # Upload template
            resp = await client.post(
                f"{self.api_url}/template",
                headers=self._headers(),
                json={"template": template_base64}
            )
            template_id = resp.json().get("data", {}).get("templateId")
            
            # Render document
            resp = await client.post(
                f"{self.api_url}/render/{template_id}",
                headers=self._headers(),
                json={
                    "data": data,
                    "convertTo": output_format,
                }
            )
            render_result = resp.json()
            render_id = render_result.get("data", {}).get("renderId")
            
            # Download rendered document
            resp = await client.get(
                f"{self.api_url}/render/{render_id}",
                headers=self._headers(),
            )
            
            if output_path:
                with open(output_path, "wb") as f:
                    f.write(resp.content)
                return {
                    "status": "success",
                    "output_path": output_path,
                    "format": output_format,
                }
            else:
                return {
                    "status": "success",
                    "content_base64": base64.b64encode(resp.content).decode(),
                    "format": output_format,
                }
    
    async def _render_local(
        self,
        template_path: str,
        data: dict,
        output_format: str,
        output_path: Optional[str],
    ) -> dict:
        """Render using local Carbone installation."""
        import subprocess
        import tempfile
        
        # Write data to temp file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(data, f)
            data_path = f.name
        
        # Determine output path
        if not output_path:
            output_path = tempfile.mktemp(suffix=f'.{output_format}')
        
        try:
            # Run carbone CLI
            result = subprocess.run(
                [
                    "carbone", "render",
                    template_path,
                    data_path,
                    "-o", output_path,
                    "-f", output_format,
                ],
                capture_output=True,
                text=True,
            )
            
            if result.returncode == 0:
                return {
                    "status": "success",
                    "output_path": output_path,
                    "format": output_format,
                }
            else:
                return {
                    "status": "error",
                    "error": result.stderr,
                }
        finally:
            os.unlink(data_path)
    
    def _find_template(self, template: str) -> Optional[str]:
        """Find template file by name or path."""
        # Direct path
        if os.path.exists(template):
            return template
        
        # In templates directory
        templates_dir = Path(self.templates_dir)
        if templates_dir.exists():
            # Exact match
            for ext in ['.docx', '.xlsx', '.pptx', '.odt', '.ods', '.odp']:
                path = templates_dir / f"{template}{ext}"
                if path.exists():
                    return str(path)
            
            # Search subdirectories
            for path in templates_dir.rglob(f"{template}*"):
                if path.is_file():
                    return str(path)
        
        return None
    
    async def list_templates(self, category: Optional[str] = None) -> dict:
        """List available templates."""
        templates_dir = Path(self.templates_dir)
        
        if not templates_dir.exists():
            return {"templates": [], "error": "Templates directory not found"}
        
        templates = []
        search_dir = templates_dir / category if category else templates_dir
        
        for path in search_dir.rglob("*"):
            if path.is_file() and path.suffix in ['.docx', '.xlsx', '.pptx', '.odt', '.ods', '.odp']:
                templates.append({
                    "name": path.stem,
                    "path": str(path.relative_to(templates_dir)),
                    "type": path.suffix[1:],
                    "category": path.parent.name if path.parent != templates_dir else None,
                })
        
        return {"templates": templates, "count": len(templates)}
    
    async def upload_template(self, file_path: str, template_name: Optional[str] = None) -> dict:
        """Upload/copy a template to the templates directory."""
        import shutil
        
        source = Path(file_path)
        if not source.exists():
            return {"error": f"File not found: {file_path}"}
        
        templates_dir = Path(self.templates_dir)
        templates_dir.mkdir(parents=True, exist_ok=True)
        
        dest_name = template_name or source.name
        if not dest_name.endswith(source.suffix):
            dest_name += source.suffix
        
        dest = templates_dir / dest_name
        shutil.copy2(source, dest)
        
        return {
            "status": "uploaded",
            "template_name": dest_name,
            "path": str(dest),
        }
    
    async def render_report(
        self,
        report_type: str,
        client_id: str,
        period: str,
        data: Optional[dict] = None,
        output_format: str = "pdf",
    ) -> dict:
        """Render a pre-configured FlowMetrics report."""
        
        # Map report types to templates
        template_map = {
            "monthly_flows": "reports/monthly_flows_report",
            "quarterly_summary": "reports/quarterly_summary",
            "platform_comparison": "reports/platform_comparison",
            "client_board_pack": "reports/board_pack",
            "data_quality": "reports/data_quality",
        }
        
        template = template_map.get(report_type)
        if not template:
            return {"error": f"Unknown report type: {report_type}"}
        
        # Build report data (in real implementation, fetch from database)
        report_data = {
            "client_id": client_id,
            "period": period,
            "generated_at": __import__('datetime').datetime.now().isoformat(),
            "report_type": report_type,
            **(data or {}),
        }
        
        # Output path
        output_path = f"/tmp/{report_type}_{client_id}_{period}.{output_format}"
        
        return await self.render(
            template=template,
            data=report_data,
            output_format=output_format,
            output_path=output_path,
        )
    
    async def batch_render(
        self,
        template: str,
        data_list: list,
        output_format: str = "pdf",
        output_dir: Optional[str] = None,
        filename_template: str = "document_{index}",
    ) -> dict:
        """Render multiple documents from same template."""
        
        output_dir = output_dir or "/tmp/batch_render"
        os.makedirs(output_dir, exist_ok=True)
        
        results = []
        for i, data in enumerate(data_list):
            # Generate filename
            filename = filename_template.format(index=i, **data)
            if not filename.endswith(f'.{output_format}'):
                filename += f'.{output_format}'
            
            output_path = os.path.join(output_dir, filename)
            
            result = await self.render(
                template=template,
                data=data,
                output_format=output_format,
                output_path=output_path,
            )
            
            results.append({
                "index": i,
                "filename": filename,
                "status": result.get("status"),
                "error": result.get("error"),
            })
        
        success_count = sum(1 for r in results if r["status"] == "success")
        
        return {
            "status": "completed",
            "total": len(data_list),
            "success": success_count,
            "failed": len(data_list) - success_count,
            "output_dir": output_dir,
            "results": results,
        }
