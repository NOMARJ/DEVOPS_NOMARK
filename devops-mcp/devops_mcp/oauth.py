"""
OAuth 2.1 implementation for MCP server with Azure Entra ID.
Supports Dynamic Client Registration (DCR) as required by Claude.ai.
"""

import os
import json
import uuid
import secrets
import hashlib
import base64
from datetime import datetime, timedelta
from typing import Optional
from urllib.parse import urlencode

# Azure Entra ID configuration
AZURE_TENANT_ID = os.environ.get("AZURE_TENANT_ID", "2601808d-88e3-4af3-a6b8-377f2c915782")
AZURE_CLIENT_ID = os.environ.get("MCP_OAUTH_CLIENT_ID", "3297d116-3d21-49af-b7f2-177e6326f6b1")
AZURE_CLIENT_SECRET = os.environ.get("MCP_OAUTH_CLIENT_SECRET", "")

# OAuth endpoints
AZURE_AUTH_URL = f"https://login.microsoftonline.com/{AZURE_TENANT_ID}/oauth2/v2.0/authorize"
AZURE_TOKEN_URL = f"https://login.microsoftonline.com/{AZURE_TENANT_ID}/oauth2/v2.0/token"
AZURE_JWKS_URL = f"https://login.microsoftonline.com/{AZURE_TENANT_ID}/discovery/v2.0/keys"

# In-memory stores (use Redis/DB in production)
_registered_clients = {}
_authorization_codes = {}
_access_tokens = {}
_refresh_tokens = {}


def get_server_url():
    """Get the MCP server URL from environment."""
    return os.environ.get("MCP_SERVER_URL", "https://20-5-185-136.sslip.io")


def get_oauth_metadata():
    """Return OAuth 2.0 Authorization Server Metadata (RFC 8414)."""
    server_url = get_server_url()
    return {
        "issuer": server_url,
        "authorization_endpoint": f"{server_url}/oauth/authorize",
        "token_endpoint": f"{server_url}/oauth/token",
        "registration_endpoint": f"{server_url}/oauth/register",
        "jwks_uri": f"{server_url}/.well-known/jwks.json",
        "scopes_supported": ["openid", "profile", "mcp:tools", "mcp:resources"],
        "response_types_supported": ["code"],
        "response_modes_supported": ["query"],
        "grant_types_supported": ["authorization_code", "refresh_token"],
        "token_endpoint_auth_methods_supported": ["client_secret_basic", "client_secret_post", "none"],
        "code_challenge_methods_supported": ["S256", "plain"],
        "service_documentation": f"{server_url}/docs",
    }


def get_protected_resource_metadata():
    """Return OAuth 2.0 Protected Resource Metadata."""
    server_url = get_server_url()
    return {
        "resource": server_url,
        "authorization_servers": [server_url],
        "scopes_supported": ["mcp:tools", "mcp:resources"],
        "bearer_methods_supported": ["header"],
    }


def register_client(client_metadata: dict) -> dict:
    """
    Dynamic Client Registration (RFC 7591).
    Claude.ai will call this to register itself as a client.
    """
    client_id = str(uuid.uuid4())
    client_secret = secrets.token_urlsafe(32)

    client_data = {
        "client_id": client_id,
        "client_secret": client_secret,
        "client_id_issued_at": int(datetime.utcnow().timestamp()),
        "client_secret_expires_at": 0,  # Never expires
        "redirect_uris": client_metadata.get("redirect_uris", []),
        "token_endpoint_auth_method": client_metadata.get("token_endpoint_auth_method", "client_secret_basic"),
        "grant_types": client_metadata.get("grant_types", ["authorization_code", "refresh_token"]),
        "response_types": client_metadata.get("response_types", ["code"]),
        "client_name": client_metadata.get("client_name", "Unknown Client"),
        "scope": client_metadata.get("scope", "mcp:tools mcp:resources"),
    }

    _registered_clients[client_id] = client_data
    return client_data


def get_client(client_id: str) -> Optional[dict]:
    """Get a registered client."""
    return _registered_clients.get(client_id)


def create_authorization_code(client_id: str, redirect_uri: str, scope: str, code_challenge: str = None, code_challenge_method: str = None) -> str:
    """Create an authorization code for the OAuth flow."""
    code = secrets.token_urlsafe(32)
    _authorization_codes[code] = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "scope": scope,
        "code_challenge": code_challenge,
        "code_challenge_method": code_challenge_method,
        "created_at": datetime.utcnow(),
        "expires_at": datetime.utcnow() + timedelta(minutes=10),
    }
    return code


def exchange_code_for_tokens(code: str, client_id: str, redirect_uri: str, code_verifier: str = None) -> Optional[dict]:
    """Exchange authorization code for access and refresh tokens."""
    auth_code = _authorization_codes.get(code)
    if not auth_code:
        return None

    # Validate code
    if auth_code["client_id"] != client_id:
        return None
    if auth_code["redirect_uri"] != redirect_uri:
        return None
    if auth_code["expires_at"] < datetime.utcnow():
        del _authorization_codes[code]
        return None

    # Validate PKCE if used
    if auth_code.get("code_challenge"):
        if not code_verifier:
            return None
        if auth_code["code_challenge_method"] == "S256":
            expected = base64.urlsafe_b64encode(
                hashlib.sha256(code_verifier.encode()).digest()
            ).rstrip(b"=").decode()
        else:
            expected = code_verifier
        if expected != auth_code["code_challenge"]:
            return None

    # Delete used code
    del _authorization_codes[code]

    # Create tokens
    access_token = secrets.token_urlsafe(32)
    refresh_token = secrets.token_urlsafe(32)
    expires_in = 3600  # 1 hour

    _access_tokens[access_token] = {
        "client_id": client_id,
        "scope": auth_code["scope"],
        "created_at": datetime.utcnow(),
        "expires_at": datetime.utcnow() + timedelta(seconds=expires_in),
    }

    _refresh_tokens[refresh_token] = {
        "client_id": client_id,
        "scope": auth_code["scope"],
        "created_at": datetime.utcnow(),
    }

    return {
        "access_token": access_token,
        "token_type": "Bearer",
        "expires_in": expires_in,
        "refresh_token": refresh_token,
        "scope": auth_code["scope"],
    }


def refresh_access_token(refresh_token: str, client_id: str) -> Optional[dict]:
    """Refresh an access token using a refresh token."""
    token_data = _refresh_tokens.get(refresh_token)
    if not token_data or token_data["client_id"] != client_id:
        return None

    # Create new access token
    access_token = secrets.token_urlsafe(32)
    expires_in = 3600

    _access_tokens[access_token] = {
        "client_id": client_id,
        "scope": token_data["scope"],
        "created_at": datetime.utcnow(),
        "expires_at": datetime.utcnow() + timedelta(seconds=expires_in),
    }

    return {
        "access_token": access_token,
        "token_type": "Bearer",
        "expires_in": expires_in,
        "refresh_token": refresh_token,
        "scope": token_data["scope"],
    }


def validate_access_token(token: str) -> Optional[dict]:
    """Validate an access token and return its data."""
    token_data = _access_tokens.get(token)
    if not token_data:
        return None
    if token_data["expires_at"] < datetime.utcnow():
        del _access_tokens[token]
        return None
    return token_data


def get_jwks():
    """Return empty JWKS (we use opaque tokens, not JWTs)."""
    return {"keys": []}
