"""
Decision Agent - Makes high-level decisions and strategies

This agent is responsible for making high-level decisions about
which projects to prioritize and what actions to take.
"""

import asyncio
import json
from typing import Any, Dict, List, Optional

from ..agent_framework.base_agent import BaseAgent, AgentConfig
from ..agent_framework.llm_client import OpenAICompatibleResponsesClient
from ..agent_framework.logger import get_logger

logger = get_logger(__name__)


class DecisionAgent(BaseAgent):
    """
    Agent for making high-level decisions

    Responsibilities:
    - Prioritize projects
    - Decide on actions
    - Evaluate trade-offs
    - Recommend strategies
    """

    def __init__(self, llm_client: Optional[OpenAICompatibleResponsesClient] = None):
        """Initialize decision agent"""
        config = AgentConfig(
            name="DecisionAgent",
            version="1.0.0",
            description="Makes high-level decisions and strategies",
            max_retries=3,
            timeout=300.0,
        )

        super().__init__(config)

        # Decision thresholds
        self.min_stars_for_pr = 50
        self.min_activity_score = 30
        self.max_projects_per_batch = 10

        self.llm_client = llm_client
        self.llm_enabled = False

    async def on_initialize(self) -> None:
        """Initialize agent and register tools"""
        if not self.llm_client:
            self.llm_client = OpenAICompatibleResponsesClient.from_env()

        self.llm_enabled = bool(self.llm_client and self.llm_client.is_enabled)
        if self.llm_enabled:
            logger.info(
                "Decision agent initialized with LLM model=%s base_url=%s",
                self.llm_client.config.model,
                self.llm_client.config.base_url,
            )
        else:
            logger.info("Decision agent initialized without LLM (rule-based mode)")

    async def on_start(self) -> None:
        """Called when agent starts"""
        logger.info("Decision agent started")

    async def on_stop(self) -> None:
        """Called when agent stops"""
        logger.info("Decision agent stopped")

    async def on_pause(self) -> None:
        """Called when agent is paused"""
        logger.info("Decision agent paused")

    async def on_resume(self) -> None:
        """Called when agent resumes"""
        logger.info("Decision agent resumed")

    async def process_task(self, task: Any) -> Any:
        """
        Process a decision task

        Args:
            task: Task to process

        Returns:
            Task result
        """
        task_type = task.get("type")

        if task_type == "prioritize_projects":
            return await self._prioritize_projects(task)
        elif task_type == "should_create_pr":
            return await self._should_create_pr(task)
        elif task_type == "recommend_action":
            return await self._recommend_action(task)
        elif task_type == "evaluate_strategy":
            return await self._evaluate_strategy(task)
        elif task_type == "llm_health_check":
            return await self._llm_health_check()
        else:
            logger.warning(f"Unknown task type: {task_type}")
            return {"error": f"Unknown task type: {task_type}"}

    async def _prioritize_projects(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        Prioritize projects for processing

        Args:
            task: Task parameters

        Returns:
            Prioritized projects
        """
        projects = task.get("projects", [])
        max_projects = task.get("limit", self.max_projects_per_batch)

        logger.info(f"Prioritizing {len(projects)} projects")

        # Score each project
        scored_projects = []
        for project in projects:
            score = self._calculate_priority_score(project)
            scored_projects.append({
                "project": project,
                "score": score,
            })

        # Sort by score
        scored_projects.sort(key=lambda x: x["score"], reverse=True)

        # Return top projects
        prioritized = scored_projects[:max_projects]

        return {
            "projects": [p["project"] for p in prioritized],
            "scores": [p["score"] for p in prioritized],
            "total_projects": len(projects),
            "prioritized_projects": len(prioritized),
        }

    async def _should_create_pr(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        Decide whether to create a PR

        Args:
            task: Task parameters

        Returns:
            Decision result
        """
        project = task.get("project", {})
        typos_found = task.get("typos_found", 0)
        quality_score = task.get("quality_score", 0)

        # Evaluate factors
        factors = {
            "stars": project.get("stars", 0),
            "activity": project.get("activity_score", 0),
            "typos_found": typos_found,
            "quality_score": quality_score,
        }

        # Decision logic
        should_create = True
        reasons = []

        # Check if project has enough stars
        if factors["stars"] < self.min_stars_for_pr:
            should_create = False
            reasons.append(f"Project has only {factors['stars']} stars (minimum: {self.min_stars_for_pr})")

        # Check if project is active enough
        if factors["activity"] < self.min_activity_score:
            should_create = False
            reasons.append(f"Project activity score {factors['activity']} is too low (minimum: {self.min_activity_score})")

        # Check if enough typos were found
        if factors["typos_found"] < 1:
            should_create = False
            reasons.append("No typos found")

        # Check quality score
        if factors["quality_score"] < 0.7:
            should_create = False
            reasons.append(f"Quality score {factors['quality_score']} is too low (minimum: 0.7)")

        return {
            "should_create": should_create,
            "reasons": reasons if not should_create else [],
            "factors": factors,
        }

    async def _recommend_action(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        Recommend an action

        Args:
            task: Task parameters

        Returns:
            Recommended action
        """
        context = task.get("context", {})

        llm_recommendation = await self._recommend_action_with_llm(context)
        if llm_recommendation:
            return llm_recommendation

        return self._recommend_action_rule_based(context)

    def _recommend_action_rule_based(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Fallback recommendation logic when LLM is unavailable."""
        project = context.get("project", {})
        scan_result = context.get("scan_result", {})

        typos_found = scan_result.get("total_typos", 0)
        stars = project.get("stars", 0)

        if typos_found == 0:
            action = "skip"
            reason = "No typos found"
        elif stars < self.min_stars_for_pr:
            action = "skip"
            reason = f"Project has only {stars} stars"
        elif typos_found < 3:
            action = "review"
            reason = "Few typos found, review manually"
        else:
            action = "proceed"
            reason = "Good candidate for PR"

        return {
            "action": action,
            "reason": reason,
            "confidence": 0.8,
            "decision_source": "rule_based",
        }

    async def _recommend_action_with_llm(self, context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Use LLM to recommend an action, with strict JSON output validation."""
        if not self.llm_enabled or not self.llm_client:
            return None

        prompt_context = {
            "context": context,
            "thresholds": {
                "min_stars_for_pr": self.min_stars_for_pr,
                "min_activity_score": self.min_activity_score,
            },
            "valid_actions": ["skip", "review", "proceed"],
        }

        system_prompt = (
            "You are a strict decision engine for typo-fix pull request workflows. "
            "Return only compact JSON."
        )
        user_prompt = (
            "Given the context below, decide a single action.\n"
            "Rules:\n"
            "1) action must be one of: skip, review, proceed\n"
            "2) confidence must be a number between 0 and 1\n"
            "3) Keep reason concise\n"
            "4) Output JSON only, no markdown\n\n"
            f"{json.dumps(prompt_context, ensure_ascii=False)}"
        )

        llm_result = await asyncio.to_thread(
            self.llm_client.generate_text,
            system_prompt,
            user_prompt,
            0.1,
        )

        if not llm_result.get("success"):
            logger.warning("LLM recommendation failed, fallback to rule-based: %s", llm_result.get("error"))
            return None

        raw_text = str(llm_result.get("text", "")).strip()
        parsed = self._extract_json_object(raw_text)
        if not parsed:
            logger.warning("LLM returned non-JSON recommendation, fallback to rule-based")
            return None

        action = str(parsed.get("action", "")).strip().lower()
        if action not in {"skip", "review", "proceed"}:
            logger.warning("LLM returned invalid action '%s', fallback to rule-based", action)
            return None

        reason = str(parsed.get("reason", "")).strip() or "LLM recommendation"
        confidence = self._clamp_confidence(parsed.get("confidence", 0.75))

        return {
            "action": action,
            "reason": reason,
            "confidence": confidence,
            "decision_source": "llm",
            "model": self.llm_client.config.model,
        }

    async def _llm_health_check(self) -> Dict[str, Any]:
        """Test whether LLM connectivity is healthy."""
        if not self.llm_client or not self.llm_enabled:
            return {
                "success": False,
                "error": "LLM is not configured. Set OPENAI_API_KEY/OPENAI_BASE_URL/OPENAI_MODEL.",
            }

        return await asyncio.to_thread(self.llm_client.health_check)

    async def _evaluate_strategy(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        Evaluate a strategy

        Args:
            task: Task parameters

        Returns:
            Strategy evaluation
        """
        strategy = task.get("strategy", "")
        context = task.get("context", {})

        # Evaluate based on strategy type
        if strategy == "aggressive":
            return {
                "strategy": strategy,
                "appropriate": context.get("time_pressure", False),
                "risk": "high",
                "expected_return": "high",
            }
        elif strategy == "conservative":
            return {
                "strategy": strategy,
                "appropriate": not context.get("time_pressure", True),
                "risk": "low",
                "expected_return": "low",
            }
        elif strategy == "balanced":
            return {
                "strategy": strategy,
                "appropriate": True,
                "risk": "medium",
                "expected_return": "medium",
            }
        else:
            return {
                "strategy": strategy,
                "appropriate": False,
                "risk": "unknown",
                "expected_return": "unknown",
            }

    def _calculate_priority_score(self, project: Dict[str, Any]) -> float:
        """
        Calculate priority score for a project

        Args:
            project: Project data

        Returns:
            Priority score (0-100)
        """
        score = 0.0

        # Stars score (30%)
        stars = project.get("stars", 0)
        stars_score = min(30, (stars / 1000) * 30)
        score += stars_score

        # Activity score (30%)
        activity = project.get("activity_score", 0)
        activity_score = min(30, activity * 0.3)
        score += activity_score

        # Airdrop potential score (20%)
        airdrop = project.get("airdrop_score", 0)
        airdrop_score = min(20, airdrop * 0.2)
        score += airdrop_score

        # Recent activity score (20%)
        recent_prs = project.get("recent_prs", 0)
        recent_score = min(20, recent_prs * 2)
        score += recent_score

        return round(score, 1)

    @staticmethod
    def _extract_json_object(text: str) -> Optional[Dict[str, Any]]:
        """Extract a JSON object from raw LLM text."""
        if not text:
            return None

        # Fast path: full JSON content.
        try:
            parsed = json.loads(text)
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            pass

        # Fallback: recover first JSON object block.
        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1 or end <= start:
            return None

        try:
            parsed = json.loads(text[start:end + 1])
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            return None

        return None

    @staticmethod
    def _clamp_confidence(value: Any) -> float:
        """Clamp confidence into [0, 1]."""
        try:
            parsed = float(value)
        except (TypeError, ValueError):
            return 0.75
        return max(0.0, min(1.0, parsed))
