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
    await expect(page.getByRole('heading', { name: /Trading Copilot/i })).toBeVisible()
    await expect(page.getByText(/Deterministic financial intelligence/i)).toBeVisible()
  })

  test('renders primary CTA buttons', async ({ page }) => {
    await expect(page.getByRole('link', { name: /Launch Scanner/i })).toBeVisible()
    await expect(page.getByRole('link', { name: /Search Stocks/i })).toBeVisible()
  })

  test('navigates to scanner page', async ({ page }) => {
    await page.getByRole('link', { name: /Launch Scanner/i }).click()
    await expect(page).toHaveURL(/.*\/scanner/)
    await expect(page.getByRole('heading', { name: /Quant Scanner/i })).toBeVisible()
  })

  test('navigates to search page', async ({ page }) => {
    await page.getByRole('link', { name: /Search Stocks/i }).click()
    await expect(page).toHaveURL(/.*\/search/)
    await expect(page.getByRole('heading', { name: /Search/i })).toBeVisible()
  })

  test('renders market overview section', async ({ page }) => {
    await expect(page.getByRole('heading', { name: /Market Overview/i })).toBeVisible()
  })

  test('renders upcoming macro events section', async ({ page }) => {
    await expect(page.getByRole('heading', { name: /Upcoming Macro Events/i })).toBeVisible()
  })

  test('renders top scanner candidates section', async ({ page }) => {
    await expect(page.getByRole('heading', { name: /Top Scanner Candidates/i })).toBeVisible()
  })

  test('renders recent company events section', async ({ page }) => {
    await expect(page.getByRole('heading', { name: /Recent Company Events/i })).toBeVisible()
  })

  test('renders features section', async ({ page }) => {
    await expect(page.getByRole('heading', { name: /Why Trading Copilot/i })).toBeVisible()
    await expect(page.getByText(/Deterministic Intelligence/i)).toBeVisible()
    await expect(page.getByText(/Evidence-First/i)).toBeVisible()
    await expect(page.getByText(/Company ≠ Stock Impact/i)).toBeVisible()
    await expect(page.getByText(/Scenario Analysis/i)).toBeVisible()
    await expect(page.getByText(/Term Definitions/i)).toBeVisible()
    await expect(page.getByText(/Zero-LLM Core/i)).toBeVisible()
  })

  test('renders bottom CTA section', async ({ page }) => {
    await expect(page.getByRole('heading', { name: /Start Your Research/i })).toBeVisible()
    await expect(page.getByRole('link', { name: /Start Researching/i })).toBeVisible()
  })
})