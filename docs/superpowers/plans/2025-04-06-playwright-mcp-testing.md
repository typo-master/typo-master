# Playwright MCP E2E 测试计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 使用 Playwright MCP 自动化测试聊天界面样式、侧边栏折叠功能和 LLM 对话功能

**Architecture:** 基于 MCP (Model Context Protocol) 的 Playwright 自动化测试，覆盖前端 UI 交互和端到端功能验证

**Tech Stack:** Playwright MCP Server, Browser Automation, E2E Testing

**Test Coverage:**
1. AI 聊天界面扁平化样式验证（发送按钮白色/浅绿色主题）
2. 工作台侧边栏展开/收缩功能
3. LLM 配置验证和对话功能

---

## Task 1: 验证服务启动和基础访问

**Files:**
- Test: `e2e/test_basic_access.spec.ts`

- [ ] **Step 1: 验证服务健康状态**

使用 Playwright MCP 访问前端首页：
```typescript
// 访问工作台页面
await page.goto('http://127.0.0.1:50121/workspace/skills');
await page.waitForLoadState('networkidle');

// 验证页面标题
const title = await page.title();
expect(title).toContain('Typo Master');
```

- [ ] **Step 2: 验证后端 API 健康**

```typescript
const response = await page.evaluate(async () => {
  const res = await fetch('http://127.0.0.1:50120/api/v1/health');
  return res.json();
});
expect(response.status).toBe('ok');
```

- [ ] **Step 3: 运行测试并验证**

Run: `npx playwright test e2e/test_basic_access.spec.ts`
Expected: PASS (页面可访问，API 健康)

---

## Task 2: 验证聊天界面扁平化样式

**Files:**
- Modify: `app/frontend/src/components/AIChat/index.tsx` (已修改)
- Test: `e2e/test_chat_ui_styling.spec.ts`

- [ ] **Step 1: 导航到 AI 对话页面**

```typescript
await page.goto('http://127.0.0.1:50121/workspace/chat');
await page.waitForSelector('.aichat-container', { timeout: 5000 });
```

- [ ] **Step 2: 验证发送按钮样式**

```typescript
// 获取发送按钮
const sendButton = await page.locator('button:has-text("发送")');
await expect(sendButton).toBeVisible();

// 验证背景色为白色
const bgColor = await sendButton.evaluate(el => {
  return window.getComputedStyle(el).backgroundColor;
});
expect(bgColor).toBe('rgb(255, 255, 255)'); // 白色

// 验证边框为绿色
const borderColor = await sendButton.evaluate(el => {
  return window.getComputedStyle(el).borderColor;
});
expect(borderColor).toBe('rgb(34, 197, 94)'); // #22c55e

// 验证文字颜色为绿色
const textColor = await sendButton.evaluate(el => {
  return window.getComputedStyle(el).color;
});
expect(textColor).toBe('rgb(34, 197, 94)');
```

- [ ] **Step 3: 验证整体扁平化风格**

```typescript
// 检查聊天容器没有过度的阴影效果
const container = await page.locator('.aichat-container');
const boxShadow = await container.evaluate(el => {
  return window.getComputedStyle(el).boxShadow;
});
// 扁平化设计应该没有或只有轻微阴影
expect(boxShadow).not.toContain('10px 10px'); // 避免厚重阴影
```

- [ ] **Step 4: 运行测试**

Run: `npx playwright test e2e/test_chat_ui_styling.spec.ts --headed`
Expected: PASS (所有样式验证通过)

---

## Task 3: 验证工作台侧边栏展开/收缩功能

**Files:**
- Modify: `app/frontend/src/pages/Workspace.tsx` (已修改)
- Modify: `app/frontend/src/styles.css` (已修改)
- Test: `e2e/test_sidebar_collapse.spec.ts`

- [ ] **Step 1: 验证初始状态（展开）**

```typescript
await page.goto('http://127.0.0.1:50121/workspace/skills');

// 验证菜单项可见
await expect(page.locator('text=AI 对话')).toBeVisible();
await expect(page.locator('text=技能管理')).toBeVisible();
await expect(page.locator('text=MCP 服务')).toBeVisible();
await expect(page.locator('text=定时触发器')).toBeVisible();
await expect(page.locator('text=任务执行')).toBeVisible();

// 记录展开时的布局宽度
const siderExpanded = await page.locator('.workspace-side-menu').boundingBox();
expect(siderExpanded?.width).toBeGreaterThan(150);
```

- [ ] **Step 2: 点击折叠按钮**

```typescript
// 点击折叠按钮（MenuFoldOutlined）
const collapseButton = await page.locator('button[title="收起"]');
await collapseButton.click();

// 等待动画完成
await page.waitForTimeout(300);
```

- [ ] **Step 3: 验证折叠状态**

