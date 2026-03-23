"""
Skill LangGraph Integration - Bridge between Skills and LangGraph

This module provides integration between the Skill system and LangGraph,
enabling Skills to be used as nodes in LangGraph workflows.
"""

from typing import Any, Dict, List, Optional, Callable, TypedDict
from dataclasses import dataclass, field
from datetime import datetime
import asyncio

from langgraph.graph import StateGraph, END, START
from langgraph.checkpoint.base import BaseCheckpointSaver

from .skill_system import (
    BaseSkill, SkillContext, SkillResult, SkillRegistry, SkillCategory
)
from .base_agent import BaseAgent
from .logger import get_logger

logger = get_logger(__name__)


class SkillState(TypedDict, total=False):
    """Base state for Skill-based LangGraph workflows"""
    # Input parameters
    skill_name: str
    skill_params: Dict[str, Any]

    # Execution state
    skill_results: Dict[str, Any]
    skill_errors: List[str]
    executed_skills: List[str]

    # Context
    agent_id: str
    memory_context: Dict[str, Any]

    # Output
    result: Dict[str, Any]
    error: str


@dataclass
class SkillNodeConfig:
    """Configuration for a skill node in the graph"""
    skill_name: str
    node_name: Optional[str] = None
    conditional: bool = False
    retry_on_error: bool = True
    max_retries: int = 3
    save_result: bool = True
    depends_on: List[str] = field(default_factory=list)


class SkillNodeWrapper:
    """
    Wrapper to execute a Skill as a LangGraph node

    This allows Skills to be used directly as nodes in LangGraph workflows,
    with automatic state management and error handling.
    """

    def __init__(
        self,
        skill: BaseSkill,
        agent: Optional[BaseAgent] = None,
        save_to_memory: bool = True,
    ):
        self.skill = skill
        self.agent = agent
        self.save_to_memory = save_to_memory
        self.execution_count = 0

    async def __call__(self, state: SkillState) -> Dict[str, Any]:
        """
        Execute skill with state from LangGraph

        Args:
            state: Current workflow state

        Returns:
            Updates to state
        """
        self.execution_count += 1

        # Create skill context
        context = SkillContext(self.agent)

        # Load memory context if available
        if self.agent and self.agent.memory_manager:
            try:
                memory_context = await self._build_memory_context()
                context.state["memory"] = memory_context
            except Exception as e:
                logger.warning(f"Failed to load memory context: {e}")

        # Get skill parameters from state
        # First check skill_params, then fall back to state itself
        params = state.get("skill_params", {}).copy()

        # Add common parameters from state (for workflow execution)
        common_params = [
            "repo_path", "owner", "repo", "typos", "output_path",
            "file_paths", "create_pr", "pr_title", "pr_body", "branch_name"
        ]
        for param in common_params:
            if param in state and param not in params:
                params[param] = state[param]

        try:
            # Execute skill
            logger.info(f"Executing skill '{self.skill.name}' (run #{self.execution_count})")
            result = await self.skill.execute(context, **params)

            # Build update
            update: Dict[str, Any] = {
                "skill_results": {
                    **state.get("skill_results", {}),
                    self.skill.name: result.data if result.success else None,
                }
            }

            if result.success:
                update["executed_skills"] = state.get("executed_skills", []) + [self.skill.name]

                # Save to memory if enabled
                if self.save_to_memory and self.agent and self.agent.memory_manager:
                    await self._save_to_memory(result, params)

            else:
                # Handle error
                error_msg = f"Skill '{self.skill.name}' failed: {result.error}"
                logger.error(error_msg)
                update["skill_errors"] = state.get("skill_errors", []) + [error_msg]

                # Retry logic
                if result.error and self.skill.metadata.required_tools:
                    update["retry_count"] = state.get("retry_count", 0) + 1

            return update

        except Exception as e:
            error_msg = f"Skill '{self.skill.name}' execution error: {e}"
            logger.error(error_msg)
            return {
                "skill_errors": state.get("skill_errors", []) + [error_msg],
                "error": error_msg,
            }

    async def _build_memory_context(self) -> Dict[str, Any]:
        """Build context from agent memory"""
        if not self.agent or not self.agent.memory_manager:
            return {}

        context = {}

        # Get similar experiences
        try:
            experiences = await self.agent.memory_manager.get_similar_experiences(
                self.skill.name, limit=3
            )
            if experiences:
                context["similar_experiences"] = [
                    {
                        "content": e.content,
                        "metadata": e.metadata,
                    }
                    for e in experiences
                ]
        except Exception as e:
            logger.debug(f"Failed to get similar experiences: {e}")

        # Get relevant knowledge
        try:
            knowledge = await self.agent.memory_manager.recall(
                self.skill.name, category="knowledge", limit=3
            )
            if knowledge:
                context["relevant_knowledge"] = [
                    {"content": k.content, "metadata": k.metadata}
                    for k in knowledge
                ]
        except Exception as e:
            logger.debug(f"Failed to get relevant knowledge: {e}")

        return context

    async def _save_to_memory(self, result: SkillResult, params: Dict[str, Any]):
        """Save skill execution to memory"""
        if not self.agent or not self.agent.memory_manager:
            return

        try:
            # Remember experience
            await self.agent.memory_manager.remember_experience(
                task_type=f"skill:{self.skill.name}",
                input_data=params,
                result=result.data if result.success else {"error": result.error},
                success=result.success
            )
        except Exception as e:
            logger.warning(f"Failed to save skill execution to memory: {e}")


