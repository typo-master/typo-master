# TypoAgent AI Skill

## 概述

TypoAgent 是一个智能代码质量治理平台，通过 MCP (Model Context Protocol) 协议和 REST API 对外提供服务。作为 AI 助手，你可以通过以下方式与 TypoAgent 集成，帮助用户完成代码拼写检查、术语统一、自动修复和 PR 创建等任务。

## 基础信息

- **服务名称**: TypoAgent
- **服务版本**: 1.0.0
- **MCP SSE 端点**: `http://localhost:50120/mcp/sse`
- **REST API 端点**: `http://localhost:50120/api/v1`
- **健康检查**: `http://localhost:50120/api/v1/health`

## 可用工具

### 1. typoagent_chat
与用户进行对话，获取智能回复。

**参数**:
```json
{
  "message": "用户消息内容",
  "conversation_id": "可选，对话ID"
}
```

**示例**:
```json
{
  "message": "你好，请帮我扫描拼写错误",
  "conversation_id": "conv-123"
}
```

### 2. typoagent_execute_skill
执行 TypoAgent 的 Skill。这是最常用的工具。

**参数**:
```json
{
  "skill_name": "skill名称",
  "params": {
    // Skill 特定参数
  }
}
```

**常用 Skills**:

#### scan_typo - 扫描拼写错误
```json
{
  "skill_name": "scan_typo",
  "params": {
    "repo_path": "./path/to/repo",
    "max_files": 100,
    "include_summary": true
  }
}
```

#### fix_typo - 修复拼写错误
```json
{
  "skill_name": "fix_typo",
  "params": {
    "repo_path": "./path/to/repo",
    "typos": [
      {"file": "README.md", "line": 10, "typo": "teh", "correction": "the"}
    ],
    "create_backup": true
  }
}
```

#### create_pr - 创建 Pull Request
```json
{
  "skill_name": "create_pr",
  "params": {
    "owner": "github-username",
    "repo": "repo-name",
    "title": "Fix typos",
    "head": "fix-typo-branch",
    "base": "main",
    "body": "This PR fixes various typos"
  }
}
```

#### ask_ai - 向 AI 询问问题
```json
{
  "skill_name": "ask_ai",
  "params": {
    "question": "如何优化代码质量？",
    "context": "可选的上下文信息"
  }
}
```

### Web3 空投 Skills

#### web3_search_airdrop_projects - 搜索高空投潜力项目
搜索 GitHub 上的 Web3 项目，分析其空投潜力（基于活跃度、社区规模、PR 接受度等）。

```json
{
  "skill_name": "web3_search_airdrop_projects",
  "params": {
    "days": 30,
    "min_stars": 100,
    "limit": 10
  }
}
```

**返回示例**:
```json
{
  "success": true,
  "result": {
    "total": 10,
    "projects": [
      {
        "name": "ethereum/solidity",
        "stars": 25000,
        "airdrop_potential_score": 85.5,
        "pr_acceptance_rate": "78%",
        "recent_merged_prs": 45
      }
    ]
  }
}
```

#### web3_analyze_project - 分析项目空投潜力
深入分析特定 Web3 项目的空投潜力和贡献机会。

```json
{
  "skill_name": "web3_analyze_project",
  "params": {
    "owner": "ethereum",
    "repo": "solidity"
  }
}
```

#### web3_find_typo_opportunities - 寻找拼写错误机会
在 Web3 项目中寻找可以修复的拼写错误（用于提交 PR 获得贡献记录）。

```json
{
  "skill_name": "web3_find_typo_opportunities",
  "params": {
    "owner": "ethereum",
    "repo": "solidity",
    "auto_fix": true
  }
}
```

#### web3_contribute_and_pr - 完整贡献工作流
一键完成：查找拼写错误 → 自动修复 → 创建 PR。

```json
{
  "skill_name": "web3_contribute_and_pr",
  "params": {
    "owner": "ethereum",
    "repo": "solidity",
    "create_pr": true
  }
}
```

**返回示例**:
```json
{
  "success": true,
  "result": {
    "owner": "ethereum",
    "repo": "solidity",
    "typos_fixed": 5,
    "pr_created": true,
    "pr_url": "https://github.com/ethereum/solidity/pull/12345",
    "pr_number": 12345
  }
}
```

#### web3_batch_farm - 批量空投农场
批量处理多个 Web3 项目，快速积累贡献记录。

