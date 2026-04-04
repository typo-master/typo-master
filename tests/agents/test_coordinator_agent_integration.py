# tests/agents/test_coordinator_agent_integration.py
import pytest
from unittest.mock import Mock, AsyncMock, patch

from src.agents.coordinator_agent import CoordinatorAgent


class TestCoordinatorAgentIntegration:
    """CoordinatorAgent 集成测试"""

    @pytest.fixture
    def agent(self):
        """CoordinatorAgent 实例"""
        return CoordinatorAgent(github_token="test_token")

    @pytest.mark.asyncio
    async def test_translate_document_workflow(self, agent):
        """测试文档翻译工作流"""
        mock_translator = Mock()
        mock_translator.translate_repo_readme = AsyncMock(return_value={
            "success": True,
            "translated_content": "# 标题\n\n这是翻译后的内容",
            "target_filename": "README.zh.md"
        })
        agent.translator = mock_translator

        result = await agent.process_task({
            "type": "translate_document",
            "repo": "owner/repo",
            "target_lang": "zh"
        })

        assert result["success"] is True
        assert "translated_content" in result

    @pytest.mark.asyncio
    async def test_find_issues_workflow(self, agent):
        """测试查找 Issues 工作流"""
        mock_analyzer = Mock()
        mock_analyzer.fetch_and_analyze_issues = AsyncMock(return_value=[
            {
                "issue_number": 1,
                "title": "Bug fix",
                "score": 80,
                "recommended": True
            }
        ])
        agent.issue_analyzer = mock_analyzer

        result = await agent.process_task({
            "type": "find_issues",
            "repo": "owner/repo",
            "limit": 10
        })

        assert result["success"] is True
        assert len(result["issues"]) == 1

    @pytest.mark.asyncio
    async def test_batch_find_contributions_workflow(self, agent):
        """测试批量查找贡献机会工作流"""
        mock_analyzer = Mock()
        mock_analyzer.fetch_and_analyze_issues = AsyncMock(return_value=[
            {"issue_number": 1, "score": 80, "recommended": True}
        ])
        agent.issue_analyzer = mock_analyzer

        mock_evaluator = Mock()
        mock_evaluator.evaluate_contribution_opportunity = Mock(return_value={
            "composite_score": 75,
            "recommendation": "recommended"
        })
        mock_evaluator.rank_opportunities = Mock(return_value=[
            {"composite_score": 75, "recommendation": "recommended"}
        ])
        agent.contribution_evaluator = mock_evaluator

        # Mock GitHubAPI - patch where it's imported in the method
        with patch('src.web3_typo_hunter.utils.github_api.GitHubAPI') as mock_github_class:
            mock_github = Mock()
            mock_github.get_repo = AsyncMock(return_value={
                "full_name": "owner/repo",
                "stargazers_count": 100
            })
            mock_github_class.return_value = mock_github

            result = await agent.process_task({
                "type": "batch_find_contributions",
                "repos": ["owner/repo1"],
                "limit": 5
            })

            assert result["success"] is True
            assert "opportunities" in result

    @pytest.mark.asyncio
    async def test_get_capabilities_includes_new_features(self, agent):
        """测试能力列表包含新功能"""
        # Set up mock agents
        agent.translator = Mock()
        agent.issue_analyzer = Mock()
        agent.contribution_evaluator = Mock()

        capabilities = await agent.get_capabilities()

        assert "document_translation" in capabilities.get("features", {})
        assert "issue_discovery" in capabilities.get("features", {})
        assert "contribution_evaluation" in capabilities.get("features", {})
