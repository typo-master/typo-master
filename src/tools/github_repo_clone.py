"""
GitHub Repository Clone Tool - Advanced cloning operations

This module provides advanced GitHub repository cloning functionality with
better error handling, progress tracking, and repository management.
"""

import os
import subprocess
from typing import Any, Dict, List, Optional
from pathlib import Path

from ..agent_framework.tool_system import tool, ToolCategory, ToolResult
from ..agent_framework.logger import get_logger

logger = get_logger(__name__)


class GitHubRepoCloner:
    """GitHub repository cloner with advanced features"""
    
    def __init__(self, token: Optional[str] = None):
        """
        Initialize GitHub repo cloner
        
        Args:
            token: GitHub personal access token
        """
        self.token = token
    
    def _get_clone_url(self, owner: str, repo: str) -> str:
        """
        Get clone URL with authentication
        
        Args:
            owner: Repository owner
            repo: Repository name
            
        Returns:
            Clone URL
        """
        if self.token:
            return f"https://{self.token}@github.com/{owner}/{repo}.git"
        return f"https://github.com/{owner}/{repo}.git"
    
    def clone(
        self,
        owner: str,
        repo: str,
        destination: str,
        branch: Optional[str] = None,
        depth: Optional[int] = None,
        single_branch: bool = False,
    ) -> str:
        """
        Clone a repository
        
        Args:
            owner: Repository owner
            repo: Repository name
            destination: Destination path
            branch: Branch to clone
            depth: Clone depth (shallow clone)
            single_branch: Clone only one branch
            
        Returns:
            Cloned repository path
        """
        url = self._get_clone_url(owner, repo)
        dest_path = Path(destination)
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        
        cmd = ["git", "clone", url, str(dest_path)]
        
        if branch:
            cmd.extend(["--branch", branch])
        if depth:
            cmd.extend(["--depth", str(depth)])
        if single_branch:
            cmd.append("--single-branch")
        
        logger.info(f"Cloning {owner}/{repo} to {destination}")
        subprocess.run(cmd, check=True, capture_output=True, text=True)
        
        return str(dest_path)
    
    def update(
        self,
        repo_path: str,
        remote: str = "origin",
        branch: Optional[str] = None,
    ) -> None:
        """
        Update a repository
        
        Args:
            repo_path: Repository path
            remote: Remote name
            branch: Branch to pull
        """
        logger.info(f"Updating repository at {repo_path}")
        
        cmd = ["git", "-C", repo_path, "fetch", remote]
        subprocess.run(cmd, check=True, capture_output=True, text=True)
        
        if branch:
            cmd = ["git", "-C", repo_path, "pull", remote, branch]
        else:
            cmd = ["git", "-C", repo_path, "pull"]
        
        subprocess.run(cmd, check=True, capture_output=True, text=True)
    
    def get_repo_info(self, repo_path: str) -> Dict[str, Any]:
        """
        Get repository information
        
        Args:
            repo_path: Repository path
            
        Returns:
            Repository information
        """
        info = {
            "path": repo_path,
            "exists": os.path.exists(repo_path),
        }
        
        if not info["exists"]:
            return info
        
        try:
            # Get remote URL
            cmd = ["git", "-C", repo_path, "config", "--get", "remote.origin.url"]
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            info["remote_url"] = result.stdout.strip()
            
            # Get current branch
            cmd = ["git", "-C", repo_path, "rev-parse", "--abbrev-ref", "HEAD"]
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            info["current_branch"] = result.stdout.strip()
            
            # Get latest commit
            cmd = ["git", "-C", repo_path, "log", "-1", "--format=%H|%s|%an|%ci"]
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            parts = result.stdout.strip().split("|")
            if len(parts) >= 4:
                info["latest_commit"] = {
                    "hash": parts[0],
                    "message": parts[1],
                    "author": parts[2],
                    "date": parts[3],
                }
            
            # Get uncommitted changes
            cmd = ["git", "-C", repo_path, "status", "--porcelain"]
            result = subprocess.run(cmd, capture_output=True, text=True)
            info["has_changes"] = len(result.stdout.strip()) > 0
            
        except subprocess.CalledProcessError:
            info["is_git_repo"] = False
        else:
            info["is_git_repo"] = True
        
        return info


# Tool functions

@tool(
    name="clone_github_repo",
    description="Clone a GitHub repository",
    category=ToolCategory.GITHUB,
    examples=[
        {
            "input": {
                "owner": "ethereum",
                "repo": "solidity",
                "destination": "./repos/solidity"
            },
            "output": "Cloned repository path"
        }
    ]
)
async def clone_github_repo(
    owner: str,
    repo: str,
    destination: str,
    branch: Optional[str] = None,
    depth: Optional[int] = None,
    single_branch: bool = False,
    token: Optional[str] = None,
) -> ToolResult:
    """
    Clone a GitHub repository
    
    Args:
        owner: Repository owner
        repo: Repository name
        destination: Destination path
        branch: Branch to clone
        depth: Clone depth (shallow clone)
        single_branch: Clone only one branch
        token: GitHub token
        
    Returns:
        Tool execution result
    """
    try:
        cloner = GitHubRepoCloner(token)
        path = cloner.clone(
            owner=owner,
            repo=repo,
            destination=destination,
            branch=branch,
            depth=depth,
            single_branch=single_branch,
        )
        
        logger.info(f"Successfully cloned {owner}/{repo}")
        return ToolResult(success=True, data={"path": path})
    except Exception as e:
        logger.error(f"Failed to clone repository: {e}")
        return ToolResult(success=False, error=str(e))


