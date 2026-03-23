"""
Skill-Enabled Coordinator Agent

A new coordinator agent that uses Skills as LangGraph nodes,
providing better modularity and reusability.
"""

from typing import Any, Dict, List, Optional
from datetime import datetime

from langgraph.graph import END, START, StateGraph
from langgraph.checkpoint.memory import MemorySaver

from .skill_agent import SkillEnabledAgent, SkillAgentConfig
from .skill_langgraph import SkillNodeWrapper, SkillGraphBuilder
from .skill_system import SkillRegistry, SkillContext, SkillResult
from .logger import get_logger

logger = get_logger(__name__)


class WorkflowState(dict):
    """State for coordinator workflow"""
    def __init__(self, **kwargs):
        super().__init__(**kwargs)


class SkillCoordinatorAgent(SkillEnabledAgent):
    """
    Skill-enabled coordinator agent

    Features:
    - Uses Skills as LangGraph nodes
    - Supports dynamic workflow composition
    - Integrates with memory system
    - Supports both single and batch workflows
    """

    def __init__(self, github_token: Optional[str] = None, work_dir: Optional[str] = None):
        config = SkillAgentConfig(
            name="SkillCoordinatorAgent",
            version="2.0.0",
            description="Skill-enabled coordinator with LangGraph integration",
            max_retries=3,
            timeout=3600.0,
            enable_memory=True,
            enable_langgraph=True,
            default_workflow="single_project",
        )
        super().__init__(config)

        self.github_token = github_token
        self.work_dir = work_dir or "./work"

        # Sub-agents
        self.discovery_agent = None
        self.scanner_agent = None
        self.quality_evaluator_agent = None
        self.fixer_agent = None
        self.decision_agent = None
        self.pr_creator_agent = None
        self.report_generator_agent = None

        # Custom workflows
        self._custom_workflows: Dict[str, Any] = {}

    async def on_initialize(self) -> None:
        """Initialize agent with sub-agents and workflows"""
        await super().on_initialize()

        # Initialize sub-agents
        from .project_discovery_agent import ProjectDiscoveryAgent
        from .typo_scanner_agent import TypoScannerAgent
        from .quality_evaluator_agent import QualityEvaluatorAgent
        from .typo_fixer_agent import TypoFixerAgent
        from .decision_agent import DecisionAgent
        from .pr_creator_agent import PRCreatorAgent
        from .report_generator_agent import ReportGeneratorAgent

        self.discovery_agent = ProjectDiscoveryAgent(github_token=self.github_token)
        self.scanner_agent = TypoScannerAgent()
        self.quality_evaluator_agent = QualityEvaluatorAgent()
        self.fixer_agent = TypoFixerAgent()
        self.decision_agent = DecisionAgent()
        self.pr_creator_agent = PRCreatorAgent(github_token=self.github_token)
        self.report_generator_agent = ReportGeneratorAgent()

        # Initialize all
        for agent in [
            self.discovery_agent, self.scanner_agent,
            self.quality_evaluator_agent, self.fixer_agent,
            self.decision_agent, self.pr_creator_agent,
            self.report_generator_agent
        ]:
            if agent:
                await agent.initialize()

        # Build custom workflows using skills
        self._build_workflows()

        logger.info("SkillCoordinatorAgent initialized")

    def _build_workflows(self):
        """Build all workflows using skills"""
        # Single project workflow using skills
        self._build_single_project_workflow()

        # Batch workflow
        self._build_batch_workflow()

        # Scan-only workflow
        self._build_scan_only_workflow()

    def _build_single_project_workflow(self):
        """Build single project workflow using skills"""
        builder = SkillGraphBuilder("single_project")
        builder.set_agent(self)

        # Add skill nodes
        builder.add_skill("repository_scan", "scan")
        builder.add_skill("typo_fix", "fix", conditional=True)
        builder.add_skill("git_operations", "git", conditional=True)
        builder.add_skill("pull_request", "pr", conditional=True)
        builder.add_skill("typo_report", "report")

        # Build graph manually for more control
        graph = StateGraph(WorkflowState)

        # Get skills
        scan_skill = SkillRegistry.get("repository_scan")
        fix_skill = SkillRegistry.get("typo_fix")
        git_skill = SkillRegistry.get("git_operations")
        pr_skill = SkillRegistry.get("pull_request")
        report_skill = SkillRegistry.get("typo_report")

        # Add nodes with wrappers
        if scan_skill:
            graph.add_node("scan", SkillNodeWrapper(scan_skill, self))
        if fix_skill:
            graph.add_node("fix", SkillNodeWrapper(fix_skill, self))
        if git_skill:
            graph.add_node("git", SkillNodeWrapper(git_skill, self))
        if pr_skill:
            graph.add_node("pr", SkillNodeWrapper(pr_skill, self))
        if report_skill:
            graph.add_node("report", SkillNodeWrapper(report_skill, self))

        # Add conditional edges
        def route_after_scan(state: WorkflowState):
            scan_result = state.get("scan_result", {})
            if not scan_result or scan_result.get("total_typos", 0) == 0:
                return "report"
            return "fix"

        def route_after_fix(state: WorkflowState):
            fix_result = state.get("fix_result", {})
            if not fix_result or fix_result.get("total_typos_fixed", 0) == 0:
                return "report"
            return "git"

        def route_after_git(state: WorkflowState):
            git_result = state.get("git_result", {})
            pr_decision = state.get("pr_decision", {})
            if pr_decision.get("should_create_pr") and git_result:
                return "pr"
            return "report"

        # Build graph
        graph.add_edge(START, "scan")
        graph.add_conditional_edges(
            "scan",
            route_after_scan,
            {"fix": "fix", "report": "report"}
        )
        graph.add_conditional_edges(
            "fix",
            route_after_fix,
            {"git": "git", "report": "report"}
        )
        graph.add_conditional_edges(
            "git",
            route_after_git,
            {"pr": "pr", "report": "report"}
        )
        graph.add_edge("pr", "report")
        graph.add_edge("report", END)

        # Compile with checkpoint
        checkpoint = MemorySaver()
        self._custom_workflows["single_project"] = graph.compile(checkpointer=checkpoint)

    def _build_batch_workflow(self):
        """Build batch processing workflow"""
        graph = StateGraph(WorkflowState)

        async def discover_node(state: WorkflowState):
            """Discover projects"""
            if not self.discovery_agent:
                return {"error": "Discovery agent not initialized"}

            result = await self.discovery_agent.process_task({
                "type": "search_projects",
                "days": state.get("days", 30),
                "min_stars": state.get("min_stars", 100),
                "limit": state.get("limit", 5),
            })

            return {"discovery_result": result}

        async def process_projects_node(state: WorkflowState):
            """Process discovered projects"""
            discovery = state.get("discovery_result", {})
            projects = discovery.get("repos", [])

            results = []
            for project in projects:
                owner = project.get("owner", {}).get("login")
                repo = project.get("name")

                if owner and repo:
                    # Run single project workflow
                    workflow = self._custom_workflows.get("single_project")
                    if workflow:
                        final_state = await workflow.ainvoke({
                            "owner": owner,
                            "repo": repo,
                            "create_pr": state.get("create_pr", True),
                        })
                        results.append(final_state.get("result", {}))

            return {"project_results": results}

        async def finalize_batch_node(state: WorkflowState):
            """Finalize batch processing"""
            results = state.get("project_results", [])

            summary = {
                "success": True,
                "total_projects": len(results),
                "total_typos_found": sum(r.get("typos_found", 0) for r in results),
                "total_typos_fixed": sum(r.get("typos_fixed", 0) for r in results),
                "total_prs_created": sum(1 for r in results if r.get("pr_created")),
                "results": results,
            }

            return {"result": summary}

        graph.add_node("discover", discover_node)
        graph.add_node("process", process_projects_node)
        graph.add_node("finalize", finalize_batch_node)

        graph.add_edge(START, "discover")
        graph.add_edge("discover", "process")
        graph.add_edge("process", "finalize")
        graph.add_edge("finalize", END)

        self._custom_workflows["batch"] = graph.compile()

    def _build_scan_only_workflow(self):
        """Build scan-only workflow"""
        graph = StateGraph(WorkflowState)

        scan_skill = SkillRegistry.get("repository_scan")
        report_skill = SkillRegistry.get("typo_report")

        if scan_skill:
            graph.add_node("scan", SkillNodeWrapper(scan_skill, self))
        if report_skill:
            graph.add_node("report", SkillNodeWrapper(report_skill, self))

        graph.add_edge(START, "scan")
        graph.add_edge("scan", "report")
        graph.add_edge("report", END)

        self._custom_workflows["scan_only"] = graph.compile()

    async def process_task(self, task: Dict[str, Any]) -> Any:
        """
        Process tasks with skill support
        """
        task_type = task.get("type")

        if task_type == "run_single_project":
            return await self._run_single_project(task)

        if task_type == "run_batch":
            return await self._run_batch(task)

        if task_type == "run_scan_only":
            return await self._run_scan_only(task)

        if task_type == "get_capabilities":
            return await self._get_capabilities()

        # Fall back to skill-enabled processing
        return await super().process_task(task)

    async def _run_single_project(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Run single project workflow"""
        owner = task.get("owner")
        repo = task.get("repo")

        if not owner or not repo:
            return {"success": False, "error": "owner and repo required"}

        workflow = self._custom_workflows.get("single_project")
        if not workflow:
            return {"success": False, "error": "Single project workflow not available"}

        try:
            final_state = await workflow.ainvoke({
                "owner": owner,
                "repo": repo,
                "create_pr": task.get("create_pr", True),
                "repo_path": f"{self.work_dir}/{owner}/{repo}",
            })

            return final_state.get("result", {"success": False, "error": "No result"})

        except Exception as e:
            logger.error(f"Single project workflow failed: {e}")
            return {"success": False, "error": str(e)}

    async def _run_batch(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Run batch workflow"""
        workflow = self._custom_workflows.get("batch")
        if not workflow:
            return {"success": False, "error": "Batch workflow not available"}

        try:
            final_state = await workflow.ainvoke({
                "days": task.get("days", 30),
                "min_stars": task.get("min_stars", 100),
                "limit": task.get("limit", 5),
                "create_pr": task.get("create_pr", True),
            })

            return final_state.get("result", {"success": False, "error": "No result"})

        except Exception as e:
            logger.error(f"Batch workflow failed: {e}")
            return {"success": False, "error": str(e)}

    async def _run_scan_only(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Run scan-only workflow"""
        owner = task.get("owner")
        repo = task.get("repo")

        if not owner or not repo:
            return {"success": False, "error": "owner and repo required"}

        workflow = self._custom_workflows.get("scan_only")
        if not workflow:
            return {"success": False, "error": "Scan-only workflow not available"}

        try:
            final_state = await workflow.ainvoke({
                "owner": owner,
                "repo": repo,
                "repo_path": f"{self.work_dir}/{owner}/{repo}",
            })

            return final_state.get("result", {"success": False, "error": "No result"})

        except Exception as e:
            logger.error(f"Scan-only workflow failed: {e}")
            return {"success": False, "error": str(e)}

    async def _get_capabilities(self) -> Dict[str, Any]:
        """Get agent capabilities"""
        return {
            "success": True,
            "agent": {
                "name": self.config.name,
                "version": self.config.version,
                "type": "SkillCoordinatorAgent",
            },
            "workflows": list(self._custom_workflows.keys()),
            "skills": self.get_available_skills(),
            "features": {
                "langgraph": True,
                "skills": True,
                "memory": self.config.enable_memory,
                "dynamic_workflows": True,
            },
        }

    async def on_stop(self) -> None:
        """Stop sub-agents"""
        for agent in [
            self.discovery_agent, self.scanner_agent,
            self.quality_evaluator_agent, self.fixer_agent,
            self.decision_agent, self.pr_creator_agent,
            self.report_generator_agent
        ]:
            if agent:
                try:
                    await agent.stop()
                except Exception as e:
                    logger.warning(f"Failed to stop sub-agent: {e}")

        await super().on_stop()


# Export
__all__ = ["SkillCoordinatorAgent", "WorkflowState"]
