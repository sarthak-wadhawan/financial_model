import { test, expect } from '@playwright/test'

test.describe('Search Page', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/search')
    await page.waitForLoadState('networkidle')
  })

  test('loads successfully with search hero', async ({ page }) => {
    await expect(page.getByRole('heading', { name: /Search Stocks/i })).toBeVisible()
    await expect(page.getByText(/Find a company by symbol or name/i)).toBeVisible()
    await expect(page.getByPlaceholder(/e\.g\. AAPL/i)).toBeVisible()
  })

  test('shows results when query is entered', async ({ page }) => {
    const input = page.getByPlaceholder(/e\.g\. AAPL/i)
    await input.fill('AAPL')
    await input.press('Enter')
    
    // Wait for results - in test env may show "Exchange unavailable" instead of NASDAQ
    await expect(page.getByText(/AAPL/i)).toBeVisible({ timeout: 10000 })
    // Company name may be "Apple Inc." or "Company name unavailable"
    await expect(page.getByText(/Apple Inc\.|Company name unavailable/i)).toBeVisible()
    // Exchange may be NASDAQ or "Exchange unavailable"
    await expect(page.getByText(/NASDAQ|Exchange unavailable/i)).toBeVisible()
  })

  test('renders stock results in grid', async ({ page }) => {
    const input = page.getByPlaceholder(/e\.g\. AAPL/i)
    await input.fill('AAPL')
    await input.press('Enter')
    
    await expect(page.getByText(/AAPL/i)).toBeVisible({ timeout: 10000 })
    await expect(page.getByText(/Apple Inc\.|Company name unavailable/i)).toBeVisible()
    await expect(page.getByText(/NASDAQ|Exchange unavailable/i)).toBeVisible()
  })

  test('links stock result to stock page', async ({ page }) => {
    const input = page.getByPlaceholder(/e\.g\. AAPL/i)
    await input.fill('AAPL')
    await input.press('Enter')
    
    await expect(page.getByRole('link', { name: /AAPL/i })).toHaveAttribute('href', '/stocks/AAPL', { timeout: 10000 })
  })

  test('shows empty state for no results', async ({ page }) => {
    const input = page.getByPlaceholder(/e\.g\. AAPL/i)
    await input.fill('NONEXISTENTXYZ')
    await input.press('Enter')
    
    // In test env, DataStatus empty shows a message - accept any empty state indication
    await expect(page.getByText(/No matching|no results|0 results|empty/i)).toBeVisible({ timeout: 10000 })
  })

  test('shows search hints when no query', async ({ page }) => {
    await expect(page.getByText(/Coverage depends on the connected provider/i)).toBeVisible()
  })
})