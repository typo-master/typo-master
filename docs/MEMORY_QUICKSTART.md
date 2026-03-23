# 记忆系统快速开始

## 环境配置

依赖已安装：
```bash
pip install chromadb mem0ai langchain-openai langchain-community
```

## 使用示例

### 1. 基础记忆操作

```python
from src.agent_framework import get_memory_manager

# 获取记忆管理器
memory = get_memory_manager("my_agent")

# 存储记忆
await memory.remember(
    content="Ethereum uses Solidity",
    category="knowledge",  # conversation, knowledge, workflow, experience
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

### 2. 在Agent中使用

```python
from src.agent_framework import BaseAgent, AgentConfig

class MyAgent(BaseAgent):
    async def process_task(self, task):
        # 记住任务
        await self.remember(
            content=f"Processing: {task}",
            category="workflow"
        )

        # 获取相似经验
        experiences = await self.get_similar_experiences("scan_project")

        # 处理任务...

        # 记录结果
        await self.memory_manager.remember_experience(
            task_type="my_task",
            input_data=task,
            result=result,
            success=True
        )

# 创建Agent
agent = MyAgent(AgentConfig(
    name="MyAgent",
    enable_memory=True
))
```

### 3. 对话记忆

```python
# 添加对话
await agent.add_to_conversation(
    role="user",
    content="Hello!",
    conversation_id="convo_001"
)

# 获取历史
messages = await agent.memory_manager.get_recent_conversation(
    conversation_id="convo_001",
    limit=10
)
```

### 4. 构建LLM上下文

```python
# 自动整合知识、对话、经验
context = await agent.build_llm_context("How to fix typos?")

# 使用上下文调用LLM
response = llm_client.generate_text(
    system_prompt="You are a helpful assistant.",
    user_prompt=f"Context:\n{context}\n\nQuestion: How to fix typos?"
)
```

## 运行演示

```bash
# 完整演示
python3 tests/demo_memory_system.py

# 快速测试
python3 tests/test_memory_quick.py
```

## 记忆层级

| 层级 | 存储 | 用途 |
|------|------|------|
| working | 内存 | 临时数据 |
| chroma | 向量DB | 语义搜索 |
| file | 文件系统 | 关键状态备份 |
| mem0 | Mem0服务 | 跨会话学习 |

## 存储路径

```
agent_memory/
├── chroma/          # 向量数据库
├── file_backup/     # 文件备份
└── mem0_data/       # Mem0数据
```

## API配置

使用阿里云百炼API（已配置）：
```bash
export OPENAI_API_KEY="sk-sp-6ae28092e0874696a091f765c7e0118b"
export OPENAI_BASE_URL="https://coding.dashscope.aliyuncs.com/apps/anthropic"
export OPENAI_MODEL="kimi-k2.5"
```

记忆系统已就绪！
