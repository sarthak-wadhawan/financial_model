import { test, expect, request as playwrightRequest, type Page } from '@playwright/test'

// Never route mutations to the normal backend. The standalone capture harness
// supplies a disposable server with a token-bound isolation marker.
const backend = process.env.WEBSITE_REPAIR_API_URL || 'http://127.0.0.1:18080'
const origin = process.env.WEBSITE_REPAIR_FRONTEND_URL || 'http://127.0.0.1:3000'
const token = process.env.WEBSITE_REPAIR_ISOLATION_TOKEN

test.beforeEach(async ({ page, request }) => {
  expect(token, 'Start website_repair_capture.cjs --serve-isolated first').toBeTruthy()
  const marker = await request.get(`${backend}/__website_repair_isolation`)
  expect(marker.ok(), 'Refusing an unverified backend').toBeTruthy()
  expect(await marker.json()).toMatchObject({ token, isolated: true })
  await page.route('**/api/v1/**', async route => {
    const url = new URL(route.request().url())
    const response = await route.fetch({ url: `${backend}${url.pathname}${url.search}` })
    await route.fulfill({ response })
  })
})

test.afterEach(async ({ page }) => {
  // Let real forwarded requests finish before Playwright disposes the page.
  // Do not ignore route errors: failures during a test remain test failures.
  await page.unrouteAll({ behavior: 'wait' })
})

async function go(page: Page, path: string) {
  await page.goto(`${origin}${path}`)
  await expect(page.locator('h1').first()).toBeVisible()
}

async function layout(page: Page) {
  await expect(page.getByRole('main')).toHaveCount(1)
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1),
    'No document-level horizontal overflow').toBeTruthy()
  await expect(page.locator('body')).not.toContainText(/NaN|undefined|Invalid Date/)
}

async function cleanup(path: string) {
  // A timed-out test disposes its request fixture; cleanup needs its own context.
  const client = await playwrightRequest.newContext()
  try {
    expect(await (await client.get(`${backend}/__website_repair_isolation`)).json()).toMatchObject({ token, isolated: true })
    const response = await client.delete(`${backend}/api/v1/${path}`)
    expect([204, 404]).toContain(response.status())
  } finally { await client.dispose() }
}

test('dashboard search AAPL renders actual Phase 9 output and honest missing data', async ({ page, request }) => {
  const errors: string[] = []
  page.on('pageerror', error => errors.push(error.message))
  await go(page, '/')
  // Start at dashboard's research entry point, never shortcut stock navigation.
  await page.getByRole('link', { name: 'Search a company', exact: true }).first().click()
  await page.getByRole('searchbox', { name: 'Symbol or company name' }).fill('AAPL')
  await page.getByRole('link', { name: /AAPL/ }).first().click()
  await expect(page).toHaveURL(/\/stocks\/AAPL/)
  const response = await request.get(`${backend}/api/v1/stocks/AAPL/interpretation`)
  expect(response.ok()).toBeTruthy()
  const interpretation = await response.json()
  await expect(page.getByRole('heading', { name: 'Company Impact', exact: true })).toBeVisible()
  await expect(page.getByRole('heading', { name: 'Stock Impact', exact: true })).toBeVisible()
  await expect(page.getByRole('heading', { name: /Scenario Analysis/ })).toBeVisible()
  await expect(page.locator('body')).toContainText(interpretation.what_happened)
  for (const missing of interpretation.missing_information || []) {
    await expect(page.locator('body')).toContainText(missing)
  }
  const stock = await (await request.get(`${backend}/api/v1/stocks/AAPL`)).json()
  if (stock.price === null) await expect(page.locator('body')).toContainText(/unavailable|not available|no price/i)
  await layout(page)
  expect(errors).toEqual([])
})

