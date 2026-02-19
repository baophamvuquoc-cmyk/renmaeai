import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
    testDir: './e2e',
    timeout: 180_000,
    expect: {
        timeout: 10_000,
    },
    fullyParallel: false,
    forbidOnly: !!process.env.CI,
    retries: process.env.CI ? 2 : 0,
    workers: 1,
    reporter: [['list'], ['html', { open: 'never' }]],
    projects: [
        {
            name: 'web',
            testMatch: '**/podcast-remake.spec.ts',
            use: {
                ...devices['Desktop Chrome'],
                baseURL: 'http://localhost:5173',
                viewport: { width: 1400, height: 900 },
                screenshot: 'only-on-failure',
                video: 'retain-on-failure',
            },
        },
        {
            name: 'electron',
            testMatch: '**/navigation.spec.ts',
        },
    ],
});
