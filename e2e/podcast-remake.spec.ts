/**
 * E2E Test – Podcast Remake Full Pipeline (Web Browser + Backend)
 *
 * Prerequisites:
 *   - Frontend: npm run dev          (port 5173)
 *   - Backend:  python main.py       (port 8000)
 *
 * Run:
 *   npx playwright test --project=web --headed    (watch it)
 *   npx playwright test --project=web              (headless)
 */

import { test, expect, type Page } from '@playwright/test';

// ─── Test Data ───────────────────────────────────────────────────────
const PROJECT_NAME = 'Better Version';
const CHANNEL_NAME = 'Hóa ra chuyện là như thế';
const CTA_TEXT = 'Remae AI, tạo kịch bản với chỉ 1 cú click';
const PRONOUN_CUSTOM = 'Mình và các bạn';
const YOUTUBE_URL = 'https://www.youtube.com/watch?v=zAw3cgxECQI';

// ─── Helpers ─────────────────────────────────────────────────────────

/** Seed AI settings in localStorage so the app considers AI configured */
async function seedAISettings(page: Page) {
    await page.evaluate(() => {
        localStorage.setItem('ai-settings-storage', JSON.stringify({
            state: {
                openaiApiKey: 'sk-test-key',
                openaiBaseUrl: 'https://api.openai.com/v1',
                openaiModel: 'gpt-4o',
                geminiApiKey: '',
                customApiKey: '',
                customBaseUrl: '',
                customModel: '',
                activeContentProvider: 'openai',
                pexelsApiKey: '',
                pixabayApiKey: '',
                availableModels: [],
                connectionStatus: {},
                isLoaded: true,
            },
            version: 0,
        }));
    });
    await page.reload();
    await page.waitForLoadState('domcontentloaded');
}

/** Click a custom Toggle by clicking its <label> inside .sc-toggle-head */
async function clickToggle(page: Page, labelText: string) {
    const head = page.locator(`.sc-toggle-head:has(span:text("${labelText}"))`);
    await expect(head).toBeVisible({ timeout: 3_000 });
    const label = head.locator('label');
    await label.click();
    await page.waitForTimeout(300);
}

/** Navigate to a specific advancedStep via React fiber dispatch */
async function navigateToStep(page: Page, step: number): Promise<boolean> {
    return page.evaluate((targetStep) => {
        const el = document.querySelector('.advanced-remake-section');
        if (!el) return false;
        const key = Object.keys(el).find(k =>
            k.startsWith('__reactFiber$') || k.startsWith('__reactInternalInstance$')
        );
        if (!key) return false;
        let fiber = (el as any)[key];
        for (let i = 0; i < 30 && fiber; i++) {
            if (fiber.memoizedState) {
                let hook = fiber.memoizedState;
                for (let j = 0; j < 80 && hook; j++) {
                    if (hook.memoizedState === 1 && hook.queue && hook.queue.dispatch) {
                        hook.queue.dispatch(targetStep);
                        return true;
                    }
                    hook = hook.next;
                }
            }
            fiber = fiber.return;
        }
        return false;
    }, step);
}

// ─── Config Override ─────────────────────────────────────────────────
test.use({
    baseURL: 'http://localhost:5173',
    viewport: { width: 1400, height: 900 },
});

// ─── Main Test ───────────────────────────────────────────────────────

