# Chat Sidebar Collapse Refinement Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 收窄工作台左侧导航栏与聊天历史折叠宽度，并在历史折叠状态保留可切换会话的入口。

**Architecture:** 在 Workspace 的 Sider 设置更小的 collapsedWidth，并用 CSS 覆盖折叠态菜单项内边距以居中图标；在 AIChat 历史区增加紧凑会话按钮列表（含 tooltip 与选中态），保持现有切换逻辑不变。

**Tech Stack:** React + TypeScript, Ant Design, CSS, Playwright

---

## File Structure
- Modify: `app/frontend/src/pages/Workspace.tsx` — 工作台左侧导航栏折叠宽度配置
- Modify: `app/frontend/src/styles.css` — 折叠态菜单项与历史紧凑项样式
- Modify: `app/frontend/src/components/AIChat/index.tsx` — 历史折叠宽度与紧凑会话切换入口
- Modify: `e2e/test_sidebar_collapse.spec.ts` — 侧边栏折叠宽度断言
- Modify: `e2e/test_chat_ui_styling.spec.ts` — 历史折叠仍可切换的 UI 测试

### Task 1: 收窄工作台侧边栏折叠宽度

**Files:**
- Modify: `app/frontend/src/pages/Workspace.tsx:331-374`
- Modify: `app/frontend/src/styles.css:703-750`
- Test: `e2e/test_sidebar_collapse.spec.ts`

- [ ] **Step 1: 写入失败的侧边栏折叠宽度断言**

```ts
// e2e/test_sidebar_collapse.spec.ts
const box = await sider.boundingBox();
expect(box?.width).toBeLessThanOrEqual(72);
```

- [ ] **Step 2: 运行测试确认失败**

Run: `npx playwright test e2e/test_sidebar_collapse.spec.ts`
Expected: FAIL（折叠宽度仍大于 72）

- [ ] **Step 3: 实现更窄的折叠宽度与折叠态菜单居中**

```tsx
// app/frontend/src/pages/Workspace.tsx
<Sider
  width={200}
  collapsedWidth={56}
  collapsible
  collapsed={siderCollapsed}
  onCollapse={setSiderCollapsed}
  ...
/>
```

```css
/* app/frontend/src/styles.css */
.workspace-side-menu.ant-layout-sider-collapsed
  .workspace-nav-menu.ant-menu-vertical .ant-menu-item {
  padding: 0 8px !important;
  justify-content: center;
}
```

- [ ] **Step 4: 重新运行测试**

Run: `npx playwright test e2e/test_sidebar_collapse.spec.ts`
Expected: PASS

- [ ] **Step 5: Commit（仅在用户明确要求时）**

```bash
git add app/frontend/src/pages/Workspace.tsx app/frontend/src/styles.css e2e/test_sidebar_collapse.spec.ts
git commit -m "chore: tighten workspace sidebar collapse width"
```

### Task 2: 历史折叠仍可切换会话

**Files:**
- Modify: `app/frontend/src/components/AIChat/index.tsx:151-1042`
- Modify: `app/frontend/src/styles.css:1367-1393`
- Test: `e2e/test_chat_ui_styling.spec.ts`

- [ ] **Step 1: 写入失败的历史折叠可切换测试**

```ts
// e2e/test_chat_ui_styling.spec.ts
import { test, expect } from '@playwright/test';

test('历史会话折叠仍可切换', async ({ page }) => {
  await page.goto('http://127.0.0.1:50121/workspace/chat');
  await page.waitForLoadState('networkidle');

  const input = page.locator('textarea[placeholder*="输入消息"]');
  await input.fill('测试1');
  await page.keyboard.press('Enter');

  await page.getByTestId('new-conversation-button').click();
  await input.fill('测试2');
  await page.keyboard.press('Enter');

  await page.getByTestId('history-collapse-toggle').click();
  const items = page.getByTestId('history-compact-item');
  await expect(items).toHaveCount(2);

  await items.nth(1).click();
  await expect(page.locator('text=测试2')).toBeVisible();
});
```

- [ ] **Step 2: 运行测试确认失败**

Run: `npx playwright test e2e/test_chat_ui_styling.spec.ts -g "历史会话折叠仍可切换"`
Expected: FAIL（找不到 data-testid 或紧凑会话入口）

- [ ] **Step 3: 添加紧凑会话入口与折叠宽度**

```tsx
// app/frontend/src/components/AIChat/index.tsx
const getCompactLabel = (index: number) => {
  const label = index + 1;
  return label > 99 ? "99+" : String(label);
};

// ...header collapse button
<Button
  data-testid="history-collapse-toggle"
  type="text"
  size="small"
  ...
/>

// ...new conversation button
<Button
  data-testid="new-conversation-button"
  size="small"
  icon={<ThunderboltOutlined />}
  ...
/>

<div
  style={{
    width: historyCollapsed ? 56 : 220,
    ...
  }}
>
  <div style={{ flex: 1, overflow: "auto", padding: historyCollapsed ? "6px 4px" : "0 4px" }}>
    {sessions.length === 0 ? (
      <Empty ... />
    ) : (
      sessions.map((session, index) =>
        historyCollapsed ? (
          <Tooltip key={session.id} title={`${session.title}\n${session.lastMessage}`}>
            <button
              type="button"
              data-testid="history-compact-item"
              className={`session-compact-item ${session.id === conversationId ? "is-active" : ""}`}
              onClick={() => switchConversation(session.id)}
            >
              {getCompactLabel(index)}
            </button>
          </Tooltip>
        ) : (
          // 现有展开态渲染
        )
      )
    )}
  </div>
</div>
```

```css
/* app/frontend/src/styles.css */
.session-compact-item {
  width: 36px;
  height: 36px;
  margin: 6px auto;
  border-radius: 8px;
  border: 1px solid transparent;
  background: #f9fafb;
  color: #374151;
  font-size: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.15s ease;
}

.session-compact-item.is-active {
  background: #dcfce7;
  border-color: #86efac;
  color: #166534;
}
```

- [ ] **Step 4: 重新运行测试**

Run: `npx playwright test e2e/test_chat_ui_styling.spec.ts -g "历史会话折叠仍可切换"`
Expected: PASS

- [ ] **Step 5: Commit（仅在用户明确要求时）**

```bash
git add app/frontend/src/components/AIChat/index.tsx app/frontend/src/styles.css e2e/test_chat_ui_styling.spec.ts
git commit -m "feat: add compact history switcher when collapsed"
```
