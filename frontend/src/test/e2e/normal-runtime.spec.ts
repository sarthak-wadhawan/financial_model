import { test as base, expect, request as playwrightRequest, type Page, type Response } from '@playwright/test'
import { mkdir, writeFile } from 'node:fs/promises'
import { randomUUID } from 'node:crypto'

const origin = 'http://127.0.0.1:3000'
const destination = 'http://127.0.0.1:8000'
const evidenceDirectory = '/tmp/opencode/runtime-integration-20261016'
const prefix = 'verification-normal-runtime-'

// Describe structure only: no response values, user names, notes, headers or credentials.
function shape(value: unknown): unknown {
  if (value === null) return 'null'
  if (Array.isArray(value)) return { type: 'array', count: value.length, item: value.length ? shape(value[0]) : null }
  if (typeof value === 'object') return Object.fromEntries(Object.entries(value).map(([key, item]) => [key, Array.isArray(item) ? { type: 'array', count: item.length } : item === null ? 'null' : typeof item]))
  return typeof value
}

const test = base.extend<{ captureRuntime: void }>({
  captureRuntime: [async ({ page }, runFixture, info) => {
    const records: unknown[] = []
    let browserErrorCount = 0
    page.on('pageerror', () => { browserErrorCount += 1 })
    const pending: Promise<void>[] = []
    const record = async (response: Response) => {
      const url = new URL(response.url())
      if (!url.pathname.startsWith('/api/v1/')) return
      const contentType = response.headers()['content-type'] ?? ''
      const bodyShape = contentType.includes('application/json')
        ? await response.json().then(shape).catch(() => 'unreadable-json') : 'non-json'
      records.push({ url: response.url(), method: response.request().method(), status: response.status(), contentType,
        browserOrigin: origin, requestOrigin: url.origin,
        configuredProxyDestination: `${destination}${url.pathname}${url.search}`, bodyShape })
    }
    const listener = (response: Response) => { pending.push(record(response)) }
    page.on('response', listener)
    page.on('requestfailed', request => {
      if (new URL(request.url()).pathname.startsWith('/api/v1/')) records.push({ url: request.url(), method: request.method(), status: 'transport-failure' })
    })
    try { await runFixture() } finally {
      page.off('response', listener)
      await Promise.all(pending)
      // Playwright otherwise auto-generates an accessibility snapshot on failure,
      // which could include pre-existing normal-database watchlists or alerts.
      await page.close()
      await mkdir(evidenceDirectory, { recursive: true })
      await writeFile(`${evidenceDirectory}/${Date.now()}-${randomUUID()}.json`, JSON.stringify({
        test: info.title, status: info.status, annotations: info.annotations, browserErrorCount,
        routing: 'Unmodified browser requests to Vite3000; destination is configured proxy target, not packet-level observation.',
        records,
      }, null, 2))
      expect(records.length, 'Browser must actually request APIs').toBeGreaterThan(0)
      expect(browserErrorCount, 'No uncaught browser errors').toBe(0)
      for (const record of records as { url: string }[]) expect(new URL(record.url).origin).toBe(origin)
    }
  }, { auto: true }],
})

test.skip(process.env.RUN_NORMAL_RUNTIME_SMOKE !== '1', 'Opt-in only: requires existing normal Vite3000 and FastAPI8000; no servers or fixtures are started.')

async function browserGet(page: Page, path: string) {
  const result = await page.evaluate(async path => {
    const response = await fetch(`/api/v1/${path}`)
    return { status: response.status, contentType: response.headers.get('content-type'), body: await response.json() }
  }, path)
  expect(result.contentType).toContain('application/json')
  expect(result.status).toBe(200)
  return result.body
}

async function cleanup(kind: 'watchlists' | 'alerts', id: string | undefined, name: string) {
  if (!id) return
  // Independent fixture survives a timed-out page. Only the exact newly-created ID/name may be deleted.
  const client = await playwrightRequest.newContext({ baseURL: `${origin}/api/v1/` })
  try {
    const current = await client.get(`${kind}/${id}`)
    if (current.status() === 404) return
    expect(current.status()).toBe(200)
    expect((await current.json()).name).toBe(name)
    expect(name.startsWith(prefix)).toBeTruthy()
    expect((await client.delete(`${kind}/${id}`)).status()).toBe(204)
    expect((await client.get(`${kind}/${id}`)).status()).toBe(404)
  } finally { await client.dispose() }
}

