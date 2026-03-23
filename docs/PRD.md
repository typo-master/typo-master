# PRD：权限控制与远程操作开关体系

## 1. 背景与问题
当前系统允许 Agent 执行多种操作（例如 git push、创建 PR、评论、运行命令等），缺少统一的权限约束，导致出现未经授权的远程动作（如推送 PR）。这带来了信任与合规风险。

## 2. 目标
- 引入**细粒度权限控制**：所有可执行操作均受权限开关约束。
- 提供**统一权限配置入口**（配置文件 + UI 设置页）。
- 默认安全：**所有远程/高风险操作默认关闭**。
- 当权限关闭时，工具应**明确拒绝执行**并给出可操作的提示。

## 3. 非目标
- 不涉及权限审计系统/日志系统的建设（可在后续迭代）。
- 不引入角色/多租户权限模型（当前仅面向单实例/单用户）。

## 4. 用户故事
1. 作为使用者，我希望能一键关闭所有远程操作，确保不会发生 push/PR/issue 等动作。
2. 作为使用者，我希望能按能力开关权限，例如“允许创建 PR 但禁止合并”。
3. 作为使用者，我希望在设置页看到清晰的权限说明与风险提示。
4. 作为使用者，我希望当权限关闭时，系统提示我如何开启对应开关。

## 5. 权限模型（建议清单）
> 以“能力/工具”为单位划分，确保最细粒度控制。

### 5.1 Git（本地/远程）
- **git_clone**
- **git_fetch**
- **git_pull**
- **git_push**
- **git_checkout**
- **git_create_branch**
- **git_add**
- **git_commit**

### 5.2 GitHub/PR（远程）
- **github_read**（只读：搜索、读取 PR/issue 等）
- **pr_create**
- **pr_update**（标题/描述）
- **pr_comment**
- **pr_merge**
- **pr_close**
- **issue_create**
- **issue_comment**
- **issue_close**

### 5.3 文件系统
- **fs_read**
- **fs_write**
- **fs_delete**

### 5.4 执行命令
- **shell_run**
- **run_tests**
- **install_deps**

### 5.5 外部访问/网络
- **web_fetch**
- **api_call**
- **llm_request**

> 备注：实际权限项需对照现有工具/能力清单进行落地。

## 6. 功能需求
### 6.1 后端配置
- 配置文件中新增权限配置块（如 `permissions` 或 `system.permissions`）。
- 支持默认值、环境变量覆盖。
- 配置变化可被工具访问（运行时读取）。

### 6.2 工具层强制拦截
- 每个工具在执行前检查对应权限。
- 权限关闭时直接拒绝，并返回**清晰、可操作**的错误信息。
- 工具层为**唯一权威检查点**，即使上层绕过也无法执行。

### 6.3 UI 权限控制页
- 新增“权限控制”设置页。
- 按类别分组展示（Git / GitHub / 文件系统 / 命令 / 外部访问）。
- Switch 形式开关，支持：
  - 全局总开关（只读提示：是否允许任何远程动作）
  - 分项开关（具体能力）
- 显示风险提示（如“开启 push 会允许将变更推送到远程仓库”）。

### 6.4 权限拒绝提示
- 统一错误模板，例如：
  - “当前未启用【git_push】权限，已拒绝执行。请在权限设置中开启该项。”

## 7. 交互与文案
- 页面标题：**权限控制**
- 总开关说明：
  - “关闭时，所有远程/高风险动作将被拒绝。”
- 分组说明：
  - Git、GitHub/PR、文件系统、命令、外部访问

## 8. 数据结构（示例）
```yaml
permissions:
  git_clone: false
  git_fetch: false
  git_pull: false
  git_push: false
  git_checkout: true
  git_create_branch: true
  git_add: true
  git_commit: true

  github_read: true
  pr_create: false
  pr_update: false
  pr_comment: false
  pr_merge: false
  pr_close: false
  issue_create: false
  issue_comment: false
  issue_close: false

  fs_read: true
  fs_write: false
  fs_delete: false

  shell_run: false
  run_tests: false
  install_deps: false

  web_fetch: false
  api_call: false
  llm_request: true
```

## 9. 验收标准
1. 当 `git_push` 关闭时，任何 push 尝试必须被拒绝。
2. 当 `pr_create` 关闭时，创建 PR 必须被拒绝。
3. UI 中开关状态与后端一致，能保存并生效。
4. 错误信息清晰说明被拒绝原因与开启路径。

## 10. 风险与注意事项
- 权限项数量增多后，需维护清晰的分组与默认值。
- 避免仅在 UI 限制；必须**工具层强制**。
- 若未来引入多用户，需要扩展权限模型。

## 11. 里程碑
- M1：完成权限清单与配置结构
- M2：完成工具层权限拦截
- M3：完成权限控制 UI
- M4：回归测试与验收
