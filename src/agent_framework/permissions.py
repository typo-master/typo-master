"""
Permissions model and helpers for tool gating.
"""

from __future__ import annotations

from typing import Dict, Iterable, Optional, Tuple


PERMISSION_GROUPS: Dict[str, Tuple[str, ...]] = {
    "global": (
        "global_remote_enabled",
    ),
    "git": (
        "git_clone",
        "git_fetch",
        "git_pull",
        "git_push",
        "git_checkout",
        "git_create_branch",
        "git_add",
        "git_commit",
    ),
    "github": (
        "github_read",
        "pr_create",
        "pr_update",
        "pr_comment",
        "pr_merge",
        "pr_close",
        "issue_create",
        "issue_comment",
        "issue_close",
    ),
    "filesystem": (
        "fs_read",
        "fs_write",
        "fs_delete",
    ),
    "commands": (
        "shell_run",
        "run_tests",
        "install_deps",
    ),
    "external": (
        "web_fetch",
        "api_call",
        "llm_request",
    ),
}


DEFAULT_PERMISSIONS: Dict[str, bool] = {
    "global_remote_enabled": False,  # 总开关：关闭时所有远程/高风险操作被拒绝
    "git_clone": False,
    "git_fetch": False,
    "git_pull": False,
    "git_push": False,
    "git_checkout": True,
    "git_create_branch": True,
    "git_add": True,
    "git_commit": True,
    "github_read": True,
    "pr_create": False,
    "pr_update": False,
    "pr_comment": False,
    "pr_merge": False,
    "pr_close": False,
    "issue_create": False,
    "issue_comment": False,
    "issue_close": False,
    "fs_read": True,
    "fs_write": False,
    "fs_delete": False,
    "shell_run": False,
    "run_tests": False,
    "install_deps": False,
    "web_fetch": False,
    "api_call": False,
    "llm_request": True,
}


def normalize_permissions(raw: Optional[Dict[str, bool]]) -> Dict[str, bool]:
    data = DEFAULT_PERMISSIONS.copy()
    if raw:
        for key, value in raw.items():
            if key in data:
                data[key] = bool(value)
    return data

TOOL_PERMISSION_MAP: Dict[str, str] = {
    "git_clone": "git_clone",
    "git_checkout": "git_checkout",
    "git_create_branch": "git_create_branch",
    "git_add": "git_add",
    "git_commit": "git_commit",
    "git_push": "git_push",
    "git_get_current_branch": "git_checkout",
    "git_get_changes": "git_checkout",
    "git_get_file_content": "git_checkout",
    "git_update_file": "git_checkout",
    "git_commit_with_author": "git_commit",
    "git_commit_amend": "git_commit",
    "git_commit_signed": "git_commit",
    "git_get_commit_info": "git_checkout",
    "search_github_repos": "github_read",
    "get_github_repo": "github_read",
    "list_pull_requests": "github_read",
    "get_file_contents": "github_read",
    "get_default_branch": "github_read",
    "create_pull_request": "pr_create",
    "create_pr": "pr_create",
    "create_pr_with_labels": "pr_create",
    "update_pr_status": "pr_update",
    "get_pr_details": "github_read",
    "merge_pull_request": "pr_merge",
    "add_pr_comment": "pr_comment",
    "update_file": "pr_update",
    "create_branch": "pr_update",
    "clone_github_repo": "git_clone",
    "update_github_repo": "git_pull",
    "get_repo_info": "github_read",
    "clone_or_update_repo": "git_clone",
    "batch_clone_repos": "git_clone",
    "read_file": "fs_read",
    "write_file": "fs_write",
    "list_files": "fs_read",
    "file_exists": "fs_read",
    "delete_file": "fs_delete",
    "create_directory": "fs_write",
    "get_file_info": "fs_read",
    "search_files": "fs_read",
    "replace_in_file": "fs_write",
    "check_spelling": "llm_request",
    "correct_spelling": "llm_request",
    "get_spelling_suggestions": "llm_request",
    "is_web3_term": "llm_request",
    "check_file_spelling": "llm_request",
    "scan_local_repo": "fs_read",
    "scan_single_file": "fs_read",
    "get_typo_summary": "fs_read",
    "generate_csv_report": "fs_write",
    "generate_json_report": "fs_write",
    "generate_markdown_report": "fs_write",
    "generate_summary_report": "fs_write",
    "generate_typo_fix_report": "fs_write",
    "generate_html_report": "fs_write",
    "mcp_execute": "api_call",
    "webhook_notify": "api_call",
    "run_sql": "api_call",
    "query_sql": "api_call",
}



_CURRENT_PERMISSIONS: Dict[str, bool] = normalize_permissions(None)


def set_current_permissions(permissions: Optional[Dict[str, bool]]) -> None:
    global _CURRENT_PERMISSIONS
    _CURRENT_PERMISSIONS = normalize_permissions(permissions)


def get_current_permissions() -> Dict[str, bool]:
    return _CURRENT_PERMISSIONS.copy()


def iter_permission_items() -> Iterable[Tuple[str, bool]]:
    for key in sorted(DEFAULT_PERMISSIONS.keys()):
        yield key, DEFAULT_PERMISSIONS[key]


def resolve_permission_for_tool(tool_name: str) -> Optional[str]:
    if not tool_name:
        return None
    return TOOL_PERMISSION_MAP.get(tool_name)


# 高风险权限列表（受 global_remote_enabled 总开关控制）
REMOTE_PERMISSIONS: set = {
    "git_clone", "git_fetch", "git_pull", "git_push",
    "pr_create", "pr_update", "pr_comment", "pr_merge", "pr_close",
    "issue_create", "issue_comment", "issue_close",
    "fs_write", "fs_delete",
    "shell_run", "run_tests", "install_deps",
    "web_fetch", "api_call",
}


def is_permission_allowed(permission_key: str, permissions: Optional[Dict[str, bool]] = None) -> bool:
    """
    检查权限是否允许（考虑总开关 global_remote_enabled）

    Args:
        permission_key: 权限键名
        permissions: 权限字典，默认使用当前全局权限

    Returns:
        True 如果允许，False 如果被拒绝
    """
    perms = permissions if permissions is not None else _CURRENT_PERMISSIONS

    # 总开关关闭时，所有高风险权限被拒绝
    if permission_key in REMOTE_PERMISSIONS:
        if not perms.get("global_remote_enabled", False):
            return False

    return perms.get(permission_key, DEFAULT_PERMISSIONS.get(permission_key, False))


def get_permission_denial_message(permission_key: str) -> str:
    """
    获取权限被拒绝时的错误信息

    Args:
        permission_key: 权限键名

    Returns:
        拒绝错误信息
    """
    perms = _CURRENT_PERMISSIONS

    # 检查是否是总开关导致被拒绝
    if permission_key in REMOTE_PERMISSIONS:
        if not perms.get("global_remote_enabled", False):
            return "当前未启用【global_remote_enabled】总开关，所有远程/高风险操作已被全局禁用。请在权限设置中开启总开关。"

    return f"当前未启用【{permission_key}】权限，已拒绝执行。请在权限设置中开启该项。"

