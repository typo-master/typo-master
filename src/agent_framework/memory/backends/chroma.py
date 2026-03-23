"""
Chroma Memory Backend - ChromaDB向量记忆后端

提供语义搜索和向量存储
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from ...logger import get_logger
from ..models import MemoryEntry
from .base import BaseMemoryBackend

logger = get_logger(__name__)


class ChromaBackend(BaseMemoryBackend):
    """
    ChromaDB 向量记忆后端

    特性：
    - 本地向量存储
    - 语义相似度搜索
    - 元数据过滤
    """

    def __init__(self, collection_name: str = "agent_memory", path: str = "./chroma_db"):
        self.collection_name = collection_name
        self.path = path
        self._client = None
        self._collection = None
        self._initialized = False

    async def _ensure_initialized(self):
        """延迟初始化 ChromaDB"""
        if self._initialized:
            return

        try:
            import chromadb
            from chromadb.config import Settings

            Path(self.path).mkdir(parents=True, exist_ok=True)

            self._client = chromadb.PersistentClient(
                path=self.path,
                settings=Settings(
                    anonymized_telemetry=False,
                    allow_reset=True,
                )
            )

            self._collection = self._client.get_or_create_collection(
                name=self.collection_name,
                metadata={"hnsw:space": "cosine"}
            )

            self._initialized = True
            logger.info(f"ChromaDB backend initialized at {self.path}")
        except ImportError:
            logger.warning("chromadb not installed, using fallback")
            self._initialized = True
        except Exception as e:
            logger.error(f"Failed to initialize ChromaDB: {e}")
            self._initialized = True

    async def _generate_embedding(self, text: str) -> List[float]:
        """生成文本embedding"""
        try:
            import openai
            import os

            client = openai.OpenAI(
                api_key=os.getenv("OPENAI_API_KEY"),
                base_url=os.getenv("OPENAI_BASE_URL", "https://api.openai.com"),
            )
            response = client.embeddings.create(
                model="text-embedding-3-small",
                input=text[:8000]
            )
            return response.data[0].embedding
        except Exception as e:
            # Fallback: hash-based embedding
            logger.debug(f"API embedding failed, using fallback: {e}")
            import hashlib
            hash_obj = hashlib.sha256(text.encode())
            hash_bytes = hash_obj.digest()
            embedding = [float(b) / 255.0 for b in hash_bytes[:128]]
            embedding.extend([0.0] * (128 - len(embedding)))
            return embedding

    def _flatten_metadata(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """将元数据扁平化（ChromaDB不支持嵌套字典）"""
        flattened = {}
        for k, v in metadata.items():
            if isinstance(v, (str, int, float, bool, list)):
                flattened[k] = v
            else:
                # 其他类型转为JSON字符串
                flattened[k] = json.dumps(v, default=str)
        return flattened

    async def store(self, entry: MemoryEntry) -> bool:
        """存储记忆到ChromaDB"""
        await self._ensure_initialized()
        if not self._collection:
            return False

        try:
            if entry.embedding is None:
                entry.embedding = await self._generate_embedding(entry.content)

            # 扁平化元数据
            metadata = self._flatten_metadata({
                "category": entry.category,
                "timestamp": entry.timestamp.isoformat(),
                "importance": entry.importance,
                "source": entry.source,
                **entry.metadata
            })

            self._collection.add(
                ids=[entry.id],
                embeddings=[entry.embedding],
                documents=[entry.content],
                metadatas=[metadata]
            )

            return True
        except Exception as e:
            logger.error(f"ChromaDB store failed: {e}")
            return False

    async def retrieve(
        self,
        query: str,
        category: Optional[str] = None,
        limit: int = 10,
        filters: Optional[Dict] = None
    ) -> List[MemoryEntry]:
        """语义搜索记忆"""
        await self._ensure_initialized()
        if not self._collection:
            return []

        try:
            query_embedding = await self._generate_embedding(query)

            where = {}
            if category:
                where["category"] = category
            if filters:
                where.update(filters)

            results = self._collection.query(
                query_embeddings=[query_embedding],
                n_results=limit,
                where=where if where else None,
            )

            entries = []
            if results["ids"] and results["ids"][0]:
                for i, memory_id in enumerate(results["ids"][0]):
                    metadata = results["metadatas"][0][i] if results["metadatas"] else {}
                    entry = MemoryEntry(
                        id=memory_id,
                        content=results["documents"][0][i],
                        metadata=metadata,
                        category=metadata.get("category", "general"),
                        timestamp=__import__('datetime').datetime.fromisoformat(
                            metadata.get("timestamp", __import__('datetime').datetime.now().isoformat())
                        ),
                        importance=float(metadata.get("importance", 1.0)),
                        source=metadata.get("source", ""),
                    )
                    entries.append(entry)

            return entries
        except Exception as e:
            logger.error(f"ChromaDB retrieve failed: {e}")
            return []

    async def delete(self, memory_id: str) -> bool:
        """删除记忆"""
        await self._ensure_initialized()
        if not self._collection:
            return False

        try:
            self._collection.delete(ids=[memory_id])
            return True
        except Exception as e:
            logger.error(f"ChromaDB delete failed: {e}")
            return False

    async def get_by_id(self, memory_id: str) -> Optional[MemoryEntry]:
        """根据ID获取记忆"""
        await self._ensure_initialized()
        if not self._collection:
            return None

        try:
            result = self._collection.get(ids=[memory_id])
            if result["ids"] and len(result["ids"]) > 0:
                metadata = result["metadatas"][0]
                return MemoryEntry(
                    id=memory_id,
                    content=result["documents"][0],
                    metadata=metadata,
                    category=metadata.get("category", "general"),
                    timestamp=__import__('datetime').datetime.fromisoformat(
                        metadata.get("timestamp", __import__('datetime').datetime.now().isoformat())
                    ),
                    importance=float(metadata.get("importance", 1.0)),
                    source=metadata.get("source", ""),
                )
            return None
        except Exception as e:
            logger.error(f"ChromaDB get_by_id failed: {e}")
            return None

    async def clear(self, category: Optional[str] = None) -> bool:
        """清空记忆"""
        await self._ensure_initialized()
        if not self._collection:
            return False

        try:
            if category:
                self._collection.delete(where={"category": category})
            else:
                self._client.delete_collection(self.collection_name)
                self._collection = self._client.get_or_create_collection(
                    name=self.collection_name,
                    metadata={"hnsw:space": "cosine"}
                )
            return True
        except Exception as e:
            logger.error(f"ChromaDB clear failed: {e}")
            return False

    async def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        try:
            await self._ensure_initialized()
            if self._collection:
                count = self._collection.count()
                return {
                    "success": True,
                    "backend": "chroma",
                    "memories_count": count,
                    "path": self.path,
                }
            return {
                "success": False,
                "backend": "chroma",
                "error": "Collection not initialized",
            }
        except Exception as e:
            return {
                "success": False,
                "backend": "chroma",
                "error": str(e),
            }
