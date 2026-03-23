"""
Simple tests for permissions system (without pytest-asyncio dependency)
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.agent_framework.permissions import (
    normalize_permissions,
    set_current_permissions,
    get_current_permissions,
    is_permission_allowed,
    get_permission_denial_message,
    DEFAULT_PERMISSIONS,
    REMOTE_PERMISSIONS,
)


def test_normalize_permissions_defaults():
    """Test that normalize_permissions returns defaults when given None"""
    result = normalize_permissions(None)
    assert result["global_remote_enabled"] is False
    assert result["git_push"] is False
    assert result["fs_read"] is True
    print("✓ test_normalize_permissions_defaults passed")


def test_normalize_permissions_override():
    """Test that normalize_permissions respects overrides"""
    result = normalize_permissions({"git_push": True, "fs_write": True})
    assert result["git_push"] is True
    assert result["fs_write"] is True
    assert result["fs_read"] is True  # unchanged default
    print("✓ test_normalize_permissions_override passed")


def test_is_permission_allowed_with_global_off():
    """Test that remote permissions are denied when global is off"""
    permissions = {"global_remote_enabled": False, "git_push": True}
    assert is_permission_allowed("git_push", permissions) is False
    assert is_permission_allowed("fs_read", permissions) is True  # local permission
    print("✓ test_is_permission_allowed_with_global_off passed")


def test_is_permission_allowed_with_global_on():
    """Test that remote permissions are allowed when global is on and permission is enabled"""
    permissions = {"global_remote_enabled": True, "git_push": True}
    assert is_permission_allowed("git_push", permissions) is True
    print("✓ test_is_permission_allowed_with_global_on passed")


def test_is_permission_allowed_specific_off():
    """Test that specific permission off is respected even when global is on"""
    permissions = {"global_remote_enabled": True, "git_push": False}
    assert is_permission_allowed("git_push", permissions) is False
    print("✓ test_is_permission_allowed_specific_off passed")


def test_get_permission_denial_message_global_off():
    """Test that denial message mentions global switch when it's off"""
    permissions = {"global_remote_enabled": False, "git_push": True}
    set_current_permissions(permissions)
    msg = get_permission_denial_message("git_push")
    assert "global_remote_enabled" in msg
    assert "总开关" in msg
    print("✓ test_get_permission_denial_message_global_off passed")


def test_get_permission_denial_message_specific_off():
    """Test that denial message mentions specific permission when global is on"""
    permissions = {"global_remote_enabled": True, "git_push": False}
    set_current_permissions(permissions)
    msg = get_permission_denial_message("git_push")
    assert "git_push" in msg
    assert "权限" in msg
    print("✓ test_get_permission_denial_message_specific_off passed")


def test_remote_permissions_set():
    """Test that REMOTE_PERMISSIONS contains expected keys"""
    assert "git_push" in REMOTE_PERMISSIONS
    assert "pr_create" in REMOTE_PERMISSIONS
    assert "api_call" in REMOTE_PERMISSIONS
    assert "fs_read" not in REMOTE_PERMISSIONS  # local permission
    print("✓ test_remote_permissions_set passed")


def test_global_switch_affects_all_remote():
    """Test that turning off global switch denies all remote permissions"""
    permissions = {"global_remote_enabled": False}
    for remote_perm in REMOTE_PERMISSIONS:
        permissions[remote_perm] = True  # Try to enable each remote permission

    set_current_permissions(permissions)

    for remote_perm in REMOTE_PERMISSIONS:
        assert is_permission_allowed(remote_perm) is False, f"{remote_perm} should be denied when global is off"
    print("✓ test_global_switch_affects_all_remote passed")


def test_global_switch_does_not_affect_local():
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
    print("✓ test_global_switch_does_not_affect_local passed")


def test_global_switch_on_allows_remote():
    """Test that turning on global switch allows remote permissions"""
    permissions = {"global_remote_enabled": True, "git_push": True, "pr_create": True}
    set_current_permissions(permissions)

    assert is_permission_allowed("git_push") is True
    assert is_permission_allowed("pr_create") is True
    print("✓ test_global_switch_on_allows_remote passed")


def test_default_permissions_structure():
    """Test that DEFAULT_PERMISSIONS has the expected structure"""
    assert "global_remote_enabled" in DEFAULT_PERMISSIONS
    assert DEFAULT_PERMISSIONS["global_remote_enabled"] is False
    assert "llm_request" in DEFAULT_PERMISSIONS
    assert DEFAULT_PERMISSIONS["llm_request"] is True
    print("✓ test_default_permissions_structure passed")


def test_normalize_ignores_unknown_keys():
    """Test that normalize_permissions ignores unknown permission keys"""
    result = normalize_permissions({"unknown_permission": True, "git_push": True})
    assert "unknown_permission" not in result
    assert result["git_push"] is True
    print("✓ test_normalize_ignores_unknown_keys passed")


def run_all_tests():
    """Run all tests"""
    print("Running permissions tests...\n")

    tests = [
        test_normalize_permissions_defaults,
        test_normalize_permissions_override,
        test_is_permission_allowed_with_global_off,
        test_is_permission_allowed_with_global_on,
        test_is_permission_allowed_specific_off,
        test_get_permission_denial_message_global_off,
        test_get_permission_denial_message_specific_off,
        test_remote_permissions_set,
        test_global_switch_affects_all_remote,
        test_global_switch_does_not_affect_local,
        test_global_switch_on_allows_remote,
        test_default_permissions_structure,
        test_normalize_ignores_unknown_keys,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            print(f"✗ {test.__name__} failed: {e}")
            failed += 1

    print(f"\n{'='*50}")
    print(f"Results: {passed} passed, {failed} failed")

    if failed == 0:
        print("All tests passed!")
        return 0
    else:
        print(f"{failed} test(s) failed!")
        return 1


if __name__ == "__main__":
    sys.exit(run_all_tests())
