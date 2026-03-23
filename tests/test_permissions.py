"""
Tests for permissions API endpoints
"""

import pytest
import asyncio
from pathlib import Path
import tempfile
import yaml

from src.agent_framework.permissions import (
    normalize_permissions,
    set_current_permissions,
    get_current_permissions,
    is_permission_allowed,
    get_permission_denial_message,
    DEFAULT_PERMISSIONS,
    REMOTE_PERMISSIONS,
)


class TestPermissionsHelpers:
    """Test cases for permissions helper functions"""

    def test_normalize_permissions_defaults(self):
        """Test that normalize_permissions returns defaults when given None"""
        result = normalize_permissions(None)
        assert result["global_remote_enabled"] is False
        assert result["git_push"] is False
        assert result["fs_read"] is True

    def test_normalize_permissions_override(self):
        """Test that normalize_permissions respects overrides"""
        result = normalize_permissions({"git_push": True, "fs_write": True})
        assert result["git_push"] is True
        assert result["fs_write"] is True
        assert result["fs_read"] is True  # unchanged default

    def test_is_permission_allowed_with_global_off(self):
        """Test that remote permissions are denied when global is off"""
        permissions = {"global_remote_enabled": False, "git_push": True}
        assert is_permission_allowed("git_push", permissions) is False
        assert is_permission_allowed("fs_read", permissions) is True  # local permission

    def test_is_permission_allowed_with_global_on(self):
        """Test that remote permissions are allowed when global is on and permission is enabled"""
        permissions = {"global_remote_enabled": True, "git_push": True}
        assert is_permission_allowed("git_push", permissions) is True

    def test_is_permission_allowed_specific_off(self):
        """Test that specific permission off is respected even when global is on"""
        permissions = {"global_remote_enabled": True, "git_push": False}
        assert is_permission_allowed("git_push", permissions) is False

    def test_get_permission_denial_message_global_off(self):
        """Test that denial message mentions global switch when it's off"""
        permissions = {"global_remote_enabled": False, "git_push": True}
        set_current_permissions(permissions)
        msg = get_permission_denial_message("git_push")
        assert "global_remote_enabled" in msg
        assert "总开关" in msg

    def test_get_permission_denial_message_specific_off(self):
        """Test that denial message mentions specific permission when global is on"""
        permissions = {"global_remote_enabled": True, "git_push": False}
        set_current_permissions(permissions)
        msg = get_permission_denial_message("git_push")
        assert "git_push" in msg
        assert "权限" in msg

    def test_remote_permissions_set(self):
        """Test that REMOTE_PERMISSIONS contains expected keys"""
        assert "git_push" in REMOTE_PERMISSIONS
        assert "pr_create" in REMOTE_PERMISSIONS
        assert "api_call" in REMOTE_PERMISSIONS
        assert "fs_read" not in REMOTE_PERMISSIONS  # local permission


class TestPermissionsGlobalSwitch:
    """Test cases for the global permissions switch"""

    def test_global_switch_affects_all_remote(self):
        """Test that turning off global switch denies all remote permissions"""
        permissions = {"global_remote_enabled": False}
        for remote_perm in REMOTE_PERMISSIONS:
            permissions[remote_perm] = True  # Try to enable each remote permission

        set_current_permissions(permissions)

        for remote_perm in REMOTE_PERMISSIONS:
            assert is_permission_allowed(remote_perm) is False, f"{remote_perm} should be denied when global is off"

    def test_global_switch_does_not_affect_local(self):
        """Test that turning off global switch doesn't affect local permissions"""
        permissions = {
            "global_remote_enabled": False,
            "fs_read": True,
            "git_checkout": True,
            "git_add": True,
        }
        set_current_permissions(permissions)

        assert is_permission_allowed("fs_read") is True
        assert is_permission_allowed("git_checkout") is True
        assert is_permission_allowed("git_add") is True

    def test_global_switch_on_allows_remote(self):
        """Test that turning on global switch allows remote permissions"""
        permissions = {"global_remote_enabled": True, "git_push": True, "pr_create": True}
        set_current_permissions(permissions)

        assert is_permission_allowed("git_push") is True
        assert is_permission_allowed("pr_create") is True


class TestPermissionsConfig:
    """Test cases for permissions configuration loading"""

    def test_default_permissions_structure(self):
        """Test that DEFAULT_PERMISSIONS has the expected structure"""
        assert "global_remote_enabled" in DEFAULT_PERMISSIONS
        assert DEFAULT_PERMISSIONS["global_remote_enabled"] is False
        assert "llm_request" in DEFAULT_PERMISSIONS
        assert DEFAULT_PERMISSIONS["llm_request"] is True

    def test_normalize_ignores_unknown_keys(self):
        """Test that normalize_permissions ignores unknown permission keys"""
        result = normalize_permissions({"unknown_permission": True, "git_push": True})
        assert "unknown_permission" not in result
        assert result["git_push"] is True


@pytest.mark.asyncio
class TestPermissionsIntegration:
    """Integration tests for permissions system"""

    async def test_global_switch_blocks_remote_execution(self):
        """Test that remote operations are blocked when global switch is off"""
        from app.agent.runtime import TypeAgentRuntime

        # Create runtime with global switch off
        permissions = {"global_remote_enabled": False, "api_call": True}
        set_current_permissions(normalize_permissions(permissions))

        # MCP execution should be blocked
        assert is_permission_allowed("api_call") is False

    async def test_global_switch_allows_remote_when_on(self):
        """Test that remote operations are allowed when global switch is on"""
        permissions = {"global_remote_enabled": True, "api_call": True}
        set_current_permissions(normalize_permissions(permissions))

        assert is_permission_allowed("api_call") is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
