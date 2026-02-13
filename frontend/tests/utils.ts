/**
 * Test utilities for frontend tests.
 *
 * Centralizes test credentials to avoid hardcoding in test files.
 * Credentials are loaded from environment variables (set in .env file).
 */

// Test credentials from environment variables
// In CI/CD, these should be set as environment variables
// For local development, these are loaded from .env file
export const TEST_EMAIL = process.env.TEST_EMAIL || 'test@...';
export const TEST_PASSWORD = process.env.TEST_PASSWORD || '***';
