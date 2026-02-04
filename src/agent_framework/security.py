"""
Agent Security - Authentication and Authorization
"""

import hashlib
import hmac
import time
import secrets
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass, field
from enum import Enum

from .logger import get_logger

logger = get_logger(__name__)


class Permission(Enum):
    """Permission types"""
    READ = "read"
    WRITE = "write"
    EXECUTE = "execute"
    ADMIN = "admin"
    ALL = "all"


@dataclass
class Role:
    """Role definition"""
    name: str
    permissions: List[Permission] = field(default_factory=list)
    description: str = ""


@dataclass
class User:
    """User definition"""
    username: str
    password_hash: str = ""
    roles: List[str] = field(default_factory=list)
    api_key: str = ""
    created_at: float = field(default_factory=time.time)


class AuthManager:
    """
    Authentication and authorization manager
    
    Provides:
    - User authentication
    - Role-based access control
    - API key management
    - Permission checking
    """
    
    def __init__(self):
        """Initialize auth manager"""
        self.users: Dict[str, User] = {}
        self.roles: Dict[str, Role] = {}
        self.api_keys: Dict[str, User] = {}
        self._init_default_roles()
    
    def _init_default_roles(self):
        """Initialize default roles"""
        # Admin role
        admin_role = Role(
            name="admin",
            permissions=[Permission.ALL],
            description="Full access to all resources"
        )
        self.roles["admin"] = admin_role
        
        # User role
        user_role = Role(
            name="user",
            permissions=[Permission.READ, Permission.WRITE],
            description="Read and write access"
        )
        self.roles["user"] = user_role
        
        # Read-only role
        readonly_role = Role(
            name="readonly",
            permissions=[Permission.READ],
            description="Read-only access"
        )
        self.roles["readonly"] = readonly_role
    
    def create_user(self, username: str, password: str, roles: List[str] = None) -> User:
        """
        Create a new user
        
        Args:
            username: Username
            password: Password
            roles: List of role names
            
        Returns:
            Created user
        """
        if username in self.users:
            raise ValueError(f"User already exists: {username}")
        
        # Generate password hash
        password_hash = self._hash_password(password)
        
        # Generate API key
        api_key = self._generate_api_key()
        
        user = User(
            username=username,
            password_hash=password_hash,
            roles=roles or ["readonly"],
            api_key=api_key
        )
        
        self.users[username] = user
        self.api_keys[api_key] = user
        
        logger.info(f"Created user: {username}")
        return user
    
    def authenticate(self, username: str, password: str) -> bool:
        """
        Authenticate a user
        
        Args:
            username: Username
            password: Password
            
        Returns:
            True if authenticated
        """
        user = self.users.get(username)
        if not user:
            return False
        
        return self._verify_password(password, user.password_hash)
    
    def authenticate_api_key(self, api_key: str) -> Optional[User]:
        """
        Authenticate using API key
        
        Args:
            api_key: API key
            
        Returns:
            User if authenticated
        """
        return self.api_keys.get(api_key)
    
    def check_permission(self, user: User, permission: Permission, resource: str = None) -> bool:
        """
        Check if user has permission
        
        Args:
            user: User
            permission: Permission
            resource: Resource (optional)
            
        Returns:
            True if has permission
        """
        for role_name in user.roles:
            role = self.roles.get(role_name)
            if role:
                if Permission.ALL in role.permissions:
                    return True
                if permission in role.permissions:
                    return True
        
        return False
    
    def get_user(self, username: str) -> Optional[User]:
        """Get user by username"""
        return self.users.get(username)
    
    def list_users(self) -> List[User]:
        """List all users"""
        return list(self.users.values())
    
    def _hash_password(self, password: str) -> str:
        """Hash password"""
        salt = secrets.token_hex(16)
        hashed = hashlib.pbkdf2_hmac(
            'sha256',
            password.encode(),
            salt.encode(),
            100000
        ).hex()
        return f"{salt}${hashed}"
    
    def _verify_password(self, password: str, password_hash: str) -> bool:
        """Verify password"""
        try:
            salt, hashed = password_hash.split('$')
            computed = hashlib.pbkdf2_hmac(
                'sha256',
                password.encode(),
                salt.encode(),
                100000
            ).hex()
            return hmac.compare_digest(computed, hashed)
        except Exception:
            return False
    
    def _generate_api_key(self) -> str:
        """Generate API key"""
        return secrets.token_urlsafe(32)