test('watchlist UI create, notes, default update, reload persistence, remove and delete', async ({ page, request }, info) => {
  const name = `website-repair-${info.project.name}-${Date.now()}`
  let id: string | undefined
  try {
    await go(page, '/watchlists')
    await page.getByRole('button', { name: 'Create Watchlist', exact: true }).first().click()
    const dialog = page.getByRole('dialog')
    await dialog.getByLabel('Name', { exact: true }).fill(name)
    await dialog.getByLabel(/Description/).fill('Disposable browser regression')
    const created = page.waitForResponse(r => r.url().endsWith('/watchlists') && r.request().method() === 'POST')
    await dialog.getByRole('button', { name: 'Save', exact: true }).click()
    const result = await created
    expect(result.status()).toBe(201)
    id = (await result.json()).id
    const card = page.locator('.watchlist-card').filter({ hasText: name })
    await card.getByRole('link', { name: `Open ${name}`, exact: true }).click()
    await expect(page.getByRole('heading', { name, exact: true }), 'Watchlist detail route must be registered').toBeVisible()
    await page.getByRole('button', { name: 'Add Symbol', exact: true }).first().click()
    await page.getByRole('dialog').getByLabel('Symbol', { exact: true }).fill('AAPL')
    await page.getByRole('dialog').getByLabel(/Notes/).fill('Evidence before decisions')
    await page.getByRole('dialog').getByRole('button', { name: 'Save', exact: true }).click()
    await expect(page.getByRole('row').filter({ hasText: 'AAPL' })).toContainText('Evidence before decisions')
    await page.getByRole('button', { name: 'Set Default', exact: true }).click()
    await expect(page.getByRole('button', { name: 'Default', exact: true })).toBeVisible()
    await page.reload()
    await expect(page.getByRole('heading', { name, exact: true })).toBeVisible()
    await expect(page.getByRole('row').filter({ hasText: 'AAPL' })).toContainText('Evidence before decisions')
    expect(await (await request.get(`${backend}/api/v1/watchlists/${id}`)).json()).toMatchObject({ is_default: true })
    await page.getByRole('row').filter({ hasText: 'AAPL' }).getByRole('button', { name: 'Remove' }).click()
    await expect(page.getByText('No symbols yet', { exact: true })).toBeVisible()
    await go(page, '/watchlists')
    await page.locator('.watchlist-card').filter({ hasText: name }).getByRole('button', { name: 'Delete', exact: true }).click()
    await page.getByRole('dialog').getByRole('button', { name: 'Delete', exact: true }).click()
    await expect(page.getByRole('heading', { name, exact: true })).toHaveCount(0)
    await expect.poll(async () => (await request.get(`${backend}/api/v1/watchlists/${id}`)).status()).toBe(404)
    await layout(page)
  } finally {
    if (id) await cleanup(`watchlists/${id}`)
  }
})

