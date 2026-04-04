"""Issue 过滤器 - 根据条件筛选 Issues"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from enum import Enum


class IssueTypeFilter(Enum):
    """Issue 类型过滤"""
    BUG = "bug"
    FEATURE = "feature"
    DOCUMENTATION = "documentation"
    GOOD_FIRST_ISSUE = "good_first_issue"
    OTHER = "other"


class DifficultyFilter(Enum):
    """难度过滤"""
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    ANY = "any"


@dataclass
class FilterCriteria:
    """过滤条件"""
    issue_types: Optional[List[str]] = None
    difficulty: Optional[str] = None
    min_score: Optional[int] = None
    max_score: Optional[int] = None
    max_estimated_hours: Optional[int] = None
    recommended_only: bool = False
    exclude_assigned: bool = True
    has_labels: List[str] = field(default_factory=list)
    exclude_labels: List[str] = field(default_factory=list)


class IssueFilter:
    """Issue 过滤器"""

    def __init__(self, criteria: Optional[FilterCriteria] = None):
        """
        初始化过滤器

        Args:
            criteria: 过滤条件
        """
        self.criteria = criteria or FilterCriteria()

    def filter(self, issues: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        过滤 Issues

        Args:
            issues: Issue 列表

        Returns:
            过滤后的 Issue 列表
        """
        results = issues

        # 按类型过滤
        if self.criteria.issue_types:
            results = [
                i for i in results
                if i.get("issue_type", "other") in self.criteria.issue_types
            ]

        # 按难度过滤
        if self.criteria.difficulty:
            results = [
                i for i in results
                if self._matches_difficulty(i, self.criteria.difficulty)
            ]

        # 按分数过滤
        if self.criteria.min_score is not None:
            results = [
                i for i in results
                if i.get("score", 0) >= self.criteria.min_score
            ]

        if self.criteria.max_score is not None:
            results = [
                i for i in results
                if i.get("score", 0) <= self.criteria.max_score
            ]

        # 按预估时间过滤
        if self.criteria.max_estimated_hours is not None:
            results = [
                i for i in results
                if self._get_estimated_hours(i) <= self.criteria.max_estimated_hours
            ]

        # 只显示推荐的
        if self.criteria.recommended_only:
            results = [
                i for i in results
                if i.get("recommended", False)
            ]

        # 按标签过滤
        if self.criteria.has_labels:
            results = [
                i for i in results
                if self._has_any_label(i, self.criteria.has_labels)
            ]

        # 排除标签
        if self.criteria.exclude_labels:
            results = [
                i for i in results
                if not self._has_any_label(i, self.criteria.exclude_labels)
            ]

        return results

    def _matches_difficulty(self, issue: Dict[str, Any], difficulty: str) -> bool:
        """
        检查 Issue 是否匹配难度

        Args:
            issue: Issue 字典
            difficulty: 目标难度

        Returns:
            是否匹配
        """
        if difficulty == "any":
            return True

        analysis = issue.get("analysis", {})
        issue_difficulty = analysis.get("difficulty", "intermediate")

        return issue_difficulty == difficulty

    def _get_estimated_hours(self, issue: Dict[str, Any]) -> int:
        """
        获取预估时间

        Args:
            issue: Issue 字典

        Returns:
            预估小时数
        """
        analysis = issue.get("analysis", {})
        return analysis.get("estimated_hours", 4)

    def _has_any_label(self, issue: Dict[str, Any], labels: List[str]) -> bool:
        """
        检查 Issue 是否有任一标签

        Args:
            issue: Issue 字典
            labels: 标签列表

        Returns:
            是否有匹配标签
        """
        # 这里假设 issue 中有 labels 字段
        # 实际实现中可能需要根据具体情况调整
        issue_labels = issue.get("labels", [])
        labels_lower = [l.lower() for l in labels]
        issue_labels_lower = [l.lower() for l in issue_labels]

        return any(l in issue_labels_lower for l in labels_lower)

    def sort_by_score(
        self,
        issues: List[Dict[str, Any]],
        descending: bool = True
    ) -> List[Dict[str, Any]]:
        """
        按分数排序

        Args:
            issues: Issue 列表
            descending: 是否降序

        Returns:
            排序后的列表
        """
        return sorted(
            issues,
            key=lambda x: x.get("score", 0),
            reverse=descending
        )

    def get_stats(self, issues: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        获取 Issue 统计信息

        Args:
            issues: Issue 列表

        Returns:
            统计信息字典
        """
        if not issues:
            return {
                "total": 0,
                "avg_score": 0,
                "recommended_count": 0
            }

        scores = [i.get("score", 0) for i in issues]
        recommended = sum(1 for i in issues if i.get("recommended", False))

        # 按类型统计
        by_type = {}
        for issue in issues:
            issue_type = issue.get("issue_type", "other")
            by_type[issue_type] = by_type.get(issue_type, 0) + 1

        return {
            "total": len(issues),
            "avg_score": sum(scores) / len(scores),
            "max_score": max(scores),
            "min_score": min(scores),
            "recommended_count": recommended,
            "by_type": by_type
        }
