# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: search-page.spec.ts >> Search Page >> renders stock results in grid
- Location: src/test/e2e/search-page.spec.ts:32:3

# Error details

```
TypeError: page.getByPlaceholderText is not a function
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
      - generic [ref=e79]:
        - heading "Search" [level=1] [ref=e80]
        - paragraph [ref=e81]: Find stocks, news, events, and filings
        - generic [ref=e83]:
          - textbox "Search stocks, news, events, filings..." [active] [ref=e87]
          - button "Search" [ref=e88] [cursor=pointer]
        - generic [ref=e92]: "Try: \"AAPL\", \"earnings\", \"FOMC\", \"Form 4\""
  - contentinfo [ref=e93]:
    - contentinfo [ref=e94]:
      - generic [ref=e95]:
        - generic [ref=e96]:
          - heading "Product" [level=4] [ref=e97]
          - navigation "Product links" [ref=e98]:
            - list [ref=e99]:
              - listitem [ref=e100]:
                - link "Scanner" [ref=e101] [cursor=pointer]:
                  - /url: /scanner
              - listitem [ref=e102]:
                - link "Macro Calendar" [ref=e103] [cursor=pointer]:
                  - /url: /macro
              - listitem [ref=e104]:
                - link "Search" [ref=e105] [cursor=pointer]:
                  - /url: /search
              - listitem [ref=e106]:
                - link "Settings" [ref=e107] [cursor=pointer]:
                  - /url: /settings
        - generic [ref=e108]:
          - heading "Data Sources" [level=4] [ref=e109]
          - navigation "Data sources" [ref=e110]:
            - list [ref=e111]:
              - listitem [ref=e112]:
                - link "SEC EDGAR" [ref=e113] [cursor=pointer]:
                  - /url: https://www.sec.gov/edgar
              - listitem [ref=e114]:
                - link "BLS" [ref=e115] [cursor=pointer]:
                  - /url: https://www.bls.gov
              - listitem [ref=e116]:
                - link "Federal Reserve" [ref=e117] [cursor=pointer]:
                  - /url: https://www.federalreserve.gov
              - listitem [ref=e118]:
                - link "BEA" [ref=e119] [cursor=pointer]:
                  - /url: https://www.bea.gov
              - listitem [ref=e120]:
                - link "Census Bureau" [ref=e121] [cursor=pointer]:
                  - /url: https://www.census.gov
              - listitem [ref=e122]:
                - link "Alpaca Markets" [ref=e123] [cursor=pointer]:
                  - /url: https://alpaca.markets
        - generic [ref=e124]:
          - heading "Legal" [level=4] [ref=e125]
          - navigation "Legal links" [ref=e126]:
            - list [ref=e127]:
              - listitem [ref=e128]:
                - link "Privacy Policy" [ref=e129] [cursor=pointer]:
                  - /url: /privacy
              - listitem [ref=e130]:
                - link "Terms of Service" [ref=e131] [cursor=pointer]:
                  - /url: /terms
              - listitem [ref=e132]:
                - link "Disclaimer" [ref=e133] [cursor=pointer]:
                  - /url: /disclaimer
        - generic [ref=e134]:
          - heading "Resources" [level=4] [ref=e135]
          - navigation "Resources" [ref=e136]:
            - list [ref=e137]:
              - listitem [ref=e138]:
                - link "Documentation" [ref=e139] [cursor=pointer]:
                  - /url: /docs
              - listitem [ref=e140]:
                - link "API Docs" [ref=e141] [cursor=pointer]:
                  - /url: /api/docs
              - listitem [ref=e142]:
                - link "GitHub" [ref=e143] [cursor=pointer]:
                  - /url: /github
              - listitem [ref=e144]:
                - link "Changelog" [ref=e145] [cursor=pointer]:
                  - /url: /changelog
      - generic [ref=e146]:
        - paragraph [ref=e147]: Trading Copilot - Deterministic Financial Intelligence. Not financial advice.
        - paragraph [ref=e148]: Data provided by SEC EDGAR, BLS, Federal Reserve, BEA, Census, Alpaca Markets.
```

# Test source

