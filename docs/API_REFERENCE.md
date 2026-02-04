# TypoAgent API Reference

## Agent Framework

### BaseAgent

所有Agent的基类，提供生命周期管理和基础功能。

```python
from src.agent_framework.base_agent import BaseAgent, AgentConfig, AgentState

class MyAgent(BaseAgent):
    async def on_initialize(self) -> None:
        """初始化时调用"""
        pass
    
    async def on_start(self) -> None:
        """启动时调用"""
        pass
    
    async def on_stop(self) -> None:
        """停止时调用"""
        pass
```

#### AgentConfig

```python
@dataclass
class AgentConfig:
    name: str                      # Agent名称
    version: str = "1.0.0"         # 版本号
    description: str = ""           # 描述
    max_retries: int = 3           # 最大重试次数
    timeout: float = 300.0         # 超时时间(秒)
    log_level: str = "INFO"        # 日志级别
    enabled: bool = True           # 是否启用
    metadata: Dict[str, Any]      # 自定义元数据
```

#### AgentState

```python
class AgentState(Enum):
    INITIALIZING = "initializing"  # 初始化中
    IDLE = "idle"                  # 空闲
    RUNNING = "running"            # 运行中
    PAUSED = "paused"              # 暂停
    STOPPING = "stopping"          # 停止中
    STOPPED = "stopped"            # 已停止
    ERROR = "error"               # 错误
```

### CoordinatorAgent

协调整个工作流程的主Agent。

```python
from src.agents.coordinator_agent import CoordinatorAgent

coordinator = CoordinatorAgent(github_token="token")
await coordinator.initialize()
await coordinator.start()

# 提交任务
result = await coordinator.submit_task({
    "type": "run_workflow",
    "workflow": "single_project",
    "owner": "owner",
    "repo": "repo",
    "create_pr": False,
})

await coordinator.stop()
```

## Specialized Agents

### ProjectDiscoveryAgent

发现Web3项目。

```python
from src.agents.project_discovery_agent import ProjectDiscoveryAgent

agent = ProjectDiscoveryAgent(github_token="token")
await agent.initialize()

# 搜索项目
projects = await agent.discover_projects(
    query="topic:blockchain",
    min_stars=100,
    limit=50
)
```

### TypoScannerAgent

扫描仓库拼写错误。

```python
from src.agents.typo_scanner_agent import TypoScannerAgent

agent = TypoScannerAgent()
await agent.initialize()

# 扫描
report = await agent.scan_repository(
    repo_path="./repo",
    max_files=100
)
```

### TypoFixerAgent

修复拼写错误。

```python
from src.agents.typo_fixer_agent import TypoFixerAgent

agent = TypoFixerAgent()
await agent.initialize()

# 修复
fixes = await agent.fix_typos(
    repo_path="./repo",
    typos=[
        {"file": "README.md", "line": 10, "typo": "teh", "correction": "the"}
    ]
)
```

### PRCreatorAgent

创建Pull Request。

```python
from src.agents.pr_creator_agent import PRCreatorAgent

agent = PRCreatorAgent(github_token="token")
await agent.initialize()

# 创建PR
pr = await agent.create_pr(
    owner="owner",
    repo="repo",
    title="Fix typos in README",
    head="fix-typo",
    base="main",
    body="Fixed spelling errors found by TypoAgent"
)
```

## Tool System

### GitHub Tools

```python
from src.tools.github_tools import (
    search_github_repos,
    get_github_repo,
    create_pull_request,
    get_file_contents,
    update_file,
    create_branch,
)

# 搜索仓库
repos = await search_github_repos(
    query="topic:ethereum stars:>100",
    limit=50,
    token="token"
)

# 获取仓库信息
repo_info = await get_github_repo(
    owner="ethereum",
    repo="solidity",
    token="token"
)

# 创建PR
pr = await create_pull_request(
    owner="owner",
    repo="repo",
    title="Fix typo",
    head="fix-typo",
    base="main",
    body="Description",
    token="token"
)
```

### Git Tools

```python
from src.tools.git_tools import (
    git_clone,
    git_checkout,
    git_create_branch,
    git_add,
    git_commit,
    git_push,
    git_get_current_branch,
    git_get_changes,
)

# 克隆
await git_clone(
    url="https://github.com/owner/repo.git",
    destination="./repos/repo"
)

# 创建分支
await git_create_branch(
    repo_path="./repos/repo",
    branch="fix-typo",
    base="main"
)

# 提交
await git_commit(
    repo_path="./repos/repo",
    message="Fix typo in README"
)

# 推送
await git_push(
    repo_path="./repos/repo",
    remote="origin",
    branch="fix-typo"
)
```

### Spell Check Tools

```python
from src.tools.spell_tools import (
    check_spelling,
    check_file_spelling,
)

# 检查文本
errors = await check_spelling("This is a tset")

# 检查文件
file_errors = await check_file_spelling(
    file_path="./README.md"
)
```

