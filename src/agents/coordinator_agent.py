"""
Coordinator Agent - LangGraph-based workflow orchestrator.

This coordinator is the single orchestration implementation and uses LangGraph
to drive typo hunting workflows across discovery, scanning, quality validation,
fixing, PR decision, PR creation, and report generation.

Features:
- LangGraph Checkpoint persistence for workflow state
- Unified memory integration for cross-workflow learning
- Conversation history for context-aware decisions
"""

from typing import Any, Dict, List, Optional, TypedDict
from datetime import datetime

from langgraph.graph import END, START, StateGraph

from ..agent_framework.base_agent import AgentConfig, BaseAgent
from ..agent_framework.logger import get_logger
from ..agent_framework.unified_memory import UnifiedMemoryManager
from ..agent_framework.llm_client import OpenAICompatibleResponsesClient

logger = get_logger(__name__)


class SingleProjectWorkflowState(TypedDict, total=False):
    owner: str
    repo: str
    create_pr: bool
    project_info: Dict[str, Any]
    scan_result: Dict[str, Any]
    quality_result: Dict[str, Any]
    fix_result: Dict[str, Any]
    pr_decision: Dict[str, Any]
    pr_result: Dict[str, Any]
    report_result: Dict[str, Any]
    error: str
    result: Dict[str, Any]


class BatchWorkflowState(TypedDict, total=False):
    days: int
    min_stars: int
    limit: int
    create_pr: bool
    discovery_result: Dict[str, Any]
    projects: List[Dict[str, Any]]
    project_results: List[Dict[str, Any]]
    error: str
    result: Dict[str, Any]


