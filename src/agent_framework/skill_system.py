"""
Skill System - Agent Skill Framework

Skills are high-level capabilities that combine multiple tools to accomplish tasks.
"""

import inspect
import asyncio
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Callable, TypeVar, Set
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime

from .logger import get_logger
from .tool_system import ToolRegistry
from .base_agent import BaseAgent

logger = get_logger(__name__)

T = TypeVar('T')


class SkillCategory(Enum):
    """Skill categories"""
    SCAN = "scan"
    FIX = "fix"
    GIT = "git"
    GITHUB = "github"
    REPORT = "report"
    ANALYSIS = "analysis"
    CUSTOM = "custom"


class SkillLevel(Enum):
    """Skill proficiency levels"""
    NOVICE = 1
    INTERMEDIATE = 2
    ADVANCED = 3
    EXPERT = 4
    MASTER = 5


@dataclass
class SkillMetadata:
    """Skill metadata"""
    name: str
    description: str
    category: SkillCategory
    version: str = "1.0.0"
    author: str = ""
    required_tools: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    examples: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class SkillResult:
    """Skill execution result"""
    success: bool
    data: Any = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    execution_time: float = 0.0
    steps_executed: List[str] = field(default_factory=list)


class SkillContext:
    """
    Context passed to skills during execution

    Provides access to:
    - Agent instance
    - Memory manager
    - Tool registry
    - Execution state
    """

    def __init__(self, agent: Optional[BaseAgent] = None):
        self.agent = agent
        self.memory = agent.memory_manager if agent else None
        self.tools = ToolRegistry()
        self.state: Dict[str, Any] = {}
        self.execution_log: List[Dict] = []

    def get_tool(self, name: str) -> Optional[Callable]:
        """Get a tool by name"""
        return self.tools.get_tool(name)

    async def call_tool(self, name: str, **kwargs) -> Any:
        """Call a tool with arguments"""
        tool = self.get_tool(name)
        if not tool:
            raise ValueError(f"Tool '{name}' not found")

        # Log tool call
        self.execution_log.append({
            "tool": name,
            "args": kwargs,
            "timestamp": datetime.now().isoformat()
        })

        return await tool(**kwargs)

    def remember(self, key: str, value: Any):
        """Store in skill context state"""
        self.state[key] = value

    def recall(self, key: str) -> Optional[Any]:
        """Retrieve from skill context state"""
        return self.state.get(key)


class BaseSkill(ABC):
    """
    Base class for all skills

    Skills are higher-level abstractions that orchestrate multiple tools
    to accomplish complex tasks.
    """

    def __init__(self, metadata: SkillMetadata):
        self.metadata = metadata
        self._execution_count = 0
        self._success_count = 0
        logger.info(f"Skill '{metadata.name}' initialized")

    @property
    def name(self) -> str:
        return self.metadata.name

    @property
    def category(self) -> SkillCategory:
        return self.metadata.category

    @abstractmethod
    async def execute(self, context: SkillContext, **kwargs) -> SkillResult:
        """
        Execute the skill

        Args:
            context: Skill execution context
            **kwargs: Skill-specific parameters

        Returns:
            Skill execution result
        """
        pass

    async def __call__(self, agent: Optional[BaseAgent] = None, **kwargs) -> SkillResult:
        """
        Execute skill with automatic context creation

        Args:
            agent: Optional agent instance
            **kwargs: Skill parameters

        Returns:
            Skill execution result
        """
        import time

        context = SkillContext(agent)
        start_time = time.time()

        try:
            result = await self.execute(context, **kwargs)
            result.execution_time = time.time() - start_time
            self._execution_count += 1
            if result.success:
                self._success_count += 1
            return result
        except Exception as e:
            logger.error(f"Skill '{self.name}' execution failed: {e}")
            return SkillResult(
                success=False,
                error=str(e),
                execution_time=time.time() - start_time
            )

    def get_stats(self) -> Dict[str, Any]:
        """Get skill execution statistics"""
        return {
            "name": self.name,
            "executions": self._execution_count,
            "successes": self._success_count,
            "success_rate": self._success_count / self._execution_count if self._execution_count > 0 else 0,
        }


class SkillRegistry:
    """
    Global skill registry

    Manages all available skills and provides skill discovery.
    """

    _skills: Dict[str, BaseSkill] = {}
    _categories: Dict[SkillCategory, Set[str]] = {}

    @classmethod
    def register(cls, skill: BaseSkill) -> None:
        """Register a skill"""
        cls._skills[skill.name] = skill

        if skill.category not in cls._categories:
            cls._categories[skill.category] = set()
        cls._categories[skill.category].add(skill.name)

        logger.info(f"Skill '{skill.name}' registered")

    @classmethod
    def get(cls, name: str) -> Optional[BaseSkill]:
        """Get a skill by name"""
        return cls._skills.get(name)

    @classmethod
    def list_skills(cls, category: Optional[SkillCategory] = None) -> List[str]:
        """List all registered skills"""
        if category:
            return list(cls._categories.get(category, set()))
        return list(cls._skills.keys())

    @classmethod
    def get_by_category(cls, category: SkillCategory) -> List[BaseSkill]:
        """Get all skills in a category"""
        names = cls._categories.get(category, set())
        return [cls._skills[n] for n in names if n in cls._skills]

    @classmethod
    def search(cls, query: str) -> List[BaseSkill]:
        """Search skills by name or description"""
        results = []
        query_lower = query.lower()

        for skill in cls._skills.values():
            if (query_lower in skill.name.lower() or
                query_lower in skill.metadata.description.lower()):
                results.append(skill)

        return results

    @classmethod
    def clear(cls):
        """Clear all registered skills"""
        cls._skills.clear()
        cls._categories.clear()


def skill(
    name: str,
    description: str,
    category: SkillCategory = SkillCategory.CUSTOM,
    version: str = "1.0.0",
    author: str = "",
    required_tools: Optional[List[str]] = None,
    tags: Optional[List[str]] = None,
    examples: Optional[List[Dict[str, Any]]] = None,
):
    """
    Decorator to register a class as a skill

    Args:
        name: Skill name
        description: Skill description
        category: Skill category
        version: Skill version
        author: Skill author
        required_tools: Required tool names
        tags: Skill tags
        examples: Usage examples
    """
    def decorator(cls):
        # Create metadata
        metadata = SkillMetadata(
            name=name,
            description=description,
            category=category,
            version=version,
            author=author,
            required_tools=required_tools or [],
            tags=tags or [],
            examples=examples or [],
        )

        # Store metadata on class
        cls._metadata = metadata

        # Register on import
        original_init = cls.__init__

        def new_init(self, *args, **kwargs):
            original_init(self, metadata, *args, **kwargs)

        cls.__init__ = new_init

        # Auto-register
        try:
            instance = cls()
            SkillRegistry.register(instance)
        except Exception as e:
            logger.warning(f"Failed to auto-register skill '{name}': {e}")

        return cls

    return decorator


# Export
__all__ = [
    "SkillCategory",
    "SkillLevel",
    "SkillMetadata",
    "SkillResult",
    "SkillContext",
    "BaseSkill",
    "SkillRegistry",
    "skill",
]
