# AI Chat UI 样式优化实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 修改 AI 聊天页面样式，去除紫色主题和大圆角，使用更扁平化的设计

**Architecture:** 
- 修改 `AIChat/index.tsx` 中的内联样式
- 发送按钮改为扁平化蓝色/绿色
- AI 思考中头像改为非紫色
- 用户头像保持绿色，添加 ClaudeCode Logo
- 减少圆角半径（16px -> 8px, 50% -> 6px）

**Tech Stack:** React, Ant Design, TypeScript

---

## 文件结构

**修改文件:**
- `app/frontend/src/components/AIChat/index.tsx` - 聊天组件主文件

**新增资源:**
- `app/frontend/public/claude-code-logo.svg` - ClaudeCode Logo (如果用户需要)

---

## Task 1: 修改发送按钮样式

**Files:**
- Modify: `app/frontend/src/components/AIChat/index.tsx:1586-1604`

- [ ] **Step 1: 修改发送按钮为扁平化蓝色**

将发送按钮从紫色渐变改为扁平化蓝色：

```typescript
// 修改前:
style={{
  height: "auto",
  minWidth: 56,
  fontSize: 13,
  borderRadius: 10,
  background: "linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%)",
  border: "none",
  boxShadow: "0 4px 14px rgba(99, 102, 241, 0.4)",
  transition: "all 0.2s ease",
}}

// 修改后:
style={{
  height: "auto",
  minWidth: 56,
  fontSize: 13,
  borderRadius: 6,
  background: "#3b82f6",
  border: "none",
  boxShadow: "0 2px 8px rgba(59, 130, 246, 0.3)",
  transition: "all 0.2s ease",
}}
```

- [ ] **Step 2: 验证修改**

检查按钮样式已更改为蓝色扁平化设计。

---

## Task 2: 修改 AI 思考中头像样式

**Files:**
- Modify: `app/frontend/src/components/AIChat/index.tsx:1305-1324`

- [ ] **Step 1: 修改 AI 思考中头像为蓝色/绿色渐变**

将紫色渐变头像改为蓝绿色渐变：

```typescript
// 修改前:
<Avatar
  size="small"
  icon={<RobotOutlined />}
  style={{
    background: "linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%)",
    flexShrink: 0,
    boxShadow: "0 0 12px rgba(99, 102, 241, 0.4)",
  }}
/>
<div
  style={{
    maxWidth: "85%",
    minWidth: 160,
    padding: "12px 16px",
    borderRadius: 16,
    background: "linear-gradient(135deg, #1e1b4b 0%, #312e81 100%)",
    border: "1px solid rgba(99, 102, 241, 0.3)",
    boxShadow: "0 4px 20px rgba(99, 102, 241, 0.2), inset 0 1px 0 rgba(255,255,255,0.05)",
  }}
>

// 修改后:
<Avatar
  size="small"
  icon={<RobotOutlined />}
  style={{
    background: "linear-gradient(135deg, #3b82f6 0%, #22c55e 100%)",
    flexShrink: 0,
    boxShadow: "0 0 12px rgba(59, 130, 246, 0.3)",
  }}
/>
<div
  style={{
    maxWidth: "85%",
    minWidth: 160,
    padding: "10px 14px",
    borderRadius: 8,
    background: "#f0f9ff",
    border: "1px solid #bae6fd",
    boxShadow: "0 2px 8px rgba(59, 130, 246, 0.1)",
  }}
>
```

- [ ] **Step 2: 验证修改**

检查 AI 思考中样式已更改为蓝绿色主题。

---

## Task 3: 减小圆角半径

**Files:**
- Modify: `app/frontend/src/components/AIChat/index.tsx` 多处

- [ ] **Step 1: 修改消息气泡圆角**

```typescript
// 修改前 (line 1240):
borderRadius: msg.role === "user" ? "12px 12px 2px 12px" : "12px 12px 12px 2px",

// 修改后:
borderRadius: msg.role === "user" ? "8px 8px 2px 8px" : "8px 8px 8px 2px",
```

- [ ] **Step 2: 修改其他大圆角**

```typescript
// 修改输入框圆角 (line 1577):
borderRadius: 10, -> borderRadius: 6,

// 修改自动补全下拉框圆角 (line 1353):
borderRadius: 10, -> borderRadius: 8,

// 修改技能面板圆角 (line 1643):
borderRadius: 6, -> borderRadius: 4,

// 修改示例卡片圆角 (line 1146):
borderRadius: 10, -> borderRadius: 6,

// 修改空状态圆形图标 (line 1092):
borderRadius: "50%", -> borderRadius: 8,
```

- [ ] **Step 3: 验证修改**

检查所有圆角已减小为更扁平化的值。

---

## Task 4: 可选 - 添加 ClaudeCode Logo 作为用户头像

**Files:**
- Create: `app/frontend/public/claude-code-logo.svg`
- Modify: `app/frontend/src/components/AIChat/index.tsx:1225-1234`

- [ ] **Step 1: 创建 ClaudeCode Logo SVG 文件**

创建 `app/frontend/public/claude-code-logo.svg`:

```svg
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32" fill="none">
  <rect width="32" height="32" rx="6" fill="#1e1e1e"/>
  <path d="M16 6L26 26H6L16 6Z" fill="#d4a574"/>
  <circle cx="16" cy="18" r="4" fill="#1e1e1e"/>
</svg>
```

或使用更简单的版本:

```svg
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="#22c55e">
  <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-1 15h-2v-2h2v2zm0-4h-2V7h2v6z"/>
</svg>
```

- [ ] **Step 2: 修改用户头像显示**

```typescript
// 修改前 (line 1225-1234):
<Avatar
  size="small"
  icon={msg.role === "user" ? <UserOutlined /> : <RobotOutlined />}
  style={{
    background: msg.role === "user"
      ? "#22c55e"
      : "#3b82f6",
    flexShrink: 0,
  }}
/>

// 修改后 - 如果用户头像需要显示 Logo:
<Avatar
  size="small"
  icon={msg.role === "user" ? null : <RobotOutlined />}
  src={msg.role === "user" ? "/claude-code-logo.svg" : null}
  style={{
    background: msg.role === "user"
      ? "#22c55e"
      : "#3b82f6",
    flexShrink: 0,
  }}
/>
```

- [ ] **Step 3: 验证修改**

检查用户头像已显示 ClaudeCode Logo。

---

## 修改汇总

| 元素 | 修改前 | 修改后 |
|------|--------|--------|
| 发送按钮 | 紫色渐变 `#6366f1` -> `#8b5cf6` | 蓝色 `#3b82f6` |
| AI 思考头像 | 紫色渐变 | 蓝绿渐变 `#3b82f6` -> `#22c55e` |
| AI 思考气泡 | 深紫背景 `#1e1b4b` | 浅蓝背景 `#f0f9ff` |
| 消息圆角 | `12px` | `8px` |
| 按钮圆角 | `10px` | `6px` |
| 卡片圆角 | `10px` | `6px` |
| 输入框圆角 | `10px` | `6px` |

---

## 验证步骤

1. 启动前端服务: `pm2 restart typomaster-frontend`
2. 访问: http://127.0.0.1:50121/workspace/chat
3. 检查以下元素:
   - [ ] 发送按钮为蓝色扁平化样式
   - [ ] AI 思考中头像为蓝绿色
   - [ ] 所有圆角变小
   - [ ] 用户头像显示 ClaudeCode Logo (如添加)