```json
{
  "skill_name": "web3_batch_farm",
  "params": {
    "projects": [
      {"owner": "ethereum", "repo": "solidity"},
      {"owner": "aave", "repo": "aave-v3-core"},
      {"owner": "uniswap", "repo": "v3-core"}
    ],
    "create_prs": true
  }
}
```

**空投农场最佳实践**:
1. 先使用 `web3_search_airdrop_projects` 找到高潜力项目
2. 使用 `web3_analyze_project` 分析具体项目
3. 使用 `web3_contribute_and_pr` 提交贡献
4. 使用 `web3_batch_farm` 批量处理多个项目

**注意事项**:
- 空投农场需要配置 GitHub Token
- 确保开启 `pr_create` 权限
- 建议先从接受率高的项目开始
- PR 质量比数量更重要

### 3. typoagent_list_skills
列出所有可用的 Skills。

**参数**:
```json
{
  "category": "可选，按类别筛选，如 scan/fix/report"
}
```

### 4. typoagent_run_workflow
运行 Agent 工作流，执行完整的自动化流程。

**参数**:
```json
{
  "workflow": "single_project",
  "owner": "仓库所有者",
  "repo": "仓库名称",
  "create_pr": true,
  "auto_fix": true
}
```

### 5. typoagent_get_capabilities
获取 Agent 的能力信息，包括可用的 workflows、skills、MCP servers 等。

**参数**: `{}`

### 6. typoagent_execute_mcp_tool
执行外部 MCP Server 的 Tool。

**参数**:
```json
{
  "server_id": "MCP服务器ID",
  "tool_name": "工具名称",
  "arguments": {
    // 工具参数
  }
}
```

### 7. typoagent_list_mcp_servers
列出配置的 MCP Servers。

**参数**: `{}`

## 典型工作流

### 工作流 1: 扫描并修复拼写错误

步骤:
1. 询问用户仓库路径
2. 调用 `typoagent_execute_skill` 执行 `scan_typo`
3. 向用户展示扫描结果（发现的拼写错误列表）
4. 询问用户是否修复
5. 如需修复，调用 `typoagent_execute_skill` 执行 `fix_typo`
6. 展示修复结果

### 工作流 2: 创建 Pull Request

步骤:
1. 确认用户已修复拼写错误
2. 询问 PR 信息（标题、分支名等）
3. 调用 `typoagent_execute_skill` 执行 `create_pr`
4. 向用户展示 PR 链接

### 工作流 3: 完整自动化流程

步骤:
1. 询问用户仓库信息（owner 和 repo）
2. 调用 `typoagent_run_workflow` 运行完整工作流
3. 向用户报告执行结果

### 工作流 4: 获取系统能力

步骤:
1. 调用 `typoagent_get_capabilities` 获取系统能力
2. 向用户展示可用的 workflows、skills 等信息

## REST API 直接调用

如果 MCP 不可用，也可以直接调用 REST API:

### 执行 Skill
```bash
POST http://localhost:50120/api/v1/skills/execute
Content-Type: application/json

{
  "skill_name": "scan_typo",
  "params": {
    "repo_path": "./my-project",
    "max_files": 100
  }
}
```

### 获取 Capabilities
```bash
GET http://localhost:50120/api/v1/capabilities
```

### 列出所有 Skills
```bash
GET http://localhost:50120/api/v1/skills
```

### 列出 MCP Servers
```bash
GET http://localhost:50120/api/v1/mcp/servers
```

### 执行 MCP Tool
```bash
POST http://localhost:50120/api/v1/mcp/execute
Content-Type: application/json

{
  "server_id": "filesystem",
  "tool_name": "read_file",
  "arguments": {
    "path": "/path/to/file.txt"
  }
}
```

## 响应格式

所有 API 返回统一格式:

成功响应:
```json
{
  "success": true,
  "result": {
    // 操作结果数据
  },
  "error": null
}
```

错误响应:
```json
{
  "success": false,
  "result": null,
  "error": "错误描述信息"
}
```

## 常见错误处理

### 错误码
- `-32700`: Parse Error - JSON 解析失败
- `-32600`: Invalid Request - 无效的请求
- `-32601`: Method Not Found - 方法不存在
- `-32602`: Invalid Params - 参数错误
- `-32603`: Internal Error - 服务器内部错误
- `-32000`: Permission Denied - 权限不足

