"""
GitHub API Tools - GitHub Operations

This module provides tools for interacting with GitHub API.
"""

import asyncio
import time
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta

import requests

from ..agent_framework.tool_system import tool, ToolCategory, ToolResult
from ..agent_framework.logger import get_logger

logger = get_logger(__name__)


class GitHubAPI:
    """GitHub API client"""
    
    def __init__(self, token: Optional[str] = None):
        """
        Initialize GitHub API client
        
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
    
    def search_repositories(
        self,
        query: str,
        sort: str = "updated",
        order: str = "desc",
        per_page: int = 100,
        page: int = 1,
    ) -> Dict[str, Any]:
        """
        Search for repositories
        
        Args:
            query: Search query
            sort: Sort field
            order: Sort order
            per_page: Results per page
            page: Page number
            
        Returns:
            Search results
        """
        params = {
            "q": query,
            "sort": sort,
            "order": order,
            "per_page": per_page,
            "page": page,
        }
        
        return self._request("GET", "/search/repositories", params=params)
    
    def get_repository(self, owner: str, repo: str) -> Dict[str, Any]:
        """
        Get repository information
        
        Args:
            owner: Repository owner
            repo: Repository name
            
        Returns:
            Repository data
        """
        return self._request("GET", f"/repos/{owner}/{repo}")
    
    def get_pull_requests(
        self,
        owner: str,
        repo: str,
        state: str = "open",
        sort: str = "created",
        direction: str = "desc",
        per_page: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        Get pull requests
        
        Args:
            owner: Repository owner
            repo: Repository name
            state: PR state (open, closed, all)
            sort: Sort field
            direction: Sort direction
            per_page: Results per page
            
        Returns:
            List of pull requests
        """
        params = {
            "state": state,
            "sort": sort,
            "direction": direction,
            "per_page": per_page,
        }
        
        return self._request("GET", f"/repos/{owner}/{repo}/pulls", params=params)
    
    def create_pull_request(
        self,
        owner: str,
        repo: str,
        title: str,
        head: str,
        base: str,
        body: str = "",
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
            
        Returns:
            Created PR data
        """
        data = {
            "title": title,
            "head": head,
            "base": base,
            "body": body,
        }
        
        return self._request("POST", f"/repos/{owner}/{repo}/pulls", json=data)
    
    def get_issues(
        self,
        owner: str,
        repo: str,
        state: str = "open",
        per_page: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        Get issues
        
        Args:
            owner: Repository owner
            repo: Repository name
            state: Issue state
            per_page: Results per page
            
        Returns:
            List of issues
        """
        params = {
            "state": state,
            "per_page": per_page,
        }
        
        return self._request("GET", f"/repos/{owner}/{repo}/issues", params=params)
    
    def get_file_contents(
        self,
        owner: str,
        repo: str,
        path: str,
        ref: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Get file contents
        
        Args:
            owner: Repository owner
            repo: Repository name
            path: File path
            ref: Git reference
            
        Returns:
            File contents
        """
        params = {}
        if ref:
            params["ref"] = ref
        
        return self._request("GET", f"/repos/{owner}/{repo}/contents/{path}", params=params)
    
    def update_file(
        self,
        owner: str,
        repo: str,
        path: str,
        content: str,
        message: str,
        sha: str,
        branch: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Update a file
        
        Args:
            owner: Repository owner
            repo: Repository name
            path: File path
            content: File content (base64 encoded)
            message: Commit message
            sha: Current file SHA
            branch: Branch name
            
        Returns:
            Updated file data
        """
        import base64
        
        data = {
            "message": message,
            "content": content,
            "sha": sha,
        }
        
        if branch:
            data["branch"] = branch
        
        return self._request("PUT", f"/repos/{owner}/{repo}/contents/{path}", json=data)
    
    def create_branch(
        self,
        owner: str,
        repo: str,
        branch: str,
        sha: str,
    ) -> Dict[str, Any]:
        """
        Create a branch
        
        Args:
            owner: Repository owner
            repo: Repository name
            branch: Branch name
            sha: SHA of the commit to branch from
            
        Returns:
            Created branch data
        """
        data = {
            "ref": f"refs/heads/{branch}",
            "sha": sha,
        }
        
        return self._request("POST", f"/repos/{owner}/{repo}/git/refs", json=data)
    
    def get_default_branch(self, owner: str, repo: str) -> str:
        """
        Get default branch name
        
        Args:
            owner: Repository owner
            repo: Repository name
            
        Returns:
            Default branch name
        """
        repo_data = self.get_repository(owner, repo)
        return repo_data.get("default_branch", "main")


# Tool functions

@tool(
    name="search_github_repos",
    description="Search for GitHub repositories",
    category=ToolCategory.GITHUB,
    examples=[
        {
            "input": {
                "query": "topic:blockchain pushed:>2024-01-01 stars:>100",
                "limit": 50
            },
            "output": "List of repositories"
        }
    ]
)
async def search_github_repos(
    query: str,
    limit: int = 100,
    sort: str = "updated",
    order: str = "desc",
    token: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Search GitHub repositories
    
    Args:
        query: Search query
        limit: Maximum number of results
        sort: Sort field
        order: Sort order
        token: GitHub token
        
    Returns:
        List of repositories
    """
    api = GitHubAPI(token)
    results = api.search_repositories(
        query=query,
        sort=sort,
        order=order,
        per_page=min(limit, 100),
    )
    
    return results.get("items", [])


@tool(
    name="get_github_repo",
    description="Get detailed information about a GitHub repository",
    category=ToolCategory.GITHUB,
    examples=[
        {
            "input": {"owner": "ethereum", "repo": "solidity"},
            "output": "Repository details"
        }
    ]
)
async def get_github_repo(
    owner: str,
    repo: str,
    token: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Get GitHub repository information
    
    Args:
        owner: Repository owner
        repo: Repository name
        token: GitHub token
        
    Returns:
        Repository information
    """
    api = GitHubAPI(token)
    return api.get_repository(owner, repo)


@tool(
    name="list_pull_requests",
    description="List pull requests for a repository",
    category=ToolCategory.GITHUB,
    examples=[
        {
            "input": {"owner": "ethereum", "repo": "solidity", "state": "closed"},
            "output": "List of pull requests"
        }
    ]
)
async def list_pull_requests(
    owner: str,
    repo: str,
    state: str = "open",
    limit: int = 100,
    token: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    List pull requests
    
    Args:
        owner: Repository owner
        repo: Repository name
        state: PR state
        limit: Maximum number of results
        token: GitHub token
        
    Returns:
        List of pull requests
    """
    api = GitHubAPI(token)
    return api.get_pull_requests(
        owner=owner,
        repo=repo,
        state=state,
        per_page=min(limit, 100),
    )


@tool(
    name="create_pull_request",
    description="Create a pull request",
    category=ToolCategory.GITHUB,
    examples=[
        {
            "input": {
                "owner": "ethereum",
                "repo": "solidity",
                "title": "Fix typo in README",
                "head": "fix-typo",
                "base": "main",
                "body": "Fixed spelling errors in README"
            },
            "output": "Created PR data"
        }
    ]
)
async def create_pull_request(
    owner: str,
    repo: str,
    title: str,
    head: str,
    base: str,
    body: str = "",
    token: Optional[str] = None,
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
        token: GitHub token
        
    Returns:
        Created PR data
    """
    api = GitHubAPI(token)
    return api.create_pull_request(
        owner=owner,
        repo=repo,
        title=title,
        head=head,
        base=base,
        body=body,
    )


@tool(
    name="get_file_contents",
    description="Get file contents from a repository",
    category=ToolCategory.GITHUB,
    examples=[
        {
            "input": {"owner": "ethereum", "repo": "solidity", "path": "README.md"},
            "output": "File contents"
        }
    ]
)
async def get_file_contents(
    owner: str,
    repo: str,
    path: str,
    ref: Optional[str] = None,
    token: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Get file contents
    
    Args:
        owner: Repository owner
        repo: Repository name
        path: File path
        ref: Git reference
        token: GitHub token
        
    Returns:
        File contents
    """
    api = GitHubAPI(token)
    return api.get_file_contents(owner, repo, path, ref)


@tool(
    name="update_file",
    description="Update a file in a repository",
    category=ToolCategory.GITHUB,
    examples=[
        {
            "input": {
                "owner": "ethereum",
                "repo": "solidity",
                "path": "README.md",
                "content": "base64_encoded_content",
                "message": "Update README",
                "sha": "file_sha"
            },
            "output": "Updated file data"
        }
    ]
)
async def update_file(
    owner: str,
    repo: str,
    path: str,
    content: str,
    message: str,
    sha: str,
    branch: Optional[str] = None,
    token: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Update a file
    
    Args:
        owner: Repository owner
        repo: Repository name
        path: File path
        content: File content (base64 encoded)
        message: Commit message
        sha: Current file SHA
        branch: Branch name
        token: GitHub token
        
    Returns:
        Updated file data
    """
    api = GitHubAPI(token)
    return api.update_file(owner, repo, path, content, message, sha, branch)


@tool(
    name="create_branch",
    description="Create a new branch",
    category=ToolCategory.GITHUB,
    examples=[
        {
            "input": {
                "owner": "ethereum",
                "repo": "solidity",
                "branch": "fix-typo",
                "sha": "commit_sha"
            },
            "output": "Created branch data"
        }
    ]
)
async def create_branch(
    owner: str,
    repo: str,
    branch: str,
    sha: str,
    token: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Create a branch
    
    Args:
        owner: Repository owner
        repo: Repository name
        branch: Branch name
        sha: Commit SHA
        token: GitHub token
        
    Returns:
        Created branch data
    """
    api = GitHubAPI(token)
    return api.create_branch(owner, repo, branch, sha)


@tool(
    name="get_default_branch",
    description="Get the default branch of a repository",
    category=ToolCategory.GITHUB,
    examples=[
        {
            "input": {"owner": "ethereum", "repo": "solidity"},
            "output": "main"
        }
    ]
)
async def get_default_branch(
    owner: str,
    repo: str,
    token: Optional[str] = None,
) -> str:
    """
    Get default branch
    
    Args:
        owner: Repository owner
        repo: Repository name
        token: GitHub token
        
    Returns:
        Default branch name
    """
    api = GitHubAPI(token)
    return api.get_default_branch(owner, repo)
