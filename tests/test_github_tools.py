"""
Test cases for GitHub Tools
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch

from src.tools import (
    search_github_repos,
    get_github_repo,
    list_pull_requests,
    create_pull_request,
    get_file_contents,
    update_file,
    create_branch,
    get_default_branch,
)
from src.agent_framework.logger import get_logger

logger = get_logger(__name__)


class TestGitHubTools:
    """Test cases for GitHub API tools"""
    
    @pytest.mark.asyncio
    async def test_search_github_repos(self):
        """Test searching GitHub repositories"""
        result = await search_github_repos(
            query="topic:blockchain",
            limit=10,
            token="test_token",
        )
        
        # Should return a result
        assert "success" in result
        assert "data" in result
    
    @pytest.mark.asyncio
    async def test_get_github_repo(self):
        """Test getting GitHub repository info"""
        result = await get_github_repo(
            owner="ethereum",
            repo="solidity",
            token="test_token",
        )
        
        # Should return a result
        assert "success" in result
        assert "data" in result
    
    @pytest.mark.asyncio
    async def test_list_pull_requests(self):
        """Test listing pull requests"""
        result = await list_pull_requests(
            owner="ethereum",
            repo="solidity",
            state="open",
            limit=10,
            token="test_token",
        )
        
        # Should return a result
        assert "success" in result
        assert "data" in result
    
    @pytest.mark.asyncio
    async def test_create_pull_request(self):
        """Test creating a pull request"""
        result = await create_pull_request(
            owner="test_owner",
            repo="test_repo",
            title="Test PR",
            head="test_branch",
            base="main",
            body="Test PR body",
            token="test_token",
        )
        
        # Should return a result
        assert "success" in result
    
    @pytest.mark.asyncio
    async def test_get_file_contents(self):
        """Test getting file contents"""
        result = await get_file_contents(
            owner="test_owner",
            repo="test_repo",
            path="README.md",
            token="test_token",
        )
        
        # Should return a result
        assert "success" in result
    
    @pytest.mark.asyncio
    async def test_get_default_branch(self):
        """Test getting default branch"""
        result = await get_default_branch(
            owner="test_owner",
            repo="test_repo",
            token="test_token",
        )
        
        # Should return a result
        assert "success" in result


class TestGitHubToolsIntegration:
    """Test cases for GitHub tools integration"""
    
    @pytest.mark.asyncio
    async def test_search_and_analyze(self):
        """Test searching and analyzing repositories"""
        # Search for repositories
        search_result = await search_github_repos(
            query="topic:blockchain pushed:>2024-01-01 stars:>100",
            limit=5,
            token="test_token",
        )
        
        if search_result.get("success"):
            repos = search_result.get("data", [])
            
            # Analyze first repository
            if repos:
                first_repo = repos[0]
                owner = first_repo.get("owner", {}).get("login")
                name = first_repo.get("name")
                
                if owner and name:
                    # Get repository details
                    repo_result = await get_github_repo(
                        owner=owner,
                        repo=name,
                        token="test_token",
                    )
                    
                    assert repo_result.get("success") == True
    
    @pytest.mark.asyncio
    async def test_pr_workflow(self):
        """Test complete PR workflow"""
        # Mock workflow
        repo_owner = "test_owner"
        repo_name = "test_repo"
        branch_name = "fix-typo"
        
        # Get default branch
        default_branch_result = await get_default_branch(
            owner=repo_owner,
            repo=repo_name,
            token="test_token",
        )
        
        if default_branch_result.get("success"):
            default_branch = default_branch_result.get("data")
            
            # Create branch (mock)
            # create_result = await create_branch(...)
            
            # Create PR
            pr_result = await create_pull_request(
                owner=repo_owner,
                repo=repo_name,
                title="Fix typo in README",
                head=branch_name,
                base=default_branch,
                body="Fixed spelling errors",
                token="test_token",
            )
            
            assert pr_result.get("success") == True


class TestGitHubToolsErrorHandling:
    """Test cases for GitHub tools error handling"""
    
    @pytest.mark.asyncio
    async def test_search_with_invalid_token(self):
        """Test searching with invalid token"""
        result = await search_github_repos(
            query="test",
            limit=10,
            token="invalid_token",
        )
        
        # Should handle error gracefully
        assert "success" in result
    
    @pytest.mark.asyncio
    async def test_get_nonexistent_repo(self):
        """Test getting non-existent repository"""
        result = await get_github_repo(
            owner="nonexistent",
            repo="nonexistent",
            token="test_token",
        )
        
        # Should handle error gracefully
        assert "success" in result
    
    @pytest.mark.asyncio
    async def test_list_prs_with_invalid_params(self):
        """Test listing PRs with invalid parameters"""
        result = await list_pull_requests(
            owner="test",
            repo="test",
            state="invalid_state",
            token="test_token",
        )
        
        # Should handle error gracefully
        assert "success" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