@tool(
    name="update_github_repo",
    description="Update a cloned GitHub repository",
    category=ToolCategory.GITHUB,
    examples=[
        {
            "input": {
                "repo_path": "./repos/solidity",
                "branch": "main"
            },
            "output": "Updated repository"
        }
    ]
)
async def update_github_repo(
    repo_path: str,
    remote: str = "origin",
    branch: Optional[str] = None,
) -> ToolResult:
    """
    Update a cloned GitHub repository
    
    Args:
        repo_path: Repository path
        remote: Remote name
        branch: Branch to pull
        
    Returns:
        Tool execution result
    """
    try:
        cloner = GitHubRepoCloner()
        cloner.update(repo_path, remote, branch)
        
        logger.info(f"Successfully updated repository at {repo_path}")
        return ToolResult(success=True, data={"path": repo_path})
    except Exception as e:
        logger.error(f"Failed to update repository: {e}")
        return ToolResult(success=False, error=str(e))


@tool(
    name="get_repo_info",
    description="Get information about a cloned repository",
    category=ToolCategory.GITHUB,
    examples=[
        {
            "input": {"repo_path": "./repos/solidity"},
            "output": "Repository information"
        }
    ]
)
async def get_repo_info(
    repo_path: str,
) -> ToolResult:
    """
    Get repository information
    
    Args:
        repo_path: Repository path
        
    Returns:
        Tool execution result with repository info
    """
    try:
        cloner = GitHubRepoCloner()
        info = cloner.get_repo_info(repo_path)
        
        return ToolResult(success=True, data=info)
    except Exception as e:
        logger.error(f"Failed to get repo info: {e}")
        return ToolResult(success=False, error=str(e))


@tool(
    name="clone_or_update_repo",
    description="Clone repository if not exists, otherwise update it",
    category=ToolCategory.GITHUB,
    examples=[
        {
            "input": {
                "owner": "ethereum",
                "repo": "solidity",
                "destination": "./repos/solidity"
            },
            "output": "Repository path"
        }
    ]
)
async def clone_or_update_repo(
    owner: str,
    repo: str,
    destination: str,
    branch: Optional[str] = None,
    token: Optional[str] = None,
) -> ToolResult:
    """
    Clone repository if not exists, otherwise update it
    
    Args:
        owner: Repository owner
        repo: Repository name
        destination: Destination path
        branch: Branch to use
        token: GitHub token
        
    Returns:
        Tool execution result
    """
    try:
        cloner = GitHubRepoCloner(token)
        
        # Check if repository exists
        info = cloner.get_repo_info(destination)
        
        if info.get("is_git_repo", False):
            # Update existing repository
            cloner.update(destination, branch=branch)
            logger.info(f"Updated existing repository at {destination}")
        else:
            # Clone new repository
            cloner.clone(owner, repo, destination, branch=branch)
            logger.info(f"Cloned new repository to {destination}")
        
        return ToolResult(success=True, data={"path": destination})
    except Exception as e:
        logger.error(f"Failed to clone/update repository: {e}")
        return ToolResult(success=False, error=str(e))


@tool(
    name="batch_clone_repos",
    description="Clone multiple repositories",
    category=ToolCategory.GITHUB,
    examples=[
        {
            "input": {
                "repos": [
                    {"owner": "ethereum", "repo": "solidity"},
                    {"owner": "openzeppelin", "repo": "contracts"}
                ],
                "base_dir": "./repos"
            },
            "output": "List of cloned repositories"
        }
    ]
)
async def batch_clone_repos(
    repos: List[Dict[str, str]],
    base_dir: str,
    token: Optional[str] = None,
) -> ToolResult:
    """
    Clone multiple repositories
    
    Args:
        repos: List of repositories to clone
        base_dir: Base directory for cloning
        token: GitHub token
        
    Returns:
        Tool execution result
    """
    try:
        cloner = GitHubRepoCloner(token)
        results = []
        
        for repo_info in repos:
            owner = repo_info["owner"]
            repo = repo_info["repo"]
            destination = os.path.join(base_dir, repo)
            
            try:
                path = cloner.clone(owner, repo, destination)
                results.append({
                    "owner": owner,
                    "repo": repo,
                    "path": path,
                    "status": "success"
                })
            except Exception as e:
                results.append({
                    "owner": owner,
                    "repo": repo,
                    "path": None,
                    "status": "failed",
                    "error": str(e)
                })
        
        return ToolResult(success=True, data={"results": results})
    except Exception as e:
        logger.error(f"Failed to batch clone repositories: {e}")
        return ToolResult(success=False, error=str(e))