import { test, expect } from '@playwright/test'

test.describe('Landing Page', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/')
    await page.waitForLoadState('networkidle')
  })

  test('loads successfully', async ({ page }) => {
    await expect(page).toHaveTitle(/Trading Copilot/)
  })

  test('renders hero section', async ({ page }) => {
    await expect(page.getByRole('heading', { name: /Your research dashboard/i })).toBeVisible()
    await expect(page.getByText(/What matters, why it matters, and the evidence behind it/i)).toBeVisible()
  })

  test('renders primary CTA buttons', async ({ page }) => {
    await expect(page.getByRole('link', { name: /Explore scanner/i })).toBeVisible()
    await expect(page.getByRole('link', { name: 'Search a company', exact: true })).toBeVisible()
  })

  test('navigates to scanner page', async ({ page }) => {
    await page.getByRole('link', { name: /Explore scanner/i }).click()
    await expect(page).toHaveURL(/.*\/scanner/)
    await expect(page.getByRole('heading', { name: /Quant Scanner/i })).toBeVisible()
  })

  test('navigates to search page', async ({ page }) => {
    await page.getByRole('link', { name: 'Search a company', exact: true }).click()
    await expect(page).toHaveURL(/.*\/search/)
    await expect(page.getByRole('heading', { name: /Search Stocks/i })).toBeVisible()
  })

  test('renders market snapshot section', async ({ page }) => {
    await expect(page.getByRole('heading', { name: /Market snapshot/i })).toBeVisible()
  })

  test('renders macro releases & upcoming events section', async ({ page }) => {
    await expect(page.getByRole('heading', { name: /Macro: releases & upcoming events/i })).toBeVisible()
  })

  test('renders top scanner candidates section', async ({ page }) => {
    await expect(page.getByRole('heading', { name: /Top scanner candidates/i })).toBeVisible()
  })

  test('renders recent company events section', async ({ page }) => {
    await expect(page.getByRole('heading', { name: /Recent company events/i })).toBeVisible()
  })

  test('renders watchlists section', async ({ page }) => {
    await expect(page.getByRole('heading', { name: /Your watchlists/i })).toBeVisible()
  })

  test('renders bottom CTA section with search link', async ({ page }) => {
    await expect(page.getByRole('link', { name: /Research a company/i })).toBeVisible()
  })
})