### 处理策略
1. **权限错误**: 提示用户检查 config.yml 中的权限设置
   ```
   错误：权限不足无法执行 git_push
   建议：请在设置中开启 Git 推送权限
   ```

2. **网络错误**: 检查服务是否运行在 `localhost:50120`
   ```
   错误：无法连接到 TypoAgent 服务
   建议：请确保 TypoAgent 后端服务已启动
   ```

3. **参数错误**: 根据返回的错误信息修正参数
   ```
   错误：参数 repo_path 不能为空
   建议：请提供有效的仓库路径
   ```

4. **MCP 服务器未找到**: 检查 MCP 服务器配置
   ```
   错误：MCP server 'filesystem' not found
   建议：请在设置中配置 MCP 服务器
   ```

## 最佳实践

1. **先检查健康状态**: 在执行操作前，先调用 `/api/v1/health` 确认服务正常

2. **获取 Capabilities**: 使用 `typoagent_get_capabilities` 了解系统能力

3. **列出 Skills**: 使用 `typoagent_list_skills` 查看所有可用 Skills

4. **批量操作**: 尽量使用工作流而非单个 Skill 调用，减少往返次数

5. **错误重试**: 对于网络错误，建议实现重试机制

6. **结果确认**: 对于修复类操作，建议先扫描查看结果，再执行修复

7. **权限检查**: 在执行敏感操作前，先检查用户权限配置

## 与用户交互的建议

### 询问仓库路径
```
请提供要扫描的仓库路径（相对或绝对路径）：
例如：./my-project 或 /Users/name/projects/my-project
```

### 展示扫描结果
```
扫描完成！发现 5 个拼写错误：

1. README.md (第 10 行): "teh" → "the"
2. src/main.js (第 25 行): "recieve" → "receive"
3. docs/guide.md (第 15 行): "adress" → "address"
...

是否要自动修复这些错误？
```

### 确认修复
```
已修复 5 个拼写错误：
- README.md: 1 处
- src/main.js: 2 处
- docs/guide.md: 2 处

是否要创建 Pull Request？
```

### PR 创建成功
```
Pull Request 创建成功！
链接：https://github.com/owner/repo/pull/123
标题：Fix typos
分支：fix/typos-20240318
```

## 安全提示

- 所有文件操作都在本地执行，不会直接影响远程仓库
- PR 创建需要显式授权，不会自动推送
- 敏感操作（如 `git_push`、`pr_create`）受权限系统控制
- 建议在生产环境使用权限配置文件限制操作范围
- 不要将真实的 GitHub Token 或 API Key 写入代码

## 示例对话

**用户**: "帮我扫描一下这个仓库的拼写错误"

**AI**:
1. 询问："请提供要扫描的仓库路径："
2. 用户回答："./my-project"
3. 调用 `typoagent_execute_skill` 执行 `scan_typo`
4. 向用户展示扫描结果
5. 询问："发现 5 个拼写错误，是否要自动修复？"

**用户**: "修复并创建一个 PR"

**AI**:
1. 调用 `typoagent_execute_skill` 执行 `fix_typo`
2. 询问："请提供 GitHub 仓库信息（owner/repo）："
3. 用户回答："myname/my-project"
4. 调用 `typoagent_execute_skill` 执行 `create_pr`
5. 向用户展示 PR 链接

**用户**: "你能做什么？"

**AI**:
1. 调用 `typoagent_get_capabilities` 获取能力信息
2. 向用户展示：
   ```
   我可以帮您：
   - 扫描代码仓库中的拼写错误
   - 自动修复发现的拼写错误
   - 创建 Pull Request
   - 查询可用的 Skills
   - 执行完整的工作流

   当前系统已启用 12 个 Skills，包括 scan_typo、fix_typo、create_pr 等。
   ```

## 更多使用示例

### 示例 1: 用户询问你能做什么

**用户**: "你能做什么？"

**你应该**:
1. 调用 `typoagent_get_capabilities` 获取系统能力
2. 向用户展示清晰的列表：

```
我是 TypoAgent 的 AI 助手，可以帮你：

🔍 **扫描与发现**
- 扫描代码仓库中的拼写错误
- 发现术语不一致问题
- 批量扫描多个仓库

🔧 **修复与优化**
- 自动修复拼写错误
- 统一术语规范
- 生成修复报告

📤 **提交与协作**
- 创建 Pull Request
- 提交 Git 变更
- 发送通知

💡 **智能问答**
- 查询 TypoAgent 能力
- 获取使用帮助
- 诊断问题

当前系统已启用 12 个 Skills，支持 5 种工作流。
```

