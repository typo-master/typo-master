"""
Tool System - Agent Tool Framework

This module provides the tool system for agents, including tool registration,
invocation, and management.
"""

import inspect
import functools
from typing import Any, Dict, List, Optional, Callable, TypeVar, get_type_hints
from dataclasses import dataclass, field
from enum import Enum
import json

from .logger import get_logger
from .permissions import (
    DEFAULT_PERMISSIONS,
    normalize_permissions,
    resolve_permission_for_tool,
    get_current_permissions,
)

logger = get_logger(__name__)

T = TypeVar('T')


class ToolCategory(Enum):
    """Tool categories"""
    GITHUB = "github"
    GIT = "git"
    SPELL_CHECK = "spell_check"
    FILE = "file"
    PR = "pr"
    REPORT = "report"
    UTILITY = "utility"
    AGENT = "agent"
    CUSTOM = "custom"


@dataclass
class ToolParameter:
    """Tool parameter definition"""
    name: str
    type: str
    description: str
    required: bool = True
    default: Any = None
    enum: Optional[List[Any]] = None


@dataclass
class ToolMetadata:
    """Tool metadata"""
    name: str
    description: str
    category: ToolCategory
    parameters: List[ToolParameter] = field(default_factory=list)
    version: str = "1.0.0"
    author: str = ""
    tags: List[str] = field(default_factory=list)
    examples: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class ToolResult:
    """Tool execution result"""
    success: bool
    data: Any = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


def tool(
    name: str,
    description: str,
    category: ToolCategory = ToolCategory.CUSTOM,
    version: str = "1.0.0",
    author: str = "",
    tags: Optional[List[str]] = None,
    examples: Optional[List[Dict[str, Any]]] = None,
):
    """
    Decorator to register a function as a tool
    
    Args:
        name: Tool name
        description: Tool description
        category: Tool category
        version: Tool version
        author: Tool author
        tags: Tool tags
        examples: Usage examples
    """
    def decorator(func: Callable) -> Callable:
        # Extract parameter information
        sig = inspect.signature(func)
        type_hints = get_type_hints(func)
        
        parameters = []
        for param_name, param in sig.parameters.items():
            if param_name == 'self':
                continue
            
            param_type = str(type_hints.get(param_name, 'any'))
            param_required = param.default == inspect.Parameter.empty
            param_default = param.default if not param_required else None
            
            parameter = ToolParameter(
                name=param_name,
                type=param_type,
                description=f"Parameter {param_name}",
                required=param_required,
                default=param_default,
            )
            parameters.append(parameter)
        
        # Create metadata
        metadata = ToolMetadata(
            name=name,
            description=description,
            category=category,
            parameters=parameters,
            version=version,
            author=author,
            tags=tags or [],
            examples=examples or [],
        )
        
        # Store metadata on the function
        func._tool_metadata = metadata
        func._is_tool = True
        
        return func
    
    return decorator


