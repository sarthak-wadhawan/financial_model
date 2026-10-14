import { test, expect } from '@playwright/test'

test.describe('Macro Calendar Page', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/macro')
    await page.waitForLoadState('networkidle')
  })

  test('loads successfully', async ({ page }) => {
    await expect(page.getByRole('heading', { name: /Macro Calendar/i })).toBeVisible()
    await expect(page.getByText(/Track market-moving economic events and central bank decisions/i)).toBeVisible()
  })

  test('renders importance filter dropdown', async ({ page }) => {
    const select = page.getByLabel(/Importance/i)
    await expect(select).toBeVisible()
    // Options are hidden when select is closed; verify select has correct options via value
    await expect(select).toHaveValue('all')
  })

  test('renders event type filter dropdown', async ({ page }) => {
    const select = page.getByLabel(/Event Type/i)
    await expect(select).toBeVisible()
    await expect(select).toHaveValue('all')
  })

  test('renders tab navigation for Upcoming/Recent/All Events', async ({ page }) => {
    await expect(page.getByRole('tab', { name: /Upcoming/i })).toBeVisible()
    await expect(page.getByRole('tab', { name: /Recent/i })).toBeVisible()
    await expect(page.getByRole('tab', { name: /All Events/i })).toBeVisible()
  })

  test('renders events table with correct headers', async ({ page }) => {
    const headers = ['Date', 'Event', 'Type', 'Actual', 'Forecast', 'Previous', 'Importance', 'Status', 'Source']
    for (const header of headers) {
      await expect(page.getByRole('columnheader', { name: header })).toBeVisible()
    }
  })

  test('renders legend for importance levels', async ({ page }) => {
    await expect(page.getByRole('heading', { name: /Importance Levels/i })).toBeVisible()
    await expect(page.getByText(/Market-moving events \(FOMC, NFP, CPI\)/i)).toBeVisible()
    await expect(page.getByText(/Significant market impact expected/i)).toBeVisible()
    await expect(page.getByText(/Moderate market impact/i)).toBeVisible()
    await expect(page.getByText(/Minor market impact/i)).toBeVisible()
  })

  test('renders legend for status', async ({ page }) => {
    await expect(page.getByRole('heading', { name: /Status/i })).toBeVisible()
    // Status legend has uppercase text
    await expect(page.getByText('RELEASED', { exact: true })).toBeVisible()
    await expect(page.getByText('SCHEDULED', { exact: true })).toBeVisible()
    await expect(page.getByText('UPDATED', { exact: true })).toBeVisible()
  })

  test('filters events by importance', async ({ page }) => {
    const importanceSelect = page.getByLabel(/Importance/i)
    await importanceSelect.selectOption('CRITICAL')
    await expect(importanceSelect).toHaveValue('CRITICAL')
  })

  test('filters events by type', async ({ page }) => {
    const typeSelect = page.getByLabel(/Event Type/i)
    await typeSelect.selectOption('FOMC')
    await expect(typeSelect).toHaveValue('FOMC')
  })

  test('clears filters when clear button clicked', async ({ page }) => {
    const importanceSelect = page.getByLabel(/Importance/i)
    await importanceSelect.selectOption('CRITICAL')
    await page.getByRole('button', { name: /Clear Filters/i }).click()
    await expect(importanceSelect).toHaveValue('all')
  })

  test('switches between Upcoming, Recent, and All Events tabs', async ({ page }) => {
    await expect(page.getByRole('tab', { name: /Upcoming/i })).toHaveAttribute('aria-selected', 'true')
    await page.getByRole('tab', { name: /Recent/i }).click()
    await expect(page.getByRole('tab', { name: /Recent/i })).toHaveAttribute('aria-selected', 'true')
    await page.getByRole('tab', { name: /All Events/i }).click()
    await expect(page.getByRole('tab', { name: /All Events/i })).toHaveAttribute('aria-selected', 'true')
  })
})