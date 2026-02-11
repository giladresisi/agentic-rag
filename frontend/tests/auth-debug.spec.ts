import { test, expect } from '@playwright/test';

const timestamp = Date.now();
const testEmail = `debug${timestamp}@example.com`;
const testPassword = 'TestPassword123!';

test('debug signup flow', async ({ page }) => {
  // Listen for console messages
  page.on('console', msg => console.log('Browser console:', msg.text()));

  // Listen for page errors
  page.on('pageerror', err => console.log('Page error:', err.message));

  // Listen for network responses
  page.on('response', response => {
    if (response.url().includes('/api/') && response.status() >= 400) {
      console.log(`API Error: ${response.status()} ${response.url()}`);
    }
  });

  await page.goto('/signup');

  // Fill in signup form
  await page.fill('#email', testEmail);
  await page.fill('#password', testPassword);
  await page.fill('#confirmPassword', testPassword);

  // Submit form
  await page.getByRole('button', { name: 'Sign Up' }).click();

  // Wait a bit to see what happens
  await page.waitForTimeout(5000);

  // Check for error messages
  const errorText = await page.locator('.text-destructive, .error, [role="alert"]').allTextContents();
  if (errorText.length > 0) {
    console.log('Error messages found:', errorText);
  }

  // Check current URL
  console.log('Current URL:', page.url());

  // Take a screenshot
  await page.screenshot({ path: 'signup-debug.png', fullPage: true });
  console.log('Screenshot saved to signup-debug.png');
});
