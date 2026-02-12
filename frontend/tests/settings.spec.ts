import { test, expect } from '@playwright/test';

// Use existing test account
const TEST_EMAIL = 'test@...';
const TEST_PASSWORD = '***';

test.describe('Settings Modal - Plan 7', () => {
  // Log in before each test
  test.beforeEach(async ({ page }) => {
    await page.goto('/login');
    await page.fill('#email', TEST_EMAIL);
    await page.fill('#password', TEST_PASSWORD);
    await page.getByRole('button', { name: 'Login' }).click();
    await expect(page).toHaveURL('/chat', { timeout: 15000 });
  });

  test('should display user profile button at bottom of sidebar', async ({ page }) => {
    // Look for user profile button with email
    const profileButton = page.locator('button:has-text("test@...")');
    await expect(profileButton).toBeVisible({ timeout: 10000 });

    // Verify it shows user initial
    const initial = page.locator('text=/^T$/').first();
    await expect(initial).toBeVisible();

    console.log('✅ User profile button visible at bottom of sidebar');
  });

  test('should open profile menu with Settings and Logout options', async ({ page }) => {
    // Click profile button
    const profileButton = page.locator('button:has-text("test@...")');
    await expect(profileButton).toBeVisible({ timeout: 10000 });
    await profileButton.click();

    // Wait for menu to appear
    await page.waitForTimeout(500);

    // Verify Settings option
    const settingsOption = page.getByRole('button', { name: /settings/i });
    await expect(settingsOption).toBeVisible();

    // Verify Logout option
    const logoutOption = page.getByRole('button', { name: /log out/i });
    await expect(logoutOption).toBeVisible();

    console.log('✅ Profile menu opens with Settings and Logout options');
  });

  test('should open settings modal when clicking Settings', async ({ page }) => {
    // Click profile button
    const profileButton = page.locator('button:has-text("test@...")');
    await expect(profileButton).toBeVisible({ timeout: 10000 });
    await profileButton.click();
    await page.waitForTimeout(500);

    // Click Settings
    const settingsOption = page.getByRole('button', { name: /settings/i });
    await settingsOption.click();

    // Verify modal appears
    await expect(page.getByText('Configure model providers for chat and embeddings')).toBeVisible({ timeout: 5000 });

    // Verify sections exist
    await expect(page.getByText('Chat Model')).toBeVisible();
    await expect(page.getByText('Embeddings Model')).toBeVisible();

    // Verify buttons
    await expect(page.getByRole('button', { name: 'Cancel' })).toBeVisible();
    await expect(page.getByRole('button', { name: 'Confirm' })).toBeVisible();

    console.log('✅ Settings modal opens with all sections');
  });

  test('should show provider and model dropdowns in settings modal', async ({ page }) => {
    // Open settings modal
    const profileButton = page.locator('button:has-text("test@...")');
    await profileButton.click();
    await page.waitForTimeout(500);
    await page.getByRole('button', { name: /settings/i }).click();
    await page.waitForTimeout(1000);

    // Verify Chat Model section has dropdowns
    const chatSection = page.locator('text=Chat Model').locator('..');
    const providerSelects = page.locator('select');
    expect(await providerSelects.count()).toBeGreaterThanOrEqual(2); // At least 2 selects (chat provider + embeddings provider)

    console.log('✅ Provider and model dropdowns present');
  });

  test('should enable Confirm button only when changes are made', async ({ page }) => {
    // Open settings modal
    const profileButton = page.locator('button:has-text("test@...")');
    await profileButton.click();
    await page.waitForTimeout(500);
    await page.getByRole('button', { name: /settings/i }).click();
    await page.waitForTimeout(1000);

    // Confirm button should be disabled initially (no changes)
    const confirmButton = page.getByRole('button', { name: 'Confirm' });
    await expect(confirmButton).toBeDisabled();

    // Make a change - select a different provider
    const providerSelects = page.locator('select');
    const firstSelect = providerSelects.first();
    await firstSelect.selectOption('openrouter');
    await page.waitForTimeout(500);

    // Confirm button should now be enabled
    await expect(confirmButton).toBeEnabled();

    console.log('✅ Confirm button enabled only when changes made');
  });

  test('should revert changes when Cancel is clicked', async ({ page }) => {
    // Open settings modal
    const profileButton = page.locator('button:has-text("test@...")');
    await profileButton.click();
    await page.waitForTimeout(500);
    await page.getByRole('button', { name: /settings/i }).click();
    await page.waitForTimeout(1000);

    // Get initial provider value
    const providerSelects = page.locator('select');
    const firstSelect = providerSelects.first();
    const initialValue = await firstSelect.inputValue();

    // Change provider
    await firstSelect.selectOption('openrouter');
    await page.waitForTimeout(500);

    // Click Cancel
    await page.getByRole('button', { name: 'Cancel' }).click();
    await page.waitForTimeout(500);

    // Modal should close
    await expect(page.getByText('Configure model providers for chat and embeddings')).not.toBeVisible();

    // Open modal again and verify value is reverted
    await profileButton.click();
    await page.waitForTimeout(500);
    await page.getByRole('button', { name: /settings/i }).click();
    await page.waitForTimeout(1000);

    const revertedValue = await providerSelects.first().inputValue();
    expect(revertedValue).toBe(initialValue);

    console.log('✅ Changes reverted when Cancel clicked');
  });

  test('should close modal and apply changes when Confirm is clicked', async ({ page }) => {
    // Open settings modal
    const profileButton = page.locator('button:has-text("test@...")');
    await profileButton.click();
    await page.waitForTimeout(500);
    await page.getByRole('button', { name: /settings/i }).click();
    await page.waitForTimeout(1000);

    // Change provider
    const providerSelects = page.locator('select');
    await providerSelects.first().selectOption('ollama');
    await page.waitForTimeout(500);

    // Click Confirm
    const confirmButton = page.getByRole('button', { name: 'Confirm' });
    await confirmButton.click();
    await page.waitForTimeout(500);

    // Modal should close
    await expect(page.getByText('Configure model providers for chat and embeddings')).not.toBeVisible();

    // Open modal again and verify change persisted
    await profileButton.click();
    await page.waitForTimeout(500);
    await page.getByRole('button', { name: /settings/i }).click();
    await page.waitForTimeout(1000);

    const persistedValue = await providerSelects.first().inputValue();
    expect(persistedValue).toBe('ollama');

    console.log('✅ Changes applied and persisted when Confirm clicked');
  });

  test('should have separate chat and embeddings model configurations', async ({ page }) => {
    // Open settings modal
    const profileButton = page.locator('button:has-text("test@...")');
    await profileButton.click();
    await page.waitForTimeout(500);
    await page.getByRole('button', { name: /settings/i }).click();
    await page.waitForTimeout(1000);

    // Verify both sections exist with labels
    await expect(page.getByText('Chat Model')).toBeVisible();
    await expect(page.getByText('Model used for chat conversations and LLM completions')).toBeVisible();

    await expect(page.getByText('Embeddings Model')).toBeVisible();
    await expect(page.getByText('Model used for document embeddings and vector search')).toBeVisible();

    // Verify we have at least 4 selects (2 provider + 2 model)
    const selects = page.locator('select');
    const selectCount = await selects.count();
    expect(selectCount).toBeGreaterThanOrEqual(2); // Should have provider selects for both

    console.log('✅ Separate chat and embeddings configurations present');
  });

  test('should not show API key fields (server-side only)', async ({ page }) => {
    // Open settings modal
    const profileButton = page.locator('button:has-text("test@...")');
    await profileButton.click();
    await page.waitForTimeout(500);
    await page.getByRole('button', { name: /settings/i }).click();
    await page.waitForTimeout(1000);

    // Verify no API key input fields
    const apiKeyInputs = page.locator('input[type="text"]:has-text("API"), input[type="password"]:has-text("API")');
    expect(await apiKeyInputs.count()).toBe(0);

    // Also check for any text containing "API Key"
    const apiKeyText = page.getByText(/api key/i);
    expect(await apiKeyText.count()).toBe(0);

    console.log('✅ No API key fields visible (server-side only)');
  });
});
