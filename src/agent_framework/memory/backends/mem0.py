"""
Mem0 Memory Backend - Mem0自适应记忆后端

提供自适应个性化记忆功能
"""

from typing import Any, Dict, List, Optional

from ...logger import get_logger
from ..models import MemoryEntry
from .base import BaseMemoryBackend

logger = get_logger(__name__)


class Mem0Backend(BaseMemoryBackend):
    """
    Mem0 记忆后端 - 自适应个性化记忆

    特性：
    - 自动提取重要信息
    - 跨会话保持
    - 自改进机制
    """

    def __init__(self, api_key: Optional[str] = None, user_id: str = "default"):
        self.api_key = api_key
        self.user_id = user_id
        self._client = None
        self._initialized = False

    async def _ensure_initialized(self):
        """延迟初始化 Mem0 客户端"""
        if self._initialized:
            return

        try:
            from mem0 import Memory

            config = {
                "vector_store": {
                    "provider": "chroma",
                    "config": {
                        "path": "./mem0_data",
                    }
                },
                "llm": {
                    "provider": "openai",
                    "config": {
                        "model": "gpt-4o-mini",
                    }
                },
                "embedder": {
                    "provider": "openai",
                    "config": {
                        "model": "text-embedding-3-small",
                    }
                }
            }

            self._client = Memory.from_config(config_dict=config)
            self._initialized = True
            logger.info("Mem0 backend initialized")
        except ImportError:
            logger.warning("mem0 not installed, using fallback")
            self._initialized = True
            self._client = None
        except Exception as e:
            logger.error(f"Failed to initialize Mem0: {e}")
            self._initialized = True
            self._client = None

    async def store(self, entry: MemoryEntry) -> bool:
        """存储记忆到Mem0"""
        await self._ensure_initialized()
        if not self._client:
            return False

        try:
            messages = [
                {"role": "user", "content": entry.content},
            ]

            result = self._client.add(
                messages=messages,
                user_id=self.user_id,
                metadata=entry.metadata,
            )

            logger.debug(f"Mem0 stored memory: {result}")
            return True
        except Exception as e:
            logger.error(f"Mem0 store failed: {e}")
            return False

    async def retrieve(
        self,
        query: str,
        category: Optional[str] = None,
        limit: int = 10,
        filters: Optional[Dict] = None
    ) -> List[MemoryEntry]:
        """从Mem0检索记忆"""
        await self._ensure_initialized()
        if not self._client:
            return []

        try:
            results = self._client.search(
                query=query,
                user_id=self.user_id,
                limit=limit,
            )

            entries = []
            for result in results:
                entry = MemoryEntry(
                    id=result.get("id", "mem0_" + str(__import__('uuid').uuid4())[:8]),
                    content=result.get("memory", ""),
                    metadata=result.get("metadata", {}),
                    category=category or "general",
                    importance=result.get("score", 1.0),
                )
                entries.append(entry)

            return entries
        except Exception as e:
            logger.error(f"Mem0 retrieve failed: {e}")
            return []

    async def delete(self, memory_id: str) -> bool:
        """删除记忆"""
        await self._ensure_initialized()
        if not self._client:
            return False

        try:
            self._client.delete(memory_id=memory_id)
            return True
        except Exception as e:
            logger.error(f"Mem0 delete failed: {e}")
            return False

    async def get_by_id(self, memory_id: str) -> Optional[MemoryEntry]:
        """Mem0不支持直接ID查询"""
        return None

    async def clear(self, category: Optional[str] = None) -> bool:
        """清空记忆"""
        await self._ensure_initialized()
        if not self._client:
            return False

        try:
            self._client.delete_all(user_id=self.user_id)
            return True
        except Exception as e:
            logger.error(f"Mem0 clear failed: {e}")
            return False

    async def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        try:
            await self._ensure_initialized()
            return {
                "success": bool(self._client),
                "backend": "mem0",
                "user_id": self.user_id,
            }
        except Exception as e:
            return {
                "success": False,
                "backend": "mem0",
                "error": str(e),
            }
