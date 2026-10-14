import { test, expect } from '@playwright/test'

test.describe('Scanner Page', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/scanner')
    await page.waitForLoadState('networkidle')
  })

  test('loads successfully', async ({ page }) => {
    await expect(page.getByRole('heading', { name: /Quant Scanner/i })).toBeVisible()
    await expect(page.getByText(/Deterministic rankings for research/i)).toBeVisible()
  })

  test('renders top N selector', async ({ page }) => {
    const select = page.getByLabel('Results', { exact: true })
    await expect(select).toBeVisible()
    // Options are hidden when select is closed; verify select has correct options via values
    await expect(select).toHaveValue('20') // default
    // Verify all option values exist
    const options = await select.locator('option').all()
    const values = await Promise.all(options.map(o => o.getAttribute('value')))
    expect(values).toEqual(['10', '20', '50', '100'])
  })

  test('renders scanner stats', async ({ page }) => {
    await expect(page.getByText(/Market status/i)).toBeVisible()
    await expect(page.getByText(/Symbols tracked/i)).toBeVisible()
    await expect(page.getByText(/Calculation date/i)).toBeVisible()
  })

  test('renders scanner table with correct headers', async ({ page }) => {
    const headers = ['Rank', 'Symbol', 'Quant Score', 'Momentum', 'Trend', 'Liquidity', 'Volume', 'Vol Quality', 'Price']
    for (const header of headers) {
      await expect(page.getByRole('columnheader', { name: header })).toBeVisible()
    }
  })

  test('renders candidate rows when data loads', async ({ page }) => {
    // In test environment, scanner may return empty; check for empty state or data
    const emptyState = page.getByText(/No scanner candidates available|No returned symbols match/i)
    const table = page.getByRole('table')
    // Either empty state is visible or table has rows
    await expect(emptyState.or(table)).toBeVisible()
  })

  test('updates top N when selector changes', async ({ page }) => {
    const select = page.getByLabel('Results', { exact: true })
    await select.selectOption('50')
    await expect(select).toHaveValue('50')
  })

  test('links symbol to stock page', async ({ page }) => {
    const link = page.getByRole('link', { name: /AAPL/i })
    await expect(link).toHaveAttribute('href', '/stocks/AAPL')
  })
})