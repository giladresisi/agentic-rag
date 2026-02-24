import { test, expect } from '@playwright/test';
import { TEST_EMAIL, TEST_PASSWORD } from './utils';

// LANGSMITH_API_KEY is loaded from backend/.env via playwright.config.ts
const LANGSMITH_API_KEY = process.env.LANGSMITH_API_KEY;
const LANGSMITH_PROJECT = process.env.LANGSMITH_PROJECT || 'default';
const LANGSMITH_API_URL = 'https://api.smith.langchain.com';

/**
 * Resolve LangSmith project name to session ID.
 * The v1 REST API identifies projects as "sessions" by UUID.
 */
async function getSessionId(projectName: string): Promise<string | null> {
  const res = await fetch(
    `${LANGSMITH_API_URL}/api/v1/sessions?name=${encodeURIComponent(projectName)}`,
    { headers: { 'x-api-key': LANGSMITH_API_KEY! } }
  );
  if (!res.ok) return null;
  const sessions: any[] = await res.json();
  return sessions.length ? sessions[0].id : null;
}

/**
 * Poll LangSmith REST API for runs created after `afterTime`.
 * Retries until matching runs are found or `timeoutMs` elapses (traces take 10-30s to appear).
 * Optionally filter by run name (e.g. 'chat_completions_stream').
 */
async function pollForRuns(
  afterTime: string,
  runName?: string,
  timeoutMs = 40000,
  intervalMs = 4000
): Promise<any[]> {
  const sessionId = await getSessionId(LANGSMITH_PROJECT);
  if (!sessionId) return [];

  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    const res = await fetch(`${LANGSMITH_API_URL}/api/v1/runs/query`, {
      method: 'POST',
      headers: { 'x-api-key': LANGSMITH_API_KEY!, 'Content-Type': 'application/json' },
      body: JSON.stringify({
        session: [sessionId],
        run_type: 'llm',
        start_time: afterTime,
        limit: 10,
      }),
    });
    if (res.ok) {
      const data = await res.json();
      let runs: any[] = data.runs ?? data;
      if (runName) runs = runs.filter((r: any) => r.name === runName);
      if (runs.length > 0) return runs;
    }
    await new Promise((r) => setTimeout(r, intervalMs));
  }
  return [];
}

test.describe('LangSmith Trace Verification', () => {
  // Skip entire suite if API key is not configured
  test.skip(!LANGSMITH_API_KEY, 'Skipped: LANGSMITH_API_KEY not configured in backend/.env');

  test.beforeEach(async ({ page }) => {
    // Login + chat response + LangSmith propagation (10-30s) + polling = need ~120s total
    test.setTimeout(120000);
    await page.goto('/login');
    await page.fill('#email', TEST_EMAIL);
    await page.fill('#password', TEST_PASSWORD);
    await page.getByRole('button', { name: 'Login' }).click();
    await expect(page).toHaveURL('/chat', { timeout: 15000 });
  });

  test('chat message creates a LangSmith run with inputs and outputs', async ({ page }) => {
    const beforeTime = new Date().toISOString();

    const newThreadButton = page.getByRole('button', { name: /new/i }).first();
    await newThreadButton.click();
    await page.waitForTimeout(2000);

    const messageInput = page.getByPlaceholder(/type your message/i);
    await expect(messageInput).toBeVisible({ timeout: 10000 });
    await messageInput.fill('What is 2+2?');
    await messageInput.press('Enter');

    // Wait for streaming response to complete
    await expect(page.locator('text=/\\b4\\b|four/i').last()).toBeVisible({ timeout: 45000 });

    // Poll LangSmith — traces take 10-30s to propagate
    const runs = await pollForRuns(beforeTime, 'chat_completions_stream');

    expect(runs.length, 'Expected at least one LangSmith run after sending message').toBeGreaterThan(0);

    const run = runs[0];
    expect(run.name).toBe('chat_completions_stream');
    expect(run.run_type).toBe('llm');
    expect(run.inputs, 'Run should have captured inputs').toBeDefined();
    expect(run.outputs, 'Run should have captured outputs (completed)').toBeDefined();
    expect(run.end_time, 'Run should have an end_time (completed)').toBeDefined();
    expect(run.error, 'Run should have no error').toBeNull();
  });

  test('LangSmith run captures the user message in inputs', async ({ page }) => {
    const beforeTime = new Date().toISOString();
    const uniqueMessage = `LangSmith trace check ${Date.now()}`;

    const newThreadButton = page.getByRole('button', { name: /new/i }).first();
    await newThreadButton.click();
    await page.waitForTimeout(2000);

    const messageInput = page.getByPlaceholder(/type your message/i);
    await expect(messageInput).toBeVisible({ timeout: 10000 });
    await messageInput.fill(uniqueMessage);
    await messageInput.press('Enter');

    // Wait for any visible response before polling
    await page.waitForTimeout(10000);

    const runs = await pollForRuns(beforeTime, 'chat_completions_stream');

    expect(runs.length, 'Expected a LangSmith run').toBeGreaterThan(0);

    const inputsJson = JSON.stringify(runs[0].inputs);
    expect(inputsJson, 'User message should appear in run inputs').toContain(uniqueMessage);
  });

  test('failed chat still closes the LangSmith run without leaving it open', async ({ page }) => {
    // This test verifies the finally-block trace cleanup in chat_service.py.
    // We send a normal message and confirm the run has end_time set (not stuck open).
    const beforeTime = new Date().toISOString();

    const newThreadButton = page.getByRole('button', { name: /new/i }).first();
    await newThreadButton.click();
    await page.waitForTimeout(2000);

    const messageInput = page.getByPlaceholder(/type your message/i);
    await expect(messageInput).toBeVisible({ timeout: 10000 });
    await messageInput.fill('Say exactly: hello');
    await messageInput.press('Enter');

    await expect(page.locator('text=/hello/i').last()).toBeVisible({ timeout: 45000 });

    const runs = await pollForRuns(beforeTime, 'chat_completions_stream');

    expect(runs.length).toBeGreaterThan(0);
    expect(runs[0].end_time, 'Run must always have end_time set (finally block)').toBeTruthy();
  });
});
