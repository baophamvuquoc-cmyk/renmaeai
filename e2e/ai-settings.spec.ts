import { test, expect } from './electron.fixture';

test.describe('AI Settings', () => {
    test.beforeEach(async ({ window }) => {
        // Navigate to AI Settings
        const aiBtn = window.locator('.app-icon-btn').nth(2);
        await aiBtn.click();
        await window.locator('.feature-open-btn', { hasText: 'Mở Cấu Hình AI' }).click();

        // Verify we are on the AI Settings page
        await expect(window.locator('.workspace-title')).toContainText('Cấu Hình AI');
    });

    test('should display the AI settings page content', async ({ window }) => {
        // The workspace content area should be visible
        const content = window.locator('.workspace-content');
        await expect(content).toBeVisible();
    });

    test('should have a back button to return to landing', async ({ window }) => {
        const backBtn = window.locator('.back-btn');
        await expect(backBtn).toBeVisible();
        await backBtn.click();

        // Should be back at the landing page
        await expect(window.locator('.hero-title')).toBeVisible();
    });
});
