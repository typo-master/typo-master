import { test, expect } from '@playwright/test';

test.describe('工作台侧边栏展开/收缩功能', () => {
  test('侧边栏初始状态为展开', async ({ page }) => {
    await page.goto('http://127.0.0.1:50121/workspace/skills');
    await page.waitForLoadState('networkidle');

    // 验证 AI 对话菜单项可见
    await expect(page.locator('.ant-menu-title-content:has-text("AI 对话")')).toBeVisible();

    // 记录展开时的布局宽度
    const sider = page.locator('.ant-layout-sider');
    const box = await sider.boundingBox();
    expect(box?.width).toBeGreaterThan(150);
  });

  test('点击折叠按钮后侧边栏收缩', async ({ page }) => {
    await page.goto('http://127.0.0.1:50121/workspace/skills');
    await page.waitForLoadState('networkidle');

    // 找到并点击折叠按钮
    const collapseButton = page.locator('.ant-layout-sider button').first();
    await expect(collapseButton).toBeVisible();
    await collapseButton.click();

    // 等待动画完成
    await page.waitForTimeout(500);

    // 验证侧边栏宽度变小
    const sider = page.locator('.ant-layout-sider');
    const box = await sider.boundingBox();
    expect(box?.width).toBeLessThanOrEqual(72);
  });

  test('点击展开按钮后侧边栏恢复', async ({ page }) => {
    await page.goto('http://127.0.0.1:50121/workspace/skills');
    await page.waitForLoadState('networkidle');

    // 先折叠
    const collapseButton = page.locator('.ant-layout-sider button').first();
    await collapseButton.click();
    await page.waitForTimeout(500);

    // 再展开
    const expandButton = page.locator('.ant-layout-sider button').first();
    await expandButton.click();
    await page.waitForTimeout(500);

    // 验证侧边栏恢复宽度
    const sider = page.locator('.ant-layout-sider');
    const box = await sider.boundingBox();
    expect(box?.width).toBeGreaterThan(150);

    // 验证菜单项再次可见（使用更精确的选择器）
    await expect(page.locator('.ant-menu-title-content:has-text("AI 对话")')).toBeVisible();
  });
});
