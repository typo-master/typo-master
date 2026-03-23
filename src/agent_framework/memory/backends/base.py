"""
Base Memory Backend - 记忆后端抽象基类

所有记忆后端的基类接口
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from ..models import MemoryEntry


class BaseMemoryBackend(ABC):
    """记忆后端抽象基类"""

    @abstractmethod
    async def store(self, entry: MemoryEntry) -> bool:
        """存储记忆"""
        pass

    @abstractmethod
    async def retrieve(
        self,
        query: str,
        category: Optional[str] = None,
        limit: int = 10,
        filters: Optional[Dict] = None
    ) -> List[MemoryEntry]:
        """检索记忆"""
        pass

    @abstractmethod
    async def delete(self, memory_id: str) -> bool:
        """删除记忆"""
        pass

    @abstractmethod
    async def get_by_id(self, memory_id: str) -> Optional[MemoryEntry]:
        """根据ID获取记忆"""
        pass

    @abstractmethod
    async def clear(self, category: Optional[str] = None) -> bool:
        """清空记忆"""
        pass

    @abstractmethod
    async def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        pass
