"""
Skill-Enabled Agent - Base Agent with Skill Support

Provides a base agent that can execute skills both standalone and as part of
LangGraph workflows.
"""

from typing import Any, Dict, List, Optional
from dataclasses import dataclass

from .base_agent import BaseAgent, AgentConfig, AgentState
from .skill_system import SkillRegistry, SkillContext, SkillResult, BaseSkill
from .skill_langgraph import SkillOrchestrator, SkillGraphBuilder
from .sku_system import SKUManager, SKUExtensionMixin
from .logger import get_logger

logger = get_logger(__name__)


@dataclass
class SkillAgentConfig(AgentConfig):
    """Configuration for skill-enabled agent"""
    # Skill settings
    auto_register_skills: bool = True
    default_workflow: str = "single_project"
    enable_skill_memory: bool = True

    # LangGraph settings
    enable_langgraph: bool = True
    langgraph_checkpoint: Optional[str] = None

    # SKU settings
    enable_sku: bool = True
    sku_directory: str = "./skus"
    auto_load_skus: bool = True


class SkillEnabledAgent(SKUExtensionMixin, BaseAgent):
    """
    Base agent with skill execution capabilities

    Features:
    - Direct skill execution
    - LangGraph workflow execution
    - Skill memory and learning
    - Dynamic workflow composition
    """

    def __init__(self, config: Optional[SkillAgentConfig] = None):
        if config is None:
            config = SkillAgentConfig()

        super().__init__(config)
        self.config: SkillAgentConfig = config

        # Skill orchestrator
        self.skill_orchestrator: Optional[SkillOrchestrator] = None

        # Active skills
        self.active_skills: Dict[str, BaseSkill] = {}

        # SKU Manager (will be initialized by SKUExtensionMixin)
        self.sku_manager: Optional[SKUManager] = None

    async def on_initialize(self) -> None:
        """Initialize skill orchestrator and SKU manager"""
        # Initialize SKU manager (from SKUExtensionMixin)
        if self.config.enable_sku:
            from pathlib import Path
            self.sku_manager = SKUManager(self)
            self.sku_manager.loader.sku_dir = Path(self.config.sku_directory)

            if self.config.auto_load_skus:
                await self.sku_manager.initialize()
                logger.info(f"SKU Manager initialized with {len(self.sku_manager.loaded_skus)} SKUs")

        # Auto-register skills if enabled (must happen before orchestrator init)
        if self.config.auto_register_skills:
            await self._auto_register_skills()

        # Initialize skill orchestrator (after skills are registered)
        if self.config.enable_langgraph:
            self.skill_orchestrator = SkillOrchestrator(self)
            self.skill_orchestrator.initialize()  # Initialize after skills registered
            logger.info(f"Skill orchestrator initialized with workflows: {self.skill_orchestrator.get_workflow_names()}")

    async def on_start(self) -> None:
        """Called when agent starts"""
        logger.info(f"SkillEnabledAgent '{self.config.name}' started")

    async def on_stop(self) -> None:
        """Called when agent stops - cleanup resources"""
        logger.info(f"SkillEnabledAgent '{self.config.name}' stopping")
        # Clear active skills
        self.active_skills.clear()
        # Clear orchestrator
        self.skill_orchestrator = None
        # Cleanup SKU manager
        if self.sku_manager:
            for sku_name in list(self.sku_manager.loaded_skus.keys()):
                await self.sku_manager.unload_sku(sku_name)
            self.sku_manager = None

    async def on_pause(self) -> None:
        """Called when agent is paused"""
        logger.info(f"SkillEnabledAgent '{self.config.name}' paused")

    async def on_resume(self) -> None:
        """Called when agent resumes from pause"""
        logger.info(f"SkillEnabledAgent '{self.config.name}' resumed")

    async def _auto_register_skills(self):
        """Auto-discover and register skills"""
        from ..skills import (
            RepositoryScanSkill,
            TypoFixSkill,
            TypoReportSkill,
            GitOperationsSkill,
            PullRequestSkill,
            RepositoryCloneSkill,
            RepositoryDownloadSkill,
            PRMonitorSkill,
            IssueTrackSkill,
            NotificationSkill,
            BatchProcessingSkill,
            SecretDetectionSkill,
            VulnerabilityScanSkill,
            InsecurePatternSkill,
            HardcodedCredentialSkill,
            DependencyAuditSkill,
        )

        skills = [
            RepositoryScanSkill(),
            TypoFixSkill(),
            TypoReportSkill(),
            GitOperationsSkill(),
            PullRequestSkill(),
            RepositoryCloneSkill(),
            RepositoryDownloadSkill(),
            PRMonitorSkill(),
            IssueTrackSkill(),
            NotificationSkill(),
            BatchProcessingSkill(),
            SecretDetectionSkill(),
            VulnerabilityScanSkill(),
            InsecurePatternSkill(),
            HardcodedCredentialSkill(),
            DependencyAuditSkill(),
        ]

        for skill in skills:
            self.active_skills[skill.name] = skill

        logger.info(f"Auto-registered {len(skills)} skills")

    async def execute_skill(
        self,
        skill_name: str,
        **kwargs
    ) -> SkillResult:
        """
        Execute a skill by name

        Args:
            skill_name: Name of skill to execute
            **kwargs: Skill parameters

        Returns:
            Skill execution result
        """
        # Check active skills first
        skill = self.active_skills.get(skill_name)

        # Check SKU manager
        if not skill and self.sku_manager:
            skill_class = self.sku_manager.get_skill(skill_name)
            if skill_class:
                skill = self.sku_manager.get_skill_instance(skill_name)

        # Fall back to registry
        if not skill:
            skill = SkillRegistry.get(skill_name)

        if not skill:
            return SkillResult(
                success=False,
                error=f"Skill '{skill_name}' not found"
            )

        # Create context
        context = SkillContext(self)

        # Execute
        return await skill.execute(context, **kwargs)

    async def run_skill_workflow(
        self,
        workflow_name: str,
        **kwargs
    ) -> SkillResult:
        """
        Run a skill workflow

        Args:
            workflow_name: Name of workflow
            **kwargs: Initial state parameters

        Returns:
            Workflow execution result
        """
        if not self.skill_orchestrator:
            return SkillResult(
                success=False,
                error="Skill orchestrator not initialized"
            )

        return await self.skill_orchestrator.run_workflow(
            workflow_name,
            kwargs
        )

    async def build_custom_workflow(
        self,
        skill_sequence: List[str],
        workflow_name: str = "custom"
    ) -> SkillGraphBuilder:
        """
        Build a custom workflow from skill sequence

        Args:
            skill_sequence: List of skill names in order
            workflow_name: Name for the workflow

        Returns:
            Graph builder
        """
        builder = SkillGraphBuilder(workflow_name)
        builder.set_agent(self)

        # Add skills
        for i, skill_name in enumerate(skill_sequence):
            node_name = f"step_{i}_{skill_name}"
            builder.add_skill(skill_name, node_name)

        # Add transitions
        builder.add_transition("START", f"step_0_{skill_sequence[0]}")

        for i in range(len(skill_sequence) - 1):
            from_node = f"step_{i}_{skill_sequence[i]}"
            to_node = f"step_{i+1}_{skill_sequence[i+1]}"
            builder.add_transition(from_node, to_node)

        builder.add_transition(f"step_{len(skill_sequence)-1}_{skill_sequence[-1]}", "END")

        return builder

    def get_available_skills(self) -> List[Dict[str, Any]]:
        """Get list of available skills (built-in + SKU)"""
        result = []

        # Built-in skills from registry
        all_skills = SkillRegistry.list_skills()
        for skill_name in all_skills:
            skill = SkillRegistry.get(skill_name)
            if skill:
                result.append({
                    "name": skill.name,
                    "description": skill.metadata.description,
                    "category": skill.metadata.category.value,
                    "required_tools": skill.metadata.required_tools,
                    "source": "builtin",
                })

        # SKU skills
        if self.sku_manager:
            capabilities = self.sku_manager.list_capabilities()
            for skill_info in capabilities.get("skills", []):
                result.append({
                    "name": skill_info["name"],
                    "description": f"From SKU: {skill_info['sku']}",
                    "category": "custom",
                    "required_tools": [],
                    "source": skill_info["sku"],
                })

        return result

    def get_available_workflows(self) -> List[str]:
        """Get list of available workflows"""
        if not self.skill_orchestrator:
            return []
        return self.skill_orchestrator.get_workflow_names()

    async def process_task(self, task: Dict[str, Any]) -> Any:
        """
        Process tasks with skill and SKU support

        Task types:
        - execute_skill: Execute a single skill
        - run_workflow: Run a skill workflow
        - build_workflow: Build custom workflow
        - get_skills: Get available skills
        - get_workflows: Get available workflows
        - load_sku: Load a SKU from path/URL/GitHub
        - unload_sku: Unload a SKU
        - list_skus: List loaded SKUs
        - get_capabilities: Get all capabilities
        """
        task_type = task.get("type")

        if task_type == "execute_skill":
            return await self._handle_execute_skill(task)

        if task_type == "run_workflow":
            return await self._handle_run_workflow(task)

        if task_type == "build_workflow":
            return await self._handle_build_workflow(task)

        if task_type == "get_skills":
            return {"skills": self.get_available_skills()}

        if task_type == "get_workflows":
            return {"workflows": self.get_available_workflows()}

        # SKU-related tasks
        if task_type == "load_sku":
            return await self._handle_load_sku(task)

        if task_type == "unload_sku":
            return await self._handle_unload_sku(task)

        if task_type == "list_skus":
            return {"skus": self.sku_manager.list_skus() if self.sku_manager else []}

        if task_type == "get_capabilities":
            return self._get_capabilities()

        # Fall back to base class
        return await super().process_task(task)

    async def _handle_execute_skill(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Handle execute_skill task"""
        skill_name = task.get("skill_name")
        params = task.get("params", {})

        if not skill_name:
            return {"success": False, "error": "skill_name required"}

        result = await self.execute_skill(skill_name, **params)

        return {
            "success": result.success,
            "data": result.data,
            "error": result.error,
            "skill": skill_name,
        }

    async def _handle_run_workflow(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Handle run_workflow task"""
        workflow_name = task.get("workflow_name", self.config.default_workflow)
        params = task.get("params", {})

        result = await self.run_skill_workflow(workflow_name, **params)

        return {
            "success": result.success,
            "data": result.data,
            "error": result.error,
            "workflow": workflow_name,
        }

    async def _handle_build_workflow(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Handle build_workflow task"""
        skill_sequence = task.get("skill_sequence", [])
        workflow_name = task.get("workflow_name", "custom")

        if not skill_sequence:
            return {"success": False, "error": "skill_sequence required"}

        try:
            builder = await self.build_custom_workflow(skill_sequence, workflow_name)
            graph = builder.build()

            # Store workflow
            if self.skill_orchestrator:
                self.skill_orchestrator.workflows[workflow_name] = graph

            return {
                "success": True,
                "workflow_name": workflow_name,
                "skills": skill_sequence,
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _handle_load_sku(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Handle load_sku task"""
        if not self.sku_manager:
            return {"success": False, "error": "SKU manager not enabled"}

        source = task.get("source")  # "path", "github", "url"

        try:
            if source == "path":
                from pathlib import Path
                sku = await self.sku_manager.load_sku(Path(task.get("path")))

            elif source == "github":
                sku = await self.sku_manager.load_sku_from_github(
                    task.get("repo"),
                    ref=task.get("ref", "main"),
                    subdir=task.get("subdir")
                )

            elif source == "url":
                sku = await self.sku_manager.loader.load_from_url(task.get("url"))

            else:
                return {"success": False, "error": f"Unknown source: {source}"}

            if not sku:
                return {"success": False, "error": "Failed to load SKU"}

            return {
                "success": True,
                "sku": {
                    "name": sku.metadata.name,
                    "version": sku.metadata.version,
                    "description": sku.metadata.description,
                }
            }

        except Exception as e:
            logger.error(f"Failed to load SKU: {e}")
            return {"success": False, "error": str(e)}

    async def _handle_unload_sku(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Handle unload_sku task"""
        if not self.sku_manager:
            return {"success": False, "error": "SKU manager not enabled"}

        name = task.get("name")
        if not name:
            return {"success": False, "error": "name required"}

        success = await self.sku_manager.unload_sku(name)
        return {"success": success}

    def _get_capabilities(self) -> Dict[str, Any]:
        """Get all agent capabilities"""
        capabilities = {
            "agent": {
                "name": self.config.name,
                "version": self.config.version,
                "type": "SkillEnabledAgent",
            },
            "workflows": self.get_available_workflows(),
            "skills": self.get_available_skills(),
            "features": {
                "langgraph": self.config.enable_langgraph,
                "skills": True,
                "sku": self.config.enable_sku,
                "memory": self.config.enable_memory,
            },
        }

        if self.sku_manager:
            capabilities["skus"] = self.sku_manager.list_skus()
            sku_capabilities = self.sku_manager.list_capabilities()
            capabilities["sku_skills"] = sku_capabilities.get("skills", [])
            capabilities["sku_tools"] = sku_capabilities.get("tools", [])

        return capabilities


# Export
__all__ = [
    "SkillAgentConfig",
    "SkillEnabledAgent",
]