test('normal runtime JSON health and AAPL/MSFT search UI', async ({ page, request }) => {
  await page.goto(`${origin}/search`)
  const health = await browserGet(page, 'health/detailed')
  expect(health).toHaveProperty('providers')
  expect(health).toMatchObject({ database: 'connected', event_store: 'connected', llm_enabled: false, market: { mode: 'real' } })
  const direct = await request.get(`${destination}/api/v1/health/detailed`)
  expect(direct.status()).toBe(200)
  expect(direct.headers()['content-type']).toContain('application/json')
  const directHealth = await direct.json()
  expect(Object.keys(directHealth.providers).sort()).toEqual(Object.keys(health.providers).sort())
  await mkdir(evidenceDirectory, { recursive: true })
  await writeFile(`${evidenceDirectory}/direct-health-${Date.now()}.json`, JSON.stringify({
    url: direct.url(), method: 'GET', status: direct.status(), contentType: direct.headers()['content-type'],
    destination, bodyShape: shape(directHealth), comparison: 'provider names match browser-through-Vite health',
  }, null, 2))
  for (const symbol of ['AAPL', 'MSFT']) {
    const received = page.waitForResponse(r => new URL(r.url()).pathname === '/api/v1/symbols/search' && new URL(r.url()).searchParams.get('q') === symbol)
    await page.getByRole('searchbox', { name: 'Symbol or company name' }).fill(symbol)
    const response = await received
    expect(response.status()).toBe(200)
    expect(await response.json()).toEqual(expect.arrayContaining([expect.objectContaining({ symbol })]))
    await expect(page.getByRole('link').filter({ has: page.locator('.result-symbol', { hasText: symbol }) }).first()).toBeVisible()
  }
})

test('normal database watchlist UI create/add notes/reload/API persistence', async ({ page, request }) => {
  const name = `${prefix}watchlist-${randomUUID()}`
  let id: string | undefined
  try {
    await page.goto(`${origin}/watchlists`)
    await page.getByRole('button', { name: 'Create Watchlist', exact: true }).first().click()
    const dialog = page.getByRole('dialog')
    await dialog.getByLabel('Name', { exact: true }).fill(name)
    const created = page.waitForResponse(r => r.url().endsWith('/watchlists') && r.request().method() === 'POST')
    await dialog.getByRole('button', { name: 'Save', exact: true }).click()
    const response = await created
    expect(response.status()).toBe(201)
    id = (await response.json()).id
    await page.getByRole('link', { name: `Open ${name}`, exact: true }).click()
    await page.getByRole('button', { name: 'Add Symbol', exact: true }).first().click()
    await page.getByRole('dialog').getByLabel('Symbol', { exact: true }).fill('AAPL')
    const notes = 'Verification only: evidence before decisions'
    await page.getByRole('dialog').getByLabel(/Notes/).fill(notes)
    await page.getByRole('dialog').getByRole('button', { name: 'Save', exact: true }).click()
    await expect(page.getByRole('row').filter({ hasText: 'AAPL' })).toContainText(notes)
    await page.reload()
    await expect(page.getByRole('heading', { name, exact: true })).toBeVisible()
    await expect(page.getByRole('row').filter({ hasText: 'AAPL' })).toContainText(notes)
    const saved = await browserGet(page, `watchlists/${id}`)
    expect(saved.name).toBe(name)
    expect(saved.items).toEqual(expect.arrayContaining([expect.objectContaining({ symbol: 'AAPL', notes })]))
    const direct = await request.get(`${destination}/api/v1/watchlists/${id}`)
    expect(direct.status()).toBe(200)
    expect(await direct.json()).toEqual(saved)
  } finally { await cleanup('watchlists', id, name) }
})

test('normal database alert UI save/reload and side-effect-free dry-run', async ({ page }, info) => {
  const name = `${prefix}alert-${randomUUID()}`
  let id: string | undefined
  try {
    await page.goto(`${origin}/alerts`)
    await page.getByRole('button', { name: 'Create Alert', exact: true }).first().click()
    const dialog = page.getByRole('dialog')
    await dialog.getByLabel('Alert Name').fill(name)
    await dialog.getByLabel('Threshold', { exact: true }).fill('0.01')
    await dialog.getByPlaceholder(/AAPL, MSFT/).fill('AAPL')
    const created = page.waitForResponse(r => r.url().endsWith('/alerts') && r.request().method() === 'POST')
    await dialog.getByRole('button', { name: 'Create Alert', exact: true }).click()
    const response = await created
    expect(response.status()).toBe(201)
    id = (await response.json()).id
    const card = page.locator('.alert-card').filter({ hasText: name })
    await expect(card).toBeVisible()
    await page.reload()
    await expect(card).toBeVisible()
    const before = await browserGet(page, `alerts/${id}`)
    const historyBefore = await browserGet(page, `alerts/${id}/triggers`)
    expect(before).toMatchObject({ name, symbols: ['AAPL'], threshold: 0.01 })
    const tested = page.waitForResponse(r => r.url().endsWith('/alerts/test') && r.request().method() === 'POST')
    await card.getByRole('button', { name: 'Dry-run', exact: true }).click()
    const dryrun = await tested
    expect(dryrun.status()).toBe(200)
    const payload = await dryrun.json()
    if (payload.status === 'unavailable') {
      expect(payload.would_trigger).toBeNull()
      expect(payload.unavailable_symbols).toContain('AAPL')
      await expect(page.locator('body')).toContainText(/unavailable|missing observations/i)
      info.annotations.push({ type: 'provider-NOT-PASS', description: 'Dry-run transport/persistence verified; provider observations unavailable.' })
    } else {
      expect(payload.status).toBe('evaluated')
      expect(typeof payload.would_trigger).toBe('boolean')
      await expect(page.locator('body')).toContainText(payload.message)
    }
    expect(await browserGet(page, `alerts/${id}`)).toEqual(before)
    expect(await browserGet(page, `alerts/${id}/triggers`)).toEqual(historyBefore)
  } finally { await cleanup('alerts', id, name) }
})

