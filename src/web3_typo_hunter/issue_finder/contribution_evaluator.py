"""贡献价值评估器 - 评估贡献的价值和空投潜力"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime


@dataclass
class ContributionValue:
    """贡献价值"""
    total_value: int  # 0-100
    learning_value: int  # 学习价值
    visibility_value: int  # 曝光价值
    skill_match_value: int  # 技能匹配价值
    airdrop_potential: int  # 空投潜力


@dataclass
class RepoMetrics:
    """仓库指标"""
    star_score: int
    fork_score: int
    activity_score: int
    web3_relevance: int
    overall: int


class ContributionEvaluator:
    """贡献价值评估器"""

    # Web3 相关主题
    WEB3_TOPICS = [
        "web3", "ethereum", "blockchain", "defi", "nft",
        "crypto", "solidity", "smart-contracts", "dao",
        "token", "airdrop", "wallet", "metamask"
    ]

    def __init__(self, llm_client=None):
        """
        初始化评估器

        Args:
            llm_client: LLM 客户端
        """
        self.llm_client = llm_client

    def _evaluate_repo_metrics(self, repo_data: Dict[str, Any]) -> Dict[str, int]:
        """
        评估仓库指标

        Args:
            repo_data: 仓库数据

        Returns:
            指标评分
        """
        if not repo_data:
            return {"overall": 0}

        stars = repo_data.get("stargazers_count", 0)
        forks = repo_data.get("forks_count", 0)
        open_issues = repo_data.get("open_issues_count", 0)

        # Star 分数 (0-25)
        if stars >= 10000:
            star_score = 25
        elif stars >= 1000:
            star_score = 20
        elif stars >= 500:
            star_score = 15
        elif stars >= 100:
            star_score = 10
        else:
            star_score = 5

        # Fork 分数 (0-15)
        if forks >= 1000:
            fork_score = 15
        elif forks >= 500:
            fork_score = 12
        elif forks >= 100:
            fork_score = 8
        else:
            fork_score = 4

        # 活跃度分数 (0-20)
        updated_at = repo_data.get("updated_at", "")
        try:
            last_update = datetime.fromisoformat(updated_at.replace("Z", "+00:00"))
            days_since_update = (datetime.now() - last_update).days

            if days_since_update <= 7:
                activity_score = 20
            elif days_since_update <= 30:
                activity_score = 15
            elif days_since_update <= 90:
                activity_score = 10
            else:
                activity_score = 5
        except:
            activity_score = 5

        # Web3 相关度 (0-20)
        topics = repo_data.get("topics", [])
        web3_match = sum(1 for t in topics if t.lower() in self.WEB3_TOPICS)
        web3_relevance = min(20, web3_match * 5)

        # 社区活跃度 (0-20) - 基于 open issues
        if open_issues >= 50:
            community_score = 20
        elif open_issues >= 20:
            community_score = 15
        elif open_issues >= 5:
            community_score = 10
        else:
            community_score = 5

        overall = star_score + fork_score + activity_score + web3_relevance + community_score

        return {
            "star_score": star_score,
            "fork_score": fork_score,
            "activity_score": activity_score,
            "web3_relevance": web3_relevance,
            "community_score": community_score,
            "overall": overall
        }

    def _calculate_airdrop_potential(self, repo_data: Dict[str, Any]) -> int:
        """
        计算空投潜力

        Args:
            repo_data: 仓库数据

        Returns:
            0-100 的空投潜力分数
        """
        if not repo_data:
            return 0

        score = 0

        # Web3 相关度
        topics = repo_data.get("topics", [])
        web3_match = sum(1 for t in topics if t.lower() in self.WEB3_TOPICS)
        score += min(40, web3_match * 10)

        # 项目规模 (stars)
        stars = repo_data.get("stargazers_count", 0)
        if stars >= 5000:
            score += 25
        elif stars >= 1000:
            score += 20
        elif stars >= 500:
            score += 15
        elif stars >= 100:
            score += 10

        # 活跃度
        updated_at = repo_data.get("updated_at", "")
        try:
            last_update = datetime.fromisoformat(updated_at.replace("Z", "+00:00"))
            days_since_update = (datetime.now() - last_update).days

            if days_since_update <= 30:
                score += 20
            elif days_since_update <= 90:
                score += 15
            elif days_since_update <= 180:
                score += 10
        except:
            pass

        # Fork 数（社区参与度）
        forks = repo_data.get("forks_count", 0)
        if forks >= 500:
            score += 15
        elif forks >= 100:
            score += 10
        elif forks >= 50:
            score += 5

        return min(100, score)

    def _evaluate_issue_value(self, issue: Dict[str, Any]) -> Dict[str, int]:
        """
        评估单个 Issue 的贡献价值

        Args:
            issue: Issue 数据

        Returns:
            价值评估结果
        """
        analysis = issue.get("analysis", {})
        difficulty = analysis.get("difficulty", "intermediate")
        score = issue.get("score", 50)
        issue_type = issue.get("issue_type", "other")

        # 学习价值 (0-30)
        difficulty_learning = {
            "beginner": 15,
            "intermediate": 25,
            "advanced": 30,
            "expert": 20  # 专家级难度太高，可能不适合学习
        }
        learning_value = difficulty_learning.get(difficulty, 20)

        # 曝光价值 (0-30) - 基于 Issue 关注度和类型
        if issue_type == "bug":
            type_value = 25
        elif issue_type == "feature":
            type_value = 20
        elif issue_type == "documentation":
            type_value = 15
        else:
            type_value = 10

        comments_count = issue.get("comments_count", 0)
        visibility_value = min(30, type_value + comments_count * 2)

        # 技能匹配价值 (0-20) - 基于技能要求的热门程度
        skills = analysis.get("skills_required", [])
        skill_match_value = min(20, len(skills) * 5)

        # 综合价值
        total_value = (score * 0.4 +
                      learning_value * 0.3 +
                      visibility_value * 0.2 +
                      skill_match_value * 0.1)

        return {
            "total_value": int(total_value),
            "learning_value": learning_value,
            "visibility_value": visibility_value,
            "skill_match_value": skill_match_value,
            "base_score": score
        }

    async def generate_strategy(
        self,
        repo_data: Dict[str, Any],
        issues: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        生成贡献策略

        Args:
            repo_data: 仓库数据
            issues: Issue 列表

        Returns:
            策略建议
        """
        if not self.llm_client:
            # 返回基本策略
            return self._generate_basic_strategy(repo_data, issues)

        try:
            strategy = await self.llm_client.generate_strategy(
                repo_name=repo_data.get("full_name", ""),
                repo_description=repo_data.get("description", ""),
                issues_summary=[{
                    "number": i.get("issue_number"),
                    "title": i.get("title"),
                    "type": i.get("issue_type"),
                    "difficulty": i.get("analysis", {}).get("difficulty")
                } for i in issues[:5]]
            )

            return strategy

        except Exception as e:
            return self._generate_basic_strategy(repo_data, issues)

    def _generate_basic_strategy(
        self,
        repo_data: Dict[str, Any],
        issues: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        生成基本贡献策略

        Args:
            repo_data: 仓库数据
            issues: Issue 列表

        Returns:
            策略建议
        """
        # 统计 Issue 类型
        type_counts = {}
        for issue in issues:
            issue_type = issue.get("issue_type", "other")
            type_counts[issue_type] = type_counts.get(issue_type, 0) + 1

        # 推荐优先级
        if type_counts.get("documentation", 0) > 0:
            recommended_start = "documentation"
            approach = "Start with documentation improvements to understand the project"
        elif type_counts.get("good_first_issue", 0) > 0:
            recommended_start = "good_first_issue"
            approach = "Look for issues labeled 'good first issue' to get started"
        else:
            recommended_start = "beginner-friendly bugs"
            approach = "Start with small bug fixes to build familiarity"

        return {
            "approach": approach,
            "recommended_start": recommended_start,
            "priority": "medium",
            "steps": [
                "Read the project's CONTRIBUTING.md",
                f"Find and comment on {recommended_start} issues",
                "Wait for assignment or approval",
                "Submit a draft PR early for feedback"
            ]
        }

    def rank_opportunities(
        self,
        opportunities: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        排序贡献机会

        Args:
            opportunities: 机会列表

        Returns:
            排序后的列表
        """
        def get_composite_score(opp: Dict[str, Any]) -> float:
            issue_value = opp.get("total_value", {}).get("total_value", 0)
            airdrop_potential = opp.get("airdrop_potential", 0)

            # 综合评分：60% 贡献价值 + 40% 空投潜力
            return issue_value * 0.6 + airdrop_potential * 0.4

        return sorted(
            opportunities,
            key=get_composite_score,
            reverse=True
        )

    def evaluate_contribution_opportunity(
        self,
        repo_data: Dict[str, Any],
        issue: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        评估单个贡献机会

        Args:
            repo_data: 仓库数据
            issue: Issue 数据

        Returns:
            完整评估结果
        """
        repo_metrics = self._evaluate_repo_metrics(repo_data)
        airdrop_potential = self._calculate_airdrop_potential(repo_data)
        issue_value = self._evaluate_issue_value(issue)

        # 综合评分
        composite_score = (
            repo_metrics["overall"] * 0.3 +
            issue_value["total_value"] * 0.5 +
            airdrop_potential * 0.2
        )

        return {
            "repo_name": repo_data.get("full_name", ""),
            "issue_number": issue.get("issue_number"),
            "issue_title": issue.get("title"),
            "repo_metrics": repo_metrics,
            "issue_value": issue_value,
            "airdrop_potential": airdrop_potential,
            "composite_score": int(composite_score),
            "recommendation": "highly_recommended" if composite_score >= 70 else "recommended" if composite_score >= 50 else "optional"
        }
