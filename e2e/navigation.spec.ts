import { test, expect } from './electron.fixture';

test.describe('Navigation', () => {
    test('should navigate to Đổi Tên File and back', async ({ window }) => {
        // Click the "Đổi Tên File" button (first button, index 0)
        const fileBtn = window.locator('.app-icon-btn').nth(0);
        await fileBtn.click();

        // Should expand and show the "Mở" button
        const openBtn = window.locator('.feature-open-btn', { hasText: 'Mở Đổi Tên File' });
        await expect(openBtn).toBeVisible();
        await openBtn.click();

        // Should navigate to the workspace with the correct header
        const header = window.locator('.workspace-title');
        await expect(header).toBeVisible();
        await expect(header).toContainText('Đổi Tên File');

        // Navigate back
        const backBtn = window.locator('.back-btn');
        await backBtn.click();

        // Should be back at the landing page
        await expect(window.locator('.hero-title')).toBeVisible();
    });

    test('should navigate to Cấu Hình AI and back', async ({ window }) => {
        // Click "Cấu Hình AI" (third button, index 2)
        const aiBtn = window.locator('.app-icon-btn').nth(2);
        await aiBtn.click();

        const openBtn = window.locator('.feature-open-btn', { hasText: 'Mở Cấu Hình AI' });
        await expect(openBtn).toBeVisible();
        await openBtn.click();

        const header = window.locator('.workspace-title');
        await expect(header).toBeVisible();
        await expect(header).toContainText('Cấu Hình AI');

        // Navigate back
        await window.locator('.back-btn').click();
        await expect(window.locator('.hero-title')).toBeVisible();
    });

    test('should navigate to Production Hub and back', async ({ window }) => {
        // Click "Production Hub" (fourth button, index 3)
        const prodBtn = window.locator('.app-icon-btn').nth(3);
        await prodBtn.click();

        const openBtn = window.locator('.feature-open-btn', { hasText: 'Mở Production Hub' });
        await expect(openBtn).toBeVisible();
        await openBtn.click();

        const header = window.locator('.workspace-title');
        await expect(header).toBeVisible();
        await expect(header).toContainText('Production Hub');

        // Navigate back
        await window.locator('.back-btn').click();
        await expect(window.locator('.hero-title')).toBeVisible();
    });

    test('should not navigate when clicking placeholder buttons', async ({ window }) => {
        // Click a placeholder button (index 4)
        const placeholder = window.locator('.app-icon-btn.placeholder').first();
        await placeholder.click({ force: true });

        // Should still be on the landing page
        await expect(window.locator('.hero-title')).toBeVisible();
        // No expanded content should appear
        await expect(window.locator('.feature-open-btn')).not.toBeVisible();
    });

    test('should show breadcrumb in workspace header', async ({ window }) => {
        // Navigate to AI Settings
        const aiBtn = window.locator('.app-icon-btn').nth(2);
        await aiBtn.click();
        await window.locator('.feature-open-btn', { hasText: 'Mở Cấu Hình AI' }).click();

        const breadcrumb = window.locator('.workspace-breadcrumb');
        await expect(breadcrumb).toBeVisible();
        await expect(breadcrumb).toContainText('RenmaeAI Studio / Cấu Hình AI');

        // Go back
        await window.locator('.back-btn').click();
    });
});
