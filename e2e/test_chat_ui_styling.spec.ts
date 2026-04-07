import { test, expect } from '@playwright/test';

test.describe('聊天界面样式测试', () => {
  test('发送按钮为白色背景绿色边框', async ({ page }) => {
    await page.goto('http://127.0.0.1:50121/workspace/chat');
    await page.waitForLoadState('networkidle');
    await page.waitForSelector('.ai-chat-card', { timeout: 10000 });

    const sendButton = page.locator('button:has-text("发送")');
    await expect(sendButton).toBeVisible();

    // 验证背景色为白色
    const bgColor = await sendButton.evaluate(el =>
      window.getComputedStyle(el).backgroundColor
    );
    expect(bgColor).toBe('rgb(255, 255, 255)');

    // 验证边框颜色为绿色 (#22c55e = rgb(34, 197, 94))
    const borderColor = await sendButton.evaluate(el =>
      window.getComputedStyle(el).borderColor
    );
    expect(borderColor).toBe('rgb(34, 197, 94)');

    // 验证文字颜色为绿色
    const textColor = await sendButton.evaluate(el =>
      window.getComputedStyle(el).color
    );
    expect(textColor).toBe('rgb(34, 197, 94)');
  });

  test('聊天容器扁平化风格无厚重阴影', async ({ page }) => {
    await page.goto('http://127.0.0.1:50121/workspace/chat');
    await page.waitForLoadState('networkidle');
    await page.waitForSelector('.ai-chat-card', { timeout: 10000 });

    // 检查聊天卡片没有厚重的阴影
    const card = page.locator('.ai-chat-card');
    await expect(card).toBeVisible();

    const boxShadow = await card.evaluate(el =>
      window.getComputedStyle(el).boxShadow
    );

    // 扁平化设计应该只有轻微阴影，不包含大范围的阴影值
    // 避免厚重阴影如 "10px 10px" 或更大的值
    const hasHeavyShadow = /\d{2,}px.*\d{2,}px/.test(boxShadow);
    expect(hasHeavyShadow).toBe(false);
  });

  test('历史会话折叠仍可切换', async ({ page }) => {
    await page.goto('http://127.0.0.1:50121/workspace/chat');
    await page.waitForLoadState('networkidle');

    const input = page.locator('textarea[placeholder*="输入消息"]');
    await input.fill('测试A');
    await page.keyboard.press('Enter');
    // 等待发送请求完成（按钮去掉 loading 类）
    await expect(page.locator('button:has-text("发送")')).not.toHaveClass(/ant-btn-loading/, { timeout: 10000 });

    // 刷新页面会自动创建新对话（IndexedDB 保留旧对话）
    await page.reload();
    await page.waitForLoadState('networkidle');
    await input.fill('测试B');
    await page.keyboard.press('Enter');
    await expect(page.locator('button:has-text("发送")')).not.toHaveClass(/ant-btn-loading/, { timeout: 10000 });

    await page.getByTestId('history-collapse-toggle').click();
    const items = page.getByTestId('history-compact-item');
    await expect(items).toHaveCount(2);

    const firstMessage = page.locator('.ai-chat-card .ant-list-item').first();
    await items.nth(0).click();
    await expect(firstMessage).toBeVisible();
    const textAfterFirst = await firstMessage.textContent();

    await items.nth(1).click();
    await expect(firstMessage).toBeVisible();
    const textAfterSecond = await firstMessage.textContent();
    expect(textAfterFirst).not.toBe(textAfterSecond);
  });
});
