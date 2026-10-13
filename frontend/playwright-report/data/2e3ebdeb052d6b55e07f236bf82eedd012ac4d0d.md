# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: stock-page.spec.ts >> Stock Page >> renders confidence assessment
- Location: src/test/e2e/stock-page.spec.ts:48:3

# Error details

```
Error: expect(locator).toBeVisible() failed

Locator: getByText(/75%/i)
Expected: visible
Timeout: 5000ms
Error: element(s) not found

Call log:
  - Expect "toBeVisible" getByText(/75%/i) with timeout 5000ms
  - waiting for getByText(/75%/i)

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
    - heading "AAPL" [level=1]
    - text: NASDAQ $--
    - tablist "Stock sections":
      - tab "Overview" [selected]
      - tab "Earnings"
      - tab "Events"
      - tab "News"
      - tab "Insiders"
      - tab "Leadership"
      - tab "Filings"
      - tab "Quant"
    - main:
      - heading "What You Need to Know" [level=2]
      - text: "HeadlineAAPL: Market update What HappenedNo material new events in period What It MeansFundamental business stable Why It MattersNo material catalyst in current period; monitoring for next catalyst"
      - heading "Company Impact" [level=3]
      - text: unknown(unknown)
      - paragraph: "Horizon: medium_term"
      - paragraph: "Confidence: 30%"
      - heading "Stock Impact" [level=3]
      - text: neutral(low)
      - paragraph: "Horizon: short_term"
      - paragraph: "Confidence: 30%"
      - heading "Scenario Analysis" [level=2]
      - text: BASE CASE40-60%
      - paragraph: Current trajectory continues; valuation reflects current expectations
      - strong: "Required conditions:"
      - list:
        - listitem: Current trajectory continues absent new catalysts
      - text: BULL CASE20-30%
      - paragraph: Positive fundamentals and supportive macro drive multiple expansion
      - strong: "Required conditions:"
      - list:
        - listitem: Earnings momentum sustains
      - text: BEAR CASE15-25%
      - paragraph: Fundamental deterioration or macro headwinds compress multiple
      - strong: "Required conditions:"
      - list:
        - listitem: Guidance cut or negative macro surprise
      - heading "What Would Change the View?" [level=2]
      - heading "Confidence Assessment" [level=2]
      - text: 30% Based on deterministic evidence synthesis
      - heading "Missing Information:" [level=4]
      - list:
        - listitem: No recent earnings result available
        - listitem: No consensus EPS estimate for comparison
        - listitem: No forward guidance available
        - listitem: No recent CPI surprise for macro context
        - listitem: No recent management statements
        - listitem: No recent news evidence
      - heading "Supporting Evidence" [level=2]
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
  3  | test.describe('Stock Page', () => {
  4  |   test.beforeEach(async ({ page }) => {
  5  |     await page.goto('/stocks/AAPL')
  6  |     await page.waitForLoadState('networkidle')
  7  |   })
  8  | 
  9  |   test('loads successfully with correct title', async ({ page }) => {
  10 |     await expect(page.getByRole('heading', { name: /AAPL/i })).toBeVisible()
  11 |     await expect(page.getByText(/NASDAQ/i)).toBeVisible()
  12 |   })
  13 | 
  14 |   test('renders all tab navigation buttons', async ({ page }) => {
  15 |     const tabs = ['Overview', 'Earnings', 'Events', 'News', 'Insiders', 'Leadership', 'Filings', 'Quant']
  16 |     for (const tab of tabs) {
  17 |       await expect(page.getByRole('tab', { name: tab })).toBeVisible()
  18 |     }
  19 |   })
  20 | 
  21 |   test('shows overview tab by default', async ({ page }) => {
  22 |     await expect(page.getByRole('tab', { name: 'Overview' })).toHaveAttribute('aria-selected', 'true')
  23 |     await expect(page.getByRole('heading', { name: /What You Need to Know/i })).toBeVisible()
  24 |   })
  25 | 
  26 |   test('switches tabs when clicked', async ({ page }) => {
  27 |     await page.getByRole('tab', { name: 'Earnings' }).click()
  28 |     await expect(page.getByRole('tab', { name: 'Earnings' })).toHaveAttribute('aria-selected', 'true')
  29 |     await expect(page.getByRole('heading', { name: /Earnings/i })).toBeVisible()
  30 |   })
  31 | 
  32 |   test('renders company impact and stock impact sections separately', async ({ page }) => {
  33 |     await expect(page.getByRole('heading', { name: /Company Impact/i })).toBeVisible()
  34 |     await expect(page.getByRole('heading', { name: /Stock Impact/i })).toBeVisible()
  35 |   })
  36 | 
  37 |   test('renders scenario analysis with Base/Bull/Bear cases', async ({ page }) => {
  38 |     await expect(page.getByRole('heading', { name: /Scenario Analysis/i })).toBeVisible()
  39 |     await expect(page.getByText(/BASE CASE/i)).toBeVisible()
  40 |     await expect(page.getByText(/BULL CASE/i)).toBeVisible()
  41 |     await expect(page.getByText(/BEAR CASE/i)).toBeVisible()
  42 |   })
  43 | 
  44 |   test('renders what would change the view section', async ({ page }) => {
  45 |     await expect(page.getByRole('heading', { name: /What Would Change the View/i })).toBeVisible()
  46 |   })
  47 | 
  48 |   test('renders confidence assessment', async ({ page }) => {
  49 |     await expect(page.getByRole('heading', { name: /Confidence Assessment/i })).toBeVisible()
> 50 |     await expect(page.getByText(/75%/i)).toBeVisible()
     |                                          ^ Error: expect(locator).toBeVisible() failed
  51 |   })
  52 | 
  53 |   test('renders missing information', async ({ page }) => {
  54 |     await expect(page.getByText(/Missing Information:/i)).toBeVisible()
  55 |     await expect(page.getByText(/No recent earnings result available/i)).toBeVisible()
  56 |   })
  57 | 
  58 |   test('renders supporting evidence section', async ({ page }) => {
  59 |     await expect(page.getByRole('heading', { name: /Supporting Evidence/i })).toBeVisible()
  60 |   })
  61 | 
  62 |   test('shows earnings tab when clicked', async ({ page }) => {
  63 |     await page.getByRole('tab', { name: 'Earnings' }).click()
  64 |     await expect(page.getByRole('heading', { name: /Earnings/i })).toBeVisible()
  65 |   })
  66 | 
  67 |   test('shows leadership tab with CEO/CFO', async ({ page }) => {
  68 |     await page.getByRole('tab', { name: 'Leadership' }).click()
  69 |     await expect(page.getByText(/Tim Cook/i)).toBeVisible()
  70 |     await expect(page.getByText(/Luca Maestri/i)).toBeVisible()
  71 |   })
  72 | 
  73 |   test('shows quant tab with signals', async ({ page }) => {
  74 |     await page.getByRole('tab', { name: 'Quant' }).click()
  75 |     await expect(page.getByRole('heading', { name: /Quant Signals/i })).toBeVisible()
  76 |   })
  77 | })
```