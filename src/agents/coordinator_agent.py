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
    
    def __init__(self, github_token: Optional[str] = None, work_dir: Optional[str] = None):
        """
        Initialize coordinator agent
        
        Args:
            github_token: GitHub API token
            work_dir: Working directory for cloning repositories
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
        self.work_dir = work_dir or "./work"
        
        # Workflow state
        self.current_project: Optional[Dict[str, Any]] = None
        self.projects_processed: List[Dict[str, Any]] = []
        self.total_typos_fixed: int = 0
        self.total_prs_created: int = 0
        
        # Sub-agents (initialized in on_initialize)
        self.discovery_agent: Optional[Any] = None
        self.scanner_agent: Optional[Any] = None
        self.fixer_agent: Optional[Any] = None
        self.pr_creator_agent: Optional[Any] = None
        self.report_generator_agent: Optional[Any] = None
        
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
        # Import and initialize sub-agents
        from .project_discovery_agent import ProjectDiscoveryAgent
        from .typo_scanner_agent import TypoScannerAgent
        from .typo_fixer_agent import TypoFixerAgent
        from .pr_creator_agent import PRCreatorAgent
        from .report_generator_agent import ReportGeneratorAgent
        
        self.discovery_agent = ProjectDiscoveryAgent(github_token=self.github_token)
        self.scanner_agent = TypoScannerAgent()
        self.fixer_agent = TypoFixerAgent()
        self.pr_creator_agent = PRCreatorAgent(github_token=self.github_token)
        self.report_generator_agent = ReportGeneratorAgent()
        
        # Initialize all sub-agents
        await self.discovery_agent.initialize()
        await self.scanner_agent.initialize()
        await self.fixer_agent.initialize()
        await self.pr_creator_agent.initialize()
        await self.report_generator_agent.initialize()
        
        # Initialize state machine
        await self.state_machine.initialize()
        
        logger.info("Coordinator agent initialized with sub-agents")
    
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
        Discover Web3 projects using ProjectDiscoveryAgent
        
        Args:
            days: Search days
            min_stars: Minimum stars
            limit: Result limit
            
        Returns:
            Discovery result
        """
        if not self.discovery_agent:
            return {"error": "Discovery agent not initialized"}
        
        logger.info(f"Discovering Web3 projects (days={days}, stars>={min_stars}, limit={limit})")
        
        try:
            result = await self.discovery_agent.process_task({
                "type": "search_projects",
                "days": days,
                "min_stars": min_stars,
                "limit": limit,
            })
            
            if "error" in result:
                logger.error(f"Project discovery failed: {result['error']}")
                return {"success": False, "error": result["error"]}
            
            # Transform repos to projects format
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
            
            logger.info(f"Discovered {len(projects)} Web3 projects")
            
            return {
                "success": True,
                "projects": projects,
                "count": len(projects),
            }
        
        except Exception as e:
            logger.error(f"Error in project discovery: {e}")
            return {"success": False, "error": str(e)}
    
    async def _scan_project(self, owner: str, repo: str) -> Dict[str, Any]:
        """
        Scan a project for typos using TypoScannerAgent
        
        Args:
            owner: Repository owner
            repo: Repository name
            
        Returns:
            Scan result
        """
        if not self.scanner_agent:
            return {"error": "Scanner agent not initialized"}
        
        repo_path = f"{self.work_dir}/{owner}/{repo}"
        repo_url = f"https://github.com/{owner}/{repo}.git"
        
        logger.info(f"Scanning project: {owner}/{repo}")
        
        try:
            # Clone repository using git_tools
            from ..tools.git_tools import git_clone
            from ..tools.file_tools import file_exists
            
            # Check if already cloned
            clone_needed = not await file_exists(f"{repo_path}/.git")
            
            if clone_needed:
                logger.info(f"Cloning repository: {repo_url}")
                clone_result = await git_clone(repo_url, repo_path)
                logger.info(f"Repository cloned to: {clone_result}")
            else:
                logger.info(f"Using existing repository at: {repo_path}")
            
            # Scan the repository
            scan_result = await self.scanner_agent.process_task({
                "type": "scan_repo",
                "repo_path": repo_path,
            })
            
            if "error" in scan_result:
                logger.error(f"Scan failed: {scan_result['error']}")
                return {"success": False, "error": scan_result["error"]}
            
            # Transform results to expected format
            total_typos = scan_result.get("total_typos", 0)
            files_with_typos = scan_result.get("files_with_typos", 0)
            results = scan_result.get("results", [])
            
            # Prepare detailed typo list
            typos_list = []
            for file_result in results:
                file_path = file_result.get("file_path", "")
                typos = file_result.get("typos", [])
                for typo in typos:
                    typos_list.append({
                        "file": file_path,
                        "typo": typo.get("typo", ""),
                        "correction": typo.get("correction", ""),
                    })
            
            logger.info(f"Found {total_typos} typos in {files_with_typos} files")
            
            return {
                "success": True,
                "total_typos": total_typos,
                "files_with_typos": files_with_typos,
                "repo_path": repo_path,
                "typos_list": typos_list,
                "detailed_results": results,
            }
        
        except Exception as e:
            logger.error(f"Error scanning project: {e}")
            return {"success": False, "error": str(e)}
    
    async def _fix_typos(self, scan_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Fix typos in a project using TypoFixerAgent
        
        Args:
            scan_result: Scan result
            
        Returns:
            Fix result
        """
        if not self.fixer_agent:
            return {"error": "Fixer agent not initialized"}
        
        repo_path = scan_result.get("repo_path", "")
        detailed_results = scan_result.get("detailed_results", [])
        
        if not detailed_results:
            logger.info("No typos to fix")
            return {
                "success": True,
                "total_typos_fixed": 0,
                "files_fixed": 0,
            }
        
        logger.info(f"Fixing typos in {len(detailed_results)} files")
        
        try:
            # Prepare files to fix
            files_to_fix = []
            for file_result in detailed_results:
                file_path = file_result.get("file_path", "")
                typos = file_result.get("typos", [])
                if file_path and typos:
                    files_to_fix.append({
                        "file_path": file_path,
                        "typos": typos,
                    })
            
            # Fix typos
            fix_result = await self.fixer_agent.process_task({
                "type": "fix_files",
                "files": files_to_fix,
            })
            
            if "error" in fix_result:
                logger.error(f"Fix failed: {fix_result['error']}")
                return {"success": False, "error": fix_result["error"]}
            
            total_fixed = fix_result.get("total_typos_fixed", 0)
            files_fixed = fix_result.get("files_fixed", 0)
            
            logger.info(f"Fixed {total_fixed} typos in {files_fixed} files")
            
            return {
                "success": True,
                "total_typos_fixed": total_fixed,
                "files_fixed": files_fixed,
                "fix_results": fix_result.get("results", []),
            }
        
        except Exception as e:
            logger.error(f"Error fixing typos: {e}")
            return {"success": False, "error": str(e)}
    
    async def _create_pr(
        self,
        owner: str,
        repo: str,
        scan_result: Dict[str, Any],
        fix_result: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Create a pull request using PRCreatorAgent
        
        Args:
            owner: Repository owner
            repo: Repository name
            scan_result: Scan result
            fix_result: Fix result
            
        Returns:
            PR creation result
        """
        if not self.pr_creator_agent:
            return {"error": "PR creator agent not initialized"}
        
        repo_path = scan_result.get("repo_path", "")
        fix_results = fix_result.get("fix_results", [])
        
        if not fix_results:
            logger.info("No changes to create PR for")
            return {
                "success": False,
                "error": "No changes to submit",
            }
        
        logger.info(f"Creating PR for {owner}/{repo}")
        
        try:
            # Prepare changes data for PR
            changes = []
            for fix in fix_results:
                file_path = fix.get("file_path", "")
                typos_fixed = fix.get("typos_fixed", 0)
                if file_path and typos_fixed > 0:
                    changes.append({
                        "file": file_path,
                        "typos": typos_fixed,
                    })
            
            # Create PR using PRCreatorAgent
            pr_result = await self.pr_creator_agent.process_task({
                "type": "create_pr",
                "owner": owner,
                "repo": repo,
                "repo_path": repo_path,
                "changes": changes,
            })
            
            if "error" in pr_result:
                logger.error(f"PR creation failed: {pr_result['error']}")
                return {"success": False, "error": pr_result["error"]}
            
            pr_number = pr_result.get("pr_number")
            pr_url = pr_result.get("pr_url")
            
            logger.info(f"Created PR #{pr_number}: {pr_url}")
            
            return {
                "success": True,
                "pr_number": pr_number,
                "pr_url": pr_url,
            }
        
        except Exception as e:
            logger.error(f"Error creating PR: {e}")
            return {"success": False, "error": str(e)}
    
    async def _generate_report(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate a report using ReportGeneratorAgent
        
        Args:
            data: Report data containing owner, repo, scan_result, fix_result
            
        Returns:
            Report generation result
        """
        if not self.report_generator_agent:
            return {"error": "Report generator agent not initialized"}
        
        owner = data.get("owner", "")
        repo = data.get("repo", "")
        scan_result = data.get("scan_result", {})
        fix_result = data.get("fix_result", {})
        
        logger.info(f"Generating report for {owner}/{repo}")
        
        try:
            # Prepare report data
            report_data = {
                "project": f"{owner}/{repo}",
                "scan_summary": {
                    "total_typos": scan_result.get("total_typos", 0),
                    "files_with_typos": scan_result.get("files_with_typos", 0),
                },
                "fix_summary": {
                    "total_typos_fixed": fix_result.get("total_typos_fixed", 0),
                    "files_fixed": fix_result.get("files_fixed", 0),
                },
                "typos_list": scan_result.get("typos_list", []),
            }
            
            # Generate typo fix report
            report_result = await self.report_generator_agent.process_task({
                "type": "generate_typo_fix_report",
                "results": [report_data],
                "output_file": f"{self.work_dir}/{owner}_{repo}_report.md",
            })
            
            if "error" in report_result:
                logger.error(f"Report generation failed: {report_result['error']}")
                return {"success": False, "error": report_result["error"]}
            
            output_file = report_result.get("output_file", "")
            
            logger.info(f"Report generated: {output_file}")
            
            return {
                "success": True,
                "report_file": output_file,
            }
        
        except Exception as e:
            logger.error(f"Error generating report: {e}")
            return {"success": False, "error": str(e)}
