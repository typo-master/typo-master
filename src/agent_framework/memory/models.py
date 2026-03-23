"""
Memory System Models - 记忆系统数据模型

定义所有记忆相关的数据类
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass
class MemoryEntry:
    """统一记忆条目"""
    id: str
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    category: str = "general"  # conversation, knowledge, workflow, experience
    timestamp: datetime = field(default_factory=datetime.now)
    importance: float = 1.0  # 0-1, 用于记忆衰减
    source: str = ""  # 来源agent/task
    embedding: Optional[List[float]] = None

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "content": self.content,
            "metadata": self.metadata,
            "category": self.category,
            "timestamp": self.timestamp.isoformat(),
            "importance": self.importance,
            "source": self.source,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MemoryEntry":
        """从字典创建"""
        return cls(
            id=data["id"],
            content=data["content"],
            metadata=data.get("metadata", {}),
            category=data.get("category", "general"),
            timestamp=datetime.fromisoformat(data.get("timestamp", datetime.now().isoformat())),
            importance=data.get("importance", 1.0),
            source=data.get("source", ""),
        )


@dataclass
class MemoryQuery:
    """记忆查询参数"""
    query: str
    category: Optional[str] = None
    limit: int = 10
    filters: Optional[Dict[str, Any]] = None
    level: str = "all"  # working, chroma, mem0, file, all


@dataclass
class MemoryConfig:
    """记忆系统配置"""
    agent_id: str
    enable_mem0: bool = True
    enable_chroma: bool = True
    enable_file: bool = True
    storage_path: str = "./agent_memory"
    max_short_term: int = 1000
    auto_save_interval: float = 300.0  # 5 minutes
