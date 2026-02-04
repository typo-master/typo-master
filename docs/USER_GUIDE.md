# Web3 Typo Hunter - 生产级使用指南

## 快速开始

### 环境要求

- Python 3.8+
- Git
- GitHub Personal Access Token

### 安装

```bash
# 克隆项目
git clone https://github.com/yourusername/typo-master.git
cd typo-master

# 安装依赖
pip install -r requirements.txt

# 开发模式安装
pip install -e .
```

### 配置

```bash
# 复制配置文件
cp config.example.yml config.yml

# 编辑配置
vim config.yml

# 设置GitHub Token
export GITHUB_TOKEN="your_github_token_here"
```

## 使用方法

### 1. 发现Web3项目

```bash
# 查找潜在空投项目
python src/scripts/web3_typo_hunter_cli.py find \
    --token $GITHUB_TOKEN \
    --days 30 \
    --min-stars 100 \
    --limit 50 \
    --format csv
```

### 2. 扫描单个项目

```bash
# 扫描项目拼写错误
python src/scripts/web3_typo_hunter_cli.py scan \
    --token $GITHUB_TOKEN \
    --repo owner/repo \
    --create-pr
```

### 3. 批量处理项目

```bash
# 批量处理项目
python src/scripts/web3_typo_hunter_cli.py process \
    --token $GITHUB_TOKEN \
    --days 30 \
    --min-stars 100 \
    --limit 5 \
    --create-pr
```

## 程序化使用

```python
import asyncio
from src.agents.coordinator_agent import CoordinatorAgent

async def main():
    # 创建协调器
    coordinator = CoordinatorAgent(github_token="your_token")
    await coordinator.initialize()
    await coordinator.start()
    
    try:
        # 提交任务
        result = await coordinator.submit_task({
            "type": "run_workflow",
            "workflow": "single_project",
            "owner": "ethereum",
            "repo": "solidity",
            "create_pr": False,
        })
        
        # 等待完成
        await coordinator.task_queue.join()
        
        print(result)
    
    finally:
        await coordinator.stop()

asyncio.run(main())
```

## 工具使用

### GitHub工具

```python
from src.tools.github_tools import search_github_repos, create_pull_request

# 搜索项目
repos = await search_github_repos(
    query="topic:blockchain stars:>100",
    limit=50,
    token="your_token"
)

# 创建PR
pr = await create_pull_request(
    owner="owner",
    repo="repo",
    title="Fix typo in README",
    head="fix-typo-branch",
    base="main",
    body="Fixed spelling errors",
    token="your_token"
)
```

### 拼写检查工具

```python
from src.tools.spell_tools import check_spelling

# 检查文本拼写
errors = await check_spelling("This is a tset document")
# 返回: [("tset", "test"), ...]
```

### Git工具

```python
from src.tools.git_tools import git_clone, git_commit, git_push

# 克隆仓库
await git_clone(
    url="https://github.com/owner/repo.git",
    destination="./repos/repo"
)

# 提交更改
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

## 配置文件说明

```yaml
# GitHub配置
github:
  token: ${GITHUB_TOKEN}  # GitHub访问令牌
  api_url: https://api.github.com  # API地址
  timeout: 30  # 超时时间(秒)
  max_retries: 3  # 最大重试次数

# 拼写检查配置
spell:
  enabled: true  # 是否启用
  min_confidence: 0.7  # 最小置信度
  filter_web3_terms: true  # 过滤Web3术语
  filter_code_identifiers: true  # 过滤代码标识符

# PR配置
pr:
  auto_create: false  # 自动创建PR
  min_typos_for_pr: 1  # 最少拼写错误数
  min_stars_for_pr: 50  # 最少星数
  validate_before_create: true  # 创建前验证

# 系统配置
system:
  log_level: INFO  # 日志级别
  max_concurrent_tasks: 10  # 最大并发任务数
  task_timeout: 3600  # 任务超时(秒)
```

## 最佳实践

### 1. 使用虚拟环境

```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或
.\venv\Scripts\activate  # Windows
```

### 2. 设置GitHub Token

```bash
# 临时设置
export GITHUB_TOKEN="your_token"

# 或写入配置文件
echo "GITHUB_TOKEN=your_token" > .env
```

### 3. 日志配置

```python
from src.agent_framework.logger import get_logger

logger = get_logger(__name__)
logger.info("Info message")
logger.error("Error message")
logger.debug("Debug message")
```

### 4. 错误处理

```python
from src.agent_framework.error_handler import retry, ErrorSeverity

@retry(max_retries=3, base_delay=1.0)
async def safe_operation():
    # 你的代码
    pass
```

## 监控和调试

### 查看日志

```bash
# 实时日志
tail -f logs/typo_agent.log

# 错误日志
grep "ERROR" logs/typo_agent.log
```

### 健康检查

```python
from src.agent_framework.health import HealthChecker

health = HealthChecker()
status = health.check_all()
print(status)
```

## 故障排除

### 常见问题

1. **GitHub API限制**
   - 减少请求频率
   - 使用认证令牌
   - 等待速率限制重置

2. **拼写检查不工作**
   - 检查pycorrector安装
   - 下载语言模型文件
   - 验证配置文件

3. **Git操作失败**
   - 检查Git安装
   - 验证仓库权限
   - 检查SSH配置

### 获取帮助

```bash
# 查看帮助
python src/scripts/web3_typo_hunter_cli.py --help

# 查看子命令帮助
python src/scripts/web3_typo_hunter_cli.py find --help
```

## 性能优化

### 并发配置

```yaml
system:
  max_concurrent_tasks: 10  # 根据系统调整
  task_timeout: 3600
```

### 缓存配置

```yaml
system:
  cache_dir: ./cache  # 使用SSD存储
  max_cache_size: 10737418240  # 10GB
```

## 安全考虑

1. **保护Token**
   - 使用环境变量
   - 不要提交到版本控制
   - 定期轮换

2. **访问控制**
   - 限制仓库访问权限
   - 使用最小权限原则

3. **数据安全**
   - 加密敏感配置
   - 安全删除临时文件