### 示例 2: 用户想扫描拼写错误

**用户**: "帮我扫描一下这个仓库的拼写错误"

**你应该**:
1. 询问仓库路径："请提供要扫描的仓库路径（例如：./my-project 或 /path/to/repo）："
2. 用户回答："./my-project"
3. 调用 `typoagent_execute_skill` 执行 `scan_typo`:
```json
{
  "skill_name": "scan_typo",
  "params": {
    "repo_path": "./my-project",
    "max_files": 100,
    "include_summary": true
  }
}
```
4. 展示结果：
```
扫描完成！发现 5 个拼写错误：

📄 README.md
  第 10 行: "teh" → "the"
  第 25 行: "recieve" → "receive"

📄 src/main.js
  第 15 行: "adress" → "address"

📄 docs/guide.md
  第 8 行: "occured" → "occurred"
  第 30 行: "seperate" → "separate"

是否要自动修复这些错误？
```

### 示例 3: 用户想修复并创建 PR

**用户**: "修复并创建一个 PR"

**你应该**:
1. 确认："好的，我会先修复拼写错误，然后创建 Pull Request。"
2. 调用 `typoagent_execute_skill` 执行 `fix_typo`:
```json
{
  "skill_name": "fix_typo",
  "params": {
    "repo_path": "./my-project",
    "create_backup": true
  }
}
```
3. 询问 PR 信息：
   - "请输入 GitHub 仓库 owner（如：myname）："
   - "请输入仓库名称（如：my-project）："
   - "请输入分支名（默认：fix/typos）："
4. 调用 `typoagent_execute_skill` 执行 `create_pr`:
```json
{
  "skill_name": "create_pr",
  "params": {
    "owner": "myname",
    "repo": "my-project",
    "title": "Fix typos in documentation and code",
    "head": "fix/typos-20240318",
    "base": "main",
    "body": "This PR fixes the following typos:\n- teh → the\n- recieve → receive\n- adress → address"
  }
}
```
5. 展示结果：
```
✅ Pull Request 创建成功！

🔗 链接: https://github.com/myname/my-project/pull/123
📋 标题: Fix typos in documentation and code
🌿 分支: fix/typos-20240318 → main
```

### 示例 4: 用户想批量处理

**用户**: "帮我扫描这几个仓库：project-a, project-b, project-c"

**你应该**:
1. 确认："好的，我会依次扫描这 3 个仓库并生成汇总报告。"
2. 逐个调用 `typoagent_execute_skill` 执行 `scan_typo`
3. 汇总结果并展示：
```
📊 批量扫描完成

project-a: 3 个拼写错误
project-b: 0 个拼写错误 ✅
project-c: 7 个拼写错误

总计：10 个拼写错误需要修复

是否要修复所有仓库的拼写错误？
```

### 示例 5: 用户遇到错误

**用户**: "扫描失败了"

**你应该**:
1. 询问详细信息："请告诉我仓库路径，我帮你诊断问题。"
2. 如果用户提供了路径，先检查健康状态：
```json
{
  "skill_name": "ask_ai",
  "params": {
    "question": "检查 TypoAgent 服务状态"
  }
}
```
3. 根据错误类型给出建议：
```
❌ 扫描失败：路径不存在

可能原因：
1. 路径拼写错误
2. 仓库未克隆到本地
3. 相对路径基准位置不对

建议：
- 确认路径正确：ls ./my-project
- 使用绝对路径：/Users/name/projects/my-project
- 先克隆仓库：git clone https://github.com/owner/repo.git
```

## 进阶技巧

### 1. 组合多个 Skills

你可以在一个对话中组合多个操作：

```
用户：扫描并修复拼写错误，然后创建 PR

你：
1. 扫描 → 发现 5 个错误
2. 修复 → 已修复 5 个错误
3. 创建 PR → PR #123 已创建
```

### 2. 使用上下文记忆

如果对话支持，记住之前的信息：

```
用户：扫描这个仓库
你：好的，./my-project 扫描完成，发现 3 个错误

用户：修复它们
你：好的，修复 ./my-project 的 3 个拼写错误
（不需要再次询问路径）
```

