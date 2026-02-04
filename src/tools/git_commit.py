"""
Git Commit Tool - Advanced Git commit operations

This module provides advanced Git commit functionality with better error handling
and commit message formatting.
"""

import subprocess
from typing import Any, Dict, List, Optional
from pathlib import Path

from ..agent_framework.tool_system import tool, ToolCategory, ToolResult
from ..agent_framework.logger import get_logger

logger = get_logger(__name__)


@tool(
    name="git_commit_with_author",
    description="Commit changes with author information",
    category=ToolCategory.GIT,
    examples=[
        {
            "input": {
                "repo_path": "./repos/solidity",
                "message": "Fix typo in README",
                "author_name": "TypoHunter",
                "author_email": "typohunter@example.com"
            },
            "output": "Commit successful"
        }
    ]
)
async def git_commit_with_author(
    repo_path: str,
    message: str,
    author_name: str,
    author_email: str,
) -> ToolResult:
    """
    Commit changes with author information
    
    Args:
        repo_path: Repository path
        message: Commit message
        author_name: Author name
        author_email: Author email
        
    Returns:
        Tool execution result
    """
    try:
        cmd = [
            "git",
            "-C", repo_path,
            "commit",
            "-m", message,
            f"--author={author_name} <{author_email}>"
        ]
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True
        )
        
        logger.info(f"Commit successful: {message}")
        return ToolResult(
            success=True,
            data={"commit_hash": result.stdout.strip()},
            metadata={"message": message}
        )
    except subprocess.CalledProcessError as e:
        logger.error(f"Commit failed: {e.stderr}")
        return ToolResult(
            success=False,
            error=str(e),
            metadata={"message": message}
        )


@tool(
    name="git_commit_amend",
    description="Amend the last commit",
    category=ToolCategory.GIT,
    examples=[
        {
            "input": {
                "repo_path": "./repos/solidity",
                "message": "Updated commit message"
            },
            "output": "Amended commit"
        }
    ]
)
async def git_commit_amend(
    repo_path: str,
    message: Optional[str] = None,
) -> ToolResult:
    """
    Amend the last commit
    
    Args:
        repo_path: Repository path
        message: New commit message (optional)
        
    Returns:
        Tool execution result
    """
    try:
        cmd = ["git", "-C", repo_path, "commit", "--amend", "--no-edit"]
        
        if message:
            cmd = ["git", "-C", repo_path, "commit", "--amend", "-m", message]
        
        subprocess.run(cmd, capture_output=True, text=True, check=True)
        
        logger.info("Commit amended successfully")
        return ToolResult(success=True, data={"amended": True})
    except subprocess.CalledProcessError as e:
        logger.error(f"Amend failed: {e.stderr}")
        return ToolResult(success=False, error=str(e))


@tool(
    name="git_get_commit_info",
    description="Get information about the last commit",
    category=ToolCategory.GIT,
    examples=[
        {
            "input": {"repo_path": "./repos/solidity"},
            "output": {"hash": "abc123", "message": "Fix typo", "author": "John Doe"}
        }
    ]
)
async def git_get_commit_info(
    repo_path: str,
    commit_hash: Optional[str] = None,
) -> ToolResult:
    """
    Get commit information
    
    Args:
        repo_path: Repository path
        commit_hash: Commit hash (defaults to HEAD)
        
    Returns:
        Tool execution result with commit info
    """
    try:
        ref = commit_hash or "HEAD"
        cmd = [
            "git",
            "-C", repo_path,
            "log",
            "-1",
            "--format=%H|%an|%ae|%s|%ci",
            ref
        ]
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True
        )
        
        parts = result.stdout.strip().split("|")
        commit_info = {
            "hash": parts[0],
            "author_name": parts[1],
            "author_email": parts[2],
            "message": parts[3],
            "date": parts[4]
        }
        
        return ToolResult(success=True, data=commit_info)
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to get commit info: {e.stderr}")
        return ToolResult(success=False, error=str(e))


@tool(
    name="git_commit_signed",
    description="Create a signed commit",
    category=ToolCategory.GIT,
    examples=[
        {
            "input": {
                "repo_path": "./repos/solidity",
                "message": "Signed commit"
            },
            "output": "Signed commit created"
        }
    ]
)
async def git_commit_signed(
    repo_path: str,
    message: str,
    gpg_key_id: Optional[str] = None,
) -> ToolResult:
    """
    Create a signed commit
    
    Args:
        repo_path: Repository path
        message: Commit message
        gpg_key_id: GPG key ID to use
        
    Returns:
        Tool execution result
    """
    try:
        cmd = ["git", "-C", repo_path, "commit", "-S", "-m", message]
        
        if gpg_key_id:
            cmd = ["git", "-C", repo_path, "commit", f"-S{gpg_key_id}", "-m", message]
        
        subprocess.run(cmd, capture_output=True, text=True, check=True)
        
        logger.info("Signed commit created")
        return ToolResult(success=True, data={"signed": True})
    except subprocess.CalledProcessError as e:
        logger.error(f"Signed commit failed: {e.stderr}")
        return ToolResult(success=False, error=str(e))