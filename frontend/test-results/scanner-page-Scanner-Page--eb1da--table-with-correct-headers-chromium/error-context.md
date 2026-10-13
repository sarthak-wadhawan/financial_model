# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: scanner-page.spec.ts >> Scanner Page >> renders scanner table with correct headers
- Location: src/test/e2e/scanner-page.spec.ts:28:3

# Error details

```
Error: expect(locator).toBeVisible() failed

Locator: getByRole('columnheader', { name: 'Rank' })
Expected: visible
Timeout: 5000ms
Error: element(s) not found

Call log:
  - Expect "toBeVisible" getByRole('columnheader', { name: 'Rank' }) with timeout 5000ms
  - waiting for getByRole('columnheader', { name: 'Rank' })

```

```yaml
- banner:
  - banner:
    - link "Trading Copilot Home":
      - /url: /
      - text: Trading Copilot
    - navigation "Main navigation":
      - link "Dashboard":
        - /url: /
      - link "Scanner":
        - /url: /scanner
      - link "Macro Calendar":
        - /url: /macro
      - link "Search":
        - /url: /search
    - group "Theme selection":
      - button "Light theme"
      - button "Dark theme"
      - button "System theme" [pressed]
- main:
  - complementary:
    - complementary "Sidebar navigation":
      - text: Trading Copilot
      - button "Collapse sidebar" [expanded]
      - navigation "Main navigation":
        - list:
          - listitem:
            - link "Dashboard":
              - /url: /
          - listitem:
            - link "Scanner":
              - /url: /scanner
          - listitem:
            - link "Macro Calendar":
              - /url: /macro
          - listitem:
            - link "Search":
              - /url: /search
          - listitem:
            - link "Settings":
              - /url: /settings
      - text: ResearcherFree
  - main:
    - heading "Quant Scanner" [level=1]
    - paragraph: Top ranked stocks by deterministic quant signals
    - combobox "Number of results":
      - option "Top 10"
      - option "Top 20" [selected]
      - option "Top 50"
      - option "Top 100"
    - text: Market Status— Symbols Tracked0 As of— 🔍
    - heading "No candidates found" [level=3]
    - paragraph: Try adjusting your scanner parameters or check back later.
- contentinfo:
  - contentinfo:
    - heading "Product" [level=4]
    - navigation "Product links":
      - list:
        - listitem:
          - link "Scanner":
            - /url: /scanner
        - listitem:
          - link "Macro Calendar":
            - /url: /macro
        - listitem:
          - link "Search":
            - /url: /search
        - listitem:
          - link "Settings":
            - /url: /settings
    - heading "Data Sources" [level=4]
    - navigation "Data sources":
      - list:
        - listitem:
          - link "SEC EDGAR":
            - /url: https://www.sec.gov/edgar
        - listitem:
          - link "BLS":
            - /url: https://www.bls.gov
        - listitem:
          - link "Federal Reserve":
            - /url: https://www.federalreserve.gov
        - listitem:
          - link "BEA":
            - /url: https://www.bea.gov
        - listitem:
          - link "Census Bureau":
            - /url: https://www.census.gov
        - listitem:
          - link "Alpaca Markets":
            - /url: https://alpaca.markets
    - heading "Legal" [level=4]
    - navigation "Legal links":
      - list:
        - listitem:
          - link "Privacy Policy":
            - /url: /privacy
        - listitem:
          - link "Terms of Service":
            - /url: /terms
        - listitem:
          - link "Disclaimer":
            - /url: /disclaimer
    - heading "Resources" [level=4]
    - navigation "Resources":
      - list:
        - listitem:
          - link "Documentation":
            - /url: /docs
        - listitem:
          - link "API Docs":
            - /url: /api/docs
        - listitem:
          - link "GitHub":
            - /url: /github
        - listitem:
          - link "Changelog":
            - /url: /changelog
    - paragraph: Trading Copilot - Deterministic Financial Intelligence. Not financial advice.
    - paragraph: Data provided by SEC EDGAR, BLS, Federal Reserve, BEA, Census, Alpaca Markets.
```

# Test source

```ts
  1  | import { test, expect } from '@playwright/test'
  2  | 
  3  | test.describe('Scanner Page', () => {
  4  |   test.beforeEach(async ({ page }) => {
  5  |     await page.goto('/scanner')
  6  |     await page.waitForLoadState('networkidle')
  7  |   })
  8  | 
  9  |   test('loads successfully', async ({ page }) => {
  10 |     await expect(page.getByRole('heading', { name: /Quant Scanner/i })).toBeVisible()
  11 |     await expect(page.getByText(/Top ranked stocks by deterministic quant signals/i)).toBeVisible()
  12 |   })
  13 | 
  14 |   test('renders top N selector', async ({ page }) => {
  15 |     await expect(page.getByLabelText(/Number of results/i)).toBeVisible()
  16 |     await expect(page.getByRole('option', { name: /Top 10/i })).toBeVisible()
  17 |     await expect(page.getByRole('option', { name: /Top 20/i })).toBeVisible()
  18 |     await expect(page.getByRole('option', { name: /Top 50/i })).toBeVisible()
  19 |     await expect(page.getByRole('option', { name: /Top 100/i })).toBeVisible()
  20 |   })
  21 | 
  22 |   test('renders scanner stats', async ({ page }) => {
  23 |     await expect(page.getByText(/Market Status/i)).toBeVisible()
  24 |     await expect(page.getByText(/Symbols Tracked/i)).toBeVisible()
  25 |     await expect(page.getByText(/As of/i)).toBeVisible()
  26 |   })
  27 | 
  28 |   test('renders scanner table with correct headers', async ({ page }) => {
  29 |     const headers = ['Rank', 'Symbol', 'Score', 'Momentum', 'Trend', 'Liquidity', 'Volume', 'Vol Quality']
  30 |     for (const header of headers) {
> 31 |       await expect(page.getByRole('columnheader', { name: header })).toBeVisible()
     |                                                                      ^ Error: expect(locator).toBeVisible() failed
  32 |     }
  33 |   })
  34 | 
  35 |   test('renders candidate rows when data loads', async ({ page }) => {
  36 |     await expect(page.getByText(/AAPL/i)).toBeVisible()
  37 |     await expect(page.getByText(/85/i)).toBeVisible()
  38 |     await expect(page.getByText(/#1/i)).toBeVisible()
  39 |   })
  40 | 
  41 |   test('updates top N when selector changes', async ({ page }) => {
  42 |     const select = page.getByLabelText(/Number of results/i)
  43 |     await select.selectOption('50')
  44 |     await expect(select).toHaveValue('50')
  45 |   })
  46 | 
  47 |   test('links symbol to stock page', async ({ page }) => {
  48 |     const link = page.getByRole('link', { name: /AAPL/i })
  49 |     await expect(link).toHaveAttribute('href', '/stocks/AAPL')
  50 |   })
  51 | })
```