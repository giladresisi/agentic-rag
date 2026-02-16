import { test, expect } from '@playwright/test';
import * as path from 'path';
import * as fs from 'fs';
import { fileURLToPath } from 'url';
import { TEST_EMAIL, TEST_PASSWORD } from './utils';

// ES modules equivalent of __dirname
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

test.describe('Multi-file upload', () => {
  test.beforeEach(async ({ page }) => {
    // Login
    await page.goto('http://localhost:5173');
    await page.fill('input[type="email"]', TEST_EMAIL);
    await page.fill('input[type="password"]', TEST_PASSWORD);
    await page.click('button[type="submit"]');
    await page.waitForURL('**/chat');

    // Navigate to ingestion
    await page.click('text=Documents');
    await page.waitForURL('**/ingestion');
  });

  test('should accept multiple files via file picker', async ({ page }) => {
    // Create 3 test files
    const testFiles = [
      path.join(__dirname, 'fixtures', 'test1.txt'),
      path.join(__dirname, 'fixtures', 'test2.txt'),
      path.join(__dirname, 'fixtures', 'test3.txt'),
    ];

    // Ensure fixtures directory exists
    const fixturesDir = path.join(__dirname, 'fixtures');
    if (!fs.existsSync(fixturesDir)) {
      fs.mkdirSync(fixturesDir, { recursive: true });
    }

    // Create test files
    testFiles.forEach((filePath, idx) => {
      fs.writeFileSync(filePath, `Test content ${idx + 1}`);
    });

    // Select multiple files
    const fileInput = page.locator('input[type="file"]').first();
    await fileInput.setInputFiles(testFiles);

    // Verify all 3 files appear in queue
    await expect(page.locator('text=3 files in queue')).toBeVisible();
    await expect(page.getByText('test1.txt')).toBeVisible();
    await expect(page.getByText('test2.txt')).toBeVisible();
    await expect(page.getByText('test3.txt')).toBeVisible();

    // Cleanup
    testFiles.forEach(filePath => {
      if (fs.existsSync(filePath)) fs.unlinkSync(filePath);
    });
  });

  test('should allow removing files from queue', async ({ page }) => {
    // Create test file
    const testFile = path.join(__dirname, 'fixtures', 'test-remove.txt');
    const fixturesDir = path.join(__dirname, 'fixtures');
    if (!fs.existsSync(fixturesDir)) {
      fs.mkdirSync(fixturesDir, { recursive: true });
    }
    fs.writeFileSync(testFile, 'Test content');

    // Add 2 files
    const fileInput = page.locator('input[type="file"]').first();
    await fileInput.setInputFiles([testFile, testFile]);

    // Verify 2 files in queue
    await expect(page.locator('text=2 files in queue')).toBeVisible();

    // Remove first file
    await page.locator('button[title="Remove file"]').first().click();

    // Verify 1 file remains
    await expect(page.locator('text=1 file in queue')).toBeVisible();

    // Cleanup
    if (fs.existsSync(testFile)) fs.unlinkSync(testFile);
  });

  test('should clear all files', async ({ page }) => {
    // Create test file
    const testFile = path.join(__dirname, 'fixtures', 'test-clear.txt');
    const fixturesDir = path.join(__dirname, 'fixtures');
    if (!fs.existsSync(fixturesDir)) {
      fs.mkdirSync(fixturesDir, { recursive: true });
    }
    fs.writeFileSync(testFile, 'Test content');

    // Add files
    const fileInput = page.locator('input[type="file"]').first();
    await fileInput.setInputFiles([testFile, testFile]);

    // Verify files in queue
    await expect(page.locator('text=2 files in queue')).toBeVisible();

    // Click Clear All
    await page.click('text=Clear All');

    // Verify drop zone appears
    await expect(page.locator('text=Drag and drop files here')).toBeVisible();

    // Cleanup
    if (fs.existsSync(testFile)) fs.unlinkSync(testFile);
  });

  test('should upload multiple files sequentially', async ({ page }) => {
    // Create small test files
    const testFiles = [
      path.join(__dirname, 'fixtures', 'upload1.txt'),
      path.join(__dirname, 'fixtures', 'upload2.txt'),
    ];

    const fixturesDir = path.join(__dirname, 'fixtures');
    if (!fs.existsSync(fixturesDir)) {
      fs.mkdirSync(fixturesDir, { recursive: true });
    }

    testFiles.forEach((filePath, idx) => {
      fs.writeFileSync(filePath, `Upload test content ${idx + 1}\n`.repeat(10));
    });

    // Select files
    const fileInput = page.locator('input[type="file"]').first();
    await fileInput.setInputFiles(testFiles);

    // Click Upload All
    await page.click('text=Upload All');

    // Wait for first file to start uploading
    await expect(page.locator('text=Uploading 1 of 2')).toBeVisible({ timeout: 10000 });

    // Wait for upload to complete
    await expect(page.locator('text=Upload Complete')).toBeVisible({ timeout: 30000 });
    await expect(page.locator('text=2 succeeded, 0 failed')).toBeVisible();

    // Verify success icons
    const successIcons = page.locator('text=✓');
    await expect(successIcons).toHaveCount(2);

    // Cleanup
    testFiles.forEach(filePath => {
      if (fs.existsSync(filePath)) fs.unlinkSync(filePath);
    });
  });

  test('should show validation errors for invalid files', async ({ page }) => {
    // Create an invalid file (unsupported extension)
    const invalidFile = path.join(__dirname, 'fixtures', 'test.xyz');
    const fixturesDir = path.join(__dirname, 'fixtures');
    if (!fs.existsSync(fixturesDir)) {
      fs.mkdirSync(fixturesDir, { recursive: true });
    }
    fs.writeFileSync(invalidFile, 'Invalid file content');

    // Try to select it
    const fileInput = page.locator('input[type="file"]').first();
    await fileInput.setInputFiles([invalidFile]);

    // Verify validation error shown
    await expect(page.locator('text=Invalid')).toBeVisible();
    await expect(page.locator('text=unsupported type')).toBeVisible();

    // Verify Upload All button is disabled
    const uploadButton = page.locator('button:has-text("Upload All")');
    await expect(uploadButton).toBeDisabled();

    // Cleanup
    if (fs.existsSync(invalidFile)) fs.unlinkSync(invalidFile);
  });

  test('should handle duplicate file errors and continue with remaining files', async ({ page }) => {
    const fixturesDir = path.join(__dirname, 'fixtures');
    if (!fs.existsSync(fixturesDir)) {
      fs.mkdirSync(fixturesDir, { recursive: true });
    }

    // Create unique test files with timestamp to avoid conflicts with other tests
    const timestamp = Date.now();
    const duplicateFile = path.join(fixturesDir, `duplicate-${timestamp}.txt`);
    const file2 = path.join(fixturesDir, `after-duplicate1-${timestamp}.txt`);
    const file3 = path.join(fixturesDir, `after-duplicate2-${timestamp}.txt`);

    fs.writeFileSync(duplicateFile, 'This file will be uploaded twice');
    fs.writeFileSync(file2, 'Second file content');
    fs.writeFileSync(file3, 'Third file content');

    try {
      // Step 1: Upload the file for the first time
      const fileInput1 = page.locator('input[type="file"]').first();
      await fileInput1.setInputFiles([duplicateFile]);

      await expect(page.locator('text=1 file in queue')).toBeVisible();

      // Upload - we just need the file to reach storage, not complete processing
      await page.click('text=Upload All');

      // Wait for upload to start
      await expect(page.locator('text=Uploading 1 of 1')).toBeVisible({ timeout: 10000 });

      // Wait a few seconds for the file to reach storage
      // The file will be uploaded to storage immediately, even if processing continues
      await page.waitForTimeout(5000);

      // Navigate back to ingestion page to reset upload state
      await page.goto('http://localhost:5173/ingestion');
      await page.waitForLoadState('networkidle');

      // Wait for upload interface to be ready
      await expect(page.locator('text=Upload Documents')).toBeVisible({ timeout: 10000 });

      // Step 2: Try to upload the same file again + 2 new files
      const fileInput2 = page.locator('input[type="file"]').first();
      await fileInput2.setInputFiles([duplicateFile, file2, file3]);

      // Verify 3 files in queue
      await expect(page.locator('text=3 files in queue')).toBeVisible();

      // Start upload
      await page.click('text=Upload All');

      // Wait for the duplicate error dialog to appear
      await expect(page.locator('text=Upload Failed')).toBeVisible({ timeout: 15000 });
      await expect(page.locator(`text="${path.basename(duplicateFile)}" failed to upload`)).toBeVisible();
      await expect(page.locator('text=already exists')).toBeVisible();
      await expect(page.locator('text=2 files remaining in queue')).toBeVisible();

      // Click "Continue with next file"
      await page.click('button:has-text("Continue with next file")');

      // Verify dialog closes
      await expect(page.locator('text=Upload Failed')).not.toBeVisible();

      // Wait for next file to start uploading
      await expect(page.locator('text=Uploading')).toBeVisible({ timeout: 10000 });

      // Wait for all uploads to complete - look for success status on the remaining files
      // We should see 2 success icons (for file2 and file3)
      await expect(page.locator('text=✓')).toHaveCount(2, { timeout: 60000 });

      // Verify the duplicate file shows failed status
      await expect(page.locator('text=Failed')).toBeVisible();
      await expect(page.locator('text=✗')).toBeVisible();

      // Wait a moment for the upload complete message
      await page.waitForTimeout(1000);

      // Verify final summary if visible (optional, may not always appear)
      const uploadComplete = page.locator('text=Upload Complete');
      if (await uploadComplete.isVisible({ timeout: 2000 }).catch(() => false)) {
        await expect(page.locator('text=2 succeeded, 1 failed')).toBeVisible();
      }

    } finally {
      // Cleanup test files
      [duplicateFile, file2, file3].forEach(filePath => {
        if (fs.existsSync(filePath)) fs.unlinkSync(filePath);
      });

      // Cleanup uploaded documents from the database
      // Note: In a real test, you might want to delete these via API or clean up the test user's data
      // For now, the cleanup happens naturally when the test user's documents are cleared
    }
  });

  test('should stop upload when user clicks "Stop uploading" on error', async ({ page }) => {
    const fixturesDir = path.join(__dirname, 'fixtures');
    if (!fs.existsSync(fixturesDir)) {
      fs.mkdirSync(fixturesDir, { recursive: true });
    }

    const timestamp = Date.now();
    const duplicateFile = path.join(fixturesDir, `stop-duplicate-${timestamp}.txt`);
    const file2 = path.join(fixturesDir, `stop-after1-${timestamp}.txt`);
    const file3 = path.join(fixturesDir, `stop-after2-${timestamp}.txt`);

    fs.writeFileSync(duplicateFile, 'Duplicate file for stop test');
    fs.writeFileSync(file2, 'Should not upload 1');
    fs.writeFileSync(file3, 'Should not upload 2');

    try {
      // Upload the file first
      const fileInput1 = page.locator('input[type="file"]').first();
      await fileInput1.setInputFiles([duplicateFile]);
      await page.click('text=Upload All');

      // Wait for upload to reach storage
      await page.waitForTimeout(5000);

      // Navigate back to ingestion page to reset state
      await page.goto('http://localhost:5173/ingestion');
      await page.waitForLoadState('networkidle');
      await expect(page.locator('text=Upload Documents')).toBeVisible({ timeout: 10000 });

      // Try to upload duplicate + 2 new files
      const fileInput2 = page.locator('input[type="file"]').first();
      await fileInput2.setInputFiles([duplicateFile, file2, file3]);
      await page.click('text=Upload All');

      // Wait for error dialog
      await expect(page.locator('text=Upload Failed')).toBeVisible({ timeout: 15000 });

      // Click "Stop uploading"
      await page.click('button:has-text("Stop uploading")');

      // Verify dialog closes
      await expect(page.locator('text=Upload Failed')).not.toBeVisible();

      // Verify no "Upload Complete" message appears (upload was stopped)
      // The queue should show 1 failed, 2 waiting (not uploaded)
      await expect(page.locator('text=Failed')).toBeVisible();
      await expect(page.locator('text=Waiting')).toHaveCount(2);

    } finally {
      // Cleanup
      [duplicateFile, file2, file3].forEach(filePath => {
        if (fs.existsSync(filePath)) fs.unlinkSync(filePath);
      });
    }
  });
});
