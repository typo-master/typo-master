# tests/web3_typo_hunter/issue_finder/test_issue_analyzer.py
import pytest
from unittest.mock import Mock, AsyncMock
from datetime import datetime

from src.web3_typo_hunter.issue_finder.issue_analyzer import IssueAnalyzer, IssueInfo


class TestIssueAnalyzer:
    """Issue 分析器测试"""

    @pytest.fixture
    def mock_github_api(self):
        """Mock GitHub API"""
        api = Mock()
        return api

    @pytest.fixture
    def mock_llm_client(self):
        """Mock LLM 客户端"""
        client = Mock()
        client.analyze_issue = AsyncMock(return_value={
            "difficulty": "beginner",
            "type": "bug",
            "skills_required": ["python"],
            "estimated_hours": 2,
            "description_summary": "Fix typo in docs"
        })
        return client

    @pytest.fixture
    def analyzer(self, mock_github_api, mock_llm_client):
        """分析器实例"""
        return IssueAnalyzer(
            github_api=mock_github_api,
            llm_client=mock_llm_client
        )

    def test_parse_issue_data(self, analyzer):
        """测试解析 Issue 数据"""
        raw_issue = {
            "number": 123,
            "title": "Bug in login",
            "body": "Users cannot login",
            "state": "open",
            "created_at": "2024-01-01T00:00:00Z",
            "labels": [{"name": "bug"}, {"name": "good first issue"}],
            "user": {"login": "reporter"},
            "comments": 5
        }

        issue = analyzer._parse_issue(raw_issue)

        assert issue.number == 123
        assert issue.title == "Bug in login"
        assert issue.issue_type == "bug"
        assert "good first issue" in issue.labels

    def test_classify_issue_type(self, analyzer):
        """测试 Issue 类型分类"""
        assert analyzer._classify_type(["bug", "critical"]) == "bug"
        assert analyzer._classify_type(["enhancement", "feature"]) == "feature"
        assert analyzer._classify_type(["documentation"]) == "documentation"
        assert analyzer._classify_type([]) == "other"

    @pytest.mark.asyncio
    async def test_analyze_single_issue(self, analyzer, mock_llm_client):
        """测试分析单个 Issue"""
        issue = IssueInfo(
            number=123,
            title="Bug in login",
            body="Users cannot login",
            state="open",
            created_at=datetime.now(),
            labels=["bug"],
            author="reporter",
            comments_count=5
        )

        result = await analyzer.analyze_issue(issue)

        assert result["issue_number"] == 123
        assert "analysis" in result
        assert result["analysis"]["difficulty"] == "beginner"
        mock_llm_client.analyze_issue.assert_called_once()

    @pytest.mark.asyncio
    async def test_fetch_and_analyze_issues(self, analyzer, mock_github_api):
        """测试获取并分析 Issues"""
        mock_github_api.get_issues = AsyncMock(return_value=[
            {
                "number": 1,
                "title": "Bug 1",
                "body": "Description 1",
                "state": "open",
                "created_at": "2024-01-01T00:00:00Z",
                "labels": [{"name": "bug"}],
                "user": {"login": "user1"},
                "comments": 2
            },
            {
                "number": 2,
                "title": "Feature 1",
                "body": "Description 2",
                "state": "open",
                "created_at": "2024-01-02T00:00:00Z",
                "labels": [{"name": "enhancement"}],
                "user": {"login": "user2"},
                "comments": 0
            }
        ])

        results = await analyzer.fetch_and_analyze_issues(
            repo_full_name="owner/repo",
            state="open",
            limit=10
        )

        assert len(results) == 2
        assert results[0]["issue_number"] == 1
        assert results[1]["issue_number"] == 2

    def test_calculate_issue_score(self, analyzer):
        """测试 Issue 评分"""
        issue = IssueInfo(
            number=1,
            title="Good first issue",
            body="Easy to fix",
            state="open",
            created_at=datetime.now(),
            labels=["good first issue", "bug"],
            author="user",
            comments_count=2
        )

        analysis = {
            "difficulty": "beginner",
            "estimated_hours": 1
        }

        score = analyzer._calculate_score(issue, analysis)

        assert score > 0
        # good first issue 标签应该增加分数
        assert score >= 50
