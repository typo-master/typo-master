"""
Typo Scanner Agent - Scans repositories for spelling errors

This agent is responsible for scanning repositories to detect spelling errors
and filtering out false positives.
"""

import os
from typing import Any, Dict, List, Optional
from pathlib import Path

from ..agent_framework.base_agent import BaseAgent, AgentConfig
from ..agent_framework.tool_system import ToolRegistry
from ..agent_framework.logger import get_logger

logger = get_logger(__name__)


class TypoScannerAgent(BaseAgent):
    """
    Agent for scanning repositories for spelling errors
    
    Responsibilities:
    - Scan files for spelling errors
    - Filter false positives (Web3 terms, code identifiers)
    - Prioritize findings
    - Generate typo reports
    """
    
    def __init__(self):
        """Initialize typo scanner agent"""
        config = AgentConfig(
            name="TypoScannerAgent",
            version="1.0.0",
            description="Scans repositories for spelling errors",
            max_retries=3,
            timeout=600.0,
        )
        
        super().__init__(config)
        
        # Supported file extensions
        self.supported_extensions = {
            '.md', '.txt', '.rst', '.adoc',
            '.py', '.js', '.ts', '.jsx', '.tsx',
            '.sol', '.rs', '.go',
        }
        
        # Maximum file size to scan (bytes)
        self.max_file_size = 100000
    
    async def on_initialize(self) -> None:
        """Initialize agent and register tools"""
        from ..tools.spell_tools import (
            check_spelling,
            check_file_spelling,
        )
        from ..tools.file_tools import (
            list_files,
            read_file,
            file_exists,
        )
        
        self.tool_registry.register(check_spelling)
        self.tool_registry.register(check_file_spelling)
        self.tool_registry.register(list_files)
        self.tool_registry.register(read_file)
        self.tool_registry.register(file_exists)
        
        logger.info("Typo scanner agent initialized")
    
    async def on_start(self) -> None:
        """Called when agent starts"""
        logger.info("Typo scanner agent started")
    
    async def on_stop(self) -> None:
        """Called when agent stops"""
        logger.info("Typo scanner agent stopped")
    
    async def on_pause(self) -> None:
        """Called when agent is paused"""
        logger.info("Typo scanner agent paused")
    
    async def on_resume(self) -> None:
        """Called when agent resumes"""
        logger.info("Typo scanner agent resumed")
    
    async def process_task(self, task: Any) -> Any:
        """
        Process a scanning task
        
        Args:
            task: Task to process
            
        Returns:
            Task result
        """
        task_type = task.get("type")
        
        if task_type == "scan_repo":
            return await self._scan_repo(task)
        elif task_type == "scan_file":
            return await self._scan_file(task)
        elif task_type == "scan_files":
            return await self._scan_files(task)
        else:
            logger.warning(f"Unknown task type: {task_type}")
            return {"error": f"Unknown task type: {task_type}"}
    
    async def _scan_repo(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        Scan a repository for spelling errors
        
        Args:
            task: Task parameters
            
        Returns:
            Scan results
        """
        repo_path = task.get("repo_path")
        
        if not repo_path:
            return {"error": "repo_path is required"}
        
        logger.info(f"Scanning repository: {repo_path}")
        
        # List all files
        files_result = await self.tool_registry.invoke(
            "list_files",
            directory=repo_path,
            recursive=True,
        )
        
        if not files_result.success:
            return {"error": "Failed to list files"}
        
        all_files = files_result.data
        
        # Filter supported files
        supported_files = [
            f for f in all_files
            if Path(f).suffix.lower() in self.supported_extensions
        ]
        
        logger.info(f"Found {len(supported_files)} supported files to scan")
        
        # Scan each file
        results = []
        total_typos = 0
        
        for file_path in supported_files:
            try:
                file_result = await self._scan_file({"file_path": file_path})
                
                if file_result.get("typos_count", 0) > 0:
                    results.append(file_result)
                    total_typos += file_result["typos_count"]
            
            except Exception as e:
                logger.error(f"Error scanning {file_path}: {e}")
        
        logger.info(f"Found {total_typos} typos in {len(results)} files")
        
        return {
            "repo_path": repo_path,
            "files_scanned": len(supported_files),
            "files_with_typos": len(results),
            "total_typos": total_typos,
            "results": results,
        }
    
    async def _scan_file(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        Scan a single file for spelling errors
        
        Args:
            task: Task parameters
            
        Returns:
            Scan results
        """
        file_path = task.get("file_path")
        
        if not file_path:
            return {"error": "file_path is required"}
        
        logger.debug(f"Scanning file: {file_path}")
        
        # Check if file exists
        exists_result = await self.tool_registry.invoke(
            "file_exists",
            file_path=file_path,
        )
        
        if not exists_result.success or not exists_result.data:
            return {"error": f"File not found: {file_path}"}
        
        # Check file size
        file_info = Path(file_path).stat()
        if file_info.st_size > self.max_file_size:
            logger.debug(f"Skipping large file: {file_path}")
            return {
                "file_path": file_path,
                "typos_count": 0,
                "typos": [],
                "skipped": True,
                "reason": "File too large",
            }
        
        # Read file content
        read_result = await self.tool_registry.invoke(
            "read_file",
            file_path=file_path,
        )
        
        if not read_result.success:
            return {"error": f"Failed to read file: {file_path}"}
        
        content = read_result.data
        
        # Check spelling
        spell_result = await self.tool_registry.invoke(
            "check_spelling",
            text=content,
        )
        
        if not spell_result.success:
            return {"error": f"Failed to check spelling: {file_path}"}
        
        typos = spell_result.data
        
        # Filter typos based on context
        filtered_typos = await self._filter_typos(file_path, content, typos)
        
        return {
            "file_path": file_path,
            "typos_count": len(filtered_typos),
            "typos": filtered_typos,
        }
    
    async def _scan_files(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        Scan multiple files for spelling errors
        
        Args:
            task: Task parameters
            
        Returns:
            Scan results
        """
        file_paths = task.get("file_paths", [])
        
        logger.info(f"Scanning {len(file_paths)} files")
        
        results = []
        total_typos = 0
        
        for file_path in file_paths:
            try:
                file_result = await self._scan_file({"file_path": file_path})
                
                if file_result.get("typos_count", 0) > 0:
                    results.append(file_result)
                    total_typos += file_result["typos_count"]
            
            except Exception as e:
                logger.error(f"Error scanning {file_path}: {e}")
        
        return {
            "files_scanned": len(file_paths),
            "files_with_typos": len(results),
            "total_typos": total_typos,
            "results": results,
        }
    
    async def _filter_typos(
        self,
        file_path: str,
        content: str,
        typos: List[Dict[str, str]],
    ) -> List[Dict[str, str]]:
        """
        Filter typos based on context
        
        Args:
            file_path: File path
            content: File content
            typos: List of typos
            
        Returns:
            Filtered typos
        """
        filtered = []
        file_ext = Path(file_path).suffix.lower()
        
        for typo_info in typos:
            typo = typo_info.get("typo", "")
            correction = typo_info.get("correction", "")
            
            # Skip short words
            if len(typo) <= 3:
                continue
            
            # Skip if it looks like code identifier
            if self._is_code_identifier(file_ext, typo, content):
                continue
            
            # Skip if it's in a URL
            if "://" in typo or typo.startswith(("http", "https", "ftp")):
                continue
            
            # Skip if it's a file path
            if "/" in typo or "\\" in typo:
                continue
            
            filtered.append(typo_info)
        
        return filtered
    
    def _is_code_identifier(self, file_ext: str, typo: str, content: str) -> bool:
        """
        Check if a typo is actually a code identifier
        
        Args:
            file_ext: File extension
            typo: Typo text
            content: File content
            
        Returns:
            True if it's a code identifier
        """
        # Code file extensions
        code_extensions = {'.py', '.js', '.ts', '.jsx', '.tsx', '.sol', '.rs', '.go'}
        
        if file_ext not in code_extensions:
            return False
        
        # Check if it's in a code context
        code_patterns = [
            f"def {typo}",
            f"class {typo}",
            f"function {typo}",
            f"const {typo}",
            f"let {typo}",
            f"var {typo}",
            f"import {typo}",
            f"from {typo}",
            f"{typo}(",
            f"{typo}=",
            f" {typo} ",
        ]
        
        for pattern in code_patterns:
            if pattern in content:
                return True
        
        return False
