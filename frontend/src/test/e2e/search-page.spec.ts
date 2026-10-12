import { test, expect } from '@playwright/test'

test.describe('Search Page', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/search')
    await page.waitForLoadState('networkidle')
  })

  test('loads successfully with search hero', async ({ page }) => {
    await expect(page.getByRole('heading', { name: /Search/i })).toBeVisible()
    await expect(page.getByText(/Find stocks, news, events, and filings/i)).toBeVisible()
    await expect(page.getByPlaceholderText(/Search stocks, news, events, filings/i)).toBeVisible()
  })

  test('renders search hints', async ({ page }) => {
    await expect(page.getByText(/Try: "AAPL", "earnings", "FOMC", "Form 4"/i)).toBeVisible()
  })

  test('shows results when query is entered', async ({ page }) => {
    const input = page.getByPlaceholderText(/Search stocks, news, events, filings/i)
    await input.fill('AAPL')
    await input.press('Enter')
    
    // Wait for results
    await expect(page.getByRole('tab', { name: /All/i })).toBeVisible({ timeout: 10000 })
    await expect(page.getByRole('tab', { name: /Stocks/i })).toBeVisible()
    await expect(page.getByRole('tab', { name: /News/i })).toBeVisible()
    await expect(page.getByRole('tab', { name: /Events/i })).toBeVisible()
    await expect(page.getByRole('tab', { name: /Filings/i })).toBeVisible()
  })

  test('renders stock results in grid', async ({ page }) => {
    const input = page.getByPlaceholderText(/Search stocks, news, events, filings/i)
    await input.fill('AAPL')
    await input.press('Enter')
    
    await expect(page.getByText(/AAPL/i)).toBeVisible({ timeout: 10000 })
    await expect(page.getByText(/Apple Inc./i)).toBeVisible()
    await expect(page.getByText(/NASDAQ/i)).toBeVisible()
  })

  test('switches between search result tabs', async ({ page }) => {
    const input = page.getByPlaceholderText(/Search stocks, news, events, filings/i)
    await input.fill('AAPL')
    await input.press('Enter')
    
    await expect(page.getByRole('tab', { name: /All/i })).toHaveAttribute('aria-selected', 'true')
    
    await page.getByRole('tab', { name: /Stocks/i }).click()
    await expect(page.getByRole('tab', { name: /Stocks/i })).toHaveAttribute('aria-selected', 'true')
    
    await page.getByRole('tab', { name: /News/i }).click()
    await expect(page.getByRole('tab', { name: /News/i })).toHaveAttribute('aria-selected', 'true')
  })

  test('links stock result to stock page', async ({ page }) => {
    const input = page.getByPlaceholderText(/Search stocks, news, events, filings/i)
    await input.fill('AAPL')
    await input.press('Enter')
    
    await expect(page.getByRole('link', { name: /AAPL/i })).toHaveAttribute('href', '/stocks/AAPL', { timeout: 10000 })
  })

  test('shows news search not implemented message', async ({ page }) => {
    const input = page.getByPlaceholderText(/Search stocks, news, events, filings/i)
    await input.fill('AAPL')
    await input.press('Enter')
    
    await page.getByRole('tab', { name: /News/i }).click()
    await expect(page.getByText(/News search not yet implemented/i)).toBeVisible({ timeout: 10000 })
  })

  test('shows events search not implemented message', async ({ page }) => {
    const input = page.getByPlaceholderText(/Search stocks, news, events, filings/i)
    await input.fill('AAPL')
    await input.press('Enter')
    
    await page.getByRole('tab', { name: /Events/i }).click()
    await expect(page.getByText(/Events search not yet implemented/i)).toBeVisible({ timeout: 10000 })
  })

  test('shows filings search not implemented message', async ({ page }) => {
    const input = page.getByPlaceholderText(/Search stocks, news, events, filings/i)
    await input.fill('AAPL')
    await input.press('Enter')
    
    await page.getByRole('tab', { name: /Filings/i }).click()
    await expect(page.getByText(/Filings search not yet implemented/i)).toBeVisible({ timeout: 10000 })
  })
})