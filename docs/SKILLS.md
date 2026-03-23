# TypoAgent Skills 系统

## 概述

TypoAgent 现在拥有一个完整的 Skill 系统，将低-level 的 Tools 组合成高-level 的业务能力。

## Skill 架构

```
┌─────────────────────────────────────────────────────────┐
│                    Skill Layer                          │
│  (High-level business capabilities)                     │
├─────────────────────────────────────────────────────────┤
│  RepositoryScanSkill  │  Scan repositories for typos   │
│  TypoFixSkill         │  Fix typos in files            │
│  TypoReportSkill      │  Generate reports              │
│  GitOperationsSkill   │  Git operations                │
│  PullRequestSkill     │  Create and manage PRs         │
├─────────────────────────────────────────────────────────┤
│                    Tool Layer                           │
│  (Low-level operations)                                 │
├─────────────────────────────────────────────────────────┤
│  scan_local_repo      │  scan_single_file              │
│  correct_spelling     │  read_file                     │
│  write_file           │  git_commit                    │
│  create_pull_request  │  ...                           │
└─────────────────────────────────────────────────────────┘
```

## 已实现的 Skills

### 1. RepositoryScanSkill
扫描代码仓库中的拼写错误。

```python
from src.skills import RepositoryScanSkill
from src.agent_framework import SkillContext

skill = RepositoryScanSkill()
context = SkillContext(agent)

result = await skill.execute(
    context,
    repo_path="./repos/solidity",
    max_files=100,
    include_summary=True,
)

if result.success:
    print(f"Found {result.data['total_typos']} typos")
    print(f"Scanned {result.data['files_scanned']} files")
```

### 2. TypoFixSkill
修复文件中的拼写错误。

```python
from src.skills import TypoFixSkill

skill = TypoFixSkill()

# Fix single typo
result = await skill.execute(
    context,
    file_path="./README.md",
    typo="recieve",
    correction="receive",
    create_backup=True,
    verify_fix=True,
)

# Fix multiple typos
result = await skill.fix_multiple(
    context,
    file_path="./README.md",
    corrections=[
        {"typo": "teh", "correction": "the"},
        {"typo": "adress", "correction": "address"},
    ],
)
```

### 3. TypoReportSkill
生成各种格式的报告。

```python
from src.skills import TypoReportSkill

skill = TypoReportSkill()

typos = [
    {"file_path": "test.md", "typo": "teh", "correction": "the"},
    {"file_path": "readme.md", "typo": "recieve", "correction": "receive"},
]

# Markdown report
result = await skill.execute(
    context,
    typos=typos,
    output_path="./report.md",
    format="markdown",  # markdown, json, csv
)

# Summary report
await skill.generate_summary(
    context,
    scan_results=[scan1, scan2],
    output_path="./summary.json",
)
```

### 4. GitOperationsSkill
执行 Git 操作。

```python
from src.skills import GitOperationsSkill

skill = GitOperationsSkill()

# Commit changes
result = await skill.execute(
    context,
    repo_path="./repos/solidity",
    files=["README.md", "CONTRIBUTING.md"],
    commit_message="Fix typos",
    create_branch="fix/typos-20240318",
    push=False,
)

# Create branch
branch_name = await skill.create_typo_fix_branch(
    context,
    repo_path="./repos/solidity",
    typo_count=5,
)
# Returns: fix/typos-20240318-5
```

### 5. PullRequestSkill
创建 Pull Request。

```python
from src.skills import PullRequestSkill

skill = PullRequestSkill()

result = await skill.execute(
    context,
    owner="ethereum",
    repo="solidity",
    head_branch="fix/typos-20240318",
    title="Fix typos in documentation",
    body="This PR fixes various typos...",
    base_branch="main",
    generate_description=True,
    typos=typo_list,  # Auto-generate title/body
)
```

## SkillManager 高级用法

### TypoAgentSkillManager
提供组合工作流程：

```python
from src.skills.skill_manager import TypoAgentSkillManager

manager = TypoAgentSkillManager(agent)

# 1. Scan and fix
result = await manager.scan_and_fix(
    repo_path="./repos/solidity",
    auto_fix=True,
    max_files=100,
)

# 2. Complete workflow: scan -> fix -> commit
result = await manager.scan_fix_and_pr(
    repo_path="./repos/solidity",
    owner="ethereum",
    repo="solidity",
)

# 3. Scan and generate report
result = await manager.generate_scan_report(
    repo_path="./repos/solidity",
    output_path="./report.md",
    format="markdown",
)

# Get statistics
stats = manager.get_stats()
```

## Skill 注册表

所有 Skills 自动注册到全局注册表：

```python
from src.agent_framework import SkillRegistry, SkillCategory

# List all skills
all_skills = SkillRegistry.list_skills()
# ['repository_scan', 'typo_fix', 'typo_report', 'git_operations', 'pull_request']

# Get skills by category
scan_skills = SkillRegistry.get_by_category(SkillCategory.SCAN)
fix_skills = SkillRegistry.get_by_category(SkillCategory.FIX)

# Get skill by name
scan_skill = SkillRegistry.get("repository_scan")

# Search skills
results = SkillRegistry.search("typo")
```

## 创建自定义 Skill

```python
from src.agent_framework import skill, BaseSkill, SkillContext, SkillResult, SkillCategory

@skill(
    name="custom_typo_skill",
    description="My custom typo skill",
    category=SkillCategory.CUSTOM,
    required_tools=["check_spelling"],
)
class CustomTypoSkill(BaseSkill):
    async def execute(self, context: SkillContext, **kwargs) -> SkillResult:
        # Your implementation
        result = await context.call_tool("check_spelling", text=kwargs["text"])

        return SkillResult(
            success=True,
            data=result,
        )
```

## Skill 执行上下文

SkillContext 提供：
- **Agent 访问**: `context.agent`
- **记忆管理**: `context.memory`
- **工具调用**: `context.call_tool(name, **args)`
- **状态存储**: `context.remember(key, value)` / `context.recall(key)`

```python
async def execute(self, context: SkillContext, **kwargs) -> SkillResult:
    # Call tool
    result = await context.call_tool("read_file", file_path="test.md")

    # Use memory
    if context.memory:
        await context.memory.remember_workflow(
            workflow_name="my_workflow",
            state={"result": result},
        )

    # Store in context state
    context.remember("temp_data", result)
    data = context.recall("temp_data")

    return SkillResult(success=True, data=result)
```

## Skill 统计

```python
# Get skill statistics
stats = skill.get_stats()
# {
#     "name": "repository_scan",
#     "executions": 10,
#     "successes": 9,
#     "success_rate": 0.9
# }

# Get manager statistics
manager_stats = manager.get_stats()
# {
#     "scan": {...},
#     "fix": {...},
#     "report": {...},
#     "git": {...},
#     "pr": {...}
# }
```

## 测试

运行 Skill 测试：

```bash
python tests/test_skills.py
```

## 与 Agent 集成

Skills 可以无缝集成到 BaseAgent：

```python
from src.agent_framework import BaseAgent, AgentConfig
from src.skills.skill_manager import TypoAgentSkillManager

class TypoAgent(BaseAgent):
    async def on_initialize(self):
        self.skill_manager = TypoAgentSkillManager(self)

    async def process_task(self, task):
        # Use skills
        result = await self.skill_manager.scan_and_fix(
            repo_path=task["repo_path"],
            auto_fix=True,
        )
        return result.data
```
