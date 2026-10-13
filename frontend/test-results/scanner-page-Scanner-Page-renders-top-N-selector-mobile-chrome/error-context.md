# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: scanner-page.spec.ts >> Scanner Page >> renders top N selector
- Location: src/test/e2e/scanner-page.spec.ts:14:3

# Error details

```
TypeError: page.getByLabelText is not a function
```

# Page snapshot

```yaml
- generic [ref=e4]:
  - banner [ref=e5]:
    - banner [ref=e6]:
      - generic [ref=e7]:
        - link "Trading Copilot Home" [ref=e8] [cursor=pointer]:
          - /url: /
          - text: Trading Copilot
        - navigation "Main navigation" [ref=e12]:
          - link "Dashboard" [ref=e13] [cursor=pointer]:
            - /url: /
          - link "Scanner" [ref=e14] [cursor=pointer]:
            - /url: /scanner
          - link "Macro Calendar" [ref=e15] [cursor=pointer]:
            - /url: /macro
          - link "Search" [ref=e16] [cursor=pointer]:
            - /url: /search
        - group "Theme selection" [ref=e18]:
          - button "Light theme" [ref=e19] [cursor=pointer]
          - button "Dark theme" [ref=e23] [cursor=pointer]
          - button "System theme" [pressed] [ref=e26] [cursor=pointer]
  - main [ref=e30]:
    - complementary [ref=e31]:
      - complementary "Sidebar navigation" [ref=e32]:
        - generic [ref=e33]:
          - generic [ref=e34]: Trading Copilot
          - button "Collapse sidebar" [expanded] [ref=e35] [cursor=pointer]
        - navigation "Main navigation" [ref=e38]:
          - list [ref=e39]:
            - listitem [ref=e40]:
              - link "Dashboard" [ref=e41] [cursor=pointer]:
                - /url: /
            - listitem [ref=e48]:
              - link "Scanner" [ref=e49] [cursor=pointer]:
                - /url: /scanner
            - listitem [ref=e53]:
              - link "Macro Calendar" [ref=e54] [cursor=pointer]:
                - /url: /macro
            - listitem [ref=e58]:
              - link "Search" [ref=e59] [cursor=pointer]:
                - /url: /search
            - listitem [ref=e64]:
              - link "Settings" [ref=e65] [cursor=pointer]:
                - /url: /settings
        - generic [ref=e70]: ResearcherFree
    - main [ref=e77]:
      - generic [ref=e78]:
        - generic [ref=e79]:
          - generic [ref=e80]:
            - heading "Quant Scanner" [level=1] [ref=e81]
            - paragraph [ref=e82]: Top ranked stocks by deterministic quant signals
          - combobox "Number of results" [ref=e84]:
            - option "Top 10"
            - option "Top 20" [selected]
            - option "Top 50"
            - option "Top 100"
        - generic [ref=e86]:
          - generic [ref=e87]: Market Status—
          - generic [ref=e88]: Symbols Tracked0
          - generic [ref=e89]: As of—
        - generic [ref=e90]:
          - generic [ref=e91]: 🔍
          - heading "No candidates found" [level=3] [ref=e92]
          - paragraph [ref=e93]: Try adjusting your scanner parameters or check back later.
  - contentinfo [ref=e94]:
    - contentinfo [ref=e95]:
      - generic [ref=e96]:
        - generic [ref=e97]:
          - heading "Product" [level=4] [ref=e98]
          - navigation "Product links" [ref=e99]:
            - list [ref=e100]:
              - listitem [ref=e101]:
                - link "Scanner" [ref=e102] [cursor=pointer]:
                  - /url: /scanner
              - listitem [ref=e103]:
                - link "Macro Calendar" [ref=e104] [cursor=pointer]:
                  - /url: /macro
              - listitem [ref=e105]:
                - link "Search" [ref=e106] [cursor=pointer]:
                  - /url: /search
              - listitem [ref=e107]:
                - link "Settings" [ref=e108] [cursor=pointer]:
                  - /url: /settings
        - generic [ref=e109]:
          - heading "Data Sources" [level=4] [ref=e110]
          - navigation "Data sources" [ref=e111]:
            - list [ref=e112]:
              - listitem [ref=e113]:
                - link "SEC EDGAR" [ref=e114] [cursor=pointer]:
                  - /url: https://www.sec.gov/edgar
              - listitem [ref=e115]:
                - link "BLS" [ref=e116] [cursor=pointer]:
                  - /url: https://www.bls.gov
              - listitem [ref=e117]:
                - link "Federal Reserve" [ref=e118] [cursor=pointer]:
                  - /url: https://www.federalreserve.gov
              - listitem [ref=e119]:
                - link "BEA" [ref=e120] [cursor=pointer]:
                  - /url: https://www.bea.gov
              - listitem [ref=e121]:
                - link "Census Bureau" [ref=e122] [cursor=pointer]:
                  - /url: https://www.census.gov
              - listitem [ref=e123]:
                - link "Alpaca Markets" [ref=e124] [cursor=pointer]:
                  - /url: https://alpaca.markets
        - generic [ref=e125]:
          - heading "Legal" [level=4] [ref=e126]
          - navigation "Legal links" [ref=e127]:
            - list [ref=e128]:
              - listitem [ref=e129]:
                - link "Privacy Policy" [ref=e130] [cursor=pointer]:
                  - /url: /privacy
              - listitem [ref=e131]:
                - link "Terms of Service" [ref=e132] [cursor=pointer]:
                  - /url: /terms
              - listitem [ref=e133]:
                - link "Disclaimer" [ref=e134] [cursor=pointer]:
                  - /url: /disclaimer
        - generic [ref=e135]:
          - heading "Resources" [level=4] [ref=e136]
          - navigation "Resources" [ref=e137]:
            - list [ref=e138]:
              - listitem [ref=e139]:
                - link "Documentation" [ref=e140] [cursor=pointer]:
                  - /url: /docs
              - listitem [ref=e141]:
                - link "API Docs" [ref=e142] [cursor=pointer]:
                  - /url: /api/docs
              - listitem [ref=e143]:
                - link "GitHub" [ref=e144] [cursor=pointer]:
                  - /url: /github
              - listitem [ref=e145]:
                - link "Changelog" [ref=e146] [cursor=pointer]:
                  - /url: /changelog
      - generic [ref=e147]:
        - paragraph [ref=e148]: Trading Copilot - Deterministic Financial Intelligence. Not financial advice.
        - paragraph [ref=e149]: Data provided by SEC EDGAR, BLS, Federal Reserve, BEA, Census, Alpaca Markets.
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
> 15 |     await expect(page.getByLabelText(/Number of results/i)).toBeVisible()
     |                       ^ TypeError: page.getByLabelText is not a function
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
  31 |       await expect(page.getByRole('columnheader', { name: header })).toBeVisible()
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