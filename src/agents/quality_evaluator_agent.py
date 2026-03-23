"""
Quality Evaluator Agent - Evaluates the quality of typo fixes

This agent is responsible for evaluating the quality of typo fixes
before creating pull requests.
"""

from typing import Any, Dict, List, Optional
from pathlib import Path

from ..agent_framework.base_agent import BaseAgent, AgentConfig
from ..agent_framework.tool_system import ToolRegistry
from ..agent_framework.logger import get_logger

logger = get_logger(__name__)


class QualityEvaluatorAgent(BaseAgent):
    """
    Agent for evaluating typo fix quality
    
    Responsibilities:
    - Validate typo corrections
    - Check for over-correction
    - Verify context appropriateness
    - Assess fix quality
    """
    
    def __init__(self):
        """Initialize quality evaluator agent"""
        config = AgentConfig(
            name="QualityEvaluatorAgent",
            version="1.0.0",
            description="Evaluates the quality of typo fixes",
            max_retries=3,
            timeout=300.0,
        )
        
        super().__init__(config)
        
        # Quality thresholds
        self.min_confidence = 0.7
        self.max_corrections_per_file = 50
    
    async def on_initialize(self) -> None:
        """Initialize agent and register tools"""
        from ..tools.spell_tools import is_web3_term
        from ..tools.file_tools import read_file
        
        self.tool_registry.register(is_web3_term)
        self.tool_registry.register(read_file)
        
        logger.info("Quality evaluator agent initialized")
    
    async def on_start(self) -> None:
        """Called when agent starts"""
        logger.info("Quality evaluator agent started")
    
    async def on_stop(self) -> None:
        """Called when agent stops"""
        logger.info("Quality evaluator agent stopped")
    
    async def on_pause(self) -> None:
        """Called when agent is paused"""
        logger.info("Quality evaluator agent paused")
    
    async def on_resume(self) -> None:
        """Called when agent resumes"""
        logger.info("Quality evaluator agent resumed")
    
    async def process_task(self, task: Any) -> Any:
        """
        Process a quality evaluation task
        
        Args:
            task: Task to process
            
        Returns:
            Task result
        """
        task_type = task.get("type")
        
        if task_type == "evaluate_fixes":
            return await self._evaluate_fixes(task)
        elif task_type == "validate_correction":
            return await self._validate_correction(task)
        elif task_type == "check_over_correction":
            return await self._check_over_correction(task)
        else:
            logger.warning(f"Unknown task type: {task_type}")
            return {"error": f"Unknown task type: {task_type}"}
    
    async def _evaluate_fixes(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        Evaluate typo fixes
        
        Args:
            task: Task parameters
            
        Returns:
            Evaluation result
        """
        file_path = task.get("file_path")
        typos = task.get("typos", [])
        
        if not file_path or not typos:
            return {"error": "file_path and typos are required"}
        
        logger.info(f"Evaluating fixes for {file_path}")
        
        # Read file content
        read_result = await self.tool_registry.invoke(
            "read_file",
            file_path=file_path,
        )
        
        if not read_result.success:
            return {"error": "Failed to read file"}

        content = read_result.data
        
        # Evaluate each correction
        evaluated_typos = []
        passed_count = 0
        failed_count = 0
        
        for typo_info in typos:
            evaluation = await self._evaluate_single_correction(
                file_path,
                content,
                typo_info,
            )
            
            if evaluation.get("passed", False):
                passed_count += 1
                evaluated_typos.append(typo_info)
            else:
                failed_count += 1
                logger.debug(f"Correction failed: {evaluation.get('reason', 'Unknown')}")
        
        # Calculate overall quality score
        total_count = len(typos)
        quality_score = passed_count / total_count if total_count > 0 else 0
        
        # Check if quality is acceptable
        quality_acceptable = quality_score >= self.min_confidence
        
        # Check for over-correction
        over_correction = await self._check_over_correction({
            "file_path": file_path,
            "typos": typos,
        })
        
        return {
            "file_path": file_path,
            "total_typos": total_count,
            "passed_typos": passed_count,
            "failed_typos": failed_count,
            "quality_score": quality_score,
            "quality_acceptable": quality_acceptable,
            "over_correction": over_correction.get("over_corrected", False),
            "evaluated_typos": evaluated_typos,
        }
    
    async def _validate_correction(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate a single correction
        
        Args:
            task: Task parameters
            
        Returns:
            Validation result
        """
        file_path = task.get("file_path")
        typo = task.get("typo", "")
        correction = task.get("correction", "")
        
        if not file_path or not typo or not correction:
            return {"error": "file_path, typo, and correction are required"}
        
        # Read file content
        read_result = await self.tool_registry.invoke(
            "read_file",
            file_path=file_path,
        )
        
        if not read_result.success:
            return {"error": "Failed to read file"}

        content = read_result.data
        
        typo_info = {"typo": typo, "correction": correction}
        evaluation = await self._evaluate_single_correction(
            file_path,
            content,
            typo_info,
        )
        
        return evaluation
    
    async def _check_over_correction(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        Check for over-correction
        
        Args:
            task: Task parameters
            
        Returns:
            Over-correction check result
        """
        file_path = task.get("file_path")
        typos = task.get("typos", [])
        
        if not file_path or not typos:
            return {"error": "file_path and typos are required"}
        
        # Check if too many corrections
        over_corrected = len(typos) > self.max_corrections_per_file
        
        # Check if corrections are too aggressive
        aggressive_corrections = 0
        for typo_info in typos:
            typo = typo_info.get("typo", "")
            correction = typo_info.get("correction", "")
            
            # Check if correction is very different from original
            if abs(len(typo) - len(correction)) > 3:
                aggressive_corrections += 1
        
        # Check if aggressive corrections are too many
        if aggressive_corrections > len(typos) * 0.3:
            over_corrected = True
        
        return {
            "file_path": file_path,
            "typos_count": len(typos),
            "over_corrected": over_corrected,
            "reason": "Too many corrections" if over_corrected else None,
        }
    
    async def _evaluate_single_correction(
        self,
        file_path: str,
        content: str,
        typo_info: Dict[str, str],
    ) -> Dict[str, Any]:
        """
        Evaluate a single correction
        
        Args:
            file_path: File path
            content: File content
            typo_info: Typo information
            
        Returns:
            Evaluation result
        """
        typo = typo_info.get("typo", "")
        correction = typo_info.get("correction", "")
        
        # Check if typo is in content
        if typo not in content:
            return {
                "passed": False,
                "reason": "Typo not found in content",
            }
        
        # Check if correction is a Web3 term
        web3_check = await self.tool_registry.invoke(
            "is_web3_term",
            word=correction,
        )
        
        if web3_check.success and web3_check.data:
            return {
                "passed": False,
                "reason": "Correction is a Web3 term",
            }
        
        # Check if typo is a Web3 term
        typo_web3_check = await self.tool_registry.invoke(
            "is_web3_term",
            word=typo,
        )
        
        if typo_web3_check.success and typo_web3_check.data:
            return {
                "passed": False,
                "reason": "Typo is a Web3 term",
            }
        
        # Check if correction is reasonable
        if self._is_unreasonable_correction(typo, correction):
            return {
                "passed": False,
                "reason": "Unreasonable correction",
            }
        
        # Check if correction is in context
        if not self._is_correction_in_context(content, typo, correction):
            return {
                "passed": False,
                "reason": "Correction not in context",
            }
        
        return {
            "passed": True,
            "typo": typo,
            "correction": correction,
        }
    
    def _is_unreasonable_correction(self, typo: str, correction: str) -> bool:
        """
        Check if a correction is unreasonable
        
        Args:
            typo: Original text
            correction: Suggested correction
            
        Returns:
            True if unreasonable
        """
        # Check if correction is too different
        if len(correction) > len(typo) * 2:
            return True
        
        # Check if correction changes the meaning significantly
        if typo.lower() != correction.lower() and len(typo) < 5:
            return True
        
        return False
    
    def _is_correction_in_context(
        self,
        content: str,
        typo: str,
        correction: str,
    ) -> bool:
        """
        Check if correction is appropriate in context
        
        Args:
            content: File content
            typo: Original text
            correction: Suggested correction
            
        Returns:
            True if appropriate
        """
        # Simple check: if typo appears multiple times, only correct first occurrence
        typo_count = content.count(typo)
        
        if typo_count > 1:
            # Check if all occurrences should be corrected
            # This is a simplified check
            return typo_count <= 3
        
        return True
