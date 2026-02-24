import { defineConfig, devices } from '@playwright/test';
import dotenv from 'dotenv';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// Load backend .env FIRST — it holds the authoritative TEST_EMAIL, TEST_PASSWORD,
// LANGSMITH_API_KEY etc. Loading it first ensures its values are not shadowed by
// any placeholder equivalents in frontend/.env.
dotenv.config({ path: path.resolve(__dirname, '../backend/.env') });
// Load frontend .env second (VITE_* vars). Vars already set above are not overridden.
dotenv.config({ path: path.resolve(__dirname, '.env') });

export default defineConfig({
  testDir: './tests',
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: 1,
  reporter: 'html',
  use: {
    baseURL: 'http://localhost:5173',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
  webServer: [
    {
      // Backend (FastAPI/uvicorn) — must be running for auth, chat, and ingestion to work.
      // On Windows (Git Bash) run from backend/: uv run uvicorn main:app --reload --port 8000
      command: 'cd ../backend && uv run uvicorn main:app --port 8000',
      url: 'http://localhost:8000/health',
      reuseExistingServer: true,
      timeout: 60000,
    },
    {
      command: 'npm run dev',
      url: 'http://localhost:5173',
      reuseExistingServer: true,
    },
  ],
});