class SkillGraphBuilder:
    """
    Builder for creating LangGraph workflows with Skills

    Simplifies the creation of LangGraph workflows using Skills as nodes.
    """

    def __init__(self, name: str = "skill_workflow"):
        self.name = name
        self.skills: Dict[str, SkillNodeConfig] = {}
        self.transitions: List[tuple] = []
        self.conditional_transitions: Dict[str, Callable] = {}
        self.agent: Optional[BaseAgent] = None

    def set_agent(self, agent: BaseAgent):
        """Set agent for skill execution"""
        self.agent = agent
        return self

    def add_skill(
        self,
        skill_name: str,
        node_name: Optional[str] = None,
        conditional: bool = False,
        **kwargs
    ) -> "SkillGraphBuilder":
        """
        Add a skill to the workflow

        Args:
            skill_name: Name of registered skill
            node_name: Optional custom node name
            conditional: Whether this is a conditional node
            **kwargs: Additional config options

        Returns:
            Self for chaining
        """
        config = SkillNodeConfig(
            skill_name=skill_name,
            node_name=node_name or skill_name,
            conditional=conditional,
            **kwargs
        )
        self.skills[config.node_name] = config
        return self

    def add_transition(self, from_node: str, to_node: str):
        """Add a simple transition between nodes"""
        self.transitions.append((from_node, to_node))
        return self

    def add_conditional_transition(
        self,
        from_node: str,
        condition: Callable,
        routes: Dict[str, str]
    ):
        """
        Add a conditional transition

        Args:
            from_node: Source node
            condition: Function that returns route key based on state
            routes: Mapping of route keys to destination nodes
        """
        self.conditional_transitions[from_node] = (condition, routes)
        return self

    def build(self) -> StateGraph:
        """
        Build the LangGraph workflow

        Returns:
            Compiled StateGraph
        """
        # Create graph
        graph = StateGraph(SkillState)

        # Add nodes
        for node_name, config in self.skills.items():
            skill = SkillRegistry.get(config.skill_name)
            if not skill:
                raise ValueError(f"Skill '{config.skill_name}' not found in registry")

            wrapper = SkillNodeWrapper(skill, self.agent)
            graph.add_node(node_name, wrapper)

        # Add edges
        for from_node, to_node in self.transitions:
            if from_node == "START":
                graph.add_edge(START, to_node)
            elif to_node == "END":
                graph.add_edge(from_node, END)
            else:
                graph.add_edge(from_node, to_node)

        # Add conditional edges
        for from_node, (condition, routes) in self.conditional_transitions.items():
            graph.add_conditional_edges(from_node, condition, routes)

        return graph.compile()


