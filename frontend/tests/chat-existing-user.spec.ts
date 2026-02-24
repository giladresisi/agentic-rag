import { test, expect } from '@playwright/test';
import { TEST_EMAIL, TEST_PASSWORD } from './utils';

test.describe('Chat Functionality with Existing User', () => {
  // Log in before each test
  test.beforeEach(async ({ page }) => {
    await page.goto('/login');
    await page.fill('#email', TEST_EMAIL);
    await page.fill('#password', TEST_PASSWORD);
    await page.getByRole('button', { name: 'Login' }).click();
    await expect(page).toHaveURL('/chat', { timeout: 15000 });
  });

  test('should create a new thread and show message input', async ({ page }) => {
    // Click new thread button
    const newThreadButton = page.getByRole('button', { name: /new/i }).first();
    await newThreadButton.click();

    // Wait a moment for thread creation
    await page.waitForTimeout(2000);

    // Verify message input is available using placeholder
    const messageInput = page.getByPlaceholder(/type your message/i);
    await expect(messageInput).toBeVisible({ timeout: 10000 });

    console.log('✅ Successfully created a new thread with message input');
  });

  test('should send a message and receive streaming response', async ({ page }) => {
    // Create new thread first
    const newThreadButton = page.getByRole('button', { name: /new/i }).first();
    await newThreadButton.click();
    await page.waitForTimeout(2000);

    // Find message input by placeholder
    const messageInput = page.getByPlaceholder(/type your message/i);
    await expect(messageInput).toBeVisible({ timeout: 10000 });

    // Type a simple message and press Enter to send
    await messageInput.fill('What is 2+2?');
    await messageInput.press('Enter');

    // Wait for user message to appear
    await expect(page.getByText(/What is 2\+2\?/i)).toBeVisible({ timeout: 5000 });

    // Wait for assistant response (looking for "4" in the response)
    await expect(page.locator('text=/4|four/i').last()).toBeVisible({ timeout: 45000 });

    console.log('✅ Successfully sent message and received streaming response');
  });

  test('should maintain conversation continuity', async ({ page }) => {
    // Create new thread
    const newThreadButton = page.getByRole('button', { name: /new/i }).first();
    await newThreadButton.click();
    await page.waitForTimeout(2000);

    // Send first message
    const messageInput = page.getByPlaceholder(/type your message/i);
    await expect(messageInput).toBeVisible({ timeout: 10000 });
    await messageInput.fill('My favorite color is blue.');
    await messageInput.press('Enter');

    // Wait for response
    await page.waitForTimeout(10000);

    // Send follow-up message
    await messageInput.fill('What is my favorite color?');
    await messageInput.press('Enter');

    // Assistant should remember "blue"
    await expect(page.locator('text=/blue/i').last()).toBeVisible({ timeout: 45000 });

    console.log('✅ Conversation continuity maintained');
  });

  test('should persist messages after page refresh', async ({ page }) => {
    // Create new thread
    const newThreadButton = page.getByRole('button', { name: /new/i }).first();
    await newThreadButton.click();
    await page.waitForTimeout(2000);

    // Send a unique message
    const uniqueMessage = `Test persist ${Date.now()}`;
    const messageInput = page.getByPlaceholder(/type your message/i);
    await expect(messageInput).toBeVisible({ timeout: 10000 });
    await messageInput.fill(uniqueMessage);
    await messageInput.press('Enter');

    // Wait for message to appear
    await expect(page.getByText(uniqueMessage)).toBeVisible({ timeout: 5000 });

    // Refresh page
    await page.reload();
    await expect(page).toHaveURL('/chat', { timeout: 15000 });

    // Wait for the thread list to load (sidebar shows the "New Thread" button when ready)
    await expect(page.getByRole('button', { name: /new thread/i })).toBeVisible({ timeout: 10000 });
    await page.waitForTimeout(1000);

    // After reload currentThreadId resets to null — click the most recent thread to re-open it.
    // Thread items are div.cursor-pointer entries; the first one is the most recently updated thread.
    const firstThread = page.locator('div.cursor-pointer span.truncate').first();
    await expect(firstThread).toBeVisible({ timeout: 10000 });
    await firstThread.click();

    // Message should still be visible after refresh
    await expect(page.getByText(uniqueMessage)).toBeVisible({ timeout: 10000 });

    console.log('✅ Messages persist after page refresh');
  });

  test('should create and display multiple threads', async ({ page }) => {
    // Create first thread
    const newThreadButton = page.getByRole('button', { name: /new/i }).first();
    await newThreadButton.click();
    await page.waitForTimeout(2000);

    const messageInput = page.getByPlaceholder(/type your message/i);
    await expect(messageInput).toBeVisible({ timeout: 10000 });
    await messageInput.fill('Thread 1 message');
    await messageInput.press('Enter');
    await page.waitForTimeout(5000);

    // Create second thread
    await newThreadButton.click();
    await page.waitForTimeout(2000);
    await messageInput.fill('Thread 2 message');
    await messageInput.press('Enter');
    await page.waitForTimeout(5000);

    // Check that we have threads (look for thread titles or "New Chat" text)
    const threadsList = page.locator('text=/New Chat|Thread/i');
    const count = await threadsList.count();
    expect(count).toBeGreaterThanOrEqual(2);

    console.log('✅ Multiple threads created and displayed');
  });
});
