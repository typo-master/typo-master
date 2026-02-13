"""
Report Generator Agent - Generates various reports

This agent is responsible for generating reports in different formats.
"""

from typing import Any, Dict, List, Optional
from datetime import datetime

from ..agent_framework.base_agent import BaseAgent, AgentConfig
from ..agent_framework.tool_system import ToolRegistry
from ..agent_framework.logger import get_logger

logger = get_logger(__name__)


class ReportGeneratorAgent(BaseAgent):
    """
    Agent for generating reports
    
    Responsibilities:
    - Generate CSV reports
    - Generate JSON reports
    - Generate Markdown reports
    - Generate HTML reports
    - Generate summary reports
    """
    
    def __init__(self):
        """Initialize report generator agent"""
        config = AgentConfig(
            name="ReportGeneratorAgent",
            version="1.0.0",
            description="Generates various reports",
            max_retries=3,
            timeout=300.0,
        )
        
        super().__init__(config)
    
    async def on_initialize(self) -> None:
        """Initialize agent and register tools"""
        from ..tools.report_tools import (
            generate_csv_report,
            generate_json_report,
            generate_markdown_report,
            generate_html_report,
            generate_summary_report,
            generate_typo_fix_report,
        )
        
        self.tool_registry.register(generate_csv_report)
        self.tool_registry.register(generate_json_report)
        self.tool_registry.register(generate_markdown_report)
        self.tool_registry.register(generate_html_report)
        self.tool_registry.register(generate_summary_report)
        self.tool_registry.register(generate_typo_fix_report)
        
        logger.info("Report generator agent initialized")
    
    async def on_start(self) -> None:
        """Called when agent starts"""
        logger.info("Report generator agent started")
    
    async def on_stop(self) -> None:
        """Called when agent stops"""
        logger.info("Report generator agent stopped")
    
    async def on_pause(self) -> None:
        """Called when agent is paused"""
        logger.info("Report generator agent paused")
    
    async def on_resume(self) -> None:
        """Called when agent resumes"""
        logger.info("Report generator agent resumed")
    
    async def process_task(self, task: Any) -> Any:
        """
        Process a report generation task
        
        Args:
            task: Task to process
            
        Returns:
            Task result
        """
        task_type = task.get("type")
        
        if task_type == "generate_csv":
            return await self._generate_csv(task)
        elif task_type == "generate_json":
            return await self._generate_json(task)
        elif task_type == "generate_markdown":
            return await self._generate_markdown(task)
        elif task_type == "generate_html":
            return await self._generate_html(task)
        elif task_type == "generate_summary":
            return await self._generate_summary(task)
        elif task_type == "generate_typo_fix_report":
            return await self._generate_typo_fix_report(task)
        else:
            logger.warning(f"Unknown task type: {task_type}")
            return {"error": f"Unknown task type: {task_type}"}
    
    async def _generate_csv(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate a CSV report
        
        Args:
            task: Task parameters
            
        Returns:
            Report generation result
        """
        data = task.get("data", [])
        columns = task.get("columns", [])
        output_file = task.get("output_file", "report.csv")
        
        logger.info(f"Generating CSV report: {output_file}")
        
        result = await self.tool_registry.invoke(
            "generate_csv_report",
            data=data,
            columns=columns,
            output_file=output_file,
        )
        
        return {
            "success": result.success,
            "output_file": output_file if result.success else None,
            "message": result.data if result.success else result.error,
        }
    
    async def _generate_json(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate a JSON report
        
        Args:
            task: Task parameters
            
        Returns:
            Report generation result
        """
        data = task.get("data", {})
        output_file = task.get("output_file", "report.json")
        indent = task.get("indent", 2)
        
        logger.info(f"Generating JSON report: {output_file}")
        
        result = await self.tool_registry.invoke(
            "generate_json_report",
            data=data,
            output_file=output_file,
            indent=indent,
        )
        
        return {
            "success": result.success,
            "output_file": output_file if result.success else None,
            "message": result.data if result.success else result.error,
        }
    
    async def _generate_markdown(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate a Markdown report
        
        Args:
            task: Task parameters
            
        Returns:
            Report generation result
        """
        title = task.get("title", "Report")
        sections = task.get("sections", [])
        output_file = task.get("output_file", "report.md")
        
        logger.info(f"Generating Markdown report: {output_file}")
        
        result = await self.tool_registry.invoke(
            "generate_markdown_report",
            title=title,
            sections=sections,
            output_file=output_file,
        )
        
        return {
            "success": result.success,
            "output_file": output_file if result.success else None,
            "message": result.data if result.success else result.error,
        }
    
    async def _generate_html(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate an HTML report
        
        Args:
            task: Task parameters
            
        Returns:
            Report generation result
        """
        title = task.get("title", "Report")
        content = task.get("content", "")
        output_file = task.get("output_file", "report.html")
        
        logger.info(f"Generating HTML report: {output_file}")
        
        result = await self.tool_registry.invoke(
            "generate_html_report",
            title=title,
            content=content,
            output_file=output_file,
        )
        
        return {
            "success": result.success,
            "output_file": output_file if result.success else None,
            "message": result.data if result.success else result.error,
        }
    
    async def _generate_summary(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate a summary report
        
        Args:
            task: Task parameters
            
        Returns:
            Report generation result
        """
        data = task.get("data", {})
        output_file = task.get("output_file", "summary.json")
        format_type = task.get("format", "json")
        
        logger.info(f"Generating summary report: {output_file}")
        
        result = await self.tool_registry.invoke(
            "generate_summary_report",
            data=data,
            output_file=output_file,
            format=format_type,
        )
        
        return {
            "success": result.success,
            "output_file": output_file if result.success else None,
            "message": result.data if result.success else result.error,
        }
    
    async def _generate_typo_fix_report(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate a typo fix report
        
        Args:
            task: Task parameters
            
        Returns:
            Report generation result
        """
        results = task.get("results", [])
        output_file = task.get("output_file", "typo_report.md")
        
        logger.info(f"Generating typo fix report: {output_file}")
        
        result = await self.tool_registry.invoke(
            "generate_typo_fix_report",
            results=results,
            output_file=output_file,
        )
        
        return {
            "success": result.success,
            "output_file": output_file if result.success else None,
            "message": result.data if result.success else result.error,
        }
