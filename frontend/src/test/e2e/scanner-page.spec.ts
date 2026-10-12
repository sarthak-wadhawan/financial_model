import { test, expect } from '@playwright/test'

test.describe('Scanner Page', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/scanner')
    await page.waitForLoadState('networkidle')
  })

  test('loads successfully', async ({ page }) => {
    await expect(page.getByRole('heading', { name: /Quant Scanner/i })).toBeVisible()
    await expect(page.getByText(/Top ranked stocks by deterministic quant signals/i)).toBeVisible()
  })

  test('renders top N selector', async ({ page }) => {
    await expect(page.getByLabelText(/Number of results/i)).toBeVisible()
    await expect(page.getByRole('option', { name: /Top 10/i })).toBeVisible()
    await expect(page.getByRole('option', { name: /Top 20/i })).toBeVisible()
    await expect(page.getByRole('option', { name: /Top 50/i })).toBeVisible()
    await expect(page.getByRole('option', { name: /Top 100/i })).toBeVisible()
  })

  test('renders scanner stats', async ({ page }) => {
    await expect(page.getByText(/Market Status/i)).toBeVisible()
    await expect(page.getByText(/Symbols Tracked/i)).toBeVisible()
    await expect(page.getByText(/As of/i)).toBeVisible()
  })

  test('renders scanner table with correct headers', async ({ page }) => {
    const headers = ['Rank', 'Symbol', 'Score', 'Momentum', 'Trend', 'Liquidity', 'Volume', 'Vol Quality']
    for (const header of headers) {
      await expect(page.getByRole('columnheader', { name: header })).toBeVisible()
    }
  })

  test('renders candidate rows when data loads', async ({ page }) => {
    await expect(page.getByText(/AAPL/i)).toBeVisible()
    await expect(page.getByText(/85/i)).toBeVisible()
    await expect(page.getByText(/#1/i)).toBeVisible()
  })

  test('updates top N when selector changes', async ({ page }) => {
    const select = page.getByLabelText(/Number of results/i)
    await select.selectOption('50')
    await expect(select).toHaveValue('50')
  })

  test('links symbol to stock page', async ({ page }) => {
    const link = page.getByRole('link', { name: /AAPL/i })
    await expect(link).toHaveAttribute('href', '/stocks/AAPL')
  })
})