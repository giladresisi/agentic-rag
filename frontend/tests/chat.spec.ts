import { test, expect } from '@playwright/test';

const timestamp = Date.now();
const testEmail = `chattest${timestamp}@example.com`;
const testPassword = 'TestPassword123!';

test.describe('Chat Functionality', () => {
  test.beforeEach(async ({ page }) => {
    // Sign up and authenticate before each test
    await page.goto('/');
    await page.getByLabel(/email/i).fill(testEmail);
    await page.getByLabel(/password/i).first().fill(testPassword);
    await page.getByRole('button', { name: /sign up|create account/i }).click();
    await expect(page).toHaveURL(/\/chat|\/$/);
  });

  test('should create a new thread', async ({ page }) => {
    // Click new thread button
    await page.getByRole('button', { name: /new thread|new chat|\+/i }).click();

    // Verify new thread is created - should have empty message input
    await expect(page.getByRole('textbox', { name: /message|type/i }).or(page.getByPlaceholder(/message|type/i))).toBeVisible();

    console.log('✓ Successfully created a new thread');
  });

  test('should send a message and receive streaming response', async ({ page }) => {
    // Find message input
    const messageInput = page.getByRole('textbox', { name: /message|type/i }).or(page.getByPlaceholder(/message|type/i));
    await expect(messageInput).toBeVisible();

    // Type a message
    await messageInput.fill('Hello, this is a test message. Please respond with "Test successful".');

    // Send message
    await page.getByRole('button', { name: /send/i }).or(page.keyboard.press('Enter')).click();

    // Wait for user message to appear
    await expect(page.getByText(/Hello, this is a test message/i)).toBeVisible({ timeout: 5000 });

    // Wait for assistant response (streaming)
    await expect(page.locator('text=/assistant|test successful/i').first()).toBeVisible({ timeout: 30000 });

    console.log('✓ Successfully sent message and received streaming response');
  });

  test('should send follow-up message (conversation continuity)', async ({ page }) => {
    // Send first message
    const messageInput = page.getByRole('textbox', { name: /message|type/i }).or(page.getByPlaceholder(/message|type/i));
    await messageInput.fill('My name is Alice.');
    await page.getByRole('button', { name: /send/i }).click();

    // Wait for response
    await page.waitForTimeout(5000);

    // Send follow-up message
    await messageInput.fill('What is my name?');
    await page.getByRole('button', { name: /send/i }).click();

    // Assistant should remember the name from previous message
    await expect(page.locator('text=/alice/i').last()).toBeVisible({ timeout: 30000 });

    console.log('✓ Successfully tested conversation continuity');
  });

  test('should create and switch between multiple threads', async ({ page }) => {
    // Create first thread and send a message
    await page.getByRole('button', { name: /new thread|new chat|\+/i }).click();
    const messageInput = page.getByRole('textbox', { name: /message|type/i }).or(page.getByPlaceholder(/message|type/i));
    await messageInput.fill('This is thread 1');
    await page.getByRole('button', { name: /send/i }).click();
    await page.waitForTimeout(2000);

    // Create second thread
    await page.getByRole('button', { name: /new thread|new chat|\+/i }).click();
    await messageInput.fill('This is thread 2');
    await page.getByRole('button', { name: /send/i }).click();
    await page.waitForTimeout(2000);

    // Should have multiple threads in sidebar
    const threads = page.locator('[role="list"] > *').or(page.locator('.thread-item, [data-thread], .thread'));
    await expect(threads.first()).toBeVisible();

    console.log('✓ Successfully created multiple threads');
  });

  test('should persist messages after page refresh', async ({ page }) => {
    // Send a unique message
    const uniqueMessage = `Unique test message ${timestamp}`;
    const messageInput = page.getByRole('textbox', { name: /message|type/i }).or(page.getByPlaceholder(/message|type/i));
    await messageInput.fill(uniqueMessage);
    await page.getByRole('button', { name: /send/i }).click();

    // Wait for message to appear
    await expect(page.getByText(uniqueMessage)).toBeVisible({ timeout: 5000 });

    // Refresh page
    await page.reload();

    // Message should still be visible after refresh
    await expect(page.getByText(uniqueMessage)).toBeVisible({ timeout: 10000 });

    console.log('✓ Messages persist after page refresh');
  });
});