class CoordinatorAgent(BaseAgent):
    """
    Coordinator agent that orchestrates typo hunting with LangGraph.

    Features:
    - Multi-layer memory (working, chroma, file)
    - Workflow checkpoint persistence
    - Cross-project learning
    """

    def __init__(self, github_token: Optional[str] = None, work_dir: Optional[str] = None, llm_client: Optional[OpenAICompatibleResponsesClient] = None):
        config = AgentConfig(
            name="CoordinatorAgent",
            version="1.2.0",
            description="LangGraph orchestrator with unified memory for typo hunting workflows",
            max_retries=3,
            timeout=3600.0,
            enable_memory=True,
            memory_backend="hybrid",
        )
        super().__init__(config)

        self.github_token = github_token
        self.work_dir = work_dir or "./work"
        self.llm_client = llm_client

        # Sub-agents (initialized in on_initialize)
        self.discovery_agent: Optional[Any] = None
        self.scanner_agent: Optional[Any] = None
        self.quality_evaluator_agent: Optional[Any] = None
        self.fixer_agent: Optional[Any] = None
        self.decision_agent: Optional[Any] = None
        self.pr_creator_agent: Optional[Any] = None
        self.report_generator_agent: Optional[Any] = None

        # New Phase 2 & 3 agents
        self.translator: Optional[Any] = None
        self.issue_analyzer: Optional[Any] = None
        self.contribution_evaluator: Optional[Any] = None

        # Compiled LangGraph workflows
        self.single_project_graph = None
        self.batch_projects_graph = None

        # Workflow execution history
        self.workflow_history: List[Dict[str, Any]] = []

    async def on_initialize(self) -> None:
        """Initialize sub-agents and compile LangGraph workflows."""
        from .decision_agent import DecisionAgent
        from .pr_creator_agent import PRCreatorAgent
        from .project_discovery_agent import ProjectDiscoveryAgent
        from .quality_evaluator_agent import QualityEvaluatorAgent
        from .report_generator_agent import ReportGeneratorAgent
        from .typo_fixer_agent import TypoFixerAgent
        from .typo_scanner_agent import TypoScannerAgent

        self.discovery_agent = ProjectDiscoveryAgent(github_token=self.github_token)
        self.scanner_agent = TypoScannerAgent()
        self.quality_evaluator_agent = QualityEvaluatorAgent()
        self.fixer_agent = TypoFixerAgent()
        self.decision_agent = DecisionAgent(llm_client=self.llm_client)
        self.pr_creator_agent = PRCreatorAgent(github_token=self.github_token)
        self.report_generator_agent = ReportGeneratorAgent()

        await self.discovery_agent.initialize()
        await self.scanner_agent.initialize()
        await self.quality_evaluator_agent.initialize()
        await self.fixer_agent.initialize()
        await self.decision_agent.initialize()
        await self.pr_creator_agent.initialize()
        await self.report_generator_agent.initialize()

        # Initialize new Phase 2 & 3 agents
        from ..web3_typo_hunter.translator.document_translator import DocumentTranslator
        from ..web3_typo_hunter.issue_finder.issue_analyzer import IssueAnalyzer
        from ..web3_typo_hunter.issue_finder.contribution_evaluator import ContributionEvaluator

        self.translator = DocumentTranslator(llm_client=self.llm_client)
        self.issue_analyzer = IssueAnalyzer(
            github_api=self.discovery_agent.github_api if self.discovery_agent else None,
            llm_client=self.llm_client
        )
        self.contribution_evaluator = ContributionEvaluator(llm_client=self.llm_client)

        # Build graphs with checkpoint support
        self.single_project_graph = self._build_single_project_graph()
        self.batch_projects_graph = self._build_batch_projects_graph()

        # Load past workflow history from memory
        await self._load_workflow_history()

        logger.info("Coordinator agent initialized with memory support")

    async def _load_workflow_history(self) -> None:
        """Load past workflow executions from memory"""
        try:
            experiences = await self.memory_manager.get_similar_experiences("workflow", limit=20)
            for exp in experiences:
                if exp.metadata and "result" in exp.metadata:
                    self.workflow_history.append(exp.metadata)
            logger.info(f"Loaded {len(self.workflow_history)} past workflows from memory")
        except Exception as e:
            logger.warning(f"Failed to load workflow history: {e}")

    async def on_start(self) -> None:
        logger.info("Coordinator agent started")

    async def on_stop(self) -> None:
        # Gracefully stop child agents that were initialized directly by coordinator.
        await self._stop_sub_agent(self.discovery_agent)
        await self._stop_sub_agent(self.scanner_agent)
        await self._stop_sub_agent(self.quality_evaluator_agent)
        await self._stop_sub_agent(self.fixer_agent)
        await self._stop_sub_agent(self.decision_agent)
        await self._stop_sub_agent(self.pr_creator_agent)
        await self._stop_sub_agent(self.report_generator_agent)
        logger.info("Coordinator agent stopped")

    async def on_pause(self) -> None:
        logger.info("Coordinator agent paused")

    async def on_resume(self) -> None:
        logger.info("Coordinator agent resumed")

    async def process_task(self, task: Any) -> Any:
        """
        Process workflow tasks.
        """
        task_type = task.get("type")
        if task_type == "run_workflow":
            return await self._run_workflow(task)
        if task_type == "process_project":
            return await self._process_project(task)
        if task_type == "get_status":
            return await self.get_status()
        if task_type == "get_capabilities":
            return await self.get_capabilities()
        # New Phase 2 & 3 task types
        if task_type == "translate_document":
            return await self._translate_document_task(task)
        if task_type == "find_issues":
            return await self._find_issues_task(task)
        if task_type == "batch_find_contributions":
            return await self._batch_find_contributions_task(task)
        logger.warning(f"Unknown task type: {task_type}")
        return {"success": False, "error": f"Unknown task type: {task_type}"}

    async def get_capabilities(self) -> Dict[str, Any]:
        """
        Return coordinator capabilities and readiness signals.
        """
        llm_enabled = False
        llm_model = None
        if self.decision_agent and getattr(self.decision_agent, "llm_client", None):
            llm_enabled = bool(getattr(self.decision_agent, "llm_enabled", False))
            llm_model = self.decision_agent.llm_client.config.model if llm_enabled else None

        return {
            "success": True,
            "framework": "LangGraph",
            "workflows": {
                "single_project": True,
                "batch_projects": True,
                "document_translation": self.translator is not None,
                "issue_discovery": self.issue_analyzer is not None,
                "contribution_evaluation": self.contribution_evaluator is not None,
            },
            "pipeline_nodes": [
                "scan_project",
                "evaluate_quality",
                "fix_typos",
                "decide_pr",
                "create_pull_request",
                "generate_report",
            ],
            "features": {
                "project_discovery": True,
                "typo_scan": True,
                "quality_evaluation": True,
                "typo_fix": True,
                "pr_decision": True,
                "pr_creation": True,
                "report_generation": True,
                "llm_decision_support": llm_enabled,
                "document_translation": self.translator is not None,
                "issue_discovery": self.issue_analyzer is not None,
                "contribution_evaluation": self.contribution_evaluator is not None,
            },
            "llm": {
                "enabled": llm_enabled,
                "model": llm_model,
            },
            "limitations": [
                "Pycorrector backend may return empty results if kenlm/model assets are missing",
                "GitHub API rate limits apply when scanning/discovery at scale",
            ],
        }

    async def _run_workflow(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Run a workflow using LangGraph."""
        workflow_type = task.get("workflow", "single_project")
        logger.info(f"Starting LangGraph workflow: {workflow_type}")

        if workflow_type == "single_project":
            return await self._run_single_project_workflow(task)
        if workflow_type == "batch_projects":
            return await self._run_batch_projects_workflow(task)
        return {"success": False, "error": f"Unknown workflow type: {workflow_type}"}

    async def _run_single_project_workflow(self, task: Dict[str, Any]) -> Dict[str, Any]:
        owner = task.get("owner")
        repo = task.get("repo")
        create_pr = task.get("create_pr", True)

        if not owner or not repo:
            return {"success": False, "error": "owner and repo are required"}
        if not self.single_project_graph:
            return {"success": False, "error": "Single project graph is not initialized"}

        final_state = await self.single_project_graph.ainvoke({
            "owner": owner,
            "repo": repo,
            "create_pr": create_pr,
        })
        result = final_state.get("result")
        if isinstance(result, dict):
            return result
        return {"success": False, "error": "Single project workflow finished without result"}

    async def _run_batch_projects_workflow(self, task: Dict[str, Any]) -> Dict[str, Any]:
        if not self.batch_projects_graph:
            return {"success": False, "error": "Batch projects graph is not initialized"}

        final_state = await self.batch_projects_graph.ainvoke({
            "days": task.get("days", 30),
            "min_stars": task.get("min_stars", 100),
            "limit": task.get("limit", 5),
            "create_pr": task.get("create_pr", True),
        })
        result = final_state.get("result")
        if isinstance(result, dict):
            return result
        return {"success": False, "error": "Batch workflow finished without result"}

    async def _process_project(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Compatibility task API for single project processing."""
        result = await self._run_single_project_workflow(task)
        if isinstance(result, dict):
            result.setdefault("owner", task.get("owner", ""))
            result.setdefault("repo", task.get("repo", ""))
        return result

    def _build_single_project_graph(self):
        graph = StateGraph(SingleProjectWorkflowState)
        graph.add_node("scan_project", self._node_scan_project)
        graph.add_node("evaluate_quality", self._node_evaluate_quality)
        graph.add_node("fix_typos", self._node_fix_typos)
        graph.add_node("decide_pr", self._node_decide_pr)
        graph.add_node("create_pull_request", self._node_create_pr)
        graph.add_node("generate_report", self._node_generate_report)
        graph.add_node("finalize", self._node_finalize_single_project)

        graph.add_edge(START, "scan_project")
        graph.add_conditional_edges(
            "scan_project",
            self._route_after_scan,
            {
                "evaluate_quality": "evaluate_quality",
                "finalize": "finalize",
            },
        )
        graph.add_edge("evaluate_quality", "fix_typos")
        graph.add_conditional_edges(
            "fix_typos",
            self._route_after_fix,
            {
                "decide_pr": "decide_pr",
                "generate_report": "generate_report",
                "finalize": "finalize",
            },
        )
        graph.add_conditional_edges(
            "decide_pr",
            self._route_after_decision,
            {
                "create_pull_request": "create_pull_request",
                "generate_report": "generate_report",
            },
        )
        graph.add_edge("create_pull_request", "generate_report")
        graph.add_edge("generate_report", "finalize")
        graph.add_edge("finalize", END)
        return graph.compile()

    def _build_batch_projects_graph(self):
        graph = StateGraph(BatchWorkflowState)
        graph.add_node("discover_projects", self._node_discover_projects)
        graph.add_node("process_projects", self._node_process_projects)
        graph.add_node("finalize_batch", self._node_finalize_batch)

        graph.add_edge(START, "discover_projects")
        graph.add_conditional_edges(
            "discover_projects",
            self._route_after_discovery,
            {
                "process_projects": "process_projects",
                "finalize_batch": "finalize_batch",
            },
        )
        graph.add_edge("process_projects", "finalize_batch")
        graph.add_edge("finalize_batch", END)
        return graph.compile()

    async def _node_scan_project(self, state: SingleProjectWorkflowState) -> Dict[str, Any]:
        owner = state.get("owner", "")
        repo = state.get("repo", "")
        scan_result = await self._scan_project(owner, repo)
        update: Dict[str, Any] = {"scan_result": scan_result}
        if not scan_result.get("success", False):
            update["error"] = scan_result.get("error", "Failed to scan project")
            return update

        project_info = await self._get_project_info(owner, repo)
        if project_info:
            update["project_info"] = project_info
        return update

    async def _node_evaluate_quality(self, state: SingleProjectWorkflowState) -> Dict[str, Any]:
        scan_result = state.get("scan_result", {})
        quality_result = await self._evaluate_scan_quality(scan_result)
        return {"quality_result": quality_result}

    async def _node_fix_typos(self, state: SingleProjectWorkflowState) -> Dict[str, Any]:
        quality_result = state.get("quality_result", {})
        scan_result = state.get("scan_result", {})

        # Prefer quality-filtered typo candidates; fallback to original scan output.
        refined_results = quality_result.get("refined_detailed_results")
        if isinstance(refined_results, list):
            scan_result = dict(scan_result)
            scan_result["detailed_results"] = refined_results
            scan_result["total_typos"] = sum(
                len(item.get("typos", [])) for item in refined_results if isinstance(item, dict)
            )

        fix_result = await self._fix_typos(scan_result)
        update: Dict[str, Any] = {"fix_result": fix_result}
        if not fix_result.get("success", False):
            update["error"] = fix_result.get("error", "Failed to fix typos")
        return update

    async def _node_decide_pr(self, state: SingleProjectWorkflowState) -> Dict[str, Any]:
        decision = await self._decide_pr(state)
        return {"pr_decision": decision}

    async def _node_create_pr(self, state: SingleProjectWorkflowState) -> Dict[str, Any]:
        pr_result = await self._create_pr(
            state.get("owner", ""),
            state.get("repo", ""),
            state.get("scan_result", {}),
            state.get("fix_result", {}),
        )
        return {"pr_result": pr_result}

    async def _node_generate_report(self, state: SingleProjectWorkflowState) -> Dict[str, Any]:
        report_result = await self._generate_report({
            "owner": state.get("owner", ""),
            "repo": state.get("repo", ""),
            "scan_result": state.get("scan_result", {}),
            "quality_result": state.get("quality_result", {}),
            "fix_result": state.get("fix_result", {}),
            "pr_decision": state.get("pr_decision", {}),
            "pr_result": state.get("pr_result", {}),
        })
        return {"report_result": report_result}

    async def _node_finalize_single_project(self, state: SingleProjectWorkflowState) -> Dict[str, Any]:
        scan_result = state.get("scan_result", {})
        fix_result = state.get("fix_result", {})
        pr_result = state.get("pr_result", {})
        pr_decision = state.get("pr_decision", {})
        quality_result = state.get("quality_result", {})
        owner = state.get("owner", "")
        repo = state.get("repo", "")

        # Build result
        if state.get("error"):
            result = {
                "success": False,
                "error": state["error"],
                "typos_found": scan_result.get("total_typos", 0),
                "typos_fixed": fix_result.get("total_typos_fixed", 0),
                "pr_created": pr_result.get("success", False),
                "owner": owner,
                "repo": repo,
            }
        elif scan_result.get("total_typos", 0) <= 0:
            result = {
                "success": True,
                "typos_found": 0,
                "typos_fixed": 0,
                "pr_created": False,
                "message": "No typos found",
                "owner": owner,
                "repo": repo,
            }
        else:
            result = {
                "success": True,
                "typos_found": scan_result.get("total_typos", 0),
                "typos_fixed": fix_result.get("total_typos_fixed", 0),
                "quality_score": quality_result.get("average_quality_score"),
                "pr_created": bool(pr_result.get("success", False)),
                "pr_decision": pr_decision,
                "owner": owner,
                "repo": repo,
            }

        # Record to memory for learning
        if self.config.enable_memory and result["success"]:
            try:
                await self.memory_manager.remember_experience(
                    task_type="single_project_workflow",
                    input_data={"owner": owner, "repo": repo},
                    result=result,
                    success=result["success"] and not result.get("error")
                )

                # Also remember project info if successful
                if result.get("typos_found", 0) > 0:
                    await self.memory_manager.remember_knowledge(
                        key=f"project:{owner}/{repo}",
                        value={
                            "typos_found": result["typos_found"],
                            "quality_score": result.get("quality_score"),
                            "pr_created": result.get("pr_created"),
                            "timestamp": datetime.now().isoformat(),
                        },
                        importance=0.8 if result.get("pr_created") else 0.5
                    )
            except Exception as e:
                logger.warning(f"Failed to record workflow memory: {e}")

        # Add to workflow history
        self.workflow_history.append({
            "timestamp": datetime.now().isoformat(),
            "owner": owner,
            "repo": repo,
            "result": result,
        })

        return {"result": result}

    async def _node_discover_projects(self, state: BatchWorkflowState) -> Dict[str, Any]:
        discovery_result = await self._discover_projects(
            days=state.get("days", 30),
            min_stars=state.get("min_stars", 100),
            limit=state.get("limit", 5),
        )
        update: Dict[str, Any] = {
            "discovery_result": discovery_result,
            "projects": discovery_result.get("projects", []),
        }
        if not discovery_result.get("success", False):
            update["error"] = discovery_result.get("error", "Failed to discover projects")
        return update

    async def _node_process_projects(self, state: BatchWorkflowState) -> Dict[str, Any]:
        projects = state.get("projects", [])
        create_pr = state.get("create_pr", True)
        results: List[Dict[str, Any]] = []

        for project in projects:
            owner = project.get("owner")
            repo = project.get("name")
            if not owner or not repo:
                continue

            final_state = await self.single_project_graph.ainvoke({
                "owner": owner,
                "repo": repo,
                "create_pr": create_pr,
            })
            project_result = final_state.get("result", {"success": False, "error": "Missing project result"})
            if isinstance(project_result, dict):
                project_result.setdefault("owner", owner)
                project_result.setdefault("repo", repo)
            results.append(project_result)

        return {"project_results": results}

    async def _node_finalize_batch(self, state: BatchWorkflowState) -> Dict[str, Any]:
        if state.get("error"):
            return {
                "result": {
                    "success": False,
                    "error": state["error"],
                    "total_projects": 0,
                    "projects_processed": 0,
                    "total_typos_found": 0,
                    "total_typos_fixed": 0,
                    "total_prs_created": 0,
                    "results": [],
                }
            }

        projects = state.get("projects", [])
        results = state.get("project_results", [])
        summary = {
            "success": True,
            "total_projects": len(projects),
            "projects_processed": len(results),
            "total_typos_found": sum(r.get("typos_found", 0) for r in results if isinstance(r, dict)),
            "total_typos_fixed": sum(r.get("typos_fixed", 0) for r in results if isinstance(r, dict)),
            "total_prs_created": sum(1 for r in results if isinstance(r, dict) and r.get("pr_created")),
            "results": results,
        }
        return {"result": summary}

    def _route_after_scan(self, state: SingleProjectWorkflowState) -> str:
        if state.get("error"):
            return "finalize"
        if state.get("scan_result", {}).get("total_typos", 0) <= 0:
            return "finalize"
        return "evaluate_quality"

    def _route_after_fix(self, state: SingleProjectWorkflowState) -> str:
        if state.get("error"):
            return "finalize"

        fix_result = state.get("fix_result", {})
        if not fix_result.get("success", False):
            return "finalize"
        if fix_result.get("total_typos_fixed", 0) <= 0:
            return "generate_report"
        return "decide_pr"

    def _route_after_decision(self, state: SingleProjectWorkflowState) -> str:
        decision = state.get("pr_decision", {})
        if decision.get("should_create_pr"):
            return "create_pull_request"
        return "generate_report"

    def _route_after_discovery(self, state: BatchWorkflowState) -> str:
        if state.get("error"):
            return "finalize_batch"
        return "process_projects"

    async def _discover_projects(self, days: int, min_stars: int, limit: int) -> Dict[str, Any]:
        if not self.discovery_agent:
            return {"success": False, "error": "Discovery agent not initialized"}

        logger.info(f"Discovering Web3 projects (days={days}, stars>={min_stars}, limit={limit})")
        try:
            result = await self.discovery_agent.process_task({
                "type": "search_projects",
                "days": days,
                "min_stars": min_stars,
                "limit": limit,
            })

            if "error" in result:
                return {"success": False, "error": result["error"]}

            repos = result.get("repos", [])
            projects = []
            for repo in repos:
                projects.append({
                    "owner": repo.get("owner", {}).get("login", ""),
                    "name": repo.get("name", ""),
                    "stars": repo.get("stargazers_count", 0),
                    "full_name": repo.get("full_name", ""),
                    "description": repo.get("description", ""),
                    "url": repo.get("html_url", ""),
                })

            return {"success": True, "projects": projects, "count": len(projects)}
        except Exception as exc:
            logger.error(f"Error in project discovery: {exc}")
            return {"success": False, "error": str(exc)}

    async def _get_project_info(self, owner: str, repo: str) -> Dict[str, Any]:
        """
        Try to enrich state with project metadata for PR decisioning.
        """
        if not self.discovery_agent:
            return {}
        try:
            result = await self.discovery_agent.process_task({
                "type": "analyze_project",
                "owner": owner,
                "repo": repo,
            })
            if isinstance(result, dict) and "error" not in result:
                return result
        except Exception as exc:
            logger.warning(f"Project info analysis failed for {owner}/{repo}: {exc}")
        return {}

    async def _scan_project(self, owner: str, repo: str) -> Dict[str, Any]:
        if not self.scanner_agent:
            return {"success": False, "error": "Scanner agent not initialized"}

        repo_path = f"{self.work_dir}/{owner}/{repo}"
        repo_url = f"https://github.com/{owner}/{repo}.git"
        logger.info(f"Scanning project: {owner}/{repo}")

        try:
            from ..tools.file_tools import file_exists
            from ..tools.git_tools import git_clone

            clone_needed = not await file_exists(f"{repo_path}/.git")
            if clone_needed:
                logger.info(f"Cloning repository: {repo_url}")
                clone_result = await git_clone(repo_url, repo_path)
                logger.info(f"Repository cloned to: {clone_result}")
            else:
                logger.info(f"Using existing repository at: {repo_path}")

            scan_result = await self.scanner_agent.process_task({
                "type": "scan_repo",
                "repo_path": repo_path,
            })
            if "error" in scan_result:
                return {"success": False, "error": scan_result["error"]}

            results = scan_result.get("results", [])
            typos_list = []
            for file_result in results:
                file_path = file_result.get("file_path", "")
                for typo in file_result.get("typos", []):
                    typos_list.append({
                        "file": file_path,
                        "typo": typo.get("typo", ""),
                        "correction": typo.get("correction", ""),
                    })

            return {
                "success": True,
                "total_typos": scan_result.get("total_typos", 0),
                "files_with_typos": scan_result.get("files_with_typos", 0),
                "repo_path": repo_path,
                "typos_list": typos_list,
                "detailed_results": results,
            }
        except Exception as exc:
            logger.error(f"Error scanning project: {exc}")
            return {"success": False, "error": str(exc)}

    async def _evaluate_scan_quality(self, scan_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Evaluate typo suggestions before applying fixes.
        """
        if not self.quality_evaluator_agent:
            return {"success": False, "error": "Quality evaluator agent not initialized"}

        detailed_results = scan_result.get("detailed_results", [])
        if not detailed_results:
            return {
                "success": True,
                "average_quality_score": 1.0,
                "files_evaluated": 0,
                "refined_detailed_results": [],
            }

        evaluated_files = []
        refined_detailed_results = []
        total_score = 0.0
        score_count = 0

        for file_result in detailed_results:
            file_path = file_result.get("file_path")
            typos = file_result.get("typos", [])
            if not file_path or not typos:
                continue

            evaluation = await self.quality_evaluator_agent.process_task({
                "type": "evaluate_fixes",
                "file_path": file_path,
                "typos": typos,
            })
            if isinstance(evaluation, dict):
                evaluated_files.append({
                    "file_path": file_path,
                    "quality_score": evaluation.get("quality_score", 0.0),
                    "quality_acceptable": evaluation.get("quality_acceptable", False),
                    "passed_typos": evaluation.get("passed_typos", 0),
                    "total_typos": evaluation.get("total_typos", 0),
                })
                total_score += float(evaluation.get("quality_score", 0.0))
                score_count += 1

                refined_detailed_results.append({
                    "file_path": file_path,
                    "typos": evaluation.get("evaluated_typos", []),
                })

        average_quality_score = (total_score / score_count) if score_count else 0.0
        return {
            "success": True,
            "average_quality_score": round(average_quality_score, 4),
            "files_evaluated": len(evaluated_files),
            "file_evaluations": evaluated_files,
            "refined_detailed_results": refined_detailed_results,
        }

    async def _fix_typos(self, scan_result: Dict[str, Any]) -> Dict[str, Any]:
        if not self.fixer_agent:
            return {"success": False, "error": "Fixer agent not initialized"}

        detailed_results = scan_result.get("detailed_results", [])
        if not detailed_results:
            return {"success": True, "total_typos_fixed": 0, "files_fixed": 0}

        try:
            files_to_fix = []
            for file_result in detailed_results:
                file_path = file_result.get("file_path", "")
                typos = file_result.get("typos", [])
                if file_path and typos:
                    files_to_fix.append({"file_path": file_path, "typos": typos})

            if not files_to_fix:
                return {"success": True, "total_typos_fixed": 0, "files_fixed": 0}

            fix_result = await self.fixer_agent.process_task({
                "type": "fix_files",
                "files": files_to_fix,
            })
            if "error" in fix_result:
                return {"success": False, "error": fix_result["error"]}

            return {
                "success": True,
                "total_typos_fixed": fix_result.get("total_typos_fixed", 0),
                "files_fixed": fix_result.get("files_fixed", 0),
                "fix_results": fix_result.get("results", []),
            }
        except Exception as exc:
            logger.error(f"Error fixing typos: {exc}")
            return {"success": False, "error": str(exc)}

    async def _decide_pr(self, state: SingleProjectWorkflowState) -> Dict[str, Any]:
        """
        Decide whether PR should be created for this workflow run.
        """
        if not state.get("create_pr", True):
            return {
                "should_create_pr": False,
                "reason": "create_pr flag is disabled",
                "source": "workflow_input",
            }

        fix_result = state.get("fix_result", {})
        if fix_result.get("total_typos_fixed", 0) <= 0:
            return {
                "should_create_pr": False,
                "reason": "No applied fixes",
                "source": "workflow_state",
            }

        if not self.decision_agent:
            return {
                "should_create_pr": True,
                "reason": "Decision agent unavailable; default allow",
                "source": "fallback",
            }

        project_info = state.get("project_info", {})
        quality_result = state.get("quality_result", {})
        scan_result = state.get("scan_result", {})

        stars = int(project_info.get("stars", 100) or 100)
        acceptance_rate = float(project_info.get("acceptance_rate", 0.0) or 0.0)
        recent_prs = int(project_info.get("recent_prs", 0) or 0)
        activity_score = min(100, int(acceptance_rate * 100) + recent_prs * 2)

        decision = await self.decision_agent.process_task({
            "type": "should_create_pr",
            "project": {
                "stars": stars,
                "activity_score": activity_score,
            },
            "typos_found": scan_result.get("total_typos", 0),
            "quality_score": quality_result.get("average_quality_score", 0.0),
        })

        should_create = bool(decision.get("should_create", False))
        return {
            "should_create_pr": should_create,
            "reason": "DecisionAgent approval" if should_create else "; ".join(decision.get("reasons", [])),
            "source": "decision_agent",
            "factors": decision.get("factors", {}),
        }

    async def _create_pr(
        self,
        owner: str,
        repo: str,
        scan_result: Dict[str, Any],
        fix_result: Dict[str, Any],
    ) -> Dict[str, Any]:
        if not self.pr_creator_agent:
            return {"success": False, "error": "PR creator agent not initialized"}

        repo_path = scan_result.get("repo_path", "")
        fix_results = fix_result.get("fix_results", [])
        if not fix_results:
            return {"success": False, "error": "No changes to submit"}

        try:
            changes = []
            for fix in fix_results:
                file_path = fix.get("file_path", "")
                typos_fixed = fix.get("typos_fixed", 0)
                if file_path and typos_fixed > 0:
                    changes.append({"file": file_path, "typos": typos_fixed})

            pr_result = await self.pr_creator_agent.process_task({
                "type": "create_pr",
                "owner": owner,
                "repo": repo,
                "repo_path": repo_path,
                "changes": changes,
            })
            if "error" in pr_result:
                return {"success": False, "error": pr_result["error"]}

            return {
                "success": True,
                "pr_number": pr_result.get("pr_number"),
                "pr_url": pr_result.get("pr_url"),
            }
        except Exception as exc:
            logger.error(f"Error creating PR: {exc}")
            return {"success": False, "error": str(exc)}

    async def _generate_report(self, data: Dict[str, Any]) -> Dict[str, Any]:
        if not self.report_generator_agent:
            return {"success": False, "error": "Report generator agent not initialized"}

        owner = data.get("owner", "")
        repo = data.get("repo", "")
        scan_result = data.get("scan_result", {})
        quality_result = data.get("quality_result", {})
        fix_result = data.get("fix_result", {})
        pr_decision = data.get("pr_decision", {})
        pr_result = data.get("pr_result", {})

        try:
            report_data = {
                "project": f"{owner}/{repo}",
                "scan_summary": {
                    "total_typos": scan_result.get("total_typos", 0),
                    "files_with_typos": scan_result.get("files_with_typos", 0),
                },
                "quality_summary": {
                    "average_quality_score": quality_result.get("average_quality_score"),
                    "files_evaluated": quality_result.get("files_evaluated"),
                },
                "fix_summary": {
                    "total_typos_fixed": fix_result.get("total_typos_fixed", 0),
                    "files_fixed": fix_result.get("files_fixed", 0),
                },
                "pr_summary": {
                    "should_create_pr": pr_decision.get("should_create_pr"),
                    "decision_reason": pr_decision.get("reason"),
                    "pr_created": pr_result.get("success", False),
                    "pr_number": pr_result.get("pr_number"),
                    "pr_url": pr_result.get("pr_url"),
                },
                "typos_list": scan_result.get("typos_list", []),
            }

            report_result = await self.report_generator_agent.process_task({
                "type": "generate_typo_fix_report",
                "results": [report_data],
                "output_file": f"{self.work_dir}/{owner}_{repo}_report.md",
            })
            if "error" in report_result:
                return {"success": False, "error": report_result["error"]}

            return {"success": True, "report_file": report_result.get("output_file", "")}
        except Exception as exc:
            logger.error(f"Error generating report: {exc}")
            return {"success": False, "error": str(exc)}

    async def _stop_sub_agent(self, agent: Optional[Any]) -> None:
        """Best-effort stop for a child agent instance."""
        if not agent:
            return
        try:
            await agent.stop()
        except Exception as exc:
            logger.warning(f"Failed to stop sub-agent cleanly: {exc}")

    # =========================================================================
    # Phase 2 & 3 New Task Handlers
    # =========================================================================

    async def _translate_document_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Handle document translation task."""
        repo = task.get("repo")
        target_lang = task.get("target_lang", "zh")

        if not repo:
            return {"success": False, "error": "repo is required"}

        if not self.translator:
            return {"success": False, "error": "Translator not initialized"}

        try:
            from ..web3_typo_hunter.utils.github_api import GitHubAPI
            github_api = GitHubAPI(self.github_token)

            result = await self.translator.translate_repo_readme(
                repo_full_name=repo,
                github_api=github_api,
                target_lang=target_lang
            )

            return result
        except Exception as exc:
            logger.error(f"Error translating document: {exc}")
            return {"success": False, "error": str(exc)}

    async def _find_issues_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Handle find issues task."""
        repo = task.get("repo")
        limit = task.get("limit", 30)

        if not repo:
            return {"success": False, "error": "repo is required"}

        if not self.issue_analyzer:
            return {"success": False, "error": "Issue analyzer not initialized"}

        try:
            issues = await self.issue_analyzer.fetch_and_analyze_issues(
                repo_full_name=repo,
                limit=limit
            )

            return {
                "success": True,
                "repo": repo,
                "issues": issues,
                "count": len(issues)
            }
        except Exception as exc:
            logger.error(f"Error finding issues: {exc}")
            return {"success": False, "error": str(exc)}

    async def _batch_find_contributions_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Handle batch find contributions task."""
        repos = task.get("repos", [])
        limit = task.get("limit", 10)

        if not repos:
            return {"success": False, "error": "repos list is required"}

        opportunities = []

        for repo in repos:
            try:
                # Get repo info
                from ..web3_typo_hunter.utils.github_api import GitHubAPI
                github_api = GitHubAPI(self.github_token)
                repo_data = await github_api.get_repo(repo)

                # Fetch and analyze issues
                issues = await self.issue_analyzer.fetch_and_analyze_issues(
                    repo_full_name=repo,
                    limit=limit
                )

                # Evaluate each issue
                for issue in issues:
                    if issue.get("recommended"):
                        opportunity = self.contribution_evaluator.evaluate_contribution_opportunity(
                            repo_data=repo_data,
                            issue=issue
                        )
                        opportunities.append(opportunity)

            except Exception as exc:
                logger.error(f"Error processing repo {repo}: {exc}")
                continue

        # Sort opportunities
        ranked_opportunities = self.contribution_evaluator.rank_opportunities(opportunities)

        return {
            "success": True,
            "opportunities": ranked_opportunities[:20],  # Return top 20
            "total": len(ranked_opportunities)
        }

    # Helper methods for testing/mocking
    def _get_translator(self):
        return self.translator

    def _get_issue_analyzer(self):
        return self.issue_analyzer

    def _get_contribution_evaluator(self):
        return self.contribution_evaluator
