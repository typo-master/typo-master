"""Issue 分析器 - 分析 GitHub Issues 寻找可贡献机会"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class IssueType(Enum):
    """Issue 类型"""
    BUG = "bug"
    FEATURE = "feature"
    DOCUMENTATION = "documentation"
    OTHER = "other"


class DifficultyLevel(Enum):
    """难度等级"""
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    EXPERT = "expert"


@dataclass
class IssueInfo:
    """Issue 信息"""
    number: int
    title: str
    body: str
    state: str
    created_at: datetime
    labels: List[str]
    author: str
    comments_count: int
    issue_type: str = "other"

    def __post_init__(self):
        if not self.issue_type or self.issue_type == "other":
            self.issue_type = self._detect_type()

    def _detect_type(self) -> str:
        """根据标签检测类型"""
        label_lower = [l.lower() for l in self.labels]

        if any(l in label_lower for l in ["bug", "fix", "error", "crash"]):
            return "bug"
        elif any(l in label_lower for l in ["feature", "enhancement", "request"]):
            return "feature"
        elif any(l in label_lower for l in ["documentation", "docs", "readme"]):
            return "documentation"

        return "other"


@dataclass
class IssueAnalysis:
    """Issue 分析结果"""
    issue_number: int
    difficulty: str
    issue_type: str
    skills_required: List[str]
    estimated_hours: int
    description_summary: str
    contribution_value: int  # 1-100
    recommended_for_beginner: bool


class IssueAnalyzer:
    """Issue 分析器"""

    def __init__(self, github_api=None, llm_client=None):
        """
        初始化 Issue 分析器

        Args:
            github_api: GitHub API 实例
            llm_client: LLM 客户端
        """
        self.github_api = github_api
        self.llm_client = llm_client

    def _parse_issue(self, raw_issue: Dict[str, Any]) -> IssueInfo:
        """
        解析原始 Issue 数据

        Args:
            raw_issue: GitHub API 返回的 Issue 数据

        Returns:
            IssueInfo 对象
        """
        labels = [label["name"] for label in raw_issue.get("labels", [])]

        created_at_str = raw_issue.get("created_at", "")
        try:
            created_at = datetime.fromisoformat(created_at_str.replace("Z", "+00:00"))
        except:
            created_at = datetime.now()

        return IssueInfo(
            number=raw_issue.get("number", 0),
            title=raw_issue.get("title", ""),
            body=raw_issue.get("body", ""),
            state=raw_issue.get("state", "open"),
            created_at=created_at,
            labels=labels,
            author=raw_issue.get("user", {}).get("login", ""),
            comments_count=raw_issue.get("comments", 0)
        )

    def _classify_type(self, labels: List[str]) -> str:
        """
        根据标签分类 Issue 类型

        Args:
            labels: 标签列表

        Returns:
            类型字符串
        """
        label_lower = [l.lower() for l in labels]

        if any(l in label_lower for l in ["bug", "fix", "error", "crash", "defect"]):
            return "bug"
        elif any(l in label_lower for l in ["feature", "enhancement", "request", "proposal"]):
            return "feature"
        elif any(l in label_lower for l in ["documentation", "docs", "readme", "wiki"]):
            return "documentation"
        elif any(l in label_lower for l in ["good first issue", "beginner friendly", "easy"]):
            return "good_first_issue"

        return "other"

    async def analyze_issue(self, issue: IssueInfo) -> Dict[str, Any]:
        """
        分析单个 Issue

        Args:
            issue: Issue 信息

        Returns:
            分析结果字典
        """
        if not self.llm_client:
            # 没有 LLM 时使用基本分析
            return self._basic_analysis(issue)

        try:
            # 使用 LLM 分析
            analysis = await self.llm_client.analyze_issue(
                title=issue.title,
                body=issue.body,
                labels=issue.labels
            )

            score = self._calculate_score(issue, analysis)

            return {
                "issue_number": issue.number,
                "title": issue.title,
                "issue_type": issue.issue_type,
                "analysis": analysis,
                "score": score,
                "recommended": score >= 60,
                "timestamp": datetime.now().isoformat()
            }

        except Exception as e:
            return {
                "issue_number": issue.number,
                "title": issue.title,
                "error": str(e),
                "recommended": False
            }

    def _basic_analysis(self, issue: IssueInfo) -> Dict[str, Any]:
        """
        基本分析（无 LLM）

        Args:
            issue: Issue 信息

        Returns:
            分析结果
        """
        labels_lower = [l.lower() for l in issue.labels]

        # 基于标签的分析
        difficulty = "intermediate"
        if any(l in labels_lower for l in ["good first issue", "beginner"]):
            difficulty = "beginner"
        elif any(l in labels_lower for l in ["hard", "complex", "advanced"]):
            difficulty = "advanced"

        estimated_hours = 4
        if difficulty == "beginner":
            estimated_hours = 2
        elif difficulty == "advanced":
            estimated_hours = 16

        analysis = {
            "difficulty": difficulty,
            "type": issue.issue_type,
            "skills_required": [],
            "estimated_hours": estimated_hours,
            "description_summary": issue.body[:200] if issue.body else ""
        }

        score = self._calculate_score(issue, analysis)

        return {
            "issue_number": issue.number,
            "title": issue.title,
            "issue_type": issue.issue_type,
            "analysis": analysis,
            "score": score,
            "recommended": score >= 60,
            "timestamp": datetime.now().isoformat()
        }

    def _calculate_score(self, issue: IssueInfo, analysis: Dict[str, Any]) -> int:
        """
        计算 Issue 的贡献价值分数

        Args:
            issue: Issue 信息
            analysis: 分析结果

        Returns:
            0-100 的分数
        """
        score = 50  # 基础分

        # 难度加分（beginner friendly 更适合贡献）
        difficulty = analysis.get("difficulty", "intermediate")
        if difficulty == "beginner":
            score += 20
        elif difficulty == "advanced":
            score -= 10

        # 标签加分
        labels_lower = [l.lower() for l in issue.labels]
        if any(l in labels_lower for l in ["good first issue", "help wanted", "beginner friendly"]):
            score += 15
        if any(l in labels_lower for l in ["bug", "critical", "urgent"]):
            score += 10

        # 讨论活跃度（有讨论但不太多的更适合参与）
        if 1 <= issue.comments_count <= 10:
            score += 5

        # 预估时间（短时间可完成的更好）
        hours = analysis.get("estimated_hours", 4)
        if hours <= 2:
            score += 10
        elif hours > 16:
            score -= 10

        return max(0, min(100, score))

    async def fetch_and_analyze_issues(
        self,
        repo_full_name: str,
        state: str = "open",
        labels: Optional[List[str]] = None,
        limit: int = 30
    ) -> List[Dict[str, Any]]:
        """
        获取并分析仓库 Issues

        Args:
            repo_full_name: 仓库全名
            state: Issue 状态
            labels: 标签过滤
            limit: 数量限制

        Returns:
            分析结果列表
        """
        if not self.github_api:
            raise ValueError("GitHub API is required")

        try:
            # 获取 Issues
            raw_issues = await self.github_api.get_issues(
                repo_full_name,
                state=state,
                labels=labels,
                limit=limit
            )

            results = []
            for raw_issue in raw_issues:
                issue = self._parse_issue(raw_issue)
                analysis = await self.analyze_issue(issue)
                results.append(analysis)

            # 按分数排序
            results.sort(key=lambda x: x.get("score", 0), reverse=True)

            return results

        except Exception as e:
            return []
