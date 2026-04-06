import { test, expect } from '@playwright/test';

test.describe('基础访问测试', () => {
  test('前端页面可访问', async ({ page }) => {
    await page.goto('http://127.0.0.1:50121/workspace/skills');
    await page.waitForLoadState('networkidle');
    const title = await page.title();
    expect(title).toContain('Typo Master');
  });

  test('后端 API 健康', async ({ page }) => {
    const response = await page.evaluate(async () => {
      const res = await fetch('http://127.0.0.1:50120/api/v1/health');
      return res.json();
    });
    expect(response.ok).toBe(true);
  });
});
