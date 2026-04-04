# tests/web3_typo_hunter/issue_finder/test_contribution_evaluator.py
import pytest
from unittest.mock import Mock, AsyncMock
from datetime import datetime

from src.web3_typo_hunter.issue_finder.contribution_evaluator import ContributionEvaluator


class TestContributionEvaluator:
    """贡献价值评估器测试"""

    @pytest.fixture
    def mock_llm_client(self):
        """Mock LLM 客户端"""
        client = Mock()
        return client

    @pytest.fixture
    def evaluator(self, mock_llm_client):
        """评估器实例"""
        return ContributionEvaluator(llm_client=mock_llm_client)

    def test_evaluate_repo_metrics(self, evaluator):
        """测试评估仓库指标"""
        repo_data = {
            "stargazers_count": 1500,
            "forks_count": 200,
            "open_issues_count": 50,
            "created_at": "2023-01-01T00:00:00Z",
            "updated_at": "2024-01-01T00:00:00Z"
        }

        metrics = evaluator._evaluate_repo_metrics(repo_data)

        assert "star_score" in metrics
        assert "activity_score" in metrics
        assert "overall" in metrics
        assert metrics["overall"] > 0

    def test_calculate_airdrop_potential(self, evaluator):
        """测试计算空投潜力"""
        repo_data = {
            "topics": ["web3", "ethereum", "defi"],
            "stargazers_count": 2000,
            "forks_count": 500
        }

        potential = evaluator._calculate_airdrop_potential(repo_data)

        assert 0 <= potential <= 100
        # Web3 项目应该有更高的空投潜力
        assert potential >= 30

    def test_evaluate_issue_contribution_value(self, evaluator):
        """测试评估 Issue 贡献价值"""
        issue = {
            "issue_number": 1,
            "title": "Fix critical bug",
            "issue_type": "bug",
            "score": 80,
            "analysis": {
                "difficulty": "intermediate",
                "skills_required": ["python", "blockchain"]
            }
        }

        value = evaluator._evaluate_issue_value(issue)

        assert "total_value" in value
        assert "learning_value" in value
        assert "visibility_value" in value
        assert value["total_value"] > 0

    @pytest.mark.asyncio
    async def test_generate_contribution_strategy(self, evaluator, mock_llm_client):
        """测试生成贡献策略"""
        mock_llm_client.generate_strategy = AsyncMock(return_value={
            "approach": "Start with documentation issues",
            "priority": "low",
            "steps": ["Find good first issues", "Comment to claim"]
        })

        repo_data = {"full_name": "owner/repo", "topics": ["web3"]}
        issues = [{"issue_number": 1, "title": "Fix docs"}]

        strategy = await evaluator.generate_strategy(repo_data, issues)

        assert "approach" in strategy
        assert "priority" in strategy
        mock_llm_client.generate_strategy.assert_called_once()

    def test_rank_contribution_opportunities(self, evaluator):
        """测试排序贡献机会"""
        opportunities = [
            {
                "issue_number": 1,
                "total_value": {"total_value": 75},
                "airdrop_potential": 60
            },
            {
                "issue_number": 2,
                "total_value": {"total_value": 85},
                "airdrop_potential": 80
            },
            {
                "issue_number": 3,
                "total_value": {"total_value": 60},
                "airdrop_potential": 40
            }
        ]

        ranked = evaluator.rank_opportunities(opportunities)

        assert len(ranked) == 3
        # 应该按综合价值排序
        assert ranked[0]["issue_number"] == 2  # 最高价值
        assert ranked[2]["issue_number"] == 3  # 最低价值

    def test_evaluate_empty_repo(self, evaluator):
        """测试评估空仓库数据"""
        metrics = evaluator._evaluate_repo_metrics({})

        assert "overall" in metrics
        assert metrics["overall"] == 0