### 3. 智能推荐

根据扫描结果给出建议：

```
扫描完成！发现 15 个拼写错误。

💡 建议：
- 这些错误集中在 docs/ 目录，可能是文档维护问题
- 建议添加拼写检查到 CI 流程
- 考虑使用 pre-commit 钩子防止未来错误

要修复并创建 PR 吗？
```

### 4. 处理用户模糊输入

当用户输入不明确时，主动询问：

```
用户：扫描一下
你：请问要扫描哪个仓库？请提供路径，如 ./my-project

用户：修复
你：请问要修复哪个仓库的拼写错误？
```

## 边界情况处理

### 情况 1: 扫描未发现错误

```
✅ 扫描完成！

未发现拼写错误，代码质量良好。

扫描统计：
- 文件数：25
- 代码行数：3,420
- 拼写错误：0

建议：
- 定期扫描以维持代码质量
- 考虑添加更多 Web3 术语到白名单
```

### 情况 2: 权限不足

```
❌ 操作失败：权限不足

错误：没有权限执行 git_push

解决方案：
1. 打开 TypoAgent 设置页面
2. 进入"权限控制"标签
3. 开启 "git_push" 权限

注意：敏感操作建议在确认后手动执行
```

### 情况 3: 服务未启动

```
❌ 无法连接到 TypoAgent

可能原因：
- TypoAgent 后端服务未启动
- 端口 50120 被占用
- 防火墙阻止连接

解决方案：
1. 启动后端服务：python app/backend/main.py
2. 检查端口：lsof -i :50120
3. 访问健康检查：http://localhost:50120/api/v1/health
```

### 情况 4: MCP 服务器未配置

```
❌ MCP 服务器未找到

错误：MCP server 'filesystem' not found

解决方案：
1. 打开 TypoAgent 设置页面
2. 进入"MCP 配置"标签
3. 添加 filesystem MCP 服务器

或者使用 REST API 直接调用
```

## 性能优化建议

### 1. 大仓库扫描

对于大型仓库，建议分批处理：

```json
{
  "skill_name": "scan_typo",
  "params": {
    "repo_path": "./large-repo",
    "max_files": 50,
    "file_pattern": "*.md"
  }
}
```

### 2. 增量扫描

只扫描变更的文件：

```
用户：只扫描最近修改的文件
你：好的，我会扫描最近 git 变更的文件
```

### 3. 异步批量操作

同时处理多个仓库：

```
正在并行扫描 3 个仓库...
[████████░░] project-a (80%)
[██████░░░░] project-b (60%)
[██████████] project-c (100%)
```

## 调试与诊断

### 1. 检查服务状态

```
用户：TypoAgent 正常工作吗？

你：让我检查一下服务状态...

✅ 后端服务：运行中
✅ MCP SSE：正常
✅ REST API：响应正常 (23ms)
✅ 已启用 Skills：12 个
✅ MCP Servers：3 个已连接

一切正常，可以开始使用！
```

### 2. 查看执行日志

```
用户：刚才的扫描详细日志在哪里看？

你：你可以在以下位置查看日志：

1. 终端日志：启动后端服务的终端
2. 日志文件：./logs/typoagent.log
3. 浏览器控制台：F12 → Console
4. 设置页面：系统 → 日志查看器
```

### 3. 测试连接

```
用户：测试一下连接

你：好的，让我测试 TypoAgent 的各项连接...

测试项目                  状态    延迟
─────────────────────────────────────
健康检查                  ✅      12ms
MCP SSE 连接              ✅      45ms
REST API 调用             ✅      23ms
Skill 执行                ✅      156ms
MCP Server 调用           ✅      89ms

所有测试通过！TypoAgent 运行正常。
```

## 与其他工具集成

### 1. 配合 Git 工作流

```
用户：在提交前扫描一下

你：好的，我会在当前 git 仓库扫描...

扫描完成！发现 2 个拼写错误。

建议：先修复再提交，保持提交记录干净
要修复吗？
```

### 2. 配合 CI/CD

```
用户：生成 CI 配置

你：我可以帮你生成 GitHub Actions 配置：

```yaml
name: Typo Check
on: [push, pull_request]
jobs:
  typo-check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Run TypoAgent
        run: |
          curl -X POST http://typoagent:50120/api/v1/skills/execute \
            -d '{"skill_name":"scan_typo","params":{"repo_path":"."}}'
