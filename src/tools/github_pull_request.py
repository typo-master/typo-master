"""
GitHub Pull Request Tool - Advanced PR operations

This module provides advanced GitHub pull request functionality including
PR creation, management, and status tracking.
"""

import asyncio
import time
from typing import Any, Dict, List, Optional
from datetime import datetime

import requests

from ..agent_framework.tool_system import tool, ToolCategory, ToolResult
from ..agent_framework.logger import get_logger

logger = get_logger(__name__)


class GitHubPRClient:
    """GitHub Pull Request client"""
    
    def __init__(self, token: Optional[str] = None):
        """
        Initialize GitHub PR client
        
        Args:
            token: GitHub personal access token
        """
        self.token = token
        self.base_url = "https://api.github.com"
        self.session = requests.Session()
        
        if self.token:
            self.session.headers.update({
                "Authorization": f"token {self.token}",
                "Accept": "application/vnd.github.v3+json",
            })
    
    def _request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """
        Make a request to GitHub API
        
        Args:
            method: HTTP method
            endpoint: API endpoint
            **kwargs: Additional request parameters
            
        Returns:
            Response data
        """
        url = f"{self.base_url}{endpoint}"
        
        try:
            response = self.session.request(method, url, **kwargs)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"GitHub API request failed: {e}")
            raise
    
    def create_pr(
        self,
        owner: str,
        repo: str,
        title: str,
        head: str,
        base: str,
        body: str = "",
        labels: Optional[List[str]] = None,
        draft: bool = False,
    ) -> Dict[str, Any]:
        """
        Create a pull request
        
        Args:
            owner: Repository owner
            repo: Repository name
            title: PR title
            head: Head branch
            base: Base branch
            body: PR description
            labels: PR labels
            draft: Whether to create as draft
            
        Returns:
            Created PR data
        """
        data = {
            "title": title,
            "head": head,
            "base": base,
            "body": body,
            "draft": draft,
        }
        
        if labels:
            data["labels"] = labels
        
        return self._request("POST", f"/repos/{owner}/{repo}/pulls", json=data)
    
    def update_pr(
        self,
        owner: str,
        repo: str,
        pr_number: int,
        title: Optional[str] = None,
        body: Optional[str] = None,
        state: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Update a pull request
        
        Args:
            owner: Repository owner
            repo: Repository name
            pr_number: PR number
            title: New title
            body: New body
            state: New state (open, closed)
            
        Returns:
            Updated PR data
        """
        data = {}
        
        if title:
            data["title"] = title
        if body:
            data["body"] = body
        if state:
            data["state"] = state
        
        return self._request("PATCH", f"/repos/{owner}/{repo}/pulls/{pr_number}", json=data)
    
    def get_pr(
        self,
        owner: str,
        repo: str,
        pr_number: int,
    ) -> Dict[str, Any]:
        """
        Get pull request details
        
        Args:
            owner: Repository owner
            repo: Repository name
            pr_number: PR number
            
        Returns:
            PR data
        """
        return self._request("GET", f"/repos/{owner}/{repo}/pulls/{pr_number}")
    
    def list_prs(
        self,
        owner: str,
        repo: str,
        state: str = "open",
        sort: str = "created",
        direction: str = "desc",
        per_page: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        List pull requests
        
        Args:
            owner: Repository owner
            repo: Repository name
            state: PR state (open, closed, all)
            sort: Sort field
            direction: Sort direction
            per_page: Results per page
            
        Returns:
            List of PRs
        """
        params = {
            "state": state,
            "sort": sort,
            "direction": direction,
            "per_page": per_page,
        }
        
        return self._request("GET", f"/repos/{owner}/{repo}/pulls", params=params)
    
    def merge_pr(
        self,
        owner: str,
        repo: str,
        pr_number: int,
        commit_title: Optional[str] = None,
        commit_message: Optional[str] = None,
        merge_method: str = "merge",
    ) -> Dict[str, Any]:
        """
        Merge a pull request
        
        Args:
            owner: Repository owner
            repo: Repository name
            pr_number: PR number
            commit_title: Commit title
            commit_message: Commit message
            merge_method: Merge method (merge, squash, rebase)
            
        Returns:
            Merge result
        """
        data = {"merge_method": merge_method}
        
        if commit_title:
            data["commit_title"] = commit_title
        if commit_message:
            data["commit_message"] = commit_message
        
        return self._request("PUT", f"/repos/{owner}/{repo}/pulls/{pr_number}/merge", json=data)
    
    def add_comment(
        self,
        owner: str,
        repo: str,
        pr_number: int,
        body: str,
    ) -> Dict[str, Any]:
        """
        Add a comment to a pull request
        
        Args:
            owner: Repository owner
            repo: Repository name
            pr_number: PR number
            body: Comment body
            
        Returns:
            Comment data
        """
        data = {"body": body}
        return self._request("POST", f"/repos/{owner}/{repo}/issues/{pr_number}/comments", json=data)


# Tool functions

@tool(
    name="create_pr_with_labels",
    description="Create a pull request with labels",
    category=ToolCategory.GITHUB,
    examples=[
        {
            "input": {
                "owner": "ethereum",
                "repo": "solidity",
                "title": "Fix typo in README",
                "head": "fix-typo",
                "base": "main",
                "body": "Fixed spelling errors",
                "labels": ["typo", "documentation"]
            },
            "output": "Created PR data"
        }
    ]
)
async def create_pr_with_labels(
    owner: str,
    repo: str,
    title: str,
    head: str,
    base: str,
    body: str = "",
    labels: Optional[List[str]] = None,
    draft: bool = False,
    token: Optional[str] = None,
) -> ToolResult:
    """
    Create a pull request with labels
    
    Args:
        owner: Repository owner
        repo: Repository name
        title: PR title
        head: Head branch
        base: Base branch
        body: PR description
        labels: PR labels
        draft: Whether to create as draft
        token: GitHub token
        
    Returns:
        Tool execution result
    """
    try:
        client = GitHubPRClient(token)
        pr = client.create_pr(
            owner=owner,
            repo=repo,
            title=title,
            head=head,
            base=base,
            body=body,
            labels=labels,
            draft=draft,
        )
        
        logger.info(f"Created PR #{pr['number']}: {title}")
        return ToolResult(success=True, data=pr)
    except Exception as e:
        logger.error(f"Failed to create PR: {e}")
        return ToolResult(success=False, error=str(e))


@tool(
    name="update_pr_status",
    description="Update pull request status",
    category=ToolCategory.GITHUB,
    examples=[
        {
            "input": {
                "owner": "ethereum",
                "repo": "solidity",
                "pr_number": 123,
                "state": "closed"
            },
            "output": "Updated PR"
        }
    ]
)
async def update_pr_status(
    owner: str,
    repo: str,
    pr_number: int,
    state: str,
    token: Optional[str] = None,
) -> ToolResult:
    """
    Update pull request status
    
    Args:
        owner: Repository owner
        repo: Repository name
        pr_number: PR number
        state: New state (open, closed)
        token: GitHub token
        
    Returns:
        Tool execution result
    """
    try:
        client = GitHubPRClient(token)
        pr = client.update_pr(owner, repo, pr_number, state=state)
        
        logger.info(f"Updated PR #{pr_number} to {state}")
        return ToolResult(success=True, data=pr)
    except Exception as e:
        logger.error(f"Failed to update PR: {e}")
        return ToolResult(success=False, error=str(e))


@tool(
    name="get_pr_details",
    description="Get detailed information about a pull request",
    category=ToolCategory.GITHUB,
    examples=[
        {
            "input": {"owner": "ethereum", "repo": "solidity", "pr_number": 123},
            "output": "PR details"
        }
    ]
)
async def get_pr_details(
    owner: str,
    repo: str,
    pr_number: int,
    token: Optional[str] = None,
) -> ToolResult:
    """
    Get pull request details
    
    Args:
        owner: Repository owner
        repo: Repository name
        pr_number: PR number
        token: GitHub token
        
    Returns:
        Tool execution result with PR details
    """
    try:
        client = GitHubPRClient(token)
        pr = client.get_pr(owner, repo, pr_number)
        
        return ToolResult(success=True, data=pr)
    except Exception as e:
        logger.error(f"Failed to get PR details: {e}")
        return ToolResult(success=False, error=str(e))


@tool(
    name="merge_pull_request",
    description="Merge a pull request",
    category=ToolCategory.GITHUB,
    examples=[
        {
            "input": {
                "owner": "ethereum",
                "repo": "solidity",
                "pr_number": 123,
                "merge_method": "merge"
            },
            "output": "Merge result"
        }
    ]
)
async def merge_pull_request(
    owner: str,
    repo: str,
    pr_number: int,
    merge_method: str = "merge",
    commit_title: Optional[str] = None,
    commit_message: Optional[str] = None,
    token: Optional[str] = None,
) -> ToolResult:
    """
    Merge a pull request
    
    Args:
        owner: Repository owner
        repo: Repository name
        pr_number: PR number
        merge_method: Merge method (merge, squash, rebase)
        commit_title: Commit title
        commit_message: Commit message
        token: GitHub token
        
    Returns:
        Tool execution result
    """
    try:
        client = GitHubPRClient(token)
        result = client.merge_pr(
            owner=owner,
            repo=repo,
            pr_number=pr_number,
            commit_title=commit_title,
            commit_message=commit_message,
            merge_method=merge_method,
        )
        
        logger.info(f"Merged PR #{pr_number}")
        return ToolResult(success=True, data=result)
    except Exception as e:
        logger.error(f"Failed to merge PR: {e}")
        return ToolResult(success=False, error=str(e))


@tool(
    name="add_pr_comment",
    description="Add a comment to a pull request",
    category=ToolCategory.GITHUB,
    examples=[
        {
            "input": {
                "owner": "ethereum",
                "repo": "solidity",
                "pr_number": 123,
                "body": "Great work!"
            },
            "output": "Comment data"
        }
    ]
)
async def add_pr_comment(
    owner: str,
    repo: str,
    pr_number: int,
    body: str,
    token: Optional[str] = None,
) -> ToolResult:
    """
    Add a comment to a pull request
    
    Args:
        owner: Repository owner
        repo: Repository name
        pr_number: PR number
        body: Comment body
        token: GitHub token
        
    Returns:
        Tool execution result
    """
    try:
        client = GitHubPRClient(token)
        comment = client.add_comment(owner, repo, pr_number, body)
        
        logger.info(f"Added comment to PR #{pr_number}")
        return ToolResult(success=True, data=comment)
    except Exception as e:
        logger.error(f"Failed to add comment: {e}")
        return ToolResult(success=False, error=str(e))