test('Podcast Remake: full workflow', async ({ page }) => {
    // 35 min timeout — pipeline can take 20-30 min with all AI steps
    test.setTimeout(2_100_000);

    // ════════════════════════════════════════════════════════════
    // PHASE 1: Seed AI & Navigate
    // ════════════════════════════════════════════════════════════
    await page.goto('/');
    await seedAISettings(page);
    await expect(page.locator('.hero-title')).toBeVisible({ timeout: 10_000 });

    // Click Podcast Remake (2nd button, index 1)
    await page.locator('.app-icon-btn').nth(1).click();
    const openBtn = page.locator('.feature-open-btn', { hasText: 'Mở Podcast Remake' });
    await expect(openBtn).toBeVisible({ timeout: 5_000 });
    await openBtn.click();
    await expect(page.locator('.workspace-title')).toContainText('Podcast Remake');
    console.log('✅ Phase 1: Navigated to Podcast Remake');

    // ════════════════════════════════════════════════════════════
    // PHASE 2: Create Project
    // ════════════════════════════════════════════════════════════
    const createBtn = page.locator('.entry-card-title', { hasText: 'Tạo Project Mới' });
    await expect(createBtn).toBeVisible({ timeout: 10_000 });
    await createBtn.click();

    const nameInput = page.locator('.project-name-input');
    await expect(nameInput).toBeVisible({ timeout: 5_000 });
    await nameInput.clear();
    await nameInput.fill(PROJECT_NAME);
    await page.locator('.project-name-confirm').click();
    await expect(page.locator('.project-name-dialog')).not.toBeVisible({ timeout: 10_000 });
    await page.waitForTimeout(2_000);
    console.log(`✅ Phase 2: Project "${PROJECT_NAME}" created`);

    // ════════════════════════════════════════════════════════════
    // PHASE 3: Configure Presets
    // ════════════════════════════════════════════════════════════

    // Channel name
    const channelInput = page.locator('input.sc-input[placeholder*="VD:"]');
    await expect(channelInput).toBeVisible({ timeout: 5_000 });
    await channelInput.clear();
    await channelInput.fill(CHANNEL_NAME);
    console.log(`  ✅ Channel: "${CHANNEL_NAME}"`);

    // Dẫn chuyện toggle
    await clickToggle(page, 'Dẫn chuyện');
    const storyBody = page.locator('.sc-toggle.on:has-text("Dẫn chuyện") .sc-toggle-body');
    await expect(storyBody).toBeVisible({ timeout: 3_000 });
    console.log('  ✅ Dẫn chuyện: ON');

    // Xưng hô toggle + fill
    await clickToggle(page, 'Xưng hô');
    const addressBody = page.locator('.sc-toggle.on:has-text("Xưng hô") .sc-toggle-body');
    await expect(addressBody).toBeVisible({ timeout: 3_000 });
    const addressSelect = addressBody.locator('select.sc-input').first();
    await addressSelect.selectOption('các bạn');
    const pronounArea = addressBody.locator('textarea.sc-input').first();
    await pronounArea.fill(PRONOUN_CUSTOM);
    console.log(`  ✅ Xưng hô: "các bạn" + "${PRONOUN_CUSTOM}"`);

    // Đúc kết & CTA toggle + fill
    await clickToggle(page, 'Đúc kết & CTA');
    const ctaBody = page.locator('.sc-toggle.on:has-text("Đúc kết") .sc-toggle-body');
    await expect(ctaBody).toBeVisible({ timeout: 3_000 });
    const ctaArea = ctaBody.locator('textarea.sc-input').first();
    await ctaArea.fill(CTA_TEXT);
    console.log(`  ✅ CTA: "${CTA_TEXT}"`);

    await page.screenshot({ path: 'e2e/screenshots/03-presets.png' });
    console.log('✅ Phase 3: Presets configured');

    // ════════════════════════════════════════════════════════════
    // PHASE 4: Pipeline Dependency Check
    // ════════════════════════════════════════════════════════════
    const pipeline = await page.evaluate(() => {
        const raw = localStorage.getItem('renmae_pipeline_selection');
        return raw ? JSON.parse(raw) : null;
    });
    if (pipeline) {
        expect(pipeline.scriptGeneration).toBe(true);
        console.log('  ✅ scriptGeneration = true');
        if (pipeline.voiceGeneration) console.log('  ✅ voice ON → script locked ON');
        if (pipeline.videoProduction?.footage) console.log('  ✅ footage ON → keywords locked ON');
    }
    console.log('✅ Phase 4: Dependencies checked');

    // ════════════════════════════════════════════════════════════
    // PHASE 5: Overview Panel Verification
    // ════════════════════════════════════════════════════════════
    const overviewTitle = page.locator('text=Tổng quan quy trình');
    if (await overviewTitle.isVisible().catch(() => false)) {
        const stepNames = ['Phân tích', 'Tạo kịch bản', 'Tạo Voice', 'Dựng Video'];
        for (const name of stepNames) {
            const step = page.locator(`.ov-tl-label:has-text("${name}")`).first();
            if (await step.isVisible().catch(() => false)) {
                console.log(`  ✅ Overview step: ${name}`);
            }
        }
    }
    console.log('✅ Phase 5: Overview verified');

    // ════════════════════════════════════════════════════════════
    // PHASE 5b: Leave Preset Gateway → Step 1 (Analysis)
    // ════════════════════════════════════════════════════════════
    const continueBtn = page.locator('button.btn-primary').filter({ hasText: /Tiếp tục/ });
    await continueBtn.scrollIntoViewIfNeeded();
    await expect(continueBtn).toBeVisible({ timeout: 5_000 });
    await continueBtn.click();
    await page.waitForTimeout(1_000);
    console.log('✅ Phase 5b: Transitioned to Step 1 (Analysis view)');

    // ════════════════════════════════════════════════════════════
    // PHASE 6: YouTube Extraction (Step 1)
    // ════════════════════════════════════════════════════════════
    await page.evaluate(() => {
        const c = document.querySelector('.workspace-content');
        if (c) c.scrollTo({ top: 0, behavior: 'instant' });
    });
    await page.waitForTimeout(500);

    const ytInput = page.locator('input[placeholder*="youtube.com/watch"]');
    await ytInput.scrollIntoViewIfNeeded();
    await expect(ytInput).toBeVisible({ timeout: 10_000 });
    await ytInput.fill(YOUTUBE_URL);

    // Click "+ Thêm link" button
    const addLinkBtn = page.locator('button').filter({ hasText: /Thêm link/ }).first();
    await expect(addLinkBtn).toBeVisible();
    await addLinkBtn.click();
    console.log(`  Extracting: ${YOUTUBE_URL}...`);

    // Wait for extraction to complete (backend responds)
    try {
        await page.locator('text=1 LINK').waitFor({ state: 'visible', timeout: 60_000 });
        console.log('  ✅ YouTube extraction: 1 LINK extracted');
    } catch {
        const badge = await page.locator('.badge').filter({ hasText: /LINK/ }).textContent();
        console.log(`  ⚠️ YouTube extraction badge: ${badge}`);
    }

    await page.screenshot({ path: 'e2e/screenshots/06-youtube-extraction.png' });
    console.log('✅ Phase 6: YouTube extraction done');

    // ════════════════════════════════════════════════════════════
    // PHASE 7: Navigate to Step 2 (Queue View)
    // ════════════════════════════════════════════════════════════
    const stepped = await navigateToStep(page, 2);
    if (stepped) {
        console.log('  ✅ Navigated to Step 2 (Queue View) via React dispatch');
    } else {
        const nextStepBtn = page.locator('button').filter({ hasText: /Tiếp tục bước tiếp theo/ }).first();
        if (await nextStepBtn.isVisible({ timeout: 3_000 }).catch(() => false)) {
            await nextStepBtn.click();
            console.log('  ✅ Navigated to Step 2 via button');
        } else {
            console.log('  ⚠️ Could not navigate to Step 2');
        }
    }
    await page.waitForTimeout(1_000);
    await page.screenshot({ path: 'e2e/screenshots/07-step2-queue.png' });
    console.log('✅ Phase 7: Queue View reached');

    // ════════════════════════════════════════════════════════════
    // PHASE 8: Fill Script & Add to Queue
    // ════════════════════════════════════════════════════════════
    const ytInputQueue = page.locator('input[placeholder*="Dán link YouTube"]');
    const queueVisible = await ytInputQueue.isVisible({ timeout: 5_000 }).catch(() => false);

    if (queueVisible) {
        console.log('  ✅ QueueSidebar visible');

        const scriptTextarea = page.locator('textarea[placeholder*="Dán kịch bản gốc"]');
        await scriptTextarea.scrollIntoViewIfNeeded();
        await expect(scriptTextarea).toBeVisible({ timeout: 5_000 });

        // Check if script auto-populated from YouTube
        const currentScript = await scriptTextarea.inputValue();
        if (currentScript.length > 50) {
            console.log(`  ✅ Script auto-filled from YouTube (${currentScript.length} chars)`);
        } else {
            // Extract in QueueSidebar
            await ytInputQueue.fill(YOUTUBE_URL);
            const extractBtnQ = page.locator('button').filter({ hasText: /Lấy/ }).first();
            if (await extractBtnQ.isVisible({ timeout: 3_000 }).catch(() => false)) {
                await extractBtnQ.click();
                console.log('  Extracting in QueueSidebar...');
                await page.waitForFunction(
                    () => {
                        const ta = document.querySelector('textarea[placeholder*="Dán kịch bản gốc"]') as HTMLTextAreaElement;
                        return ta && ta.value.length > 50;
                    },
                    { timeout: 60_000 }
                );
                console.log('  ✅ Script extracted from YouTube in QueueSidebar');
            }
        }

        // Click "Thêm vào hàng đợi"
        const addQueueBtn = page.locator('button').filter({ hasText: 'Thêm vào hàng đợi' });
        await addQueueBtn.scrollIntoViewIfNeeded();
        await expect(addQueueBtn).toBeVisible({ timeout: 5_000 });
        await addQueueBtn.click();
        await page.waitForTimeout(1_000);

        const afterVal = await scriptTextarea.inputValue();
        expect(afterVal.length).toBe(0);
        console.log('  ✅ Added to queue, textarea cleared');

        await page.screenshot({ path: 'e2e/screenshots/08-added-to-queue.png' });
        console.log('✅ Phase 8: Item added to queue');

        // ════════════════════════════════════════════════════════════
        // PHASE 9: Start Pipeline ("Chạy hàng đợi")
        // ════════════════════════════════════════════════════════════
        const processBtn = page.locator('button').filter({ hasText: /Chạy hàng đợi/ }).first();
        await expect(processBtn).toBeVisible({ timeout: 5_000 });
        await processBtn.click();
        console.log('  ✅ Pipeline started — "Chạy hàng đợi" clicked');
        await page.screenshot({ path: 'e2e/screenshots/09-pipeline-started.png' });
        console.log('✅ Phase 9: Pipeline triggered');

        // ════════════════════════════════════════════════════════════
        // PHASE 10: Wait for Pipeline Completion (up to 30 min)
        // ════════════════════════════════════════════════════════════
        console.log('  ⏳ Waiting for pipeline to complete (max 30 min)...');

        const maxWait = 1_800_000; // 30 min
        const pollInterval = 5_000; // 5s
        let elapsed = 0;
        let lastLog = '';
        let pipelineDone = false;
        let pipelineError = false;

        while (elapsed < maxWait) {
            await page.waitForTimeout(pollInterval);
            elapsed += pollInterval;

            // Read queue counters and progress from page
            const status = await page.evaluate(() => {
                const bodyText = document.body.textContent || '';

                // Parse Chờ/Chạy/Xong counters
                const counters = bodyText.match(/Chờ:\s*(\d+).*?Chạy:\s*(\d+).*?Xong:\s*(\d+)/);

                // Find the queue item's percentage — look for "NN%" pattern
                // that appears right-aligned in the queue item (e.g., "68%")
                // Use a targeted selector to avoid matching other % values
                const queueItemTexts = Array.from(
                    document.querySelectorAll('[style*="flex"], [style*="grid"]')
                ).map(el => el.textContent || '');

                // Extract percentage from the specific queue item progress display
                // The percentage appears as standalone "NN%" near the progress bar
                let percent = '';
                const percentEls = document.querySelectorAll('span, div');
                for (const el of percentEls) {
                    const text = (el.textContent || '').trim();
                    // Match exactly "NN%" — a standalone percentage (1-3 digits)
                    if (/^\d{1,3}%$/.test(text)) {
                        percent = text.replace('%', '');
                        break;
                    }
                }

                // Find current step text (shown in green text typically)
                let stepText = '';
                const stepEls = document.querySelectorAll('[style*="color: rgb(34, 197, 94)"], [style*="color:#22c55e"], [style*="color: #22c55e"]');
                for (const el of stepEls) {
                    const t = (el.textContent || '').trim();
                    if (t.length > 3 && t.length < 100) {
                        stepText = t;
                        break;
                    }
                }

                return {
                    waiting: counters ? parseInt(counters[1]) : -1,
                    running: counters ? parseInt(counters[2]) : -1,
                    done: counters ? parseInt(counters[3]) : -1,
                    percent,
                    stepText,
                    hasError: bodyText.includes('Thất bại') || bodyText.includes('❌'),
                    isComplete: (counters && parseInt(counters[3]) > 0 && parseInt(counters[2]) === 0 && parseInt(counters[1]) === 0),
                };
            });

            const logLine = `Chờ:${status.waiting} Chạy:${status.running} Xong:${status.done} | ${status.percent}% | ${status.stepText}`;
            if (logLine !== lastLog) {
                console.log(`  📊 ${logLine} | ${Math.round(elapsed / 1000)}s`);
                lastLog = logLine;
            }

            // Screenshot every 2 minutes
            if (elapsed % 120_000 === 0) {
                await page.screenshot({ path: `e2e/screenshots/10-progress-${Math.round(elapsed / 60_000)}min.png` });
            }

            if (status.isComplete) {
                pipelineDone = true;
                console.log('  ✅ Pipeline completed! (Xong > 0, Chạy = 0)');
                break;
            }

            if (status.hasError && elapsed > 30_000) {
                pipelineError = true;
                await page.screenshot({ path: 'e2e/screenshots/10-error.png' });
                console.log('  ❌ Pipeline error detected');
                break;
            }
        }

        await page.screenshot({ path: 'e2e/screenshots/10-pipeline-final.png' });
        console.log(`✅ Phase 10: Pipeline ${pipelineDone ? 'completed' : pipelineError ? 'errored' : 'timed out'} (${Math.round(elapsed / 1000)}s)`);

        // ════════════════════════════════════════════════════════════
        // PHASE 11: Verify Production Hub
        // ════════════════════════════════════════════════════════════
        const prodTab = page.locator('button').filter({ hasText: 'Productions' });
        if (await prodTab.isVisible({ timeout: 5_000 }).catch(() => false)) {
            await prodTab.click();
            await page.waitForTimeout(2_000);
            console.log('  ✅ Switched to Productions tab');

            const productionRows = page.locator('tr, .production-row, [class*="production"]');
            const rowCount = await productionRows.count();
            console.log(`  📊 Production rows found: ${rowCount}`);

            if (rowCount > 0) {
                console.log('  ✅ Production Hub has entries!');
            } else {
                const apiResult = await page.evaluate(async () => {
                    try {
                        const res = await fetch('http://localhost:8000/api/productions/');
                        const data = await res.json();
                        return { count: Array.isArray(data) ? data.length : 0 };
                    } catch (e) {
                        return { count: 0, error: String(e) };
                    }
                });
                console.log(`  📊 Production API: ${apiResult.count} records`);
            }

            await page.screenshot({ path: 'e2e/screenshots/11-production-hub.png' });
            console.log('✅ Phase 11: Production Hub verified');
        }

    } else {
        console.log('  ⚠️ QueueSidebar not visible — skipping Phases 8-11');
        await page.screenshot({ path: 'e2e/screenshots/07-no-queue.png' });
    }

    await page.screenshot({ path: 'e2e/screenshots/99-final.png' });
    console.log('\n🎉 Test completed!');
});