class SkillOrchestrator:
    """
    Orchestrates multiple skills in a workflow

    Provides high-level workflow management with skill composition.
    """

    def __init__(self, agent: Optional[BaseAgent] = None):
        self.agent = agent
        self.workflows: Dict[str, Any] = {}
        self._workflow_builders: Dict[str, Callable] = {}
        self._initialized = False

    def initialize(self):
        """Initialize workflows after skills are registered"""
        if self._initialized:
            return

        self._build_default_workflows()
        self._initialized = True

    def _register_workflow_builder(self, name: str, builder_fn: Callable):
        """Register a workflow builder for lazy initialization"""
        self._workflow_builders[name] = builder_fn

    def _build_default_workflows(self):
        """Build default typo hunting workflows"""
        # Single project workflow
        try:
            self.workflows["single_project"] = self._build_single_project_workflow()
        except ValueError as e:
            logger.warning(f"Could not build single_project workflow: {e}")

        # Batch workflow
        try:
            self.workflows["batch"] = self._build_batch_workflow()
        except ValueError as e:
            logger.warning(f"Could not build batch workflow: {e}")

        # Scan only workflow
        try:
            self.workflows["scan_only"] = self._build_scan_only_workflow()
        except ValueError as e:
            logger.warning(f"Could not build scan_only workflow: {e}")

    def _build_single_project_workflow(self):
        """Build single project typo fix workflow"""
        builder = SkillGraphBuilder("single_project")
        if self.agent:
            builder.set_agent(self.agent)

        # Add skills
        builder.add_skill("repository_scan", "scan")
        builder.add_skill("typo_fix", "fix")
        builder.add_skill("git_operations", "git")
        builder.add_skill("typo_report", "report")

        # Add transitions
        builder.add_transition("START", "scan")
        builder.add_transition("scan", "fix")
        builder.add_transition("fix", "git")
        builder.add_transition("git", "report")
        builder.add_transition("report", "END")

        # Add conditional transition from scan
        def route_after_scan(state: SkillState):
            scan_result = state.get("skill_results", {}).get("repository_scan")
            if not scan_result or scan_result.get("total_typos", 0) == 0:
                return "end"
            return "continue"

        builder.add_conditional_transition(
            "scan",
            route_after_scan,
            {"continue": "fix", "end": "report"}
        )

        return builder.build()

    def _build_batch_workflow(self):
        """Build batch processing workflow"""
        builder = SkillGraphBuilder("batch")
        if self.agent:
            builder.set_agent(self.agent)

        # For batch, we use the single project workflow in a loop
        # This is simplified - in practice you'd use a map-reduce pattern
        builder.add_skill("repository_scan", "scan")
        builder.add_transition("START", "scan")
        builder.add_transition("scan", "END")

        return builder.build()

    def _build_scan_only_workflow(self):
        """Build scan-only workflow (no fixes)"""
        builder = SkillGraphBuilder("scan_only")
        if self.agent:
            builder.set_agent(self.agent)

        builder.add_skill("repository_scan", "scan")
        builder.add_skill("typo_report", "report")

        builder.add_transition("START", "scan")
        builder.add_transition("scan", "report")
        builder.add_transition("report", "END")

        return builder.build()

    async def run_workflow(
        self,
        workflow_name: str,
        initial_state: Dict[str, Any],
    ) -> SkillResult:
        """
        Run a workflow

        Args:
            workflow_name: Name of workflow to run
            initial_state: Initial state for workflow

        Returns:
            Skill result with workflow output
        """
        workflow = self.workflows.get(workflow_name)
        if not workflow:
            return SkillResult(
                success=False,
                error=f"Workflow '{workflow_name}' not found"
            )

        try:
            # Prepare state
            state: SkillState = {
                **initial_state,
                "skill_results": {},
                "skill_errors": [],
                "executed_skills": [],
            }

            # Execute workflow
            logger.info(f"Starting workflow '{workflow_name}'")
            final_state = await workflow.ainvoke(state)

            # Build result
            result_data = {
                "workflow": workflow_name,
                "executed_skills": final_state.get("executed_skills", []),
                "skill_results": final_state.get("skill_results", {}),
                "skill_errors": final_state.get("skill_errors", []),
            }

            # Check for errors
            errors = final_state.get("skill_errors", [])
            if errors:
                return SkillResult(
                    success=False,
                    data=result_data,
                    error="; ".join(errors)
                )

            return SkillResult(
                success=True,
                data=result_data
            )

        except Exception as e:
            logger.error(f"Workflow '{workflow_name}' failed: {e}")
            return SkillResult(
                success=False,
                error=str(e)
            )

    def get_workflow_names(self) -> List[str]:
        """Get list of available workflows"""
        return list(self.workflows.keys())


# Export
__all__ = [
    "SkillState",
    "SkillNodeConfig",
    "SkillNodeWrapper",
    "SkillGraphBuilder",
    "SkillOrchestrator",
]
