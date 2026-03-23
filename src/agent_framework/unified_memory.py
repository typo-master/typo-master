"""
Unified Memory Module - 统一记忆系统入口

向后兼容的导入入口
"""

from .memory import (
    UnifiedMemoryManager,
    get_memory_manager,
    MemoryEntry,
    MemoryQuery,
    MemoryConfig,
)

__all__ = [
    "UnifiedMemoryManager",
    "get_memory_manager",
    "MemoryEntry",
    "MemoryQuery",
    "MemoryConfig",
]
