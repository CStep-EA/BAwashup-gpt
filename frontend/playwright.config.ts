import { defineConfig, devices } from '@playwright/test'

/**
 * Bower Ag CowCare Tool — Playwright E2E Configuration
 * Sprint 15: Mobile-first (390px) E2E tests.
 *
 * Usage:
 *   npx playwright test                     # run all specs
 *   npx playwright test --headed            # visual mode
 *   npx playwright test --grep "login"      # filter by name
 *
 * Expects:
 *   - Frontend dev server running on http://localhost:5173
 *   - Backend API running on http://localhost:8000
 *   - Test user accounts in Supabase (see conftest.py TEST_USERS)
 */

export default defineConfig({
  testDir: './e2e',
  timeout: 60_000,
  expect: {
    timeout: 10_000,
  },
  fullyParallel: false, // Sequential — tests share auth state
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  workers: 1, // Single worker — avoid auth race conditions

  reporter: [
    ['list'],
    ['html', { open: 'never' }],
  ],

  use: {
    baseURL: process.env.E2E_BASE_URL || 'http://localhost:5173',
    // 390px mobile viewport — Document A requirement
    viewport: { width: 390, height: 844 },
    actionTimeout: 10_000,
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
  },

  projects: [
    {
      name: 'mobile-chromium',
      use: {
        ...devices['Pixel 7'],
        viewport: { width: 390, height: 844 },
      },
    },
  ],

  // Optional: start dev server automatically
  // Uncomment when running locally:
  // webServer: {
  //   command: 'npm run dev',
  //   url: 'http://localhost:5173',
  //   reuseExistingServer: true,
  //   timeout: 30_000,
  // },
})
