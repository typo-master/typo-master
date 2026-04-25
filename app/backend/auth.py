"""GitHub OAuth authentication and JWT token management."""

import asyncio
import os
import time
from typing import Any, Dict, Optional

import httpx
import jwt
from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.backend.models import AuthToken
from app.backend.storage import MySQLStorage

# JWT 配置
JWT_SECRET = os.getenv("JWT_SECRET", "typomaster-dev-secret-change-in-prod")
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_SECONDS = int(os.getenv("JWT_EXPIRATION_SECONDS", "86400"))  # 24h

# GitHub OAuth 配置
GITHUB_CLIENT_ID = os.getenv("GITHUB_CLIENT_ID", "")
GITHUB_CLIENT_SECRET = os.getenv("GITHUB_CLIENT_SECRET", "")
GITHUB_OAUTH_AUTHORIZE_URL = "https://github.com/login/oauth/authorize"
GITHUB_OAUTH_TOKEN_URL = "https://github.com/login/oauth/access_token"
GITHUB_API_USER_URL = "https://api.github.com/user"

security_scheme = HTTPBearer(auto_error=False)


def get_github_auth_url(state: str) -> str:
    """Generate GitHub OAuth authorization URL."""
    if not GITHUB_CLIENT_ID:
        raise HTTPException(status_code=500, detail="GITHUB_CLIENT_ID is not configured")
    return (
        f"{GITHUB_OAUTH_AUTHORIZE_URL}"
        f"?client_id={GITHUB_CLIENT_ID}"
        f"&state={state}"
        f"&scope=read:user,user:email"
    )


async def exchange_github_code(code: str) -> str:
    """Exchange GitHub OAuth code for access token."""
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            GITHUB_OAUTH_TOKEN_URL,
            json={
                "client_id": GITHUB_CLIENT_ID,
                "client_secret": GITHUB_CLIENT_SECRET,
                "code": code,
            },
            headers={"Accept": "application/json"},
        )
        data = resp.json()
        access_token = data.get("access_token")
        if not access_token:
            raise HTTPException(status_code=400, detail=f"GitHub OAuth failed: {data.get('error_description', 'unknown error')}")
        return access_token


async def get_github_user_info(access_token: str) -> Dict[str, Any]:
    """Fetch GitHub user profile using access token."""
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            GITHUB_API_USER_URL,
            headers={
                "Authorization": f"Bearer {access_token}",
                "Accept": "application/json",
            },
        )
        if resp.status_code != 200:
            raise HTTPException(status_code=400, detail="Failed to fetch GitHub user info")
        user_data = resp.json()

        # Try to fetch primary email if not public
        email = user_data.get("email")
        if not email:
            try:
                email_resp = await client.get(
                    "https://api.github.com/user/emails",
                    headers={
                        "Authorization": f"Bearer {access_token}",
                        "Accept": "application/json",
                    },
                )
                if email_resp.status_code == 200:
                    emails = email_resp.json()
                    primary = next((e for e in emails if e.get("primary")), None)
                    if primary:
                        email = primary.get("email")
            except Exception:
                pass

        return {
            "github_id": user_data["id"],
            "username": user_data["login"],
            "display_name": user_data.get("name") or user_data["login"],
            "avatar_url": user_data.get("avatar_url", ""),
            "email": email,
            "bio": user_data.get("bio"),
        }


def create_jwt_token(user_id: str, username: str) -> str:
    """Create a JWT token for the given user."""
    now = int(time.time())
    payload = {
        "user_id": user_id,
        "username": username,
        "iat": now,
        "exp": now + JWT_EXPIRATION_SECONDS,
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def verify_jwt_token(token: str) -> Optional[Dict[str, Any]]:
    """Verify and decode a JWT token. Returns payload or None."""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
        return None


async def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_scheme),
) -> Optional[Dict[str, Any]]:
    """FastAPI dependency: extract and verify current user from JWT.

    Returns None if no token provided (anonymous access).
    Raises 401 if token is invalid/expired.
    """
    if credentials is None:
        return None
    payload = verify_jwt_token(credentials.credentials)
    if payload is None:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    storage: MySQLStorage = request.app.state.storage
    user = await asyncio.to_thread(storage.get_user_by_id, payload["user_id"])
    if user is None or not user.get("is_active", False):
        raise HTTPException(status_code=401, detail="User not found or inactive")
    return user


async def require_login(
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user),
) -> Dict[str, Any]:
    """FastAPI dependency: require authenticated user (401 if anonymous)."""
    if current_user is None:
        raise HTTPException(status_code=401, detail="Login required")
    return current_user
