import { test, expect } from '@playwright/test';

test.describe.configure({ mode: 'serial' }); // Run tests one after another

test.describe('Authentication Flow', () => {
  test('should enforce protected routes', async ({ page }) => {
    // Try to access chat page without authentication
    await page.goto('/chat');

    // Should redirect to login page
    await expect(page).toHaveURL('/login', { timeout: 10000 });
    await expect(page.getByRole('heading', { name: 'Login' })).toBeVisible();

    console.log('✓ Protected routes are enforced');
  });

  test('should sign up a new user', async ({ page }) => {
    // Wait to avoid rate limiting
    await page.waitForTimeout(5000);

    // Generate unique email for this specific test
    const testEmail = `test${Date.now()}${Math.random().toString(36).substring(7)}@example.com`;
    const testPassword = 'TestPassword123!';

    // Navigate to signup page
    await page.goto('/signup');

    // Should see signup form
    await expect(page.getByRole('heading', { name: 'Sign Up' })).toBeVisible();

    // Fill in signup form
    await page.fill('#email', testEmail);
    await page.fill('#password', testPassword);
    await page.fill('#confirmPassword', testPassword);

    // Submit signup form
    await page.getByRole('button', { name: 'Sign Up' }).click();

    // Should redirect to /chat after successful signup
    await expect(page).toHaveURL('/chat', { timeout: 15000 });

    // Verify we're authenticated - should see chat interface
    await expect(page.locator('textarea, input[type="text"]').first()).toBeVisible({ timeout: 10000 });

    console.log(`✓ Successfully signed up user: ${testEmail}`);
  });

  test('should log out and log back in', async ({ page }) => {
    // Wait to avoid rate limiting
    await page.waitForTimeout(8000);

    // Generate unique email for this test
    const testEmail = `test${Date.now()}${Math.random().toString(36).substring(7)}@example.com`;
    const testPassword = 'TestPassword123!';

    // First, sign up
    await page.goto('/signup');
    await page.fill('#email', testEmail);
    await page.fill('#password', testPassword);
    await page.fill('#confirmPassword', testPassword);
    await page.getByRole('button', { name: 'Sign Up' }).click();
    await expect(page).toHaveURL('/chat', { timeout: 15000 });

    // Log out (look for logout button in nav or user menu)
    const logoutButton = page.getByRole('button', { name: /log out|sign out|logout/i });
    await logoutButton.click();

    // Should redirect back to login page
    await expect(page).toHaveURL('/login', { timeout: 10000 });
    await expect(page.getByRole('heading', { name: 'Login' })).toBeVisible();

    // Wait before logging back in
    await page.waitForTimeout(3000);

    // Now log back in
    await page.fill('#email', testEmail);
    await page.fill('#password', testPassword);
    await page.getByRole('button', { name: 'Login' }).click();

    // Should be back in chat interface
    await expect(page).toHaveURL('/chat', { timeout: 15000 });
    await expect(page.locator('textarea, input[type="text"]').first()).toBeVisible({ timeout: 10000 });

    console.log('✓ Successfully logged out and logged back in');
  });

  test('should verify JWT authentication persists', async ({ page }) => {
    // Wait to avoid rate limiting
    await page.waitForTimeout(8000);

    // Generate unique email for this test
    const testEmail = `test${Date.now()}${Math.random().toString(36).substring(7)}@example.com`;
    const testPassword = 'TestPassword123!';

    // Sign up first
    await page.goto('/signup');
    await page.fill('#email', testEmail);
    await page.fill('#password', testPassword);
    await page.fill('#confirmPassword', testPassword);
    await page.getByRole('button', { name: 'Sign Up' }).click();
    await expect(page).toHaveURL('/chat', { timeout: 15000 });

    // Check that auth token is stored (localStorage)
    const authData = await page.evaluate(() => window.localStorage.getItem('auth'));
    expect(authData).toBeTruthy();

    // Refresh page - should remain authenticated
    await page.reload();
    await expect(page).toHaveURL('/chat');
    await expect(page.locator('textarea, input[type="text"]').first()).toBeVisible({ timeout: 10000 });

    console.log('✓ JWT authentication persists after page refresh');
  });
});
