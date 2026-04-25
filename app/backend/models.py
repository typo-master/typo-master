"""User data models for authentication."""

from dataclasses import dataclass
from typing import Optional


@dataclass
class User:
    """Represents a registered user."""
    user_id: str
    github_id: int
    username: str
    display_name: str
    avatar_url: str
    email: Optional[str] = None
    bio: Optional[str] = None
    created_at: str = ""
    last_login_at: str = ""
    is_active: bool = True


@dataclass
class AuthToken:
    """JWT token payload."""
    user_id: str
    username: str
    exp: int = 0
    iat: int = 0
