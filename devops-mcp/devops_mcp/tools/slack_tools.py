"""
Slack Tools for DevOps MCP
==========================
Tools for sending Slack notifications and managing channels.
"""

import os
import httpx
from typing import Any, Optional, List


class SlackTools:
    """Slack notification tools."""
    
    def __init__(self):
        self.token = os.environ.get("SLACK_BOT_TOKEN")
        self.webhook_url = os.environ.get("SLACK_WEBHOOK_URL")
        self.base_url = "https://slack.com/api"
    
    def is_configured(self) -> bool:
        return bool(self.token or self.webhook_url)
    
    def _headers(self):
        return {"Authorization": f"Bearer {self.token}"}
    
    def get_tools(self) -> dict[str, dict]:
        return {
            "slack_send_message": {
                "description": "Send a message to a Slack channel",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "channel": {"type": "string", "description": "Channel ID or name"},
                        "text": {"type": "string", "description": "Message text"},
                        "blocks": {"type": "array", "description": "Block Kit blocks (optional)"},
                        "thread_ts": {"type": "string", "description": "Thread timestamp for replies"},
                    },
                    "required": ["channel", "text"],
                },
                "handler": self.send_message,
            },
            "slack_send_webhook": {
                "description": "Send a message via webhook (no token required)",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "text": {"type": "string", "description": "Message text"},
                        "blocks": {"type": "array", "description": "Block Kit blocks"},
                        "webhook_url": {"type": "string", "description": "Override webhook URL"},
                    },
                    "required": ["text"],
                },
                "handler": self.send_webhook,
            },
            "slack_channel_list": {
                "description": "List Slack channels",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "types": {"type": "string", "description": "Channel types (public_channel,private_channel)", "default": "public_channel"},
                        "limit": {"type": "integer", "default": 100},
                    },
                },
                "handler": self.list_channels,
            },
            "slack_channel_history": {
                "description": "Get channel message history",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "channel": {"type": "string", "description": "Channel ID"},
                        "limit": {"type": "integer", "default": 20},
                    },
                    "required": ["channel"],
                },
                "handler": self.get_channel_history,
            },
            "slack_user_list": {
                "description": "List Slack users",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "limit": {"type": "integer", "default": 100},
                    },
                },
                "handler": self.list_users,
            },
            "slack_react": {
                "description": "Add a reaction to a message",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "channel": {"type": "string", "description": "Channel ID"},
                        "timestamp": {"type": "string", "description": "Message timestamp"},
                        "emoji": {"type": "string", "description": "Emoji name (without colons)"},
                    },
                    "required": ["channel", "timestamp", "emoji"],
                },
                "handler": self.add_reaction,
            },
            "slack_upload_file": {
                "description": "Upload a file to Slack",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "channels": {"type": "string", "description": "Comma-separated channel IDs"},
                        "file_path": {"type": "string", "description": "Local file path"},
                        "title": {"type": "string", "description": "File title"},
                        "initial_comment": {"type": "string", "description": "Message to include"},
                    },
                    "required": ["channels", "file_path"],
                },
                "handler": self.upload_file,
            },
            "slack_notify_deployment": {
                "description": "Send a formatted deployment notification",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "channel": {"type": "string", "description": "Channel ID"},
                        "project": {"type": "string", "description": "Project name"},
                        "environment": {"type": "string", "description": "Environment (production, staging)"},
                        "status": {"type": "string", "enum": ["started", "success", "failed"]},
                        "url": {"type": "string", "description": "Deployment URL"},
                        "commit": {"type": "string", "description": "Commit SHA"},
                        "author": {"type": "string", "description": "Who triggered it"},
                    },
                    "required": ["channel", "project", "environment", "status"],
                },
                "handler": self.notify_deployment,
            },
        }
    
    async def send_message(
        self,
        channel: str,
        text: str,
        blocks: Optional[List[dict]] = None,
        thread_ts: Optional[str] = None,
    ) -> dict:
        body = {
            "channel": channel,
            "text": text,
        }
        if blocks:
            body["blocks"] = blocks
        if thread_ts:
            body["thread_ts"] = thread_ts
        
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self.base_url}/chat.postMessage",
                headers=self._headers(),
                json=body,
            )
            data = resp.json()
        
        return {
            "ok": data.get("ok"),
            "ts": data.get("ts"),
            "channel": data.get("channel"),
            "error": data.get("error"),
        }
    
    async def send_webhook(
        self,
        text: str,
        blocks: Optional[List[dict]] = None,
        webhook_url: Optional[str] = None,
    ) -> dict:
        url = webhook_url or self.webhook_url
        if not url:
            return {"error": "No webhook URL configured"}
        
        body = {"text": text}
        if blocks:
            body["blocks"] = blocks
        
        async with httpx.AsyncClient() as client:
            resp = await client.post(url, json=body)
        
        return {
            "status": resp.status_code,
            "ok": resp.status_code == 200,
        }
    
    async def list_channels(self, types: str = "public_channel", limit: int = 100) -> dict:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self.base_url}/conversations.list",
                headers=self._headers(),
                params={"types": types, "limit": limit},
            )
            data = resp.json()
        
        return {
            "channels": [
                {
                    "id": c["id"],
                    "name": c["name"],
                    "is_private": c.get("is_private", False),
                    "num_members": c.get("num_members", 0),
                }
                for c in data.get("channels", [])
            ]
        }
    
    async def get_channel_history(self, channel: str, limit: int = 20) -> dict:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self.base_url}/conversations.history",
                headers=self._headers(),
                params={"channel": channel, "limit": limit},
            )
            data = resp.json()
        
        return {
            "messages": [
                {
                    "text": m.get("text", ""),
                    "user": m.get("user"),
                    "ts": m.get("ts"),
                    "type": m.get("type"),
                }
                for m in data.get("messages", [])
            ]
        }
    
    async def list_users(self, limit: int = 100) -> dict:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self.base_url}/users.list",
                headers=self._headers(),
                params={"limit": limit},
            )
            data = resp.json()
        
        return {
            "users": [
                {
                    "id": u["id"],
                    "name": u.get("name"),
                    "real_name": u.get("real_name"),
                    "is_bot": u.get("is_bot", False),
                }
                for u in data.get("members", [])
                if not u.get("deleted")
            ]
        }
    
    async def add_reaction(self, channel: str, timestamp: str, emoji: str) -> dict:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self.base_url}/reactions.add",
                headers=self._headers(),
                json={
                    "channel": channel,
                    "timestamp": timestamp,
                    "name": emoji,
                },
            )
            data = resp.json()
        
        return {"ok": data.get("ok"), "error": data.get("error")}
    
    async def upload_file(
        self,
        channels: str,
        file_path: str,
        title: Optional[str] = None,
        initial_comment: Optional[str] = None,
    ) -> dict:
        with open(file_path, "rb") as f:
            file_content = f.read()
        
        data = {
            "channels": channels,
            "filename": os.path.basename(file_path),
        }
        if title:
            data["title"] = title
        if initial_comment:
            data["initial_comment"] = initial_comment
        
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self.base_url}/files.upload",
                headers=self._headers(),
                data=data,
                files={"file": file_content},
            )
            result = resp.json()
        
        return {
            "ok": result.get("ok"),
            "file_id": result.get("file", {}).get("id"),
            "error": result.get("error"),
        }
    
    async def notify_deployment(
        self,
        channel: str,
        project: str,
        environment: str,
        status: str,
        url: Optional[str] = None,
        commit: Optional[str] = None,
        author: Optional[str] = None,
    ) -> dict:
        emoji = {"started": "🚀", "success": "✅", "failed": "❌"}.get(status, "📦")
        color = {"started": "#2196F3", "success": "#36a64f", "failed": "#ff0000"}.get(status, "#808080")
        
        blocks = [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"{emoji} *Deployment {status.upper()}*\n\n*Project:* {project}\n*Environment:* {environment}",
                },
            },
        ]
        
        context_elements = []
        if commit:
            context_elements.append({"type": "mrkdwn", "text": f"Commit: `{commit[:7]}`"})
        if author:
            context_elements.append({"type": "mrkdwn", "text": f"By: {author}"})
        if url:
            context_elements.append({"type": "mrkdwn", "text": f"<{url}|View Deployment>"})
        
        if context_elements:
            blocks.append({"type": "context", "elements": context_elements})
        
        return await self.send_message(
            channel=channel,
            text=f"Deployment {status}: {project} to {environment}",
            blocks=blocks,
        )
