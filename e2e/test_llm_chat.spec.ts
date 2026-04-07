import { test, expect } from '@playwright/test';

test.describe('LLM 配置和对话功能', () => {
  test('LLM 配置正确加载', async ({ page }) => {
    // 访问后端 capabilities API 验证 LLM 配置
    const response = await page.evaluate(async () => {
      const res = await fetch('http://127.0.0.1:50120/api/v1/capabilities');
      return res.json();
    });

    // 验证 LLM 配置存在
    expect(response.llm).toBeDefined();
    expect(response.llm.model).toBe('kimi-k2.5');
  });

  test('AI 对话页面可访问', async ({ page }) => {
    await page.goto('http://127.0.0.1:50121/workspace/chat');
    await page.waitForLoadState('networkidle');

    // 等待输入框可用（使用 placeholder 定位）
    await page.waitForSelector('textarea[placeholder*="输入消息"]', { timeout: 5000 });

    // 验证发送按钮存在
    await expect(page.locator('button:has-text("发送")')).toBeVisible();

    // 验证没有"LLM is not configured"错误提示
    const errorCount = await page.locator('text=LLM is not configured').count();
    expect(errorCount).toBe(0);
  });
});
