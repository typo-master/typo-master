# Memory System Module Structure

## 模块化重构完成

原来的 `unified_memory.py` (897行) 已重构为模块化的结构：

```
src/agent_framework/memory/
├── __init__.py          # 包导出 (47行)
├── models.py            # 数据模型 (69行)
├── manager.py           # 统一管理器 (386行)
└── backends/
    ├── __init__.py      # 后端导出 (20行)
    ├── base.py          # 抽象基类 (50行)
    ├── file.py          # 文件后端 (160行)
    ├── chroma.py        # ChromaDB后端 (265行)
    └── mem0.py          # Mem0后端 (175行)
```

## 文件大小对比

| 重构前 | 重构后 |
|--------|--------|
| unified_memory.py (897行) | 多个小文件，最大386行 |

## 模块职责

### models.py
- `MemoryEntry`: 记忆条目数据类
- `MemoryQuery`: 查询参数数据类
- `MemoryConfig`: 配置数据类

### manager.py
- `UnifiedMemoryManager`: 统一管理器，整合所有后端
- `get_memory_manager()`: 单例工厂函数

### backends/
- `base.py`: `BaseMemoryBackend` 抽象基类
- `file.py`: `FileBackend` 文件系统存储
- `chroma.py`: `ChromaBackend` 向量数据库存储
- `mem0.py`: `Mem0Backend` 自适应记忆

## 使用方式

```python
# 从 memory 包导入
from src.agent_framework.memory import (
    UnifiedMemoryManager,
    MemoryEntry,
    get_memory_manager,
    FileBackend,
    ChromaBackend,
)

# 使用
memory = get_memory_manager("my_agent")
```

## 优势

1. **单一职责**: 每个文件只负责一个功能
2. **易于维护**: 修改后端不影响其他部分
3. **可扩展**: 添加新后端只需创建新文件
4. **可测试**: 可以单独测试每个后端
5. **清晰导入**: 从 `memory` 包统一导入