### File Tools

```python
from src.tools.file_tools import (
    read_file,
    write_file,
    list_files,
    file_exists,
)

# 读取文件
content = await read_file(
    file_path="./README.md",
    encoding="utf-8"
)

# 写入文件
result = await write_file(
    file_path="./test.txt",
    content="Hello, World!"
)

# 列出文件
files = await list_files(
    directory="./src",
    pattern="*.py"
)
```

### PR Tools

```python
from src.tools.pr_tools import (
    create_pr_with_labels,
    update_pr_status,
    get_pr_details,
    merge_pull_request,
    add_pr_comment,
)

# 创建带标签的PR
pr = await create_pr_with_labels(
    owner="owner",
    repo="repo",
    title="Fix typo",
    head="fix-typo",
    base="main",
    labels=["typo", "documentation"],
    token="token"
)

# 获取PR详情
details = await get_pr_details(
    owner="owner",
    repo="repo",
    pr_number=123,
    token="token"
)
```

## Configuration

### ConfigManager

```python
from src.agent_framework.config import ConfigManager, AppConfig

# 创建配置管理器
manager = ConfigManager(config_file="config.yml")

# 加载配置
config = manager.load()

# 获取配置值
log_level = manager.get("system.log_level", "INFO")

# 设置配置值
manager.set("system.log_level", "DEBUG")

# 验证配置
is_valid = manager.validate()

# 保存配置
manager.save("config.yml")
```

### AppConfig

```python
from src.agent_framework.config import (
    AppConfig,
    SystemConfig,
    GitHubConfig,
    SpellConfig,
    PRConfig,
)

config = AppConfig(
    system=SystemConfig(
        log_level="DEBUG",
        max_concurrent_tasks=10,
        task_timeout=3600.0,
    ),
    github=GitHubConfig(
        token="token",
        timeout=30.0,
        max_retries=3,
    ),
    spell=SpellConfig(
        enabled=True,
        min_confidence=0.7,
    ),
    pr=PRConfig(
        auto_create=False,
        min_typos_for_pr=1,
    ),
)
```

## Message System

### Message

```python
from src.agent_framework.message import Message, MessageType

# 创建消息
message = Message(
    type=MessageType.REQUEST,
    sender="agent1",
    receiver="agent2",
    content={"action": "scan"},
    correlation_id="corr-123"
)

# 序列化
msg_dict = message.to_dict()
json_str = message.to_json()

# 反序列化
from src.agent_framework.message import Message
message = Message.from_dict(msg_dict)
```

## State Management

### StateStore

```python
from src.agent_framework.state import StateStore, StateSnapshot

# 创建状态存储
store = StateStore(storage_path="./state")

# 保存状态
snapshot = StateSnapshot(
    state_id="agent_state",
    agent_id="agent1",
    timestamp=time.time(),
    state_data={"key": "value"}
)
file_path = store.save(snapshot)

# 加载状态
loaded = store.load(file_path)

# 验证状态
is_valid = loaded.verify()
```

## Error Handling

### ErrorHandler

```python
from src.agent_framework.error_handler import (
    ErrorHandler,
    ErrorSeverity,
    ErrorCategory,
    RetryStrategy,
    retry,
)

# 创建错误处理器
handler = ErrorHandler()

# 处理错误
error_info = handler.handle(
    exception=exc,
    category=ErrorCategory.NETWORK,
    severity=ErrorSeverity.HIGH,
    context={"request": "data"}
)

# 使用重试装饰器
@retry(max_retries=3, base_delay=1.0)
async def risky_operation():
    pass
```

## Logger

```python
from src.agent_framework.logger import get_logger

logger = get_logger(__name__)

logger.info("Info message")
logger.error("Error message")
logger.debug("Debug message")
logger.warning("Warning message")
```

## Health Check

```python
from src.agent_framework.health import HealthChecker

health = HealthChecker()

# 检查所有组件
status = health.check_all()

# 检查单个组件
component_status = health.check_component("memory")

# 获取健康报告
report = health.get_report()
```

## Metrics

```python
from src.agent_framework.metrics import MetricsCollector

collector = MetricsCollector()

# 记录指标
collector.record_metric("tasks_completed", 1)
collector.record_latency("operation_duration", 0.5)

# 获取指标
metrics = collector.get_metrics()

# 获取摘要
summary = collector.get_summary()
```

## Tool Registry

```python
from src.agent_framework.tool_system import ToolRegistry, tool, ToolCategory

# 创建工具注册表
registry = ToolRegistry()

# 注册工具
@tool(
    name="custom_tool",
    description="A custom tool",
    category=ToolCategory.CUSTOM,
)
async def custom_tool(param: str) -> str:
    return f"Result: {param}"

registry.register(custom_tool)

# 获取工具
tool = registry.get_tool("custom_tool")

# 列出工具
tools = registry.list_tools()

# 调用工具
result = await tool.invoke(param="value")
```
