#!/usr/bin/env python3
"""
DevOps MCP Server
=================
A Model Context Protocol server providing tools for infrastructure management.

Integrations:
- Azure (VMs, Container Apps, Storage, Key Vault)
- Supabase (Database, Auth, Storage)
- Vercel (Deployments)
- GitHub (Repos, PRs, Actions)
- n8n (Workflows)
- Slack (Notifications)

Usage:
    python -m devops_mcp                    # stdio mode (for Claude Desktop/Code)
    python -m devops_mcp --sse --port 8080  # SSE mode (for Claude.ai connector)
"""

import argparse
import asyncio
import json
import os
import logging
from typing import Any, Optional
from datetime import datetime

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import (
    Tool,
    TextContent,
    Resource,
    ResourceTemplate,
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("devops-mcp")

# Import tool modules
from .tools.azure_tools import AzureTools
from .tools.supabase_tools import SupabaseTools
from .tools.github_tools import GitHubTools
from .tools.vercel_tools import VercelTools
from .tools.n8n_tools import N8nTools
from .tools.slack_tools import SlackTools
from .tools.skills_tools import SkillsTools
from .tools.carbone_tools import CarboneTools
from .tools.metabase_tools import MetabaseTools

# Initialize server
server = Server("devops-mcp")

# Initialize tool providers
azure = AzureTools()
supabase = SupabaseTools()
github = GitHubTools()
vercel = VercelTools()
n8n = N8nTools()
slack = SlackTools()
skills = SkillsTools()
carbone = CarboneTools()
metabase = MetabaseTools()

# Collect all tools
ALL_TOOLS = {
    **azure.get_tools(),
    **supabase.get_tools(),
    **github.get_tools(),
    **vercel.get_tools(),
    **n8n.get_tools(),
    **slack.get_tools(),
    **skills.get_tools(),
    **carbone.get_tools(),
    **metabase.get_tools(),
}


@server.list_tools()
async def list_tools() -> list[Tool]:
    """List all available DevOps tools."""
    return [
        Tool(
            name=name,
            description=tool["description"],
            inputSchema=tool["input_schema"],
        )
        for name, tool in ALL_TOOLS.items()
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    """Execute a DevOps tool."""
    if name not in ALL_TOOLS:
        return [TextContent(type="text", text=f"Unknown tool: {name}")]

    tool = ALL_TOOLS[name]
    handler = tool["handler"]

    try:
        result = await handler(**arguments)
        return [TextContent(type="text", text=json.dumps(result, indent=2, default=str))]
    except Exception as e:
        return [TextContent(type="text", text=f"Error executing {name}: {str(e)}")]


@server.list_resources()
async def list_resources() -> list[Resource]:
    """List available resources (skills, configs, etc.)."""
    resources = []
    
    # Add skills as resources
    skills_manifest = skills.get_manifest()
    for skill in skills_manifest.get("skills", []):
        resources.append(
            Resource(
                uri=f"skill://{skill['id']}",
                name=skill["name"],
                description=skill.get("description", ""),
                mimeType="text/markdown",
            )
        )
    
    # Add config resources
    resources.append(
        Resource(
            uri="config://devops-mcp",
            name="DevOps MCP Configuration",
            description="Current MCP server configuration and status",
            mimeType="application/json",
        )
    )
    
    return resources


@server.read_resource()
async def read_resource(uri: str) -> str:
    """Read a resource by URI."""
    if uri.startswith("skill://"):
        skill_id = uri.replace("skill://", "")
        return skills.get_skill_content(skill_id)
    
    if uri == "config://devops-mcp":
        return json.dumps({
            "version": "1.0.0",
            "integrations": {
                "azure": azure.is_configured(),
                "supabase": supabase.is_configured(),
                "github": github.is_configured(),
                "vercel": vercel.is_configured(),
                "n8n": n8n.is_configured(),
                "slack": slack.is_configured(),
            },
            "tools_count": len(ALL_TOOLS),
            "timestamp": datetime.utcnow().isoformat(),
        }, indent=2)
    
    return f"Resource not found: {uri}"


@server.list_resource_templates()
async def list_resource_templates() -> list[ResourceTemplate]:
    """List resource templates for dynamic resources."""
    return [
        ResourceTemplate(
            uriTemplate="skill://{skill_id}",
            name="Skill Documentation",
            description="Get documentation for a specific skill",
        ),
        ResourceTemplate(
            uriTemplate="azure://vm/{resource_group}/{vm_name}",
            name="Azure VM Details",
            description="Get details about a specific Azure VM",
        ),
        ResourceTemplate(
            uriTemplate="supabase://table/{table_name}",
            name="Supabase Table Schema",
            description="Get schema for a Supabase table",
        ),
    ]


async def run_stdio():
    """Run the MCP server in stdio mode (for Claude Desktop/Code)."""
    logger.info("Starting DevOps MCP in stdio mode")
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options(),
        )


def run_sse(host: str, port: int, auth_token: str = None):
    """Run the MCP server in SSE mode (for Claude.ai connector)."""
    try:
        from mcp.server.sse import SseServerTransport
        from starlette.applications import Starlette
        from starlette.routing import Route, Mount
        from starlette.responses import JSONResponse, Response, RedirectResponse
        from starlette.middleware import Middleware
        from starlette.middleware.cors import CORSMiddleware
        import uvicorn
    except ImportError as e:
        logger.error(f"SSE mode requires additional dependencies: {e}")
        logger.error("Install with: pip install 'mcp[sse]' starlette uvicorn")
        return

    # Import OAuth module
    from .oauth import (
        get_oauth_metadata,
        get_protected_resource_metadata,
        register_client,
        create_authorization_code,
        exchange_code_for_tokens,
        refresh_access_token,
        validate_access_token,
        get_jwks,
    )

    # Get auth token from env if not provided
    if auth_token is None:
        auth_token = os.environ.get("MCP_AUTH_TOKEN")

    # Create SSE transport - client will POST to /messages
    sse_transport = SseServerTransport("/messages")

    def check_auth(request) -> bool:
        """Check if request has valid authentication via OAuth or static token."""
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]
            # Check OAuth token first
            if validate_access_token(token):
                return True
            # Fall back to static token
            if auth_token and token == auth_token:
                return True
            return False
        # Allow unauthenticated if no auth configured
        if not auth_token:
            return True
        return False

    async def sse_app(scope, receive, send):
        """ASGI app for SSE connections."""
        from starlette.requests import Request
        request = Request(scope, receive)

        # Check auth for SSE connections
        if not check_auth(request):
            logger.warning(f"Unauthorized SSE connection attempt from {request.client}")
            response = Response("Unauthorized", status_code=401)
            await response(scope, receive, send)
            return

        logger.info(f"SSE connection from {request.client}")
        try:
            async with sse_transport.connect_sse(scope, receive, send) as streams:
                await server.run(
                    streams[0],
                    streams[1],
                    server.create_initialization_options(),
                )
        except Exception as e:
            logger.error(f"SSE error: {e}")

    async def messages_app(scope, receive, send):
        """ASGI app for POST messages."""
        from starlette.requests import Request
        request = Request(scope, receive)

        # Check auth for message posts
        if not check_auth(request):
            logger.warning(f"Unauthorized message attempt from {request.client}")
            response = Response("Unauthorized", status_code=401)
            await response(scope, receive, send)
            return

        await sse_transport.handle_post_message(scope, receive, send)

    async def health_check(request):
        """Health check endpoint."""
        return JSONResponse({
            "status": "healthy",
            "service": "devops-mcp",
            "version": "1.0.0",
            "tools_count": len(ALL_TOOLS),
            "auth_required": bool(auth_token),
            "timestamp": datetime.now().isoformat(),
        })

    async def list_tools_endpoint(request):
        """List available tools (for debugging)."""
        return JSONResponse({
            "tools": [
                {"name": name, "description": tool["description"]}
                for name, tool in ALL_TOOLS.items()
            ]
        })

    # OAuth 2.0 endpoints
    async def oauth_authorization_server_metadata(request):
        """RFC 8414 - OAuth 2.0 Authorization Server Metadata."""
        return JSONResponse(get_oauth_metadata())

    async def oauth_protected_resource_metadata(request):
        """OAuth 2.0 Protected Resource Metadata."""
        return JSONResponse(get_protected_resource_metadata())

    async def oauth_protected_resource_sse(request):
        """OAuth 2.0 Protected Resource Metadata for /sse path."""
        return JSONResponse(get_protected_resource_metadata())

    async def oauth_jwks(request):
        """JWKS endpoint."""
        return JSONResponse(get_jwks())

    async def oauth_register(request):
        """Dynamic Client Registration (RFC 7591)."""
        try:
            body = await request.json()
            client_data = register_client(body)
            logger.info(f"Registered new OAuth client: {client_data['client_id']}")
            return JSONResponse(client_data, status_code=201)
        except Exception as e:
            logger.error(f"Client registration failed: {e}")
            return JSONResponse({"error": "invalid_client_metadata"}, status_code=400)

    async def oauth_authorize(request):
        """Authorization endpoint - auto-approve for simplicity."""
        client_id = request.query_params.get("client_id")
        redirect_uri = request.query_params.get("redirect_uri")
        response_type = request.query_params.get("response_type")
        scope = request.query_params.get("scope", "mcp:tools mcp:resources")
        state = request.query_params.get("state", "")
        code_challenge = request.query_params.get("code_challenge")
        code_challenge_method = request.query_params.get("code_challenge_method", "plain")

        if response_type != "code":
            return JSONResponse({"error": "unsupported_response_type"}, status_code=400)

        # Auto-approve and create authorization code
        code = create_authorization_code(
            client_id=client_id,
            redirect_uri=redirect_uri,
            scope=scope,
            code_challenge=code_challenge,
            code_challenge_method=code_challenge_method,
        )

        # Redirect back with code
        redirect_url = f"{redirect_uri}?code={code}"
        if state:
            redirect_url += f"&state={state}"

        logger.info(f"OAuth authorization granted for client {client_id}")
        return RedirectResponse(url=redirect_url, status_code=302)

    async def oauth_token(request):
        """Token endpoint."""
        import base64
        try:
            # Support both form and JSON
            content_type = request.headers.get("content-type", "")
            if "application/json" in content_type:
                body = await request.json()
            else:
                form = await request.form()
                body = dict(form)

            grant_type = body.get("grant_type")
            client_id = body.get("client_id")
            client_secret = body.get("client_secret")

            # Also check Basic auth
            auth_header = request.headers.get("authorization", "")
            if auth_header.startswith("Basic "):
                decoded = base64.b64decode(auth_header[6:]).decode()
                client_id, client_secret = decoded.split(":", 1)

            if grant_type == "authorization_code":
                code = body.get("code")
                redirect_uri = body.get("redirect_uri")
                code_verifier = body.get("code_verifier")

                tokens = exchange_code_for_tokens(code, client_id, redirect_uri, code_verifier)
                if tokens:
                    logger.info(f"OAuth tokens issued for client {client_id}")
                    return JSONResponse(tokens)
                return JSONResponse({"error": "invalid_grant"}, status_code=400)

            elif grant_type == "refresh_token":
                refresh_token_val = body.get("refresh_token")
                tokens = refresh_access_token(refresh_token_val, client_id)
                if tokens:
                    return JSONResponse(tokens)
                return JSONResponse({"error": "invalid_grant"}, status_code=400)

            return JSONResponse({"error": "unsupported_grant_type"}, status_code=400)

        except Exception as e:
            logger.error(f"Token endpoint error: {e}")
            return JSONResponse({"error": "server_error"}, status_code=500)

    # Create Starlette app with CORS - allow all origins for Claude.ai compatibility
    app = Starlette(
        debug=True,
        routes=[
            # Health and tools
            Route("/health", health_check, methods=["GET"]),
            Route("/tools", list_tools_endpoint, methods=["GET"]),
            # OAuth 2.0 discovery endpoints
            Route("/.well-known/oauth-authorization-server", oauth_authorization_server_metadata, methods=["GET"]),
            Route("/.well-known/oauth-protected-resource", oauth_protected_resource_metadata, methods=["GET"]),
            Route("/.well-known/oauth-protected-resource/sse", oauth_protected_resource_sse, methods=["GET"]),
            Route("/.well-known/jwks.json", oauth_jwks, methods=["GET"]),
            # OAuth 2.0 endpoints
            Route("/oauth/register", oauth_register, methods=["POST"]),
            Route("/oauth/authorize", oauth_authorize, methods=["GET"]),
            Route("/oauth/token", oauth_token, methods=["POST"]),
            # Legacy /register endpoint (some clients use this)
            Route("/register", oauth_register, methods=["POST"]),
            # MCP SSE endpoints
            Mount("/sse", app=sse_app),
            Mount("/messages", app=messages_app),
        ],
        middleware=[
            Middleware(
                CORSMiddleware,
                allow_origins=["*"],  # Allow all for Claude.ai
                allow_credentials=True,
                allow_methods=["GET", "POST", "OPTIONS"],
                allow_headers=["*"],
            )
        ],
    )

    logger.info(f"Starting DevOps MCP SSE server on {host}:{port}")
    logger.info(f"SSE endpoint: http://{host}:{port}/sse")
    logger.info(f"OAuth endpoints: /oauth/authorize, /oauth/token, /oauth/register")
    logger.info(f"Health check: http://{host}:{port}/health")

    uvicorn.run(app, host=host, port=port, log_level="info")


def main():
    """Main entry point with CLI argument parsing."""
    parser = argparse.ArgumentParser(
        description="DevOps MCP Server - Infrastructure management tools for Claude"
    )
    parser.add_argument(
        "--sse",
        action="store_true",
        help="Run in SSE mode for Claude.ai connector (default: stdio mode)"
    )
    parser.add_argument(
        "--host",
        default="0.0.0.0",
        help="Host to bind SSE server (default: 0.0.0.0)"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8080,
        help="Port for SSE server (default: 8080)"
    )
    parser.add_argument(
        "--auth-token",
        default=None,
        help="Bearer token for authentication (or set MCP_AUTH_TOKEN env var)"
    )

    args = parser.parse_args()

    if args.sse:
        run_sse(args.host, args.port, args.auth_token)
    else:
        asyncio.run(run_stdio())


if __name__ == "__main__":
    main()
