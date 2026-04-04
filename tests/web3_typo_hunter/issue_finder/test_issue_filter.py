# tests/web3_typo_hunter/issue_finder/test_issue_filter.py
import pytest
from datetime import datetime, timedelta

from src.web3_typo_hunter.issue_finder.issue_filter import IssueFilter, FilterCriteria


class TestIssueFilter:
    """Issue 过滤器测试"""

    @pytest.fixture
    def sample_issues(self):
        """示例 Issues"""
        return [
            {
                "issue_number": 1,
                "title": "Fix typo",
                "issue_type": "documentation",
                "analysis": {
                    "difficulty": "beginner",
                    "estimated_hours": 1
                },
                "score": 85,
                "recommended": True
            },
            {
                "issue_number": 2,
                "title": "Add feature X",
                "issue_type": "feature",
                "analysis": {
                    "difficulty": "advanced",
                    "estimated_hours": 20
                },
                "score": 40,
                "recommended": False
            },
            {
                "issue_number": 3,
                "title": "Bug in login",
                "issue_type": "bug",
                "analysis": {
                    "difficulty": "intermediate",
                    "estimated_hours": 4
                },
                "score": 75,
                "recommended": True
            }
        ]

    def test_filter_by_difficulty(self, sample_issues):
        """测试按难度过滤"""
        criteria = FilterCriteria(difficulty="beginner")
        filter_obj = IssueFilter(criteria)

        results = filter_obj.filter(sample_issues)

        assert len(results) == 1
        assert results[0]["issue_number"] == 1

    def test_filter_by_type(self, sample_issues):
        """测试按类型过滤"""
        criteria = FilterCriteria(issue_types=["bug"])
        filter_obj = IssueFilter(criteria)

        results = filter_obj.filter(sample_issues)

        assert len(results) == 1
        assert results[0]["issue_number"] == 3

    def test_filter_by_score(self, sample_issues):
        """测试按分数过滤"""
        criteria = FilterCriteria(min_score=70)
        filter_obj = IssueFilter(criteria)

        results = filter_obj.filter(sample_issues)

        assert len(results) == 2
        assert all(r["score"] >= 70 for r in results)

    def test_filter_by_max_hours(self, sample_issues):
        """测试按预估时间过滤"""
        criteria = FilterCriteria(max_estimated_hours=5)
        filter_obj = IssueFilter(criteria)

        results = filter_obj.filter(sample_issues)

        assert len(results) == 2
        assert all(r["analysis"]["estimated_hours"] <= 5 for r in results)

    def test_filter_by_recommended_only(self, sample_issues):
        """测试只显示推荐的"""
        criteria = FilterCriteria(recommended_only=True)
        filter_obj = IssueFilter(criteria)

        results = filter_obj.filter(sample_issues)

        assert len(results) == 2
        assert all(r["recommended"] for r in results)

    def test_combined_filters(self, sample_issues):
        """测试组合过滤条件"""
        criteria = FilterCriteria(
            difficulty="beginner",
            min_score=80,
            recommended_only=True
        )
        filter_obj = IssueFilter(criteria)

        results = filter_obj.filter(sample_issues)

        assert len(results) == 1
        assert results[0]["issue_number"] == 1

    def test_empty_criteria(self, sample_issues):
        """测试空过滤条件"""
        criteria = FilterCriteria()
        filter_obj = IssueFilter(criteria)

        results = filter_obj.filter(sample_issues)

        assert len(results) == 3
