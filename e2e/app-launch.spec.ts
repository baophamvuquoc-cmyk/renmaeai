import { test, expect } from './electron.fixture';

test.describe('App Launch', () => {
    test('should create at least one window', async ({ electronApp }) => {
        // Wait for the first window to appear
        const firstWindow = await electronApp.firstWindow();
        expect(firstWindow).toBeTruthy();
        const windows = electronApp.windows();
        expect(windows.length).toBeGreaterThanOrEqual(1);
    });

    test('should show the landing page with hero title', async ({ window }) => {
        const heroTitle = window.locator('.hero-title');
        await expect(heroTitle).toBeVisible();
        await expect(heroTitle).toContainText('RenmaeAI Studio');
    });

    test('should render all app buttons in the grid', async ({ window }) => {
        const buttons = window.locator('.app-icon-btn');
        await expect(buttons).toHaveCount(6);
    });

    test('should show AI status badge in the status bar', async ({ window }) => {
        const badge = window.locator('.statusbar-badge');
        await expect(badge).toBeVisible();
        // Should contain either "AI Ready" or "AI Chưa Cấu Hình"
        const text = await badge.textContent();
        expect(text).toMatch(/AI Ready|AI Chưa Cấu Hình/);
    });

    test('should display app name in status bar', async ({ window }) => {
        const appName = window.locator('.app-name');
        await expect(appName).toBeVisible();
        await expect(appName).toContainText('RenmaeAI');
    });

    test('placeholder buttons should be disabled', async ({ window }) => {
        const placeholders = window.locator('.app-icon-btn.placeholder');
        const count = await placeholders.count();
        expect(count).toBeGreaterThanOrEqual(2);

        for (let i = 0; i < count; i++) {
            await expect(placeholders.nth(i)).toBeDisabled();
        }
    });
});
