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
});
