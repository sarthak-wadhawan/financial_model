import { test, expect } from '@playwright/test'

test.describe('Stock Page', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/stocks/AAPL')
    await page.waitForLoadState('networkidle')
  })

  test('loads successfully with correct title', async ({ page }) => {
    await expect(page.getByRole('heading', { name: /AAPL/i })).toBeVisible()
    await expect(page.getByText(/NASDAQ/i)).toBeVisible()
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
    await expect(page.getByRole('heading', { name: /Earnings/i })).toBeVisible()
  })

  test('renders company impact and stock impact sections separately', async ({ page }) => {
    await expect(page.getByRole('heading', { name: /Company Impact/i })).toBeVisible()
    await expect(page.getByRole('heading', { name: /Stock Impact/i })).toBeVisible()
  })

  test('renders scenario analysis with Base/Bull/Bear cases', async ({ page }) => {
    await expect(page.getByRole('heading', { name: /Scenario Analysis/i })).toBeVisible()
    await expect(page.getByText(/BASE CASE/i)).toBeVisible()
    await expect(page.getByText(/BULL CASE/i)).toBeVisible()
    await expect(page.getByText(/BEAR CASE/i)).toBeVisible()
  })

  test('renders what would change the view section', async ({ page }) => {
    await expect(page.getByRole('heading', { name: /What Would Change the View/i })).toBeVisible()
  })

  test('renders confidence assessment', async ({ page }) => {
    await expect(page.getByRole('heading', { name: /Confidence Assessment/i })).toBeVisible()
    await expect(page.getByText(/75%/i)).toBeVisible()
  })

  test('renders missing information', async ({ page }) => {
    await expect(page.getByText(/Missing Information:/i)).toBeVisible()
    await expect(page.getByText(/No recent earnings result available/i)).toBeVisible()
  })

  test('renders supporting evidence section', async ({ page }) => {
    await expect(page.getByRole('heading', { name: /Supporting Evidence/i })).toBeVisible()
  })

  test('shows earnings tab when clicked', async ({ page }) => {
    await page.getByRole('tab', { name: 'Earnings' }).click()
    await expect(page.getByRole('heading', { name: /Earnings/i })).toBeVisible()
  })

  test('shows leadership tab with CEO/CFO', async ({ page }) => {
    await page.getByRole('tab', { name: 'Leadership' }).click()
    await expect(page.getByText(/Tim Cook/i)).toBeVisible()
    await expect(page.getByText(/Luca Maestri/i)).toBeVisible()
  })

  test('shows quant tab with signals', async ({ page }) => {
    await page.getByRole('tab', { name: 'Quant' }).click()
    await expect(page.getByRole('heading', { name: /Quant Signals/i })).toBeVisible()
  })
})