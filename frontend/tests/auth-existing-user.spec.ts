import { test, expect } from '@playwright/test';
import { TEST_EMAIL, TEST_PASSWORD } from './utils';

test.describe('Authentication with Existing User', () => {
  test('should enforce protected routes', async ({ page }) => {
    // Try to access chat page without authentication
    await page.goto('/chat');
    // Wait for the app to fully initialise and the auth guard to fire
    await page.waitForLoadState('networkidle');

    // Should redirect to login page
    await expect(page).toHaveURL('/login', { timeout: 15000 });
    await expect(page.getByRole('heading', { name: 'Login' })).toBeVisible();

    console.log('✅ Protected routes are enforced');
  });

  test('should log in with existing user', async ({ page }) => {
    await page.goto('/login');

    // Fill in login form
    await page.fill('#email', TEST_EMAIL);
    await page.fill('#password', TEST_PASSWORD);

    // Submit login
    await page.getByRole('button', { name: 'Login' }).click();

    // Should redirect to /chat after successful login
    await expect(page).toHaveURL('/chat', { timeout: 15000 });

    // Verify we're in the chat interface - should see either:
    // 1. "Select a thread" message (no active thread), OR
    // 2. Thread sidebar with "New" button
    const emptyStateOrSidebar = page.getByText(/Select a thread|Agentic RAG/i).or(page.getByRole('button', { name: /new/i }));
    await expect(emptyStateOrSidebar.first()).toBeVisible({ timeout: 10000 });

    // Verify user email is shown in header
    await expect(page.getByText(TEST_EMAIL)).toBeVisible();

    console.log('✅ Successfully logged in with existing user');
  });

  test('should verify JWT authentication persists after refresh', async ({ page }) => {
    // Log in first
    await page.goto('/login');
    await page.fill('#email', TEST_EMAIL);
    await page.fill('#password', TEST_PASSWORD);
    await page.getByRole('button', { name: 'Login' }).click();
    await expect(page).toHaveURL('/chat', { timeout: 15000 });

    // Check that user is authenticated - look for user email in header
    await expect(page.getByText(TEST_EMAIL)).toBeVisible();

    // Refresh page - should remain authenticated
    await page.reload();
    // Give the auth guard time to restore the session before asserting the URL
    await expect(page).toHaveURL('/chat', { timeout: 15000 });

    // Should still see user email after refresh
    await expect(page.getByText(TEST_EMAIL)).toBeVisible({ timeout: 15000 });

    console.log('✅ JWT authentication persists after page refresh');
  });

  test('should log out successfully', async ({ page }) => {
    // Log in first
    await page.goto('/login');
    await page.fill('#email', TEST_EMAIL);
    await page.fill('#password', TEST_PASSWORD);
    await page.getByRole('button', { name: 'Login' }).click();
    await expect(page).toHaveURL('/chat', { timeout: 15000 });

    // Open the profile dropdown first (the logout button is hidden inside it)
    await page.getByText(TEST_EMAIL).click();
    // Click "Log out" in the dropdown (button text is "Log out" with a space)
    const logoutButton = page.getByRole('button', { name: /log out/i });
    await expect(logoutButton).toBeVisible({ timeout: 5000 });
    await logoutButton.click();

    // Should redirect back to login page
    await expect(page).toHaveURL('/login', { timeout: 10000 });
    await expect(page.getByRole('heading', { name: 'Login' })).toBeVisible();

    console.log('✅ Successfully logged out');
  });
});
