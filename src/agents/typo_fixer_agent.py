"""
Typo Fixer Agent - Fixes spelling errors in repositories

This agent is responsible for fixing spelling errors in repositories
and preparing changes for pull requests.
"""

from typing import Any, Dict, List, Optional
from pathlib import Path

from ..agent_framework.base_agent import BaseAgent, AgentConfig
from ..agent_framework.tool_system import ToolRegistry
from ..agent_framework.logger import get_logger

logger = get_logger(__name__)


class TypoFixerAgent(BaseAgent):
    """
    Agent for fixing spelling errors in repositories
    
    Responsibilities:
    - Fix identified spelling errors
    - Validate corrections
    - Manage file changes
    - Prepare commits
    """
    
    def __init__(self):
        """Initialize typo fixer agent"""
        config = AgentConfig(
            name="TypoFixerAgent",
            version="1.0.0",
            description="Fixes spelling errors in repositories",
            max_retries=3,
            timeout=600.0,
        )
        
        super().__init__(config)
    
    async def on_initialize(self) -> None:
        """Initialize agent and register tools"""
        from ..tools.spell_tools import correct_spelling
        from ..tools.file_tools import (
            read_file,
            write_file,
            replace_in_file,
        )
        from ..tools.git_tools import (
            git_add,
            git_commit,
            git_get_changes,
        )
        
        self.tool_registry.register(correct_spelling)
        self.tool_registry.register(read_file)
        self.tool_registry.register(write_file)
        self.tool_registry.register(replace_in_file)
        self.tool_registry.register(git_add)
        self.tool_registry.register(git_commit)
        self.tool_registry.register(git_get_changes)
        
        logger.info("Typo fixer agent initialized")
    
    async def on_start(self) -> None:
        """Called when agent starts"""
        logger.info("Typo fixer agent started")
    
    async def on_stop(self) -> None:
        """Called when agent stops"""
        logger.info("Typo fixer agent stopped")
    
    async def on_pause(self) -> None:
        """Called when agent is paused"""
        logger.info("Typo fixer agent paused")
    
    async def on_resume(self) -> None:
        """Called when agent resumes"""
        logger.info("Typo fixer agent resumed")
    
    async def process_task(self, task: Any) -> Any:
        """
        Process a fixing task
        
        Args:
            task: Task to process
            
        Returns:
            Task result
        """
        task_type = task.get("type")
        
        if task_type == "fix_file":
            return await self._fix_file(task)
        elif task_type == "fix_files":
            return await self._fix_files(task)
        elif task_type == "prepare_commit":
            return await self._prepare_commit(task)
        else:
            logger.warning(f"Unknown task type: {task_type}")
            return {"error": f"Unknown task type: {task_type}"}
    
    async def _fix_file(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        Fix spelling errors in a file
        
        Args:
            task: Task parameters
            
        Returns:
            Fix results
        """
        file_path = task.get("file_path")
        typos = task.get("typos", [])
        
        if not file_path:
            return {"error": "file_path is required"}
        
        logger.info(f"Fixing typos in {file_path}")
        
        # Read file content
        read_result = await self.tool_registry.invoke(
            "read_file",
            file_path=file_path,
        )
        
        if not read_result.success:
            return {"error": f"Failed to read file: {file_path}"}
        
        content = read_result.data
        original_content = content
        
        # Fix each typo
        fixed_count = 0
        for typo_info in typos:
            typo = typo_info.get("typo", "")
            correction = typo_info.get("correction", "")
            
            if not typo or not correction:
                continue
            
            # Replace typo (only first occurrence to avoid over-correction)
            if typo in content:
                content = content.replace(typo, correction, 1)
                fixed_count += 1
        
        # Write back if changes were made
        if content != original_content:
            write_result = await self.tool_registry.invoke(
                "write_file",
                file_path=file_path,
                content=content,
            )
            
            if not write_result.success:
                return {"error": f"Failed to write file: {file_path}"}
            
            logger.info(f"Fixed {fixed_count} typos in {file_path}")
        
        return {
            "file_path": file_path,
            "typos_fixed": fixed_count,
            "success": True,
        }
    
    async def _fix_files(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        Fix spelling errors in multiple files
        
        Args:
            task: Task parameters
            
        Returns:
            Fix results
        """
        files_to_fix = task.get("files", [])
        
        logger.info(f"Fixing typos in {len(files_to_fix)} files")
        
        results = []
        total_fixed = 0
        
        for file_info in files_to_fix:
            try:
                file_path = file_info.get("file_path")
                typos = file_info.get("typos", [])
                
                if not file_path or not typos:
                    continue
                
                fix_result = await self._fix_file({
                    "file_path": file_path,
                    "typos": typos,
                })
                
                if fix_result.get("success"):
                    results.append(fix_result)
                    total_fixed += fix_result["typos_fixed"]
            
            except Exception as e:
                logger.error(f"Error fixing file: {e}")
        
        return {
            "files_fixed": len(results),
            "total_typos_fixed": total_fixed,
            "results": results,
        }
    
    async def _prepare_commit(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        Prepare a commit for fixed typos
        
        Args:
            task: Task parameters
            
        Returns:
            Commit results
        """
        repo_path = task.get("repo_path")
        message = task.get("message", "Fix spelling errors")
        
        if not repo_path:
            return {"error": "repo_path is required"}
        
        logger.info(f"Preparing commit: {message}")
        
        # Get changed files
        changes_result = await self.tool_registry.invoke(
            "git_get_changes",
            repo_path=repo_path,
        )
        
        if not changes_result.success:
            return {"error": "Failed to get changes"}
        
        staged_files = changes_result.data.get("staged", [])
        unstaged_files = changes_result.data.get("unstaged", [])
        
        # Stage all changed files
        all_files = staged_files + unstaged_files
        
        if not all_files:
            logger.info("No files to commit")
            return {
                "success": True,
                "files_committed": 0,
                "message": "No files to commit",
            }
        
        for file_path in all_files:
            await self.tool_registry.invoke(
                "git_add",
                repo_path=repo_path,
                files=[file_path],
            )
        
        # Commit changes
        commit_result = await self.tool_registry.invoke(
            "git_commit",
            repo_path=repo_path,
            message=message,
        )
        
        if not commit_result.success:
            return {"error": "Failed to commit"}
        
        logger.info(f"Committed {len(all_files)} files")
        
        return {
            "success": True,
            "files_committed": len(all_files),
            "message": message,
        }
