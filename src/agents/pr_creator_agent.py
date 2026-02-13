"""
PR Creator Agent - Creates pull requests for typo fixes

This agent is responsible for creating pull requests for typo fixes.
"""

from typing import Any, Dict, List, Optional

from ..agent_framework.base_agent import BaseAgent, AgentConfig
from ..agent_framework.tool_system import ToolRegistry
from ..agent_framework.logger import get_logger

logger = get_logger(__name__)


class PRCreatorAgent(BaseAgent):
    """
    Agent for creating pull requests
    
    Responsibilities:
    - Create pull requests
    - Generate PR descriptions
    - Validate PRs
    - Track PR status
    """
    
    def __init__(self, github_token: Optional[str] = None):
        """
        Initialize PR creator agent
        
        Args:
            github_token: GitHub API token
        """
        config = AgentConfig(
            name="PRCreatorAgent",
            version="1.0.0",
            description="Creates pull requests for typo fixes",
            max_retries=3,
            timeout=300.0,
        )
        
        super().__init__(config)
        self.github_token = github_token
    
    async def on_initialize(self) -> None:
        """Initialize agent and register tools"""
        from ..tools.pr_tools import (
            create_pr,
            generate_pr_title,
            generate_pr_body,
            prepare_pr,
            validate_pr,
        )
        from ..tools.git_tools import (
            git_get_current_branch,
            git_push,
        )
        from ..tools.github_tools import get_default_branch
        
        self.tool_registry.register(create_pr)
        self.tool_registry.register(generate_pr_title)
        self.tool_registry.register(generate_pr_body)
        self.tool_registry.register(prepare_pr)
        self.tool_registry.register(validate_pr)
        self.tool_registry.register(git_get_current_branch)
        self.tool_registry.register(git_push)
        self.tool_registry.register(get_default_branch)
        
        logger.info("PR creator agent initialized")
    
    async def on_start(self) -> None:
        """Called when agent starts"""
        logger.info("PR creator agent started")
    
    async def on_stop(self) -> None:
        """Called when agent stops"""
        logger.info("PR creator agent stopped")
    
    async def on_pause(self) -> None:
        """Called when agent is paused"""
        logger.info("PR creator agent paused")
    
    async def on_resume(self) -> None:
        """Called when agent resumes"""
        logger.info("PR creator agent resumed")
    
    async def process_task(self, task: Any) -> Any:
        """
        Process a PR creation task
        
        Args:
            task: Task to process
            
        Returns:
            Task result
        """
        task_type = task.get("type")
        
        if task_type == "create_pr":
            return await self._create_pr(task)
        elif task_type == "prepare_pr":
            return await self._prepare_pr(task)
        elif task_type == "validate_pr":
            return await self._validate_pr(task)
        else:
            logger.warning(f"Unknown task type: {task_type}")
            return {"error": f"Unknown task type: {task_type}"}
    
    async def _create_pr(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a pull request
        
        Args:
            task: Task parameters
            
        Returns:
            PR creation result
        """
        owner = task.get("owner")
        repo = task.get("repo")
        changes = task.get("changes", [])
        
        if not owner or not repo:
            return {"error": "owner and repo are required"}
        
        logger.info(f"Creating PR for {owner}/{repo}")
        
        # Get current branch
        branch_result = await self.tool_registry.invoke(
            "git_get_current_branch",
            repo_path=task.get("repo_path"),
        )
        
        if not branch_result.success:
            return {"error": "Failed to get current branch"}
        
        current_branch = branch_result.data
        
        # Get default branch
        default_branch_result = await self.tool_registry.invoke(
            "get_default_branch",
            owner=owner,
            repo=repo,
            token=self.github_token,
        )
        
        if not default_branch_result.success:
            return {"error": "Failed to get default branch"}
        
        default_branch = default_branch_result.data
        
        # Generate PR title and body
        title_result = await self.tool_registry.invoke(
            "generate_pr_title",
            changes=changes,
        )
        
        body_result = await self.tool_registry.invoke(
            "generate_pr_body",
            changes=changes,
        )
        
        if not title_result.success or not body_result.success:
            return {"error": "Failed to generate PR content"}
        
        title = title_result.data
        body = body_result.data
        
        # Validate PR
        validation_result = await self.tool_registry.invoke(
            "validate_pr",
            title=title,
            body=body,
            changes=changes,
        )
        
        if not validation_result.success:
            return {"error": "PR validation failed", "errors": validation_result.data.get("errors", []) if validation_result.data else []}
        
        # Push changes
        push_result = await self.tool_registry.invoke(
            "git_push",
            repo_path=task.get("repo_path"),
            remote="origin",
            branch=current_branch,
        )
        
        if not push_result.success:
            return {"error": "Failed to push changes"}
        
        # Create PR
        pr_result = await self.tool_registry.invoke(
            "create_pr",
            owner=owner,
            repo=repo,
            title=title,
            head=current_branch,
            base=default_branch,
            body=body,
            token=self.github_token,
        )
        
        if not pr_result.success:
            return {"error": "Failed to create PR"}
        
        pr_data = pr_result.data
        
        logger.info(f"Created PR #{pr_data.get('pr_number')}: {pr_data.get('url')}")
        
        return {
            "success": True,
            "pr_number": pr_data.get("pr_number"),
            "pr_url": pr_data.get("url"),
            "title": title,
        }
    
    async def _prepare_pr(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        Prepare PR components
        
        Args:
            task: Task parameters
            
        Returns:
            PR preparation result
        """
        owner = task.get("owner")
        repo = task.get("repo")
        changes = task.get("changes", [])
        
        logger.info(f"Preparing PR for {owner}/{repo}")
        
        # Generate PR title
        title_result = await self.tool_registry.invoke(
            "generate_pr_title",
            changes=changes,
        )
        
        # Generate PR body
        body_result = await self.tool_registry.invoke(
            "generate_pr_body",
            changes=changes,
        )
        
        # Validate PR
        validation_result = await self.tool_registry.invoke(
            "validate_pr",
            title=title_result.data if title_result.success else "",
            body=body_result.data if body_result.success else "",
            changes=changes,
        )
        
        return {
            "title": title_result.data if title_result.success else "",
            "body": body_result.data if body_result.success else "",
            "valid": validation_result.success,
            "errors": validation_result.data.get("errors", []) if validation_result.data else [],
        }
    
    async def _validate_pr(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate a pull request
        
        Args:
            task: Task parameters
            
        Returns:
            Validation result
        """
        title = task.get("title", "")
        body = task.get("body", "")
        changes = task.get("changes", [])
        
        validation_result = await self.tool_registry.invoke(
            "validate_pr",
            title=title,
            body=body,
            changes=changes,
        )
        
        return {
            "success": validation_result.success,
            "valid": validation_result.data.get("valid", False) if validation_result.data else False,
            "errors": validation_result.data.get("errors", []) if validation_result.data else [],
        }
