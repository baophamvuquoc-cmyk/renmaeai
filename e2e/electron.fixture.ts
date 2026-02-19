import { test as base, type Page } from '@playwright/test';
import { _electron as electron, type ElectronApplication } from 'playwright';
import { spawn, type ChildProcess } from 'child_process';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const PROJECT_ROOT = path.resolve(__dirname, '..');
const VITE_URL = 'http://localhost:5173';

async function isServerRunning(url: string): Promise<boolean> {
    try {
        const res = await fetch(url, { method: 'HEAD' });
        return res.ok;
    } catch {
        return false;
    }
}

async function waitForServer(url: string, timeoutMs = 30_000): Promise<void> {
    const start = Date.now();
    while (Date.now() - start < timeoutMs) {
        if (await isServerRunning(url)) return;
        await new Promise((r) => setTimeout(r, 500));
    }
    throw new Error(`Server at ${url} did not start within ${timeoutMs}ms`);
}

interface ElectronFixtures {
    electronApp: ElectronApplication;
    window: Page;
}

export const test = base.extend<ElectronFixtures>({
    // eslint-disable-next-line no-empty-pattern
    electronApp: async ({ }, use) => {
        let viteProcess: ChildProcess | null = null;

        // Only start Vite if it isn't already running
        const alreadyRunning = await isServerRunning(VITE_URL);
        if (!alreadyRunning) {
            viteProcess = spawn('npx', ['vite', '--port', '5173', '--strictPort'], {
                cwd: PROJECT_ROOT,
                shell: true,
                stdio: 'pipe',
            });
            viteProcess.stdout?.on('data', (d) => process.stdout.write(`[vite] ${d}`));
            viteProcess.stderr?.on('data', (d) => process.stderr.write(`[vite] ${d}`));
            await waitForServer(VITE_URL);
        }

        // Launch Electron
        const app = await electron.launch({
            args: [path.join(PROJECT_ROOT, 'electron', 'main.js')],
            cwd: PROJECT_ROOT,
            env: {
                ...process.env,
                NODE_ENV: 'development',
            },
        });

        await use(app);

        // Teardown — close Electron with a timeout to prevent hanging
        try {
            await Promise.race([
                app.close(),
                new Promise((_, reject) =>
                    setTimeout(() => reject(new Error('Electron close timed out')), 10_000)
                ),
            ]);
        } catch {
            // Force-kill the Electron process if close hangs
            const electronPid = app.process().pid;
            if (electronPid && process.platform === 'win32') {
                spawn('taskkill', ['/pid', electronPid.toString(), '/T', '/F'], { windowsHide: true });
            }
        }

        // Kill Vite only if we started it
        if (viteProcess?.pid) {
            try {
                if (process.platform === 'win32') {
                    spawn('taskkill', ['/pid', viteProcess.pid.toString(), '/T', '/F'], {
                        windowsHide: true,
                    });
                } else {
                    process.kill(viteProcess.pid);
                }
            } catch {
                // already dead
            }
        }
    },

    window: async ({ electronApp }, use) => {
        const page = await electronApp.firstWindow();
        await page.waitForLoadState('domcontentloaded');
        await use(page);
    },
});

export { expect } from '@playwright/test';
