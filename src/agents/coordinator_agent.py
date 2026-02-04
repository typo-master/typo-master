"""
Coordinator Agent - Orchestrates the typo hunting workflow

This agent is responsible for coordinating all other agents and managing
the overall workflow of discovering projects, scanning for typos, fixing
them, and creating pull requests.
"""

import asyncio
from typing import Any, Dict, List, Optional
from datetime import datetime

from ..agent_framework.base_agent import BaseAgent, AgentConfig
from ..agent_framework.state_machine import StateMachine, State, Transition
from ..agent_framework.logger import get_logger

logger = get_logger(__name__)


class CoordinatorAgent(BaseAgent):
    """
    Coordinator agent that orchestrates the typo hunting workflow
    
    Responsibilities:
    - Coordinate between agents
    - Manage workflow state
    - Handle errors and retries
    - Track progress
    - Generate final reports
    """
    
    def __init__(self, github_token: Optional[str] = None):
        """
        Initialize coordinator agent
        
        Args:
            github_token: GitHub API token
        """
        config = AgentConfig(
            name="CoordinatorAgent",
            version="1.0.0",
            description="Orchestrates the typo hunting workflow",
            max_retries=3,
            timeout=3600.0,  # 1 hour timeout
        )
        
        super().__init__(config)
        self.github_token = github_token
        
        # Workflow state
        self.current_project: Optional[Dict[str, Any]] = None
        self.projects_processed: List[Dict[str, Any]] = []
        self.total_typos_fixed: int = 0
        self.total_prs_created: int = 0
        
        # Initialize state machine
        self._init_state_machine()
    
    def _init_state_machine(self) -> None:
        """Initialize the workflow state machine"""
        self.state_machine = StateMachine("idle")
        
        # Define states
        self.state_machine.add_state(State("idle"))
        self.state_machine.add_state(State("discovering"))
        self.state_machine.add_state(State("scanning"))
        self.state_machine.add_state(State("fixing"))
        self.state_machine.add_state(State("creating_pr"))
        self.state_machine.add_state(State("reporting"))
        self.state_machine.add_state(State("completed"))
        
        # Define transitions
        self.state_machine.add_transition(
            Transition("idle", "discovering", "start_workflow")
        )
        self.state_machine.add_transition(
            Transition("discovering", "scanning", "projects_found")
        )
        self.state_machine.add_transition(
            Transition("scanning", "fixing", "typos_found")
        )
        self.state_machine.add_transition(
            Transition("fixing", "creating_pr", "fixes_applied")
        )
        self.state_machine.add_transition(
            Transition("creating_pr", "reporting", "pr_created")
        )
        self.state_machine.add_transition(
            Transition("reporting", "completed", "report_generated")
        )
        self.state_machine.add_transition(
            Transition("creating_pr", "completed", "skip_pr")
        )
    
    async def on_initialize(self) -> None:
        """Initialize agent and register tools"""
        # Initialize state machine
        await self.state_machine.initialize()
        
        logger.info("Coordinator agent initialized")
    
    async def on_start(self) -> None:
        """Called when agent starts"""
        logger.info("Coordinator agent started")
    async def on_stop(self) -> None:
        """Called when agent stops"""
        logger.info("Coordinator agent stopped")
    
    async def on_pause(self) -> None:
        """Called when agent is paused"""
        logger.info("Coordinator agent paused")
    
    async def on_resume(self) -> None:
        """Called when agent resumes"""
        logger.info("Coordinator agent resumed")
    
    async def process_task(self, task: Any) -> Any:
        """
        Process a workflow task
        
        Args:
            task: Task to process
            
        Returns:
            Task result
        """
        task_type = task.get("type")
        
        if task_type == "run_workflow":
            return await self._run_workflow(task)
        elif task_type == "process_project":
            return await self._process_project(task)
        elif task_type == "get_status":
            return await self.get_status()
        else:
            logger.warning(f"Unknown task type: {task_type}")
            return {"error": f"Unknown task type: {task_type}"}
    
    async def _run_workflow(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        Run the complete workflow
        
        Args:
            task: Task parameters
            
        Returns:
            Workflow results
        """
        workflow_type = task.get("workflow", "single_project")
        
        logger.info(f"Starting workflow: {workflow_type}")
        
        # Trigger workflow start
        await self.state_machine.trigger_event("start_workflow")
        
        if workflow_type == "single_project":
            return await self._run_single_project_workflow(task)
        elif workflow_type == "batch_projects":
            return await self._run_batch_projects_workflow(task)
        else:
            return {"error": f"Unknown workflow type: {workflow_type}"}
    
    async def _run_single_project_workflow(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        Run workflow for a single project
        
        Args:
            task: Task parameters
            
        Returns:
            Workflow results
        """
        owner = task.get("owner")
        repo = task.get("repo")
        create_pr = task.get("create_pr", True)
        
        logger.info(f"Processing single project: {owner}/{repo}")
        
        # Discover project
        await self.state_machine.trigger_event("projects_found")
        
        # Scan for typos
        scan_result = await self._scan_project(owner, repo)
        
        if scan_result.get("total_typos", 0) == 0:
            logger.info(f"No typos found in {owner}/{repo}")
            return {
                "success": True,
                "typos_found": 0,
                "message": "No typos found",
            }
        
        await self.state_machine.trigger_event("typos_found")
        
        # Fix typos
        fix_result = await self._fix_typos(scan_result)
        
        if not fix_result.get("success"):
            return {"error": "Failed to fix typos"}
        
        await self.state_machine.trigger_event("fixes_applied")
        
        # Create PR if requested
        if create_pr:
            pr_result = await self._create_pr(owner, repo, scan_result, fix_result)
            
            if pr_result.get("success"):
                self.total_prs_created += 1
                await self.state_machine.trigger_event("pr_created")
            else:
                logger.warning(f"Failed to create PR: {pr_result.get('error')}")
                await self.state_machine.trigger_event("skip_pr")
        else:
            await self.state_machine.trigger_event("skip_pr")
        
        # Generate report
        report_result = await self._generate_report({
            "owner": owner,
            "repo": repo,
            "scan_result": scan_result,
            "fix_result": fix_result,
        })
        
        await self.state_machine.trigger_event("report_generated")
        
        return {
            "success": True,
            "typos_found": scan_result.get("total_typos", 0),
            "typos_fixed": fix_result.get("total_typos_fixed", 0),
            "pr_created": create_pr and pr_result.get("success", False),
        }
    
    async def _run_batch_projects_workflow(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        Run workflow for multiple projects
        
        Args:
            task: Task parameters
            
        Returns:
            Workflow results
        """
        days = task.get("days", 30)
        min_stars = task.get("min_stars", 100)
        limit = task.get("limit", 5)
        create_pr = task.get("create_pr", True)
        
        logger.info(f"Processing batch workflow (days={days}, stars>={min_stars}, limit={limit})")
        
        # Discover projects
        discovery_result = await self._discover_projects(days, min_stars, limit)
        
        if not discovery_result.get("success"):
            return {"error": "Failed to discover projects"}
        
        projects = discovery_result.get("projects", [])
        
        await self.state_machine.trigger_event("projects_found")
        
        # Process each project
        results = []
        for project in projects:
            try:
                result = await self._process_project({
                    "owner": project.get("owner"),
                    "repo": project.get("name"),
                    "create_pr": create_pr,
                })
                results.append(result)
            except Exception as e:
                logger.error(f"Error processing project: {e}")
        
        # Generate summary report
        summary = {
            "total_projects": len(projects),
            "projects_processed": len(results),
            "total_typos_found": sum(r.get("typos_found", 0) for r in results),
            "total_typos_fixed": sum(r.get("typos_fixed", 0) for r in results),
            "total_prs_created": sum(1 for r in results if r.get("pr_created")),
            "results": results,
        }
        
        return summary
    
    async def _process_project(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a single project
        
        Args:
            task: Task parameters
            
        Returns:
            Processing result
        """
        owner = task.get("owner")
        repo = task.get("repo")
        create_pr = task.get("create_pr", True)
        
        logger.info(f"Processing project: {owner}/{repo}")
        
        # Scan for typos
        scan_result = await self._scan_project(owner, repo)
        
        if scan_result.get("total_typos", 0) == 0:
            return {
                "owner": owner,
                "repo": repo,
                "typos_found": 0,
                "typos_fixed": 0,
                "pr_created": False,
            }
        
        # Fix typos
        fix_result = await self._fix_typos(scan_result)
        
        if not fix_result.get("success"):
            return {
                "owner": owner,
                "repo": repo,
                "typos_found": scan_result.get("total_typos", 0),
                "typos_fixed": 0,
                "pr_created": False,
                "error": "Failed to fix typos",
            }
        
        # Create PR if requested
        pr_created = False
        if create_pr:
            pr_result = await self._create_pr(owner, repo, scan_result, fix_result)
            pr_created = pr_result.get("success", False)
        
        return {
            "owner": owner,
            "repo": repo,
            "typos_found": scan_result.get("total_typos", 0),
            "typos_fixed": fix_result.get("total_typos_fixed", 0),
            "pr_created": pr_created,
        }
    
    async def _discover_projects(
        self,
        days: int,
        min_stars: int,
        limit: int,
    ) -> Dict[str, Any]:
        """
        Discover Web3 projects
        
        Args:
            days: Search days
            min_stars: Minimum stars
            limit: Result limit
            
        Returns:
            Discovery result
        """
        # This would call the ProjectDiscoveryAgent
        # For now, return mock data
        return {
            "success": True,
            "projects": [
                {
                    "owner": "example",
                    "name": "example-repo",
                    "stars": 100,
                }
            ] * limit,
        }
    
    async def _scan_project(self, owner: str, repo: str) -> Dict[str, Any]:
        """
        Scan a project for typos
        
        Args:
            owner: Repository owner
            repo: Repository name
            
        Returns:
            Scan result
        """
        # This would call the TypoScannerAgent
        # For now, return mock data
        return {
            "success": True,
            "total_typos": 5,
            "files_with_typos": 2,
        }
    
    async def _fix_typos(self, scan_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Fix typos in a project
        
        Args:
            scan_result: Scan result
            
        Returns:
            Fix result
        """
        # This would call the TypoFixerAgent
        # For now, return mock data
        return {
            "success": True,
            "total_typos_fixed": scan_result.get("total_typos", 0),
        }
    
    async def _create_pr(
        self,
        owner: str,
        repo: str,
        scan_result: Dict[str, Any],
        fix_result: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Create a pull request
        
        Args:
            owner: Repository owner
            repo: Repository name
            scan_result: Scan result
            fix_result: Fix result
            
        Returns:
            PR creation result
        """
        # This would call the PRCreatorAgent
        # For now, return mock data
        return {
            "success": True,
            "pr_number": 123,
            "pr_url": f"https://github.com/{owner}/{repo}/pull/123",
        }
    
    async def _generate_report(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate a report
        
        Args:
            data: Report data
            
        Returns:
            Report generation result
        """
        # This would call the ReportGeneratorAgent
        # For now, return mock data
        return {
            "success": True,
            "report_file": "report.md",
        }
