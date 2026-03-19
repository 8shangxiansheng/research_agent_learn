import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { defineConfig, devices } from '@playwright/test'

const frontendDir = path.dirname(fileURLToPath(import.meta.url))
const projectRoot = path.resolve(frontendDir, '..')
const backendCommand =
  process.env.PLAYWRIGHT_BACKEND_CMD
  ?? 'python -m uvicorn app.main:app --host 127.0.0.1 --port 8000'

export default defineConfig({
  testDir: './e2e',
  fullyParallel: false,
  retries: process.env.CI ? 2 : 0,
  reporter: process.env.CI ? [['github'], ['html', { open: 'never' }]] : 'list',
  use: {
    baseURL: 'http://127.0.0.1:4173',
    trace: 'on-first-retry',
    testIdAttribute: 'data-test',
  },
  webServer: [
    {
      command: backendCommand,
      cwd: projectRoot,
      url: 'http://127.0.0.1:8000/health',
      reuseExistingServer: !process.env.CI,
      env: {
        ...process.env,
        ACADEMIC_QA_MOCK_MODE: '1',
        DATABASE_URL: `sqlite:///${path.join(projectRoot, 'playwright-e2e.db')}`,
      },
    },
    {
      command: 'npm run dev -- --host 127.0.0.1 --port 4173',
      cwd: frontendDir,
      url: 'http://127.0.0.1:4173',
      reuseExistingServer: !process.env.CI,
      env: {
        ...process.env,
      },
    },
  ],
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
})