test('alert UI CRUD, side-effect-free dry-run, real manual evaluation/history/ack', async ({ page, request }, info) => {
  const name = `website-repair-alert-${info.project.name}-${Date.now()}`
  let id: string | undefined
  page.on('dialog', async dialog => { await dialog.accept() })
  try {
    await go(page, '/alerts')
    await page.getByRole('button', { name: 'Create Alert', exact: true }).first().click()
    const dialog = page.getByRole('dialog')
    await dialog.getByLabel('Alert Name').fill(name)
    await dialog.getByLabel('Threshold', { exact: true }).fill('0.01')
    await dialog.getByPlaceholder(/AAPL, MSFT/).fill('AAPL')
    const created = page.waitForResponse(r => r.url().endsWith('/alerts') && r.request().method() === 'POST')
    await dialog.getByRole('button', { name: 'Create Alert', exact: true }).click()
    const result = await created
    expect(result.status()).toBe(201)
    id = (await result.json()).id
    const card = page.locator('.alert-card').filter({ hasText: name })
    await card.getByRole('button', { name: 'Deactivate', exact: true }).click()
    await expect(card.getByRole('button', { name: 'Activate', exact: true })).toBeVisible()
    await page.reload()
    await expect(card.getByRole('button', { name: 'Activate', exact: true })).toBeVisible()
    await card.getByRole('button', { name: 'Activate', exact: true }).click()
    await expect(card.getByRole('button', { name: 'Deactivate', exact: true })).toBeVisible()
    const before = await (await request.get(`${backend}/api/v1/alerts/${id}`)).json()
    const tested = page.waitForResponse(r => r.url().endsWith('/alerts/test') && r.request().method() === 'POST')
    await card.getByRole('button', { name: 'Dry-run', exact: true }).click()
    const dryrun = await tested
    expect(dryrun.ok()).toBeTruthy()
    const payload = await dryrun.json()
    if (payload.status === 'unavailable') {
      expect(payload.would_trigger).toBeNull()
      expect(payload.unavailable_symbols).toContain('AAPL')
      expect(payload.current_values).toEqual({})
      await expect(page.locator('body')).toContainText(/unavailable|missing observations/i)
    } else {
      expect(payload.status).toBe('evaluated')
      expect(typeof payload.would_trigger).toBe('boolean')
    }
    expect(payload.message).toMatch(/missing|unavailable|dry.run|current|condition/i)
    const after = await (await request.get(`${backend}/api/v1/alerts/${id}`)).json()
    expect(after.trigger_count).toBe(before.trigger_count)
    expect(after.last_triggered).toBe(before.last_triggered)
    const evaluated = page.waitForResponse(r => r.url().endsWith(`/alerts/${id}/evaluate`) && r.request().method() === 'POST')
    await card.getByRole('button', { name: 'Evaluate', exact: true }).click()
    const manualResponse = await evaluated
    expect(manualResponse.ok()).toBeTruthy()
    const manual = await manualResponse.json()
    expect(manual.delivery).toBe('in_app_history_only')
    if (manual.status === 'unavailable') {
      info.annotations.push({ type: 'external-provider-unavailable', description: 'Real evaluate exercised, but populated trigger/ack path NOT verified in this run; deterministic component/API coverage verifies populated path.' })
      expect(manual.would_trigger).toBeNull()
      expect(manual.triggers).toEqual([])
      expect(await (await request.get(`${backend}/api/v1/alerts/${id}/triggers`)).json()).toEqual([])
      await expect(page.getByText('Observations unavailable; no match can be determined.')).toBeVisible()
    } else {
      expect(manual.status).toBe('evaluated')
      expect(manual.triggers).toHaveLength(1)
      const trigger = manual.triggers[0]
      expect(trigger.metadata.observation.source).toBeTruthy()
      expect(trigger.metadata.observation.as_of).toBeTruthy()
      await expect(page.getByText(/Observation source:/).first()).toContainText(trigger.metadata.observation.source)
      await page.getByRole('button', { name: 'View trigger history' }).click()
      const history = page.locator('.trigger-history-list .trigger-item').filter({ hasText: trigger.message })
      await expect(history).toContainText(trigger.metadata.observation.as_of)
      await history.getByRole('button', { name: 'Acknowledge', exact: true }).click()
      await expect(history.getByText('Acknowledged', { exact: true })).toBeVisible()
      const persisted = await (await request.get(`${backend}/api/v1/alerts/${id}/triggers`)).json()
      expect(persisted).toEqual(expect.arrayContaining([expect.objectContaining({ id: trigger.id, acknowledged: true })]))
      await page.reload()
      await page.getByRole('button', { name: /^Triggered/ }).click()
      await expect(history.getByText('Acknowledged', { exact: true })).toBeVisible()
    }
    await page.getByRole('button', { name: /^All \(/ }).click()
    await card.getByRole('button', { name: 'Delete', exact: true }).click()
    await page.getByRole('dialog').getByRole('button', { name: 'Delete', exact: true }).click()
    await expect(card).toHaveCount(0)
    await layout(page)
  } finally {
    if (id) await cleanup(`alerts/${id}`)
  }
})

test('stock term survives mobile touch synthetic hover exit; desktop supports focus/link/Escape', async ({ page, isMobile }, info) => {
  if (isMobile) await page.setViewportSize({ width: 375, height: 812 })
  await go(page, '/stocks/AAPL')
  const term = page.getByRole('button', { name: 'EPS', exact: true })
  if (isMobile) await term.tap()
  else await term.focus()
  await expect(term).toHaveAttribute('aria-expanded', 'true')
  const popover = page.getByRole('note')
  await expect(popover).toBeVisible()
  await expect(popover.getByRole('link', { name: /Learn more/ })).toHaveAttribute('href', /^https:\/\//)
  await page.screenshot({ path: info.outputPath('stock-term-header-after.png'), fullPage: true })
  if (isMobile) {
    // The synthetic mouseleave used to undo a successful tap immediately.
    await page.waitForTimeout(500)
    await expect(term).toHaveAttribute('aria-expanded', 'true')
    await popover.getByRole('button', { name: /Close EPS definition/ }).tap()
  } else await term.press('Escape')
  await expect(term).toHaveAttribute('aria-expanded', 'false')
  const header = page.locator('.stock-header')
  const headerBox = await header.boundingBox()
  const tabsBox = await page.getByRole('tablist', { name: 'Stock sections' }).boundingBox()
  expect(tabsBox!.width).toBeGreaterThan(headerBox!.width * 0.9)
  await layout(page)
})

test('calendar UI downloads filtered valid ICS without direct database access', async ({ page }) => {
  await go(page, '/calendar')
  await page.getByRole('button', { name: 'Export Calendar', exact: true }).click()
  const dialog = page.getByRole('dialog')
  await dialog.getByLabel('Earnings', { exact: true }).check()
  await dialog.getByPlaceholder(/AAPL, MSFT/).fill('AAPL')
  await dialog.getByLabel('From Date').fill('2026-01-01')
  await dialog.getByLabel('To Date').fill('2026-12-31')
  const exported = page.waitForResponse(r => r.url().endsWith('/calendar/export') && r.request().method() === 'POST')
  const download = page.waitForEvent('download')
  await dialog.getByRole('button', { name: /Export.*Download/ }).click()
  const response = await exported
  expect(response.ok()).toBeTruthy()
  expect(response.request().postDataJSON()).toMatchObject({ symbols: ['AAPL'], event_types: ['earnings'], from_date: '2026-01-01', to_date: '2026-12-31' })
  const payload = await response.json()
  const file = await download
  expect(file.suggestedFilename()).toBe(payload.filename)
  const stream = await file.createReadStream()
  expect(stream).toBeTruthy()
  const chunks: Buffer[] = []
  for await (const chunk of stream!) chunks.push(Buffer.from(chunk))
  const content = Buffer.concat(chunks).toString('utf8')
  expect(content).toBe(payload.content)
  expect(content).toContain('BEGIN:VCALENDAR')
  expect(content).toContain('VERSION:2.0')
  expect(content).toContain('END:VCALENDAR')
  expect((content.match(/BEGIN:VEVENT/g) || []).length).toBe(payload.event_count)
  await expect(page.getByText('Export Complete!', { exact: true })).toBeVisible()
})

test('MOCKED trigger transport: acknowledgement updates UI (not real trigger ingestion)', async ({ page }) => {
  let acknowledged = false
  const trigger = { id: 'website-repair-mocked-trigger', alert_id: 'mocked-alert', symbol: 'AAPL', severity: 'info', message: 'MOCKED browser acknowledgement fixture', value: 201, threshold: 200, triggered_at: new Date().toISOString() }
  await page.route('**/api/v1/alerts/triggers/recent**', route => route.fulfill({ json: [{ ...trigger, acknowledged }] }))
  await page.route('**/api/v1/alerts/triggers/website-repair-mocked-trigger/acknowledge', async route => {
    expect(route.request().method()).toBe('POST')
    acknowledged = true
    await route.fulfill({ json: { acknowledged: true } })
  })
  await go(page, '/alerts')
  await page.getByRole('button', { name: /^Triggered/ }).click()
  await expect(page.getByText(trigger.message)).toBeVisible()
  await page.getByRole('button', { name: 'Acknowledge', exact: true }).click()
  await expect(page.getByRole('button', { name: 'Acknowledge', exact: true })).toHaveCount(0)
  expect(acknowledged).toBeTruthy()
})

test('MOCKED provider failure is visibly unavailable, not fake financial values', async ({ page }) => {
  await page.route('**/api/v1/market/overview', route => route.fulfill({ status: 503, json: { detail: 'MOCKED provider unavailable — regression fixture' } }))
  await go(page, '/')
  await expect(page.getByText(/Could not load market snapshot/)).toBeVisible()
  await expect(page.getByText(/this is not an empty result/i)).toBeVisible()
  await layout(page)
})
