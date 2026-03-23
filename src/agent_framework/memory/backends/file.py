"""
File Memory Backend - 文件系统记忆后端

提供基于文件的持久化存储，简单可靠
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from ...logger import get_logger
from ..models import MemoryEntry
from .base import BaseMemoryBackend

logger = get_logger(__name__)


class FileBackend(BaseMemoryBackend):
    """
    文件系统记忆后端

    用于：
    - 关键状态备份
    - 配置持久化
    - 作为fallback
    """

    def __init__(self, storage_path: str = "./agent_memory"):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self._memories: Dict[str, MemoryEntry] = {}
        self._loaded = False

    async def _load(self):
        """加载已有记忆"""
        if self._loaded:
            return

        try:
            for file_path in self.storage_path.glob("*.json"):
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    entry = MemoryEntry.from_dict(data)
                    self._memories[entry.id] = entry

            self._loaded = True
            logger.info(f"FileBackend loaded {len(self._memories)} memories")
        except Exception as e:
            logger.error(f"FileBackend load failed: {e}")
            self._loaded = True

    async def store(self, entry: MemoryEntry) -> bool:
        """存储记忆到文件"""
        await self._load()

        try:
            self._memories[entry.id] = entry

            file_path = self.storage_path / f"{entry.id}.json"
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(entry.to_dict(), f, indent=2, default=str)

            return True
        except Exception as e:
            logger.error(f"FileBackend store failed: {e}")
            return False

    async def retrieve(
        self,
        query: str,
        category: Optional[str] = None,
        limit: int = 10,
        filters: Optional[Dict] = None
    ) -> List[MemoryEntry]:
        """检索记忆（简单文本匹配）"""
        await self._load()

        results = []
        query_lower = query.lower()

        for entry in self._memories.values():
            if category and entry.category != category:
                continue

            if filters:
                match = True
                for k, v in filters.items():
                    if entry.metadata.get(k) != v:
                        match = False
                        break
                if not match:
                    continue

            if query_lower in entry.content.lower():
                results.append(entry)

            if len(results) >= limit:
                break

        # 按重要性排序
        results.sort(key=lambda x: x.importance, reverse=True)
        return results

    async def delete(self, memory_id: str) -> bool:
        """删除记忆"""
        await self._load()

        if memory_id not in self._memories:
            return False

        try:
            del self._memories[memory_id]
            file_path = self.storage_path / f"{memory_id}.json"
            if file_path.exists():
                file_path.unlink()
            return True
        except Exception as e:
            logger.error(f"FileBackend delete failed: {e}")
            return False

    async def get_by_id(self, memory_id: str) -> Optional[MemoryEntry]:
        """根据ID获取记忆"""
        await self._load()
        return self._memories.get(memory_id)

    async def clear(self, category: Optional[str] = None) -> bool:
        """清空记忆"""
        await self._load()

        try:
            if category:
                to_delete = [k for k, v in self._memories.items() if v.category == category]
                for k in to_delete:
                    await self.delete(k)
            else:
                for file_path in self.storage_path.glob("*.json"):
                    file_path.unlink()
                self._memories.clear()

            return True
        except Exception as e:
            logger.error(f"FileBackend clear failed: {e}")
            return False

    async def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        try:
            await self._load()
            return {
                "success": True,
                "backend": "file",
                "memories_count": len(self._memories),
                "storage_path": str(self.storage_path),
            }
        except Exception as e:
            return {
                "success": False,
                "backend": "file",
                "error": str(e),
            }
