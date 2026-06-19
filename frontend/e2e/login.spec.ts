/**
 * Bower Ag CowCare Tool — E2E: Login Tests
 * Sprint 15: 3 tests covering login flow at 390px mobile viewport.
 *
 * Tests:
 *   1. Rep (consultant) login → redirects to / (dashboard)
 *   2. Customer login → redirects to /my-reports
 *   3. Wrong password → shows error banner
 */

import { test, expect } from '@playwright/test'

// Test credentials (must match Supabase test users)
const REP_EMAIL = process.env.E2E_REP_EMAIL || 'consultant@bowerag.test'
const REP_PASSWORD = process.env.E2E_REP_PASSWORD || 'TestConsult123!'
const CUSTOMER_EMAIL = process.env.E2E_CUSTOMER_EMAIL || 'customer@bowerag.test'
const CUSTOMER_PASSWORD = process.env.E2E_CUSTOMER_PASSWORD || 'TestCustomer123!'

test.describe('Login Flow', () => {
  test.beforeEach(async ({ page }) => {
    // Clear any existing auth state
    await page.goto('/login')
    await page.evaluate(() => localStorage.clear())
    await page.reload()
    await page.waitForURL('**/login')
  })

  test('E2E-L1: Rep login redirects to dashboard', async ({ page }) => {
    // Verify login page renders
    await expect(page.locator('h1')).toContainText('CowCare Tool')
    await expect(page.locator('button[type="submit"]')).toContainText('Sign In')

    // Fill credentials
    await page.fill('#email', REP_EMAIL)
    await page.fill('#password', REP_PASSWORD)

    // Click Sign In
    await page.click('button[type="submit"]')

    // Should redirect to dashboard (/) or /chat
    await page.waitForURL((url) => {
      const path = url.pathname
      return path === '/' || path === '/chat'
    }, { timeout: 15_000 })

    // Verify we're NOT on the login page anymore
    await expect(page).not.toHaveURL(/\/login/)
  })

  test('E2E-L2: Customer login redirects to /my-reports', async ({ page }) => {
    await page.fill('#email', CUSTOMER_EMAIL)
    await page.fill('#password', CUSTOMER_PASSWORD)
    await page.click('button[type="submit"]')

    // Customer should redirect to /my-reports
    await page.waitForURL('**/my-reports', { timeout: 15_000 })
    await expect(page).toHaveURL(/\/my-reports/)
  })

  test('E2E-L3: Wrong password shows error', async ({ page }) => {
    await page.fill('#email', REP_EMAIL)
    await page.fill('#password', 'WrongPassword999!')
    await page.click('button[type="submit"]')

    // Error banner should appear
    await expect(page.locator('[class*="text-danger"], [class*="bg-red"]')).toBeVisible({
      timeout: 10_000,
    })

    // Should still be on login page
    await expect(page).toHaveURL(/\/login/)
  })
})