class AuditLogger:
    """
    Audit logger for security events
    
    Provides:
    - Event logging
    - Audit trail
    - Security monitoring
    """
    
    def __init__(self):
        """Initialize audit logger"""
        self.events: List[Dict[str, Any]] = []
        self.logger = get_logger(__name__)
    
    def log_event(self, event_type: str, user: str, details: Dict[str, Any] = None) -> None:
        """
        Log a security event
        
        Args:
            event_type: Event type
            user: Username
            details: Event details
        """
        event = {
            "event_type": event_type,
            "user": user,
            "timestamp": time.time(),
            "details": details or {}
        }
        
        self.events.append(event)
        self.logger.info(f"Security event: {event_type} by {user}")
    
    def get_events(self, user: str = None, event_type: str = None, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get audit events
        
        Args:
            user: Filter by user (optional)
            event_type: Filter by event type (optional)
            limit: Maximum number of events
            
        Returns:
            List of events
        """
        events = self.events
        
        if user:
            events = [e for e in events if e["user"] == user]
        
        if event_type:
            events = [e for e in events if e["event_type"] == event_type]
        
        return events[-limit:]


class SecurityContext:
    """
    Security context for operations
    
    Provides:
    - User context
    - Permission checking
    - Security validation
    """
    
    def __init__(self, auth_manager: AuthManager):
        """
        Initialize security context
        
        Args:
            auth_manager: Auth manager
        """
        self.auth_manager = auth_manager
        self.current_user: Optional[User] = None
        self.audit_logger = AuditLogger()
    
    def login(self, username: str, password: str) -> bool:
        """
        Login user
        
        Args:
            username: Username
            password: Password
            
        Returns:
            True if successful
        """
        if not self.auth_manager.authenticate(username, password):
            self.audit_logger.log_event("login_failed", username)
            return False
        
        self.current_user = self.auth_manager.get_user(username)
        self.audit_logger.log_event("login_success", username)
        return True
    
    def logout(self) -> None:
        """Logout current user"""
        if self.current_user:
            username = self.current_user.username
            self.current_user = None
            self.audit_logger.log_event("logout", username)
    
    def check_permission(self, permission: Permission, resource: str = None) -> bool:
        """
        Check if current user has permission
        
        Args:
            permission: Permission
            resource: Resource (optional)
            
        Returns:
            True if has permission
        """
        if not self.current_user:
            return False
        
        return self.auth_manager.check_permission(self.current_user, permission, resource)
    
    def require_permission(self, permission: Permission, resource: str = None):
        """
        Decorator to require permission
        
        Args:
            permission: Required permission
            resource: Resource (optional)
            
        Returns:
            Decorator
        """
        def decorator(func):
            async def wrapper(*args, **kwargs):
                if not self.check_permission(permission, resource):
                    raise PermissionError(f"Permission required: {permission}")
                return await func(*args, **kwargs)
            return wrapper
        return decorator
    
    def get_current_user(self) -> Optional[User]:
        """Get current user"""
        return self.current_user


def get_auth_manager() -> AuthManager:
    """Get global auth manager instance"""
    if not hasattr(get_auth_manager, "_instance"):
        get_auth_manager._instance = AuthManager()
    return get_auth_manager._instance


def get_security_context() -> SecurityContext:
    """Get global security context instance"""
    if not hasattr(get_security_context, "_instance"):
        get_security_context._instance = SecurityContext(get_auth_manager())
    return get_security_context._instance
