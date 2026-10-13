# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: macro-calendar.spec.ts >> Macro Calendar Page >> loads successfully
- Location: src/test/e2e/macro-calendar.spec.ts:9:3

# Error details

```
Error: expect(locator).toBeVisible() failed

Locator: getByRole('heading', { name: /Macro Calendar/i })
Expected: visible
Timeout: 5000ms
Error: element(s) not found

Call log:
  - Expect "toBeVisible" getByRole('heading', { name: /Macro Calendar/i }) with timeout 5000ms
  - waiting for getByRole('heading', { name: /Macro Calendar/i })

```

# Test source

```ts
  1  | import { test, expect } from '@playwright/test'
  2  | 
  3  | test.describe('Macro Calendar Page', () => {
  4  |   test.beforeEach(async ({ page }) => {
  5  |     await page.goto('/macro')
  6  |     await page.waitForLoadState('networkidle')
  7  |   })
  8  | 
  9  |   test('loads successfully', async ({ page }) => {
> 10 |     await expect(page.getByRole('heading', { name: /Macro Calendar/i })).toBeVisible()
     |                                                                          ^ Error: expect(locator).toBeVisible() failed
  11 |     await expect(page.getByText(/Track market-moving economic events/i)).toBeVisible()
  12 |   })
  13 | 
  14 |   test('renders importance filter dropdown', async ({ page }) => {
  15 |     await expect(page.getByLabelText(/Importance/i)).toBeVisible()
  16 |     await expect(page.getByRole('option', { name: /All Importance/i })).toBeVisible()
  17 |     await expect(page.getByRole('option', { name: /CRITICAL/i })).toBeVisible()
  18 |     await expect(page.getByRole('option', { name: /HIGH/i })).toBeVisible()
  19 |     await expect(page.getByRole('option', { name: /MEDIUM/i })).toBeVisible()
  20 |     await expect(page.getByRole('option', { name: /LOW/i })).toBeVisible()
  21 |   })
  22 | 
  23 |   test('renders event type filter dropdown', async ({ page }) => {
  24 |     await expect(page.getByLabelText(/Event Type/i)).toBeVisible()
  25 |     await expect(page.getByRole('option', { name: /All Types/i })).toBeVisible()
  26 |     await expect(page.getByRole('option', { name: /FOMC/i })).toBeVisible()
  27 |     await expect(page.getByRole('option', { name: /CPI/i })).toBeVisible()
  28 |     await expect(page.getByRole('option', { name: /NFP/i })).toBeVisible()
  29 |   })
  30 | 
  31 |   test('renders tab navigation for Upcoming/Recent/All Events', async ({ page }) => {
  32 |     await expect(page.getByRole('tab', { name: /Upcoming/i })).toBeVisible()
  33 |     await expect(page.getByRole('tab', { name: /Recent/i })).toBeVisible()
  34 |     await expect(page.getByRole('tab', { name: /All Events/i })).toBeVisible()
  35 |   })
  36 | 
  37 |   test('renders events table with correct headers', async ({ page }) => {
  38 |     const headers = ['Date', 'Event', 'Type', 'Actual', 'Forecast', 'Previous', 'Importance', 'Status', 'Source']
  39 |     for (const header of headers) {
  40 |       await expect(page.getByRole('columnheader', { name: header })).toBeVisible()
  41 |     }
  42 |   })
  43 | 
  44 |   test('renders legend for importance levels', async ({ page }) => {
  45 |     await expect(page.getByRole('heading', { name: /Importance Levels/i })).toBeVisible()
  46 |     await expect(page.getByText(/Market-moving events/i)).toBeVisible()
  47 |     await expect(page.getByText(/Significant market impact expected/i)).toBeVisible()
  48 |     await expect(page.getByText(/Moderate market impact/i)).toBeVisible()
  49 |     await expect(page.getByText(/Minor market impact/i)).toBeVisible()
  50 |   })
  51 | 
  52 |   test('renders legend for status', async ({ page }) => {
  53 |     await expect(page.getByRole('heading', { name: /Status/i })).toBeVisible()
  54 |     await expect(page.getByText(/RELEASED/i)).toBeVisible()
  55 |     await expect(page.getByText(/SCHEDULED/i)).toBeVisible()
  56 |     await expect(page.getByText(/UPDATED/i)).toBeVisible()
  57 |   })
  58 | 
  59 |   test('filters events by importance', async ({ page }) => {
  60 |     const importanceSelect = page.getByLabelText(/Importance/i)
  61 |     await importanceSelect.selectOption('CRITICAL')
  62 |     await expect(importanceSelect).toHaveValue('CRITICAL')
  63 |   })
  64 | 
  65 |   test('filters events by type', async ({ page }) => {
  66 |     const typeSelect = page.getByLabelText(/Event Type/i)
  67 |     await typeSelect.selectOption('FOMC')
  68 |     await expect(typeSelect).toHaveValue('FOMC')
  69 |   })
  70 | 
  71 |   test('clears filters when clear button clicked', async ({ page }) => {
  72 |     const importanceSelect = page.getByLabelText(/Importance/i)
  73 |     await importanceSelect.selectOption('CRITICAL')
  74 |     await page.getByRole('button', { name: /Clear Filters/i }).click()
  75 |     await expect(importanceSelect).toHaveValue('all')
  76 |   })
  77 | 
  78 |   test('switches between Upcoming, Recent, and All Events tabs', async ({ page }) => {
  79 |     await expect(page.getByRole('tab', { name: /Upcoming/i })).toHaveAttribute('aria-selected', 'true')
  80 |     await page.getByRole('tab', { name: /Recent/i }).click()
  81 |     await expect(page.getByRole('tab', { name: /Recent/i })).toHaveAttribute('aria-selected', 'true')
  82 |     await page.getByRole('tab', { name: /All Events/i }).click()
  83 |     await expect(page.getByRole('tab', { name: /All Events/i })).toHaveAttribute('aria-selected', 'true')
  84 |   })
  85 | })
```