```typescript
// 验证侧边栏宽度变小
const siderCollapsed = await page.locator('.workspace-side-menu').boundingBox();
expect(siderCollapsed?.width).toBeLessThan(100);

// 验证菜单项文字被隐藏，只显示图标
const menuItem = await page.locator('.ant-menu-item').first();
const textContent = await menuItem.textContent();
// 折叠后应该只显示图标，不显示文字或文字被截断
```

- [ ] **Step 4: 点击展开按钮**

```typescript
// 点击展开按钮（MenuUnfoldOutlined）
const expandButton = await page.locator('button[title="展开"]');
await expandButton.click();

// 等待动画完成
await page.waitForTimeout(300);

// 验证侧边栏恢复宽度
const siderReexpanded = await page.locator('.workspace-side-menu').boundingBox();
expect(siderReexpanded?.width).toBeGreaterThan(150);
```

- [ ] **Step 5: 运行测试**

Run: `npx playwright test e2e/test_sidebar_collapse.spec.ts --headed`
Expected: PASS (侧边栏可正常展开/折叠)

---

## Task 4: 验证 LLM 配置和对话功能

**Files:**
- Modify: `ecosystem.config.js` (已修改)
- Test: `e2e/test_llm_chat.spec.ts`

- [ ] **Step 1: 验证 LLM 配置已加载**

```typescript
// 访问后端 capabilities API 验证 LLM 配置
const response = await page.evaluate(async () => {
  const res = await fetch('http://127.0.0.1:50120/api/v1/capabilities');
  return res.json();
});

// 验证 LLM 配置存在
expect(response.llm).toBeDefined();
expect(response.llm.model).toBe('kimi-k2.5');
```

- [ ] **Step 2: 测试基础对话功能**

```typescript
await page.goto('http://127.0.0.1:50121/workspace/chat');

// 等待输入框可用
await page.waitForSelector('.aichat-input textarea');

// 输入测试消息
const testMessage = '你好，请回复"测试成功"';
await page.fill('.aichat-input textarea', testMessage);

// 点击发送
await page.click('button:has-text("发送")');

// 等待回复出现（最多 30 秒）
await page.waitForSelector('.aichat-message-assistant', { timeout: 30000 });
```

- [ ] **Step 3: 验证没有"LLM is not configured"错误**

```typescript
// 检查页面没有错误提示
const errorElements = await page.locator('text=LLM is not configured').count();
expect(errorElements).toBe(0);

// 检查有 AI 回复内容
const assistantMessage = await page.locator('.aichat-message-assistant').first();
const messageText = await assistantMessage.textContent();
expect(messageText?.length).toBeGreaterThan(0);
```

- [ ] **Step 4: 运行测试**

Run: `npx playwright test e2e/test_llm_chat.spec.ts --headed --timeout=60000`
Expected: PASS (LLM 正常工作，有回复)

---

## Task 5: 整合测试套件

**Files:**
- Create: `e2e/playwright.config.ts`
- Create: `package.json` (添加测试脚本)

- [ ] **Step 1: 创建 Playwright 配置**

```typescript
// e2e/playwright.config.ts
import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: '.',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: 'html',
  use: {
    baseURL: 'http://127.0.0.1:50121',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
});
```

- [ ] **Step 2: 添加 package.json 脚本**

```json
{
  "scripts": {
    "test:e2e": "playwright test",
    "test:e2e:headed": "playwright test --headed"
  }
}
```

- [ ] **Step 3: 运行完整测试套件**

Run: `npm run test:e2e`
Expected: 所有测试通过

---

## Task 6: 测试报告和截图

- [ ] **Step 1: 生成测试报告**

```bash
npx playwright show-report
```

- [ ] **Step 2: 手动验证截图**

检查 `test-results/` 目录中的截图：
1. `chat-ui-styling.png` - 聊天界面样式
2. `sidebar-expanded.png` - 侧边栏展开
3. `sidebar-collapsed.png` - 侧边栏折叠
4. `llm-chat-response.png` - LLM 对话回复

---

## 执行总结

**前置条件:**
- 服务已启动（frontend: 50121, backend: 50120）
- Playwright MCP Server 已配置

**测试范围:**
| 功能 | 测试文件 | 优先级 |
|-----|---------|-------|
| 基础访问 | test_basic_access.spec.ts | P0 |
| 聊天 UI 样式 | test_chat_ui_styling.spec.ts | P0 |
| 侧边栏折叠 | test_sidebar_collapse.spec.ts | P0 |
| LLM 对话 | test_llm_chat.spec.ts | P0 |

**执行命令:**
```bash
# 安装 Playwright
npm init playwright@latest

# 运行所有测试
npx playwright test

# 带界面运行
npx playwright test --headed

# 调试模式
npx playwright test --debug
```
