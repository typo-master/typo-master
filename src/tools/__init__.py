"""
Tools Module - Agent Tools

This module provides various tools for agents to use.
"""

from .github_tools import *
from .git_tools import *
from .spell_tools import *
from .file_tools import *
from .pr_tools import *
from .report_tools import *
from .git_commit import *
from .github_pull_request import *
from .github_repo_clone import *
from .repo_typo_scanner import *

__all__ = [
    # GitHub tools
    "search_github_repos",
    "get_github_repo",
    "list_pull_requests",
    "create_pull_request",
    "get_file_contents",
    "update_file",
    "create_branch",
    "get_default_branch",
    # Git tools
    "git_clone",
    "git_checkout",
    "git_create_branch",
    "git_add",
    "git_commit",
    "git_push",
    "git_get_current_branch",
    "git_get_changes",
    "git_get_file_content",
    "git_update_file",
    # Spell tools
    "check_spelling",
    "correct_spelling",
    "get_spelling_suggestions",
    "is_web3_term",
    "check_file_spelling",
    # File tools
    "read_file",
    "write_file",
    "list_files",
    "file_exists",
    "delete_file",
    "create_directory",
    "get_file_info",
    "search_files",
    "replace_in_file",
    # PR tools
    "create_pr",
    "generate_pr_title",
    "generate_pr_body",
    "prepare_pr",
    "validate_pr",
    "format_pr_description",
    # Report tools
    "generate_csv_report",
    "generate_json_report",
    "generate_markdown_report",
    "generate_html_report",
    "generate_summary_report",
    "generate_typo_fix_report",
    # Git Commit tools
    "git_commit_with_author",
    "git_commit_amend",
    "git_get_commit_info",
    "git_create_signed_commit",
    # GitHub PR tools
    "create_pr_with_labels",
    "update_pr_status",
    "get_pr_details",
    "merge_pull_request",
    "add_pr_comment",
    "get_pr_files",
    # GitHub Repo Clone tools
    "clone_github_repo",
    "update_github_repo",
    "get_repo_info",
    "clone_or_update_repo",
    "batch_clone_repos",
    # Repo Typo Scanner tools
    "scan_local_repo",
    "scan_single_file",
    "get_typo_summary",
    "RepoTypoScanner",
]