```
```

### 3. 配合编辑器

```
用户：VS Code 能集成吗？

你：可以！有几种方式：

1. 使用 REST API 扩展
2. 配置 Task Runner
3. 使用 MCP 直接集成（如果 VS Code 支持）

需要我帮你生成 VS Code 配置吗？
```

## AI 助手配置示例

### Claude Desktop 配置

在 Claude Desktop 中，你可以直接粘贴 Skill 内容，或者配置 MCP：

```json
{
  "mcpServers": {
    "typoagent": {
      "command": "python",
      "args": ["-m", "typoagent.mcp_client"],
      "env": {
        "TYPOAGENT_URL": "http://localhost:50120"
      }
    }
  }
}
```

或者直接在对话中粘贴：
```
请阅读这个 Skill 文档，然后帮我操作 TypoAgent：
[Paste Skill Content Here]
```

### Cursor 配置

在 Cursor 的 Composer 或 Chat 中直接粘贴 Skill 内容：
```
你是我的 TypoAgent 助手。请根据以下 Skill 文档帮我操作 TypoAgent：
[Paste Skill Content Here]
```

### ChatGPT 配置

在 ChatGPT 中开启 Custom Instructions：
```
你是我的 TypoAgent 助手，专门帮我操作代码质量治理工具。

请根据以下 Skill 文档理解 TypoAgent 的能力：
[Paste Skill Content Here]

当我说"扫描"、"修复"、"创建 PR"等与代码质量相关的操作时，
请使用上述能力帮我完成。
```

### GitHub Copilot Chat 配置

在 VS Code 中使用 Copilot Chat：
```
@workspace 请根据以下 TypoAgent Skill 文档帮我操作：
[Paste Skill Content Here]

现在请帮我扫描当前项目的拼写错误。
```

## 故障排除指南

### AI 助手无法访问 TypoAgent

**症状**: AI 助手返回连接错误或超时

**诊断步骤**:
1. 检查 TypoAgent 后端是否运行
   ```bash
   curl http://localhost:50120/api/v1/health
   ```

2. 检查端口是否被占用
   ```bash
   lsof -i :50120
   ```

3. 检查防火墙设置

**解决方案**:
```
用户：AI 说连不上 TypoAgent

你：让我帮你诊断一下...

1. 首先检查服务状态：
   curl http://localhost:50120/api/v1/health

   如果返回 {"status": "healthy"}，服务正常。
   如果无响应，需要启动后端服务。

2. 启动后端服务：
   cd /path/to/typo-master
   python app/backend/main.py

3. 再次测试连接。
```

### AI 助手理解错误

**症状**: AI 执行了错误的操作或返回不相关信息

**可能原因**:
- Skill 内容未完整粘贴
- AI 上下文长度限制
- AI 混淆了多个工具

**解决方案**:
1. 重新粘贴完整的 Skill 内容
2. 简化请求，一次只做一个操作
3. 明确指定工具名称

```
用户：AI 做错了

你：请尝试以下步骤：

1. 清除当前对话上下文
2. 重新粘贴完整的 Skill 文档
3. 使用明确的指令，如：
   "请使用 typoagent_execute_skill 执行 scan_typo，参数是..."

4. 如果仍有问题，检查 AI 助手是否支持 function calling。
```

### 权限被拒绝

**症状**: 操作返回 "Permission denied" 错误

**解决方案**:
```
用户：AI 说没有权限创建 PR

你：这是正常的安全机制。请按以下步骤开启权限：

1. 打开 TypoAgent 控制台：http://localhost:50121
2. 进入"设置"页面
3. 找到"权限控制"部分
4. 开启 "pr_create" 权限
5. 重新执行操作

注意：敏感权限建议仅在需要时开启。
```

### 响应缓慢或超时

**症状**: AI 助手响应慢或操作超时

**可能原因**:
- 仓库太大
- 网络延迟
- AI 处理时间长

**解决方案**:
```
用户：扫描很慢

你：让我们优化一下：

1. 限制扫描范围：
   "只扫描 docs 目录"
   "只扫描 .md 文件"
   "最多扫描 50 个文件"

2. 分批处理：
   "先扫描前 20 个文件"

3. 检查仓库大小：
   "仓库有多少文件？"

4. 如果仓库很大，建议使用命令行工具而非 AI 助手。
```