test('normal runtime Dashboard/Scanner/Macro/AAPL response and rendered data', async ({ page }, info) => {
  const flows = [
    { path: '/', api: '/market/overview', heading: /research dashboard/i },
    { path: '/scanner', api: '/scanner/top', heading: 'Quant Scanner' },
    { path: '/macro', api: '/events/macro', heading: 'Macro Calendar' },
    { path: '/stocks/AAPL', api: '/stocks/AAPL/interpretation', heading: /AAPL/ },
  ]
  for (const flow of flows) {
    const received = page.waitForResponse(r => new URL(r.url()).pathname === `/api/v1${flow.api}`)
    await page.goto(`${origin}${flow.path}`)
    const response = await received
    expect(response.headers()['content-type']).toContain('application/json')
    expect([200, 503]).toContain(response.status())
    const data = await response.json()
    await expect(page.getByRole('heading', { level: 1 }).first()).toContainText(flow.heading)
    if (response.status() === 503) {
      expect(data.detail).toBeTruthy()
      await expect(page.locator('body')).toContainText(/could not load|unavailable/i)
      info.annotations.push({ type: 'provider-NOT-PASS', description: `${flow.api}: explicit 503 unavailable; no provider success claimed.` })
    } else if (flow.path === '/stocks/AAPL') {
      expect(data.what_happened).toBeTruthy()
      await expect(page.locator('body')).toContainText(data.what_happened)
      for (const heading of ['Company Impact', 'Stock Impact']) await expect(page.getByRole('heading', { name: heading, exact: true })).toBeVisible()
    } else if (flow.path === '/scanner') {
      expect(Array.isArray(data)).toBeTruthy()
      if (data.length) await expect(page.getByRole('link', { name: data[0].symbol, exact: true }).first()).toBeVisible()
      else await expect(page.locator('body')).toContainText(/no.*scanner candidates/i)
    } else if (flow.path === '/macro') {
      expect(Array.isArray(data)).toBeTruthy()
      await page.getByRole('tab', { name: 'All Events', exact: true }).click()
      if (data.length) await expect(page.locator('body')).toContainText(data[0].title)
      else await expect(page.locator('body')).toContainText(/no.*events/i)
    } else {
      expect(data.market_status).toBeTruthy()
      await expect(page.locator('body')).toContainText(data.market_status)
    }
    await expect(page.locator('body')).not.toContainText(/NaN|Invalid Date/)
  }
})

test('normal runtime calendar UI exports valid filtered ICS', async ({ page }) => {
  await page.goto(`${origin}/calendar`)
  await page.getByRole('button', { name: 'Export Calendar', exact: true }).click()
  const dialog = page.getByRole('dialog')
  await dialog.getByLabel('Earnings', { exact: true }).check()
  await dialog.getByPlaceholder(/AAPL, MSFT/).fill('AAPL')
  await dialog.getByLabel('From Date').fill('2026-01-01')
  await dialog.getByLabel('To Date').fill('2026-12-31')
  const received = page.waitForResponse(r => r.url().endsWith('/calendar/export') && r.request().method() === 'POST')
  const downloading = page.waitForEvent('download')
  await dialog.getByRole('button', { name: /Export.*Download/ }).click()
  const response = await received
  expect(response.status()).toBe(200)
  expect(response.request().postDataJSON()).toMatchObject({ symbols: ['AAPL'], event_types: ['earnings'], from_date: '2026-01-01', to_date: '2026-12-31' })
  const payload = await response.json()
  const download = await downloading
  expect(download.suggestedFilename()).toBe(payload.filename)
  const stream = await download.createReadStream()
  expect(stream).toBeTruthy()
  const chunks: Buffer[] = []
  for await (const chunk of stream!) chunks.push(Buffer.from(chunk))
  const content = Buffer.concat(chunks).toString('utf8')
  expect(content).toBe(payload.content)
  expect(content).toMatch(/^BEGIN:VCALENDAR\r?\n/)
  expect(content).toContain('VERSION:2.0')
  expect(content.trimEnd()).toMatch(/END:VCALENDAR$/)
  expect((content.match(/BEGIN:VEVENT/g) || []).length).toBe(payload.event_count)
  expect((content.match(/END:VEVENT/g) || []).length).toBe(payload.event_count)
  await expect(page.getByText('Export Complete!', { exact: true })).toBeVisible()
})
