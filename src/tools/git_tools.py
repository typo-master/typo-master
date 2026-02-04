"""
Git Tools - Git Operations

This module provides tools for Git operations.
"""

import os
import subprocess
from typing import Any, Dict, List, Optional
from pathlib import Path

from ..agent_framework.tool_system import tool, ToolCategory
from ..agent_framework.logger import get_logger

logger = get_logger(__name__)


class GitOperations:
    """Git operations wrapper"""
    
    def __init__(self, repo_path: str):
        """
        Initialize Git operations
        
        Args:
            repo_path: Repository path
        """
        self.repo_path = Path(repo_path)
    
    def _run_git_command(self, *args: str) -> str:
        """
        Run a git command
        
        Args:
            *args: Git command arguments
            
        Returns:
            Command output
        """
        cmd = ["git"] + list(args)
        result = subprocess.run(
            cmd,
            cwd=self.repo_path,
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout
    
    def clone(self, url: str, destination: Optional[str] = None) -> str:
        """
        Clone a repository
        
        Args:
            url: Repository URL
            destination: Destination path
            
        Returns:
            Cloned repository path
        """
        if destination:
            dest_path = Path(destination)
        else:
            dest_path = self.repo_path
        
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Cloning repository from {url} to {dest_path}")
        self._run_git_command("clone", url, str(dest_path))
        
        return str(dest_path)
    
    def checkout(self, branch: str) -> None:
        """
        Checkout a branch
        
        Args:
            branch: Branch name
        """
        logger.info(f"Checking out branch: {branch}")
        self._run_git_command("checkout", branch)
    
    def create_branch(self, branch: str, base: Optional[str] = None) -> None:
        """
        Create a new branch
        
        Args:
            branch: Branch name
            base: Base branch
        """
        logger.info(f"Creating branch: {branch}")
        if base:
            self._run_git_command("checkout", "-b", branch, base)
        else:
            self._run_git_command("checkout", "-b", branch)
    
    def pull(self, remote: str = "origin", branch: Optional[str] = None) -> None:
        """
        Pull changes from remote
        
        Args:
            remote: Remote name
            branch: Branch name
        """
        logger.info(f"Pulling from {remote}")
        if branch:
            self._run_git_command("pull", remote, branch)
        else:
            self._run_git_command("pull")
    
    def push(self, remote: str = "origin", branch: Optional[str] = None) -> None:
        """
        Push changes to remote
        
        Args:
            remote: Remote name
            branch: Branch name
        """
        logger.info(f"Pushing to {remote}")
        if branch:
            self._run_git_command("push", remote, branch)
        else:
            self._run_git_command("push")
    
    def add(self, *files: str) -> None:
        """
        Stage files
        
        Args:
            *files: Files to stage
        """
        logger.info(f"Staging files: {files}")
        self._run_git_command("add", *files)
    
    def commit(self, message: str) -> None:
        """
        Commit changes
        
        Args:
            message: Commit message
        """
        logger.info(f"Committing with message: {message}")
        self._run_git_command("commit", "-m", message)
    
    def get_current_branch(self) -> str:
        """
        Get current branch name
        
        Returns:
            Branch name
        """
        output = self._run_git_command("rev-parse", "--abbrev-ref", "HEAD")
        return output.strip()
    
    def get_file_changes(self) -> Dict[str, List[str]]:
        """
        Get changed files
        
        Returns:
            Dictionary with staged and unstaged files
        """
        staged = []
        unstaged = []
        
        try:
            output = self._run_git_command("diff", "--name-only", "--cached")
            staged = [f for f in output.strip().split("\n") if f]
        except subprocess.CalledProcessError:
            pass
        
        try:
            output = self._run_git_command("diff", "--name-only")
            unstaged = [f for f in output.strip().split("\n") if f]
        except subprocess.CalledProcessError:
            pass
        
        return {"staged": staged, "unstaged": unstaged}
    
    def get_file_content(self, file_path: str) -> str:
        """
        Get file content
        
        Args:
            file_path: File path
            
        Returns:
            File content
        """
        full_path = self.repo_path / file_path
        with open(full_path, 'r', encoding='utf-8') as f:
            return f.read()
    
    def update_file(self, file_path: str, content: str) -> None:
        """
        Update file content
        
        Args:
            file_path: File path
            content: New content
        """
        full_path = self.repo_path / file_path
        with open(full_path, 'w', encoding='utf-8') as f:
            f.write(content)


# Tool functions

@tool(
    name="git_clone",
    description="Clone a Git repository",
    category=ToolCategory.GIT,
    examples=[
        {
            "input": {
                "url": "https://github.com/ethereum/solidity.git",
                "destination": "./repos/solidity"
            },
            "output": "Cloned repository path"
        }
    ]
)
async def git_clone(
    url: str,
    destination: Optional[str] = None,
) -> str:
    """
    Clone a Git repository
    
    Args:
        url: Repository URL
        destination: Destination path
        
    Returns:
        Cloned repository path
    """
    git = GitOperations(destination or "./temp_repo")
    return git.clone(url, destination)


@tool(
    name="git_checkout",
    description="Checkout a Git branch",
    category=ToolCategory.GIT,
    examples=[
        {
            "input": {"repo_path": "./repos/solidity", "branch": "main"},
            "output": "Checked out branch"
        }
    ]
)
async def git_checkout(
    repo_path: str,
    branch: str,
) -> None:
    """
    Checkout a branch
    
    Args:
        repo_path: Repository path
        branch: Branch name
    """
    git = GitOperations(repo_path)
    git.checkout(branch)


@tool(
    name="git_create_branch",
    description="Create a new Git branch",
    category=ToolCategory.GIT,
    examples=[
        {
            "input": {"repo_path": "./repos/solidity", "branch": "fix-typo", "base": "main"},
            "output": "Created branch"
        }
    ]
)
async def git_create_branch(
    repo_path: str,
    branch: str,
    base: Optional[str] = None,
) -> None:
    """
    Create a new branch
    
    Args:
        repo_path: Repository path
        branch: Branch name
        base: Base branch
    """
    git = GitOperations(repo_path)
    git.create_branch(branch, base)


@tool(
    name="git_add",
    description="Stage files in Git",
    category=ToolCategory.GIT,
    examples=[
        {
            "input": {"repo_path": "./repos/solidity", "files": ["README.md", "src/main.py"]},
            "output": "Staged files"
        }
    ]
)
async def git_add(
    repo_path: str,
    files: List[str],
) -> None:
    """
    Stage files
    
    Args:
        repo_path: Repository path
        files: Files to stage
    """
    git = GitOperations(repo_path)
    git.add(*files)


@tool(
    name="git_commit",
    description="Commit changes in Git",
    category=ToolCategory.GIT,
    examples=[
        {
            "input": {"repo_path": "./repos/solidity", "message": "Fix typo in README"},
            "output": "Committed changes"
        }
    ]
)
async def git_commit(
    repo_path: str,
    message: str,
) -> None:
    """
    Commit changes
    
    Args:
        repo_path: Repository path
        message: Commit message
    """
    git = GitOperations(repo_path)
    git.commit(message)


@tool(
    name="git_push",
    description="Push changes to remote",
    category=ToolCategory.GIT,
    examples=[
        {
            "input": {"repo_path": "./repos/solidity", "remote": "origin", "branch": "fix-typo"},
            "output": "Pushed changes"
        }
    ]
)
async def git_push(
    repo_path: str,
    remote: str = "origin",
    branch: Optional[str] = None,
) -> None:
    """
    Push changes to remote
    
    Args:
        repo_path: Repository path
        remote: Remote name
        branch: Branch name
    """
    git = GitOperations(repo_path)
    git.push(remote, branch)


@tool(
    name="git_get_current_branch",
    description="Get current Git branch",
    category=ToolCategory.GIT,
    examples=[
        {
            "input": {"repo_path": "./repos/solidity"},
            "output": "main"
        }
    ]
)
async def git_get_current_branch(
    repo_path: str,
) -> str:
    """
    Get current branch
    
    Args:
        repo_path: Repository path
        
    Returns:
        Branch name
    """
    git = GitOperations(repo_path)
    return git.get_current_branch()


@tool(
    name="git_get_changes",
    description="Get changed files in Git",
    category=ToolCategory.GIT,
    examples=[
        {
            "input": {"repo_path": "./repos/solidity"},
            "output": {"staged": ["README.md"], "unstaged": []}
        }
    ]
)
async def git_get_changes(
    repo_path: str,
) -> Dict[str, List[str]]:
    """
    Get changed files
    
    Args:
        repo_path: Repository path
        
    Returns:
        Dictionary with staged and unstaged files
    """
    git = GitOperations(repo_path)
    return git.get_file_changes()


@tool(
    name="git_get_file_content",
    description="Get file content from Git repository",
    category=ToolCategory.GIT,
    examples=[
        {
            "input": {"repo_path": "./repos/solidity", "file_path": "README.md"},
            "output": "File content"
        }
    ]
)
async def git_get_file_content(
    repo_path: str,
    file_path: str,
) -> str:
    """
    Get file content
    
    Args:
        repo_path: Repository path
        file_path: File path
        
    Returns:
        File content
    """
    git = GitOperations(repo_path)
    return git.get_file_content(file_path)


@tool(
    name="git_update_file",
    description="Update file content in Git repository",
    category=ToolCategory.GIT,
    examples=[
        {
            "input": {
                "repo_path": "./repos/solidity",
                "file_path": "README.md",
                "content": "New content"
            },
            "output": "Updated file"
        }
    ]
)
async def git_update_file(
    repo_path: str,
    file_path: str,
    content: str,
) -> None:
    """
    Update file content
    
    Args:
        repo_path: Repository path
        file_path: File path
        content: New content
    """
    git = GitOperations(repo_path)
    git.update_file(file_path, content)
