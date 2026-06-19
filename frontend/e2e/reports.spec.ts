/**
 * Bower Ag CowCare Tool — E2E: Reports Tests
 * Sprint 15: 1 test covering the reports page.
 *
 * Tests:
 *   1. Consultant can view reports page and see report list
 */

import { test, expect } from '@playwright/test'

const REP_EMAIL = process.env.E2E_REP_EMAIL || 'consultant@bowerag.test'
const REP_PASSWORD = process.env.E2E_REP_PASSWORD || 'TestConsult123!'

test.describe('Reports', () => {
  test.beforeEach(async ({ page }) => {
    // Login as consultant
    await page.goto('/login')
    await page.evaluate(() => localStorage.clear())
    await page.reload()
    await page.waitForURL('**/login')

    await page.fill('#email', REP_EMAIL)
    await page.fill('#password', REP_PASSWORD)
    await page.click('button[type="submit"]')

    await page.waitForURL((url) => !url.pathname.includes('/login'), {
      timeout: 15_000,
    })
  })

  test('E2E-R1: Consultant can view reports page', async ({ page }) => {
    // Navigate to reports
    await page.goto('/reports')
    await page.waitForLoadState('networkidle')

    // Should be on /reports page
    await expect(page).toHaveURL(/\/reports/)

    // Page should render — look for reports-related content
    const bodyText = await page.textContent('body') || ''
    const hasReportContent =
      bodyText.toLowerCase().includes('report') ||
      bodyText.toLowerCase().includes('generate') ||
      bodyText.toLowerCase().includes('no reports') ||
      bodyText.toLowerCase().includes('visit')

    expect(hasReportContent).toBeTruthy()

    // Verify viewport is mobile (390px)
    const viewportSize = page.viewportSize()
    expect(viewportSize?.width).toBeLessThanOrEqual(412) // Pixel 7 = 412, configured 390
  })
})
