# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: landing-page.spec.ts >> Landing Page >> renders features section
- Location: src/test/e2e/landing-page.spec.ts:51:3

# Error details

```
Error: expect(locator).toBeVisible() failed

Locator: getByText(/Evidence-First/i)
Expected: visible
Error: strict mode violation: getByText(/Evidence-First/i) resolved to 3 elements:
    1) <p class="hero-subtitle">Deterministic financial intelligence. Evidence-fi…</p> aka getByText('Deterministic financial intelligence. Evidence-first research for individual')
    2) <h3>Evidence-First</h3> aka getByRole('heading', { name: 'Evidence-First' })
    3) <p>Evidence-first stock research. No hallucinations.…</p> aka getByText('Evidence-first stock research')

Call log:
  - Expect "toBeVisible" getByText(/Evidence-First/i) with timeout 5000ms
  - waiting for getByText(/Evidence-First/i)

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
        - generic [ref=e80]:
          - heading "Trading Copilot" [level=1] [ref=e81]
          - paragraph [ref=e82]: Deterministic financial intelligence. Evidence-first research for individual investors.
          - generic [ref=e83]:
            - link "Launch Scanner" [ref=e84] [cursor=pointer]:
              - /url: /scanner
            - link "Search Stocks" [ref=e85] [cursor=pointer]:
              - /url: /search
        - generic [ref=e86]:
          - generic [ref=e87]:
            - heading "Market Overview" [level=2] [ref=e88]
            - link "View all macro events →" [ref=e89] [cursor=pointer]:
              - /url: /macro
          - generic [ref=e90]:
            - generic [ref=e91]: S&P 500 (SPY)——
            - generic [ref=e92]: VIX——
            - generic [ref=e93]: DXY——
            - generic [ref=e94]: 10Y Yield——
        - generic [ref=e95]:
          - generic [ref=e96]:
            - heading "Upcoming Macro Events" [level=2] [ref=e97]
            - link "View all →" [ref=e98] [cursor=pointer]:
              - /url: /macro
          - generic [ref=e99]:
            - generic [ref=e100]:
              - generic [ref=e101]: 13Oct
              - generic [ref=e102]: Test Event Tomorrowtest
              - generic [ref=e103]: high
            - generic [ref=e104]:
              - generic [ref=e105]: 17Oct
              - generic [ref=e106]: Test Event in 5 daystest
              - generic [ref=e107]: high
        - generic [ref=e108]:
          - generic [ref=e109]:
            - heading "Top Scanner Candidates" [level=2] [ref=e110]
            - link "View scanner →" [ref=e111] [cursor=pointer]:
              - /url: /scanner
          - table [ref=e113]:
            - rowgroup [ref=e114]:
              - row [ref=e115]:
                - columnheader "Rank" [ref=e116]
                - columnheader "Symbol" [ref=e117]
                - columnheader "Score" [ref=e118]
                - columnheader "Momentum" [ref=e119]
                - columnheader "Trend" [ref=e120]
                - columnheader "Liquidity" [ref=e121]
                - columnheader "Volume" [ref=e122]
                - columnheader "Vol Quality" [ref=e123]
            - rowgroup [ref=e124]:
              - row [ref=e125]:
                - cell "No candidates available" [ref=e126]
        - generic [ref=e127]:
          - generic [ref=e128]:
            - heading "Recent Company Events" [level=2] [ref=e129]
            - link "View all →" [ref=e130] [cursor=pointer]:
              - /url: /search
          - generic [ref=e131]: No recent events
        - generic [ref=e133]:
          - heading "Why Trading Copilot?" [level=2] [ref=e134]
          - generic [ref=e135]:
            - generic [ref=e136]:
              - generic [ref=e137]: 📊
              - heading "Deterministic Intelligence" [level=3] [ref=e138]
              - paragraph [ref=e139]: No hallucinations. Every claim traced to primary sources with evidence.
            - generic [ref=e140]:
              - generic [ref=e141]: 🔍
              - heading "Evidence-First" [level=3] [ref=e142]
              - paragraph [ref=e143]: Every claim traced to SEC filings, earnings calls, macro data with citations.
            - generic [ref=e144]:
              - generic [ref=e145]: ⚖️
              - heading "Company ≠ Stock Impact" [level=3] [ref=e146]
              - paragraph [ref=e147]: Fundamental business impact separated from stock price bias with confidence.
            - generic [ref=e148]:
              - generic [ref=e149]: 🎯
              - heading "Scenario Analysis" [level=3] [ref=e150]
              - paragraph [ref=e151]: Base/Bull/Bear cases with explicit conditions and falsification criteria.
            - generic [ref=e152]:
              - generic [ref=e153]: 📚
              - heading "Term Definitions" [level=3] [ref=e154]
              - paragraph [ref=e155]: Hover any financial term for instant definition with authoritative source.
            - generic [ref=e156]:
              - generic [ref=e157]: 🤖
              - heading "Zero-LLM Core" [level=3] [ref=e158]
              - paragraph [ref=e159]: All core functionality works without LLMs. Optional local AI only enhances.
        - generic [ref=e160]:
          - heading "Start Your Research" [level=2] [ref=e161]
          - paragraph [ref=e162]: Evidence-first stock research. No hallucinations. No hidden agendas.
          - link "Start Researching" [ref=e163] [cursor=pointer]:
            - /url: /scanner
  - contentinfo [ref=e164]:
    - contentinfo [ref=e165]:
      - generic [ref=e166]:
        - generic [ref=e167]:
          - heading "Product" [level=4] [ref=e168]
          - navigation "Product links" [ref=e169]:
            - list [ref=e170]:
              - listitem [ref=e171]:
                - link "Scanner" [ref=e172] [cursor=pointer]:
                  - /url: /scanner
              - listitem [ref=e173]:
                - link "Macro Calendar" [ref=e174] [cursor=pointer]:
                  - /url: /macro
              - listitem [ref=e175]:
                - link "Search" [ref=e176] [cursor=pointer]:
                  - /url: /search
              - listitem [ref=e177]:
                - link "Settings" [ref=e178] [cursor=pointer]:
                  - /url: /settings
        - generic [ref=e179]:
          - heading "Data Sources" [level=4] [ref=e180]
          - navigation "Data sources" [ref=e181]:
            - list [ref=e182]:
              - listitem [ref=e183]:
                - link "SEC EDGAR" [ref=e184] [cursor=pointer]:
                  - /url: https://www.sec.gov/edgar
              - listitem [ref=e185]:
                - link "BLS" [ref=e186] [cursor=pointer]:
                  - /url: https://www.bls.gov
              - listitem [ref=e187]:
                - link "Federal Reserve" [ref=e188] [cursor=pointer]:
                  - /url: https://www.federalreserve.gov
              - listitem [ref=e189]:
                - link "BEA" [ref=e190] [cursor=pointer]:
                  - /url: https://www.bea.gov
              - listitem [ref=e191]:
                - link "Census Bureau" [ref=e192] [cursor=pointer]:
                  - /url: https://www.census.gov
              - listitem [ref=e193]:
                - link "Alpaca Markets" [ref=e194] [cursor=pointer]:
                  - /url: https://alpaca.markets
        - generic [ref=e195]:
          - heading "Legal" [level=4] [ref=e196]
          - navigation "Legal links" [ref=e197]:
            - list [ref=e198]:
              - listitem [ref=e199]:
                - link "Privacy Policy" [ref=e200] [cursor=pointer]:
                  - /url: /privacy
              - listitem [ref=e201]:
                - link "Terms of Service" [ref=e202] [cursor=pointer]:
                  - /url: /terms
              - listitem [ref=e203]:
                - link "Disclaimer" [ref=e204] [cursor=pointer]:
                  - /url: /disclaimer
        - generic [ref=e205]:
          - heading "Resources" [level=4] [ref=e206]
          - navigation "Resources" [ref=e207]:
            - list [ref=e208]:
              - listitem [ref=e209]:
                - link "Documentation" [ref=e210] [cursor=pointer]:
                  - /url: /docs
              - listitem [ref=e211]:
                - link "API Docs" [ref=e212] [cursor=pointer]:
                  - /url: /api/docs
              - listitem [ref=e213]:
                - link "GitHub" [ref=e214] [cursor=pointer]:
                  - /url: /github
              - listitem [ref=e215]:
                - link "Changelog" [ref=e216] [cursor=pointer]:
                  - /url: /changelog
      - generic [ref=e217]:
        - paragraph [ref=e218]: Trading Copilot - Deterministic Financial Intelligence. Not financial advice.
        - paragraph [ref=e219]: Data provided by SEC EDGAR, BLS, Federal Reserve, BEA, Census, Alpaca Markets.
```