## 最佳实践总结

### 1. 清晰明确的指令

✅ **好的指令**:
- "扫描 ./my-project 仓库的拼写错误"
- "修复 README.md 中的拼写错误"
- "创建 PR，owner 是 myname，repo 是 my-project"

❌ **模糊的指令**:
- "扫描一下"
- "修复它"
- "创建 PR"

### 2. 分步骤执行

复杂任务分成多个简单步骤：

```
步骤 1: 扫描仓库
步骤 2: 查看结果
步骤 3: 确认修复
步骤 4: 创建 PR
```

### 3. 验证每一步

在执行下一步前确认上一步成功：

```
你：扫描完成，发现 5 个错误。
     1. teh → the (README.md:10)
     2. recieve → receive (src/main.js:25)
     ...

     确认修复这些错误吗？

用户：确认

你：正在修复...
     修复完成！已修复 5 个错误。

     现在创建 PR 吗？
```

### 4. 保持上下文

在多轮对话中记住关键信息：

```
用户：扫描 ./project-a
你：完成，发现 3 个错误

用户：修复它
你：修复 ./project-a 的 3 个错误（不需要再次询问路径）
```

### 5. 主动提供帮助

不要等用户问，主动给出建议：

```
扫描完成！发现 15 个拼写错误。

💡 建议：
- 错误集中在 docs/ 目录，建议优先修复文档
- 可以创建一个专门的文档修复 PR
- 建议添加 pre-commit 钩子防止未来错误

要修复吗？
```

### 6. 错误恢复

当出错时给出明确的恢复步骤：

```
❌ 操作失败：路径不存在

恢复步骤：
1. 确认路径正确：ls ./my-project
2. 如果路径错误，提供正确路径
3. 重新执行操作

或者：
- 使用绝对路径：/Users/name/projects/my-project
- 先克隆仓库：git clone https://github.com/owner/repo.git
```

## 示例：完整对话流程

```
用户：帮我检查代码质量

你：好的！我可以帮你扫描拼写错误、检查术语一致性等。
     请提供要检查的仓库路径。

用户：./my-website

你：好的，正在扫描 ./my-website...
     [调用 typoagent_execute_skill scan_typo]

     ✅ 扫描完成！

     📊 统计：
     - 文件数：42
     - 扫描行数：3,850
     - 拼写错误：7 个
     - 术语不一致：2 处

     🔍 发现的拼写错误：
     1. README.md:15    "recieve" → "receive"
     2. docs/api.md:23  "adress" → "address"
     3. src/app.js:45   "teh" → "the"
     ...

     🔍 术语不一致：
     1. "userId" vs "user_id" vs "userID"
        建议统一为 "userId"

     要修复这些问题吗？

用户：修复拼写错误，不修复术语

你：好的，正在修复拼写错误...
     [调用 typoagent_execute_skill fix_typo]

     ✅ 修复完成！

     已修复 7 个拼写错误：
     - README.md: 1 处
     - docs/api.md: 2 处
     - src/app.js: 1 处
     - ...

     已自动创建备份文件。

     要创建 Pull Request 吗？

用户：好的，创建 PR

你：好的，请提供 GitHub 仓库信息：

     1. Owner（如：myname）：

用户：myname

你：2. 仓库名称（如：my-website）：

用户：my-website

你：好的，正在创建 PR...
     [调用 typoagent_execute_skill create_pr]

     ✅ Pull Request 创建成功！

     🔗 https://github.com/myname/my-website/pull/42

     📋 标题：Fix typos in documentation and code
     📝 描述：修复了 7 个拼写错误...
     🌿 分支：fix/typos-20240318 → main

     还需要我做什么吗？

用户：没有了，谢谢

你：不客气！如果以后需要检查其他仓库，随时告诉我。
     建议定期运行扫描以保持代码质量。 😊
```

## 最后检查清单

在结束对话前，确保：

- [ ] 用户的问题已解决
- [ ] 所有操作都已成功完成
- [ ] 用户了解操作结果
- [ ] 提供了下一步建议（如有必要）
- [ ] 用户没有未回答的问题

## 更多信息

- 完整 API 文档: http://localhost:50121/docs
- MCP 协议规范: https://spec.modelcontextprotocol.io/
- Skill 详细说明: http://localhost:50121/docs/skills
- 问题反馈: https://github.com/your-repo/typo-agent/issues
