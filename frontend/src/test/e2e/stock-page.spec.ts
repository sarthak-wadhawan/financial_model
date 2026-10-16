import { test, expect } from '@playwright/test'

test.describe('Stock Page', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/stocks/AAPL')
    await page.waitForLoadState('networkidle')
  })

  test('loads successfully with correct title', async ({ page }) => {
    const response = await page.request.get('/api/v1/stocks/AAPL')
    expect(response.ok()).toBeTruthy()
    const detail = await response.json()
    expect(detail.symbol).toBe('AAPL')
    expect(detail.name).toEqual(expect.any(String))
    expect(detail.name.length).toBeGreaterThan(0)
    await expect(page.getByRole('heading', { level: 1, name: detail.name, exact: true })).toBeVisible()
    await expect(page.locator('.stock-exchange')).toContainText(detail.symbol)
    // In test env, exchange may be "Exchange unavailable"
    await expect(page.getByText(/NASDAQ|Exchange unavailable/i)).toBeVisible()
  })

  test('renders all tab navigation buttons', async ({ page }) => {
    const tabs = ['Overview', 'Earnings', 'Events', 'News', 'Insiders', 'Leadership', 'Filings', 'Quant']
    for (const tab of tabs) {
      await expect(page.getByRole('tab', { name: tab })).toBeVisible()
    }
  })

  test('shows overview tab by default', async ({ page }) => {
    await expect(page.getByRole('tab', { name: 'Overview' })).toHaveAttribute('aria-selected', 'true')
    await expect(page.getByRole('heading', { name: /What You Need to Know/i })).toBeVisible()
  })

  test('switches tabs when clicked', async ({ page }) => {
    await page.getByRole('tab', { name: 'Earnings' }).click()
    await expect(page.getByRole('tab', { name: 'Earnings' })).toHaveAttribute('aria-selected', 'true')
    await expect(page.getByRole('heading', { name: /Earnings evidence/i })).toBeVisible()
  })

  test('renders company impact and stock impact sections separately', async ({ page }) => {
    await expect(page.getByRole('heading', { name: /Company Impact/i })).toBeVisible()
    await expect(page.getByRole('heading', { name: 'Stock Impact', exact: true })).toBeVisible()
  })

  test('renders scenario analysis with Base/Bull/Bear cases', async ({ page }) => {
    await expect(page.getByRole('heading', { name: /Scenario Analysis/i })).toBeVisible()
    await expect(page.getByRole('heading', { name: 'BASE CASE', exact: true })).toBeVisible()
    await expect(page.getByRole('heading', { name: 'BULL CASE', exact: true })).toBeVisible()
    await expect(page.getByRole('heading', { name: 'BEAR CASE', exact: true })).toBeVisible()
  })

  test('renders what would change the view section', async ({ page }) => {
    await expect(page.getByRole('heading', { name: /What Would Change the View/i })).toBeVisible()
  })

  test('renders confidence & missing information section', async ({ page }) => {
    // This is a details/summary element
    await expect(page.getByText(/Confidence & missing information/i)).toBeVisible()
  })

  test('renders missing information', async ({ page }) => {
    await expect(page.getByRole('heading', { name: /Missing Information/i })).toBeVisible()
  })

  test('renders supporting evidence section', async ({ page }) => {
    await expect(page.getByText(/Supporting Evidence/i)).toBeVisible()
  })

  test('shows earnings tab when clicked', async ({ page }) => {
    await page.getByRole('tab', { name: 'Earnings' }).click()
    await expect(page.getByRole('heading', { name: /Earnings evidence/i })).toBeVisible()
  })

  test('shows leadership tab', async ({ page }) => {
    await page.getByRole('tab', { name: 'Leadership' }).click()
    await expect(page.getByRole('heading', { name: /Evidence-derived leadership/i })).toBeVisible()
  })

  test('shows quant tab with signals', async ({ page }) => {
    await page.getByRole('tab', { name: 'Quant' }).click()
    await expect(page.getByRole('heading', { name: /Quant Signals/i })).toBeVisible()
  })
})