# Test source

```ts
  1  | import { test, expect } from '@playwright/test'
  2  | 
  3  | test.describe('Landing Page', () => {
  4  |   test.beforeEach(async ({ page }) => {
  5  |     await page.goto('/')
  6  |     await page.waitForLoadState('networkidle')
  7  |   })
  8  | 
  9  |   test('loads successfully', async ({ page }) => {
  10 |     await expect(page).toHaveTitle(/Trading Copilot/)
  11 |   })
  12 | 
  13 |   test('renders hero section', async ({ page }) => {
  14 |     await expect(page.getByRole('heading', { name: /Trading Copilot/i })).toBeVisible()
  15 |     await expect(page.getByText(/Deterministic financial intelligence/i)).toBeVisible()
  16 |   })
  17 | 
  18 |   test('renders primary CTA buttons', async ({ page }) => {
  19 |     await expect(page.getByRole('link', { name: /Launch Scanner/i })).toBeVisible()
  20 |     await expect(page.getByRole('link', { name: /Search Stocks/i })).toBeVisible()
  21 |   })
  22 | 
  23 |   test('navigates to scanner page', async ({ page }) => {
  24 |     await page.getByRole('link', { name: /Launch Scanner/i }).click()
  25 |     await expect(page).toHaveURL(/.*\/scanner/)
  26 |     await expect(page.getByRole('heading', { name: /Quant Scanner/i })).toBeVisible()
  27 |   })
  28 | 
  29 |   test('navigates to search page', async ({ page }) => {
  30 |     await page.getByRole('link', { name: /Search Stocks/i }).click()
  31 |     await expect(page).toHaveURL(/.*\/search/)
  32 |     await expect(page.getByRole('heading', { name: /Search/i })).toBeVisible()
  33 |   })
  34 | 
  35 |   test('renders market overview section', async ({ page }) => {
  36 |     await expect(page.getByRole('heading', { name: /Market Overview/i })).toBeVisible()
  37 |   })
  38 | 
  39 |   test('renders upcoming macro events section', async ({ page }) => {
  40 |     await expect(page.getByRole('heading', { name: /Upcoming Macro Events/i })).toBeVisible()
  41 |   })
  42 | 
  43 |   test('renders top scanner candidates section', async ({ page }) => {
  44 |     await expect(page.getByRole('heading', { name: /Top Scanner Candidates/i })).toBeVisible()
  45 |   })
  46 | 
  47 |   test('renders recent company events section', async ({ page }) => {
  48 |     await expect(page.getByRole('heading', { name: /Recent Company Events/i })).toBeVisible()
  49 |   })
  50 | 
  51 |   test('renders features section', async ({ page }) => {
  52 |     await expect(page.getByRole('heading', { name: /Why Trading Copilot/i })).toBeVisible()
  53 |     await expect(page.getByText(/Deterministic Intelligence/i)).toBeVisible()
> 54 |     await expect(page.getByText(/Evidence-First/i)).toBeVisible()
     |                                                     ^ Error: expect(locator).toBeVisible() failed
  55 |     await expect(page.getByText(/Company ≠ Stock Impact/i)).toBeVisible()
  56 |     await expect(page.getByText(/Scenario Analysis/i)).toBeVisible()
  57 |     await expect(page.getByText(/Term Definitions/i)).toBeVisible()
  58 |     await expect(page.getByText(/Zero-LLM Core/i)).toBeVisible()
  59 |   })
  60 | 
  61 |   test('renders bottom CTA section', async ({ page }) => {
  62 |     await expect(page.getByRole('heading', { name: /Start Your Research/i })).toBeVisible()
  63 |     await expect(page.getByRole('link', { name: /Start Researching/i })).toBeVisible()
  64 |   })
  65 | })
```