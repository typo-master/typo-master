"""
Memory System Module - 统一记忆系统

提供多层级、多后端的记忆管理功能

架构:
- models: 数据模型
- backends: 各种存储后端
- manager: 统一管理器

Example:
    from src.agent_framework.memory import get_memory_manager

    memory = get_memory_manager("my_agent")

    # 存储
    await memory.remember(
        content="Important information",
        category="knowledge",
        importance=0.9
    )

    # 检索
    results = await memory.recall("search query", limit=5)
"""

from .models import MemoryEntry, MemoryQuery, MemoryConfig
from .manager import UnifiedMemoryManager, get_memory_manager
from .backends.base import BaseMemoryBackend
from .backends.file import FileBackend
from .backends.chroma import ChromaBackend
from .backends.mem0 import Mem0Backend

__all__ = [
    # Models
    "MemoryEntry",
    "MemoryQuery",
    "MemoryConfig",
    # Manager
    "UnifiedMemoryManager",
    "get_memory_manager",
    # Backends
    "BaseMemoryBackend",
    "FileBackend",
    "ChromaBackend",
    "Mem0Backend",
]
