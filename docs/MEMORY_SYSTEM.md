# Agent 记忆系统重构

## 概述

成功重构了 TypoAgent 的记忆系统，从原来的三层割裂架构改为统一、集成的多层记忆架构。

## 架构对比

### 重构前
```
❌ LangGraph State (临时，无持久化)
❌ BaseAgent StateManager (文件存储，未使用)
❌ Vector Memory (框架存在，未集成)
```

### 重构后
```
✅ UnifiedMemoryManager (统一接口)
  ├── Working Memory (运行时)
  ├── ChromaDB (向量语义搜索)
  ├── Mem0 (自适应长期记忆)
  └── File Backend (关键状态备份)
```

## 新功能

### 1. 统一记忆管理器 (UnifiedMemoryManager)

位置: `src/agent_framework/unified_memory.py`

特性:
- **多层存储**: working → chroma → file
- **分类管理**: conversation, knowledge, workflow, experience
- **重要性评分**: 0-1 分数，用于记忆衰减和优先级
- **元数据支持**: 灵活的元数据存储

### 2. BaseAgent 集成

所有 Agent 现在自动拥有:
```python
self.memory_manager  # UnifiedMemoryManager
self.conversation_history  # 对话历史

# 便利方法
await self.remember(content, category, importance)
await self.recall(query, category, limit)
await self.add_to_conversation(role, content)
await self.build_llm_context(query)
```

### 3. CoordinatorAgent 增强

- 工作流执行自动记录经验
- 项目信息自动存储到知识库
- 加载历史工作流用于学习
- 对话上下文构建

### 4. Agent Runtime 对话记忆

Backend API 现在支持:
- 对话历史持久化
- 记忆上下文注入到 LLM 提示
- 跨会话记忆保持

## 使用示例

### 基本记忆操作

```python
from src.agent_framework import get_memory_manager

memory = get_memory_manager("my_agent")

# 存储记忆
memory_id = await memory.remember(
    content="Ethereum uses Solidity for smart contracts",
    category="knowledge",
    importance=0.9,
    metadata={"topic": "blockchain"}
)

# 检索记忆
results = await memory.recall(
    query="smart contracts",
    category="knowledge",
    limit=5
)
```

### 在 Agent 中使用

```python
class MyAgent(BaseAgent):
    async def process_task(self, task):
        # 记住任务输入
        await self.remember(
            content=f"Processing task: {task}",
            category="workflow"
        )

        # 获取类似经验
        experiences = await self.get_similar_experiences("my_task")

        # 处理...

        # 记住结果
        await self.memory_manager.remember_experience(
            task_type="my_task",
            input_data=task,
            result=result,
            success=True
        )
```

### 对话记忆

```python
# 自动记录在 Agent Runtime
await agent.add_to_conversation(
    role="user",
    content="What can you do?",
    conversation_id="convo_123"
)

# 获取历史
messages = await agent.memory_manager.get_recent_conversation(
    conversation_id="convo_123",
    limit=10
)
```

## 配置

### AgentConfig 新增选项

```python
AgentConfig(
    enable_memory=True,           # 启用记忆
    memory_backend="hybrid",      # 后端类型
    memory_categories=[           # 启用的分类
        "conversation",
        "knowledge",
        "workflow",
        "experience"
    ]
)
```

### 环境变量

```bash
# OpenAI (用于embedding)
export OPENAI_API_KEY=your_key

# 可选: Mem0配置
export MEM0_API_KEY=your_key
```

## 依赖

新增依赖 (已添加到 requirements.txt):
```
mem0ai>=0.1.0
chromadb>=0.5.0
langchain-openai>=0.2.0
langchain-community>=0.3.0
```

安装:
```bash
pip install -r requirements.txt
```

## 存储结构

```
agent_memory/
├── chroma/              # ChromaDB 向量存储
│   └── agent_{id}/
├── file_backup/         # 文件备份
│   └── {memory_id}.json
└── mem0_data/          # Mem0 数据 (如启用)
```

## 性能考量

### 检索优先级
1. Working Memory (内存，O(1))
2. ChromaDB (向量相似度)
3. File Backend (文本匹配)
4. Mem0 (语义提取)

### 存储策略
- **working**: 临时数据，重启丢失
- **chroma**: 向量化数据，支持语义搜索
- **file**: 关键状态，持久化备份
- **mem0**: 自适应记忆，跨会话学习
- **all**: 同时存储到所有层级

## 测试

```bash
# 运行记忆系统测试
pytest tests/test_unified_memory.py -v

# 需要 OPENAI_API_KEY 的测试
export OPENAI_API_KEY=your_key
pytest tests/test_unified_memory.py -v
```

## 未来扩展

### 计划中的功能
1. **LangGraph Checkpoint**: 工作流状态持久化
2. **知识图谱**: 项目-项目关系、typo-修正关系
3. **学习Agent**: 自动提取模式和优化策略
4. **分布式记忆**: Redis/Memcached 支持

### 集成更多记忆库

当前支持:
- ✅ Mem0 (自适应记忆)
- ✅ ChromaDB (向量存储)
- ✅ File (文件备份)

可扩展:
- Pinecone (云端向量)
- Weaviate (知识图谱)
- Milvus (大规模向量)
- Redis (缓存层)

## 注意事项

1. **API Keys**: 生产环境需要配置 OPENAI_API_KEY
2. **存储空间**: ChromaDB 会占用磁盘空间
3. **隐私**: 记忆内容可能包含敏感信息
4. **备份**: 重要记忆建议定期备份

## 迁移指南

从旧版本迁移:

1. 安装新依赖
2. 重启 Agent (自动创建新记忆管理器)
3. 旧的状态文件保留但不自动迁移
4. 新工作流自动使用记忆系统

不需要代码修改，BaseAgent 自动集成。
