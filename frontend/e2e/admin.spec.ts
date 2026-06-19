/**
 * Bower Ag CowCare Tool — E2E: Admin Tests
 * Sprint 15: 2 tests covering admin access control at 390px.
 *
 * Tests:
 *   1. Consultant blocked from admin panel → 403 / redirect
 *   2. Admin manager can see analytics dashboard
 */

import { test, expect } from '@playwright/test'

const CONSULTANT_EMAIL = process.env.E2E_REP_EMAIL || 'consultant@bowerag.test'
const CONSULTANT_PASSWORD = process.env.E2E_REP_PASSWORD || 'TestConsult123!'
const ADMIN_EMAIL = process.env.E2E_ADMIN_EMAIL || 'manager@bowerag.test'
const ADMIN_PASSWORD = process.env.E2E_ADMIN_PASSWORD || 'TestManager123!'

/**
 * Helper: Login with given credentials and wait for redirect.
 */
async function loginAs(page: any, email: string, password: string) {
  await page.goto('/login')
  await page.evaluate(() => localStorage.clear())
  await page.reload()
  await page.waitForURL('**/login')

  await page.fill('#email', email)
  await page.fill('#password', password)
  await page.click('button[type="submit"]')

  await page.waitForURL((url: URL) => !url.pathname.includes('/login'), {
    timeout: 15_000,
  })
}

test.describe('Admin Access Control', () => {
  test('E2E-A1: Consultant cannot access admin panel', async ({ page }) => {
    await loginAs(page, CONSULTANT_EMAIL, CONSULTANT_PASSWORD)

    // Try to navigate directly to admin dashboard
    await page.goto('/admin')
    await page.waitForLoadState('networkidle')

    // Should either:
    //   a) Show 403/Access Denied message
    //   b) Redirect away from /admin
    //   c) Show empty/error state
    const currentUrl = page.url()
    const bodyText = await page.textContent('body') || ''

    const blocked =
      !currentUrl.includes('/admin') ||
      bodyText.toLowerCase().includes('access denied') ||
      bodyText.toLowerCase().includes('forbidden') ||
      bodyText.toLowerCase().includes('permission') ||
      bodyText.includes('403')

    expect(blocked).toBeTruthy()
  })

  test('E2E-A2: Admin manager can view analytics', async ({ page }) => {
    await loginAs(page, ADMIN_EMAIL, ADMIN_PASSWORD)

    // Navigate to admin dashboard
    await page.goto('/admin')
    await page.waitForLoadState('networkidle')

    // Should see admin content — look for analytics keywords or admin heading
    const bodyText = await page.textContent('body') || ''
    const isAdmin =
      bodyText.toLowerCase().includes('admin') ||
      bodyText.toLowerCase().includes('analytics') ||
      bodyText.toLowerCase().includes('dashboard') ||
      bodyText.toLowerCase().includes('users') ||
      bodyText.toLowerCase().includes('summary')

    expect(isAdmin).toBeTruthy()

    // Verify the page is actually /admin (not redirected)
    await expect(page).toHaveURL(/\/admin/)
  })
})