class ToolRegistry:
    """
    Central registry for tools

    Manages tool registration, discovery, and invocation.
    """

    def __init__(self, permissions: Optional[Dict[str, bool]] = None):
        self.tools: Dict[str, Callable] = {}
        self.metadata: Dict[str, ToolMetadata] = {}
        self.categories: Dict[ToolCategory, List[str]] = {}
        self.permissions_override = normalize_permissions(permissions) if permissions is not None else None

    def set_permissions(self, permissions: Optional[Dict[str, bool]]) -> None:
        self.permissions_override = normalize_permissions(permissions) if permissions is not None else None

    def refresh_permissions(self) -> None:
        if self.permissions_override is None:
            return
        self.permissions_override = normalize_permissions(get_current_permissions())
    
    def register(self, func: Callable) -> str:
        """
        Register a tool function
        
        Args:
            func: Tool function
            
        Returns:
            Tool name
        """
        if not hasattr(func, '_is_tool'):
            logger.warning(f"Function {func.__name__} is not decorated with @tool")
            return None
        
        metadata: ToolMetadata = func._tool_metadata
        tool_name = metadata.name
        
        # Register tool
        self.tools[tool_name] = func
        self.metadata[tool_name] = metadata
        
        # Add to category
        if metadata.category not in self.categories:
            self.categories[metadata.category] = []
        self.categories[metadata.category].append(tool_name)
        
        logger.info(f"Registered tool: {tool_name} ({metadata.category.value})")
        return tool_name
    
    def register_module(self, module: Any) -> List[str]:
        """
        Register all tools from a module
        
        Args:
            module: Module to register tools from
            
        Returns:
            List of registered tool names
        """
        registered = []
        
        for name, obj in inspect.getmembers(module):
            if inspect.isfunction(obj) and hasattr(obj, '_is_tool'):
                tool_name = self.register(obj)
                if tool_name:
                    registered.append(tool_name)
        
        logger.info(f"Registered {len(registered)} tools from module")
        return registered
    
    def get_tool(self, name: str) -> Optional[Callable]:
        """
        Get a tool by name
        
        Args:
            name: Tool name
            
        Returns:
            Tool function or None
        """
        return self.tools.get(name)
    
    def get_metadata(self, name: str) -> Optional[ToolMetadata]:
        """
        Get tool metadata
        
        Args:
            name: Tool name
            
        Returns:
            Tool metadata or None
        """
        return self.metadata.get(name)
    
    def list_tools(self, category: Optional[ToolCategory] = None) -> List[str]:
        """
        List all tools or tools in a category
        
        Args:
            category: Optional category filter
            
        Returns:
            List of tool names
        """
        if category:
            return self.categories.get(category, []).copy()
        return list(self.tools.keys())
    
    def get_tool_info(self, name: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed information about a tool
        
        Args:
            name: Tool name
            
        Returns:
            Tool information dictionary or None
        """
        metadata = self.metadata.get(name)
        if not metadata:
            return None
        
        return {
            "name": metadata.name,
            "description": metadata.description,
            "category": metadata.category.value,
            "version": metadata.version,
            "author": metadata.author,
            "tags": metadata.tags,
            "parameters": [
                {
                    "name": p.name,
                    "type": p.type,
                    "description": p.description,
                    "required": p.required,
                    "default": p.default,
                }
                for p in metadata.parameters
            ],
            "examples": metadata.examples,
        }
    
    async def invoke(self, name: str, **kwargs) -> ToolResult:
        """
        Invoke a tool
        
        Args:
            name: Tool name
            **kwargs: Tool arguments
            
        Returns:
            Tool result
        """
        tool_func = self.get_tool(name)
        if not tool_func:
            return ToolResult(
                success=False,
                error=f"Tool not found: {name}"
            )
        
        metadata = self.metadata.get(name)
        
        # Validate parameters
        for param in metadata.parameters:
            if param.required and param.name not in kwargs:
                return ToolResult(
                    success=False,
                    error=f"Missing required parameter: {param.name}"
                )
        
        permission_key = resolve_permission_for_tool(name)
        if permission_key:
            permissions = self.permissions_override
            if permissions is None:
                permissions = get_current_permissions()
            if not permissions.get(permission_key, DEFAULT_PERMISSIONS.get(permission_key, False)):
                return ToolResult(
                    success=False,
                    error=f"当前未启用【{permission_key}】权限，已拒绝执行。请在权限设置中开启该项。",
                )

        try:
            # Invoke tool
            result = tool_func(**kwargs)
            
            # Handle async functions
            if inspect.iscoroutine(result):
                result = await result
            
            return ToolResult(
                success=True,
                data=result,
                metadata={
                    "tool_name": name,
                    "execution_time": 0.0,
                }
            )
        
        except Exception as e:
            logger.error(f"Tool invocation error: {e}")
            return ToolResult(
                success=False,
                error=str(e)
            )
    
    def validate_tool(self, name: str) -> bool:
        """
        Validate a tool
        
        Args:
            name: Tool name
            
        Returns:
            True if tool is valid
        """
        tool_func = self.get_tool(name)
        if not tool_func:
            return False
        
        metadata = self.metadata.get(name)
        if not metadata:
            return False
        
        # Check function signature matches metadata
        sig = inspect.signature(tool_func)
        param_names = [p for p in sig.parameters.keys() if p != 'self']
        metadata_param_names = [p.name for p in metadata.parameters]
        
        if set(param_names) != set(metadata_param_names):
            logger.warning(f"Tool {name} signature mismatch")
            return False
        
        return True
    
    def export_schema(self) -> Dict[str, Any]:
        """
        Export tool schema for external systems
        
        Returns:
            Tool schema dictionary
        """
        schema = {
            "version": "1.0.0",
            "tools": {},
            "categories": {cat.value: tools for cat, tools in self.categories.items()},
        }
        
        for name, metadata in self.metadata.items():
            schema["tools"][name] = {
                "name": metadata.name,
                "description": metadata.description,
                "category": metadata.category.value,
                "version": metadata.version,
                "parameters": [
                    {
                        "name": p.name,
                        "type": p.type,
                        "description": p.description,
                        "required": p.required,
                        "default": p.default,
                    }
                    for p in metadata.parameters
                ],
                "tags": metadata.tags,
                "examples": metadata.examples,
            }
        
        return schema
    
    def import_schema(self, schema: Dict[str, Any]) -> None:
        """
        Import tool schema from external system
        
        Args:
            schema: Tool schema dictionary
        """
        # This would be used to load tool definitions from external sources
        # Implementation depends on the specific use case
        pass


# Built-in utility tools

@tool(
    name="echo",
    description="Echo back the input text",
    category=ToolCategory.UTILITY,
    examples=[{"input": {"text": "hello"}, "output": "hello"}]
)
async def echo_tool(text: str) -> str:
    """Echo the input text"""
    return text


@tool(
    name="get_time",
    description="Get the current timestamp",
    category=ToolCategory.UTILITY,
    examples=[{"output": "2024-01-01T00:00:00Z"}]
)
async def get_time_tool() -> str:
    """Get current timestamp"""
    from datetime import datetime
    return datetime.now().isoformat()


@tool(
    name="sleep",
    description="Sleep for a specified number of seconds",
    category=ToolCategory.UTILITY,
    examples=[{"input": {"seconds": 1}, "output": "slept for 1 second"}]
)
async def sleep_tool(seconds: float) -> str:
    """Sleep for specified seconds"""
    import asyncio
    await asyncio.sleep(seconds)
    return f"slept for {seconds} second(s)"