```ts
  1  | import { test, expect } from '@playwright/test'
  2  | 
  3  | test.describe('Search Page', () => {
  4  |   test.beforeEach(async ({ page }) => {
  5  |     await page.goto('/search')
  6  |     await page.waitForLoadState('networkidle')
  7  |   })
  8  | 
  9  |   test('loads successfully with search hero', async ({ page }) => {
  10 |     await expect(page.getByRole('heading', { name: /Search/i })).toBeVisible()
  11 |     await expect(page.getByText(/Find stocks, news, events, and filings/i)).toBeVisible()
  12 |     await expect(page.getByPlaceholderText(/Search stocks, news, events, filings/i)).toBeVisible()
  13 |   })
  14 | 
  15 |   test('renders search hints', async ({ page }) => {
  16 |     await expect(page.getByText(/Try: "AAPL", "earnings", "FOMC", "Form 4"/i)).toBeVisible()
  17 |   })
  18 | 
  19 |   test('shows results when query is entered', async ({ page }) => {
  20 |     const input = page.getByPlaceholderText(/Search stocks, news, events, filings/i)
  21 |     await input.fill('AAPL')
  22 |     await input.press('Enter')
  23 |     
  24 |     // Wait for results
  25 |     await expect(page.getByRole('tab', { name: /All/i })).toBeVisible({ timeout: 10000 })
  26 |     await expect(page.getByRole('tab', { name: /Stocks/i })).toBeVisible()
  27 |     await expect(page.getByRole('tab', { name: /News/i })).toBeVisible()
  28 |     await expect(page.getByRole('tab', { name: /Events/i })).toBeVisible()
  29 |     await expect(page.getByRole('tab', { name: /Filings/i })).toBeVisible()
  30 |   })
  31 | 
  32 |   test('renders stock results in grid', async ({ page }) => {
> 33 |     const input = page.getByPlaceholderText(/Search stocks, news, events, filings/i)
     |                        ^ TypeError: page.getByPlaceholderText is not a function
  34 |     await input.fill('AAPL')
  35 |     await input.press('Enter')
  36 |     
  37 |     await expect(page.getByText(/AAPL/i)).toBeVisible({ timeout: 10000 })
  38 |     await expect(page.getByText(/Apple Inc./i)).toBeVisible()
  39 |     await expect(page.getByText(/NASDAQ/i)).toBeVisible()
  40 |   })
  41 | 
  42 |   test('switches between search result tabs', async ({ page }) => {
  43 |     const input = page.getByPlaceholderText(/Search stocks, news, events, filings/i)
  44 |     await input.fill('AAPL')
  45 |     await input.press('Enter')
  46 |     
  47 |     await expect(page.getByRole('tab', { name: /All/i })).toHaveAttribute('aria-selected', 'true')
  48 |     
  49 |     await page.getByRole('tab', { name: /Stocks/i }).click()
  50 |     await expect(page.getByRole('tab', { name: /Stocks/i })).toHaveAttribute('aria-selected', 'true')
  51 |     
  52 |     await page.getByRole('tab', { name: /News/i }).click()
  53 |     await expect(page.getByRole('tab', { name: /News/i })).toHaveAttribute('aria-selected', 'true')
  54 |   })
  55 | 
  56 |   test('links stock result to stock page', async ({ page }) => {
  57 |     const input = page.getByPlaceholderText(/Search stocks, news, events, filings/i)
  58 |     await input.fill('AAPL')
  59 |     await input.press('Enter')
  60 |     
  61 |     await expect(page.getByRole('link', { name: /AAPL/i })).toHaveAttribute('href', '/stocks/AAPL', { timeout: 10000 })
  62 |   })
  63 | 
  64 |   test('shows news search not implemented message', async ({ page }) => {
  65 |     const input = page.getByPlaceholderText(/Search stocks, news, events, filings/i)
  66 |     await input.fill('AAPL')
  67 |     await input.press('Enter')
  68 |     
  69 |     await page.getByRole('tab', { name: /News/i }).click()
  70 |     await expect(page.getByText(/News search not yet implemented/i)).toBeVisible({ timeout: 10000 })
  71 |   })
  72 | 
  73 |   test('shows events search not implemented message', async ({ page }) => {
  74 |     const input = page.getByPlaceholderText(/Search stocks, news, events, filings/i)
  75 |     await input.fill('AAPL')
  76 |     await input.press('Enter')
  77 |     
  78 |     await page.getByRole('tab', { name: /Events/i }).click()
  79 |     await expect(page.getByText(/Events search not yet implemented/i)).toBeVisible({ timeout: 10000 })
  80 |   })
  81 | 
  82 |   test('shows filings search not implemented message', async ({ page }) => {
  83 |     const input = page.getByPlaceholderText(/Search stocks, news, events, filings/i)
  84 |     await input.fill('AAPL')
  85 |     await input.press('Enter')
  86 |     
  87 |     await page.getByRole('tab', { name: /Filings/i }).click()
  88 |     await expect(page.getByText(/Filings search not yet implemented/i)).toBeVisible({ timeout: 10000 })
  89 |   })
  90 | })
```