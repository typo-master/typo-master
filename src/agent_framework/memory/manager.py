"""
Memory Manager - 统一记忆管理器

整合多种记忆后端，提供统一接口
"""

import json
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..logger import get_logger
from .models import MemoryConfig, MemoryEntry
from .backends.base import BaseMemoryBackend
from .backends.file import FileBackend
from .backends.chroma import ChromaBackend
from .backends.mem0 import Mem0Backend

logger = get_logger(__name__)


class UnifiedMemoryManager:
    """
    统一记忆管理器

    架构：
    - L1: 工作内存 (内存) - 临时
    - L2: ChromaDB (向量) - 会话级
    - L3: Mem0 (自适应) - 跨会话
    - L4: File (文件) - 关键状态
    """

    def __init__(self, config: Optional[MemoryConfig] = None, **kwargs):
        """
        初始化记忆管理器

        Args:
            config: MemoryConfig对象，或直接用关键字参数
        """
        if config is None:
            config = MemoryConfig(**kwargs)

        self.config = config
        self.agent_id = config.agent_id

        # 创建存储路径
        self.storage_path = Path(config.storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)

        # 初始化各层后端
        self.backends: Dict[str, BaseMemoryBackend] = {}

        if config.enable_chroma:
            chroma_path = self.storage_path / "chroma"
            self.backends["chroma"] = ChromaBackend(
                collection_name=f"agent_{self.agent_id}",
                path=str(chroma_path)
            )

        if config.enable_mem0:
            import os
            self.backends["mem0"] = Mem0Backend(
                api_key=os.getenv("OPENAI_API_KEY"),
                user_id=self.agent_id
            )

        if config.enable_file:
            file_path = self.storage_path / "file_backup"
            self.backends["file"] = FileBackend(str(file_path))

        # 工作内存（运行时）
        self._working_memory: Dict[str, MemoryEntry] = {}
        self._max_working = config.max_short_term

        logger.info(f"UnifiedMemoryManager initialized for agent {self.agent_id}")

    # ==================== 核心存储接口 ====================

    async def remember(
        self,
        content: str,
        category: str = "general",
        importance: float = 1.0,
        metadata: Optional[Dict] = None,
        source: str = "",
        level: str = "chroma"
    ) -> str:
        """
        记住信息

        Args:
            content: 记忆内容
            category: 类别 (conversation, knowledge, workflow, experience)
            importance: 重要性 0-1
            metadata: 元数据
            source: 来源
            level: 存储层级 (working, chroma, mem0, file, all)
        """
        memory_id = str(uuid.uuid4())
        entry = MemoryEntry(
            id=memory_id,
            content=content,
            metadata=metadata or {},
            category=category,
            importance=importance,
            source=source or self.agent_id,
        )

        # 工作内存 - 总是存储
        self._working_memory[memory_id] = entry

        # 清理过期工作内存
        if len(self._working_memory) > self._max_working:
            oldest = sorted(self._working_memory.items(), key=lambda x: x[1].timestamp)[0][0]
            del self._working_memory[oldest]

        # 根据层级存储到后端
        if level in ["file", "all"] and "file" in self.backends:
            await self.backends["file"].store(entry)

        if level in ["chroma", "all"] and "chroma" in self.backends:
            await self.backends["chroma"].store(entry)

        if level in ["mem0", "all"] and "mem0" in self.backends:
            await self.backends["mem0"].store(entry)

        logger.debug(f"Remembered [{category}]: {content[:50]}...")
        return memory_id

    async def recall(
        self,
        query: str,
        category: Optional[str] = None,
        limit: int = 10,
        level: str = "chroma"
    ) -> List[MemoryEntry]:
        """
        回忆信息

        优先顺序: working -> chroma -> file -> mem0
        """
        results = []
        seen_ids = set()

        # 1. 工作内存
        if level in ["working", "all"]:
            for entry in self._working_memory.values():
                if category and entry.category != category:
                    continue
                if query.lower() in entry.content.lower():
                    results.append(entry)
                    seen_ids.add(entry.id)

        # 2. ChromaDB
        if level in ["chroma", "all"] and "chroma" in self.backends:
            chroma_results = await self.backends["chroma"].retrieve(
                query, category, limit, None
            )
            for entry in chroma_results:
                if entry.id not in seen_ids:
                    results.append(entry)
                    seen_ids.add(entry.id)

        # 3. FileBackend
        if level in ["file", "all"] and "file" in self.backends:
            file_results = await self.backends["file"].retrieve(
                query, category, limit, None
            )
            for entry in file_results:
                if entry.id not in seen_ids:
                    results.append(entry)
                    seen_ids.add(entry.id)

        # 4. Mem0
        if level in ["mem0", "all"] and "mem0" in self.backends:
            mem0_results = await self.backends["mem0"].retrieve(
                query, category, limit, None
            )
            for entry in mem0_results:
                if entry.id not in seen_ids:
                    results.append(entry)
                    seen_ids.add(entry.id)

        # 按重要性排序
        results.sort(key=lambda x: x.importance, reverse=True)
        return results[:limit]

    async def forget(self, memory_id: str) -> bool:
        """忘记特定记忆"""
        if memory_id in self._working_memory:
            del self._working_memory[memory_id]

        success = False
        for backend in self.backends.values():
            if await backend.delete(memory_id):
                success = True

        return success

    async def clear(self, category: Optional[str] = None) -> bool:
        """清空记忆"""
        if category:
            to_delete = [k for k, v in self._working_memory.items() if v.category == category]
            for k in to_delete:
                del self._working_memory[k]
        else:
            self._working_memory.clear()

        for backend in self.backends.values():
            await backend.clear(category)

        return True

    # ==================== 快捷方法 ====================

    async def remember_conversation(
        self,
        role: str,
        content: str,
        conversation_id: str = ""
    ) -> str:
        """记录对话"""
        return await self.remember(
            content=f"[{role}] {content}",
            category="conversation",
            importance=0.8,
            metadata={"role": role, "conversation_id": conversation_id},
            source="chat"
        )

    async def remember_knowledge(
        self,
        key: str,
        value: Any,
        importance: float = 1.0
    ) -> str:
        """记录知识"""
        return await self.remember(
            content=f"{key}: {json.dumps(value, ensure_ascii=False)}",
            category="knowledge",
            importance=importance,
            metadata={"key": key, "value": value},
            source="learning"
        )

    async def remember_workflow(
        self,
        workflow_name: str,
        state: Dict[str, Any],
        importance: float = 0.9
    ) -> str:
        """记录工作流状态"""
        from datetime import datetime
        return await self.remember(
            content=f"Workflow {workflow_name} state",
            category="workflow",
            importance=importance,
            metadata={
                "workflow": workflow_name,
                "state": state,
                "timestamp": datetime.now().isoformat()
            },
            source="workflow",
            level="file"
        )

    async def remember_experience(
        self,
        task_type: str,
        input_data: Dict,
        result: Dict,
        success: bool
    ) -> str:
        """记录经验"""
        return await self.remember(
            content=f"Task {task_type}: {'success' if success else 'failed'}",
            category="experience",
            importance=1.0 if success else 0.7,
            metadata={
                "task_type": task_type,
                "success": str(success),
                "input_json": json.dumps(input_data, default=str),
                "result_json": json.dumps(result, default=str),
            },
            source="experience",
            level="all"
        )

    async def get_recent_conversation(
        self,
        conversation_id: str,
        limit: int = 10
    ) -> List[MemoryEntry]:
        """获取最近对话历史"""
        return await self.recall(
            query=conversation_id,
            category="conversation",
            limit=limit
        )

    async def get_similar_experiences(
        self,
        task_type: str,
        limit: int = 5
    ) -> List[MemoryEntry]:
        """获取相似任务经验"""
        return await self.recall(
            query=task_type,
            category="experience",
            limit=limit
        )

    # ==================== 上下文构建 ====================

    async def build_context(
        self,
        query: str,
        max_tokens: int = 4000
    ) -> str:
        """
        为LLM构建上下文

        整合：
        - 相关知识
        - 最近对话
        - 相似经验
        """
        context_parts = []
        token_estimate = 0

        # 1. 相关知识
        knowledge = await self.recall(query, category="knowledge", limit=5)
        if knowledge:
            context_parts.append("### Relevant Knowledge")
            for k in knowledge:
                text = f"- {k.content}"
                context_parts.append(text)
                token_estimate += len(text) // 4

        # 2. 最近对话
        conversation = await self.recall(query, category="conversation", limit=5)
        if conversation:
            context_parts.append("\n### Recent Conversation")
            for c in conversation:
                text = f"- {c.content}"
                context_parts.append(text)
                token_estimate += len(text) // 4

        # 3. 相似经验
        if token_estimate < max_tokens * 0.7:
            experiences = await self.recall(query, category="experience", limit=3)
            if experiences:
                context_parts.append("\n### Similar Experiences")
                for e in experiences:
                    text = f"- {e.content}"
                    context_parts.append(text)
                    token_estimate += len(text) // 4

        return "\n".join(context_parts)

    # ==================== 健康检查 ====================

    async def health_check(self) -> Dict[str, Any]:
        """检查所有后端健康状态"""
        results = {
            "agent_id": self.agent_id,
            "working_memory": len(self._working_memory),
            "backends": {},
        }

        for name, backend in self.backends.items():
            results["backends"][name] = await backend.health_check()

        return results


# 全局记忆管理器缓存
_memory_managers: Dict[str, UnifiedMemoryManager] = {}


def get_memory_manager(agent_id: str, **kwargs) -> UnifiedMemoryManager:
    """获取或创建记忆管理器（单例模式）"""
    if agent_id not in _memory_managers:
        config = MemoryConfig(agent_id=agent_id, **kwargs)
        _memory_managers[agent_id] = UnifiedMemoryManager(config)
    return _memory_managers[agent_id]
