#!/usr/bin/env node
// Standalone harness: no package/config edits, no production database writes.
const fs = require('node:fs/promises')
const path = require('node:path')
const { spawn } = require('node:child_process')
const { randomUUID } = require('node:crypto')
const { chromium } = require('playwright')
const root = path.resolve(__dirname, '..')
const routes = [ ['dashboard', '/'], ['scanner', '/scanner'], ['stock', '/stocks/AAPL'], ['watchlists', '/watchlists'], ['calendar', '/calendar'], ['alerts', '/alerts'], ['search', '/search'], ['macro', '/macro'] ]
const origin = process.env.WEBSITE_REPAIR_FRONTEND_URL || 'http://127.0.0.1:3000'
const backend = process.env.WEBSITE_REPAIR_API_URL || 'http://127.0.0.1:18080'
const delay = ms => new Promise(resolve => setTimeout(resolve, ms))

async function serve() {
  const dir = await fs.mkdtemp('/tmp/opencode/website-repair-')
  const token = randomUUID()
  const url = new URL(backend)
  if (!['127.0.0.1', 'localhost'].includes(url.hostname)) throw new Error('Isolated server must bind loopback')
  const python = `
from pathlib import Path
import uvicorn
import backend.main as m
original = m.load_config
def isolated_config(*args, **kwargs):
    c = original(*args, **kwargs)
    c.events.db_path = Path(${JSON.stringify(path.join(dir, 'events.db'))})
    return c
m.load_config = isolated_config
@m.app.get('/__website_repair_isolation')
def marker():
    return {'isolated': True, 'token': ${JSON.stringify(token)}}
uvicorn.run(m.app, host='127.0.0.1', port=${Number(url.port || 18080)}, log_level='warning')
`
  const child = spawn(process.env.WEBSITE_REPAIR_PYTHON || 'python3', ['-c', python], {
    cwd: root, stdio: ['ignore', 'inherit', 'inherit'], env: { ...process.env, LLM_ENABLED: 'false', TRADING_COPILOT_DB_PATH: path.join(dir, 'events.db') },
  })
  const stop = () => child.kill('SIGTERM')
  process.once('SIGINT', stop)
  process.once('SIGTERM', stop)
  try {
    let ready = false
    for (let i = 0; i < 100; i++) {
      if (child.exitCode !== null) throw new Error(`Isolated backend exited ${child.exitCode}`)
      try {
        const response = await fetch(`${backend}/__website_repair_isolation`)
        const marker = await response.json()
        if (marker.token === token) { ready = true; break }
        throw new Error('Port occupied by a different backend')
      } catch (error) {
        if (error.message.includes('occupied')) throw error
      }
      await delay(200)
    }
    if (!ready) throw new Error('Isolated backend readiness timeout')
    const envFile = path.join(dir, 'environment.sh')
    await fs.writeFile(envFile, `export WEBSITE_REPAIR_API_URL='${backend}'\nexport WEBSITE_REPAIR_ISOLATION_TOKEN='${token}'\nexport WEBSITE_REPAIR_FRONTEND_URL='${origin}'\n`)
    console.log(`Isolated backend ready; DB: ${path.join(dir, 'events.db')}\nIn another terminal: source ${envFile}\nLeave this process running during tests. No event/trigger fixtures inserted.`)
    await new Promise((resolve, reject) => {
      child.once('exit', code => code && code !== 0 ? reject(new Error(`Backend exited ${code}`)) : resolve())
      child.once('error', reject)
    })
  } finally { stop() }
}

async function capture() {
  if (process.env.WEBSITE_REPAIR_IMPLEMENTATION_COMPLETE !== '1') {
    throw new Error('Final screenshots gated: set WEBSITE_REPAIR_IMPLEMENTATION_COMPLETE=1 only after implementation handoff')
  }
  const out = await fs.mkdtemp('/tmp/opencode/website-repair-browser-')
  const browser = await chromium.launch({ headless: true })
  const report = { generatedAt: new Date().toISOString(), origin, backend, browser: browser.version(), label: 'Evidence only; independent review required', cases: [] }
  try {
    // Real runtime is never intercepted. Empty data is the real disposable DB,
    // not fabricated records. Provider failures are explicitly mocked transport.
    for (const state of ['real-runtime', 'isolated-empty', 'MOCKED-provider-error']) {
      if (state !== 'real-runtime') {
        const response = await fetch(`${backend}/__website_repair_isolation`)
        const marker = await response.json()
        if (!process.env.WEBSITE_REPAIR_ISOLATION_TOKEN || marker.token !== process.env.WEBSITE_REPAIR_ISOLATION_TOKEN || !marker.isolated) {
          throw new Error('Empty/mocked matrix requires verified disposable backend')
        }
      }
      for (const viewportName of ['desktop', 'mobile']) {
        const viewport = viewportName === 'desktop' ? { width: 1440, height: 1000 } : { width: 375, height: 812 }
        for (const theme of ['light', 'dark']) {
          // All primary desktop pages plus search/macro; dashboard + stock mobile.
          for (const [name, routePath] of routes.filter(([n]) => viewportName === 'desktop' || ['dashboard', 'stock'].includes(n))) {
            const context = await browser.newContext({ viewport, colorScheme: theme, isMobile: viewportName === 'mobile', hasTouch: viewportName === 'mobile' })
            await context.addInitScript(t => localStorage.setItem('theme', t), theme)
            const page = await context.newPage()
            const item = { state, name, routePath, viewport, theme, errors: [], consoleErrors: [], failedRequests: [], responses: [], mockedPaths: [], interactions: [], screenshot: null }
            report.cases.push(item)
            const safeURL = value => { const u = new URL(value); return `${u.origin}${u.pathname}` }
            page.on('pageerror', error => item.errors.push(error.message))
            page.on('console', message => { if (message.type() === 'error') item.consoleErrors.push(message.text()) })
            page.on('requestfailed', req => item.failedRequests.push({ url: safeURL(req.url()), failure: req.failure()?.errorText }))
            page.on('response', response => item.responses.push({ url: safeURL(response.url()), status: response.status(), resource: response.request().resourceType() }))
            if (state !== 'real-runtime') {
              await page.route('**/api/v1/**', async route => {
                const u = new URL(route.request().url())
                // Read-only even if a page tries an unexpected startup mutation.
                if (!['GET', 'HEAD'].includes(route.request().method())) return route.fulfill({ status: 405, json: { detail: 'Capture harness is read-only' } })
                if (state === 'MOCKED-provider-error' && /^\/api\/v1\/(market|scanner|stocks|events)/.test(u.pathname)) {
                  item.mockedPaths.push(u.pathname)
                  return route.fulfill({ status: 503, json: { detail: 'MOCKED screenshot provider failure; not a real provider observation' } })
                }
                const response = await route.fetch({ url: `${backend}${u.pathname}${u.search}` })
                await route.fulfill({ response })
              })
            }
            try {
              const started = Date.now()
              await page.goto(`${origin}${routePath}`, { waitUntil: 'domcontentloaded' })
              await page.locator('h1').first().waitFor({ timeout: 15000 })
              // Bounded stabilization; networkidle may time out on retrying errors.
              await page.waitForLoadState('networkidle', { timeout: 10000 }).catch(() => item.interactions.push('networkidle timeout: inspect pending requests'))
              await page.evaluate(() => document.fonts.ready)
              item.durationMs = Date.now() - started
              item.dom = await page.evaluate(() => {
                const style = element => { if (!element) return null; const c = getComputedStyle(element); return { display: c.display, padding: c.padding, color: c.color, background: c.backgroundColor, gridTemplateColumns: c.gridTemplateColumns } }
                return { title: document.title, headings: [...document.querySelectorAll('h1,h2,h3')].map(e => e.textContent), mainCount: document.querySelectorAll('main').length, width: innerWidth, scrollWidth: document.documentElement.scrollWidth, overflow: document.documentElement.scrollWidth > innerWidth + 1, themeClass: document.documentElement.className, app: style(document.querySelector('.app')), content: style(document.querySelector('.app-content')), card: style(document.querySelector('.card,.impact-card,.watchlist-card')), text: document.body.innerText }
              })
              // Document individual endpoints used, not only status=200. Safe payload
              // projections avoid persisting account notes or arbitrary API fields.
              item.renderedHonesty = { invalidNumber: /NaN|undefined|Invalid Date/.test(item.dom.text), unavailableVisible: /unavailable|missing|no .*|failed|error/i.test(item.dom.text) }
              const filename = `${state}-${viewportName}-${theme}-${name}.png`
              if (state.startsWith('MOCKED')) await page.evaluate(() => {
                const label = document.createElement('div'); label.textContent = 'MOCKED PROVIDER ERROR — NOT REAL RUNTIME'; label.style.cssText = 'position:fixed;top:0;right:0;z-index:2147483647;background:#fff;color:#900;padding:8px;font:14px sans-serif;border:2px solid #900'; document.body.append(label)
              })
              item.screenshot = path.join(out, filename)
              await page.screenshot({ path: item.screenshot, fullPage: true })
              // Additional read-only dialog/evidence/term states, if available.
              const details = page.locator('details').first()
              if (await details.count()) {
                await details.locator('summary').click()
                await page.screenshot({ path: path.join(out, `${state}-${viewportName}-${theme}-${name}-expanded.png`), fullPage: true })
                item.interactions.push('first disclosure expanded')
              }
              const openDialog = page.getByRole('button', { name: /^(Create Watchlist|Create Alert|Export Calendar)$/ }).first()
              if (await openDialog.count()) {
                await openDialog.click()
                await page.getByRole('dialog').waitFor({ timeout: 3000 })
                await page.screenshot({ path: path.join(out, `${state}-${viewportName}-${theme}-${name}-dialog.png`), fullPage: true })
                item.interactions.push('dialog opened without submission')
                await page.keyboard.press('Escape')
              }
            } catch (error) { item.errors.push(`Capture: ${error.message}`) }
            finally { await context.close(); await fs.writeFile(path.join(out, 'metadata.json'), JSON.stringify(report, null, 2)) }
          }
        }
      }
    }
  } finally { await browser.close(); console.log(`Evidence directory: ${out}`) }
  // Not an approval: obvious browser/layout failures make the harness nonzero.
  if (report.cases.some(c => c.errors.length || c.dom?.overflow)) process.exitCode = 1
}

async function runTests() {
  const dir = await fs.mkdtemp('/tmp/opencode/website-repair-runner-')
  // The shared B-owned config intentionally rejects a pre-existing dev server.
  // This ephemeral config explicitly tests the selected already-running runtime.
  const config = path.join(dir, 'playwright.config.cjs')
  const playwright = path.join(__dirname, 'node_modules/@playwright/test')
  await fs.writeFile(config, `const { defineConfig, devices } = require(${JSON.stringify(playwright)}); module.exports = defineConfig({ testDir: ${JSON.stringify(path.join(__dirname, 'src/test/e2e'))}, testMatch: 'website-repair.spec.ts', outputDir: ${JSON.stringify(path.join(dir, 'results'))}, workers: 1, retries: 0, reporter: 'line', use: { baseURL: ${JSON.stringify(origin)}, screenshot: 'only-on-failure', trace: 'retain-on-failure' }, projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }, { name: 'mobile-chrome', use: { ...devices['Pixel 5'] } }] });`)
  const response = await fetch(origin)
  if (!response.ok) throw new Error('Selected frontend runtime is not reachable')
  console.log(`Explicit runtime: ${origin}; temporary runner artifacts: ${dir}`)
  const child = spawn(process.execPath, [path.join(__dirname, 'node_modules/@playwright/test/cli.js'), 'test', '--config', config, ...process.argv.slice(process.argv.indexOf('--test') + 1)], { cwd: __dirname, stdio: 'inherit', env: process.env })
  process.exitCode = await new Promise((resolve, reject) => { child.once('error', reject); child.once('exit', code => resolve(code === null ? 1 : code)) })
}

async function main() {
  if (process.argv.includes('--serve-isolated')) return serve()
  if (process.argv.includes('--capture')) return capture()
  if (process.argv.includes('--test')) return runTests()
  console.log(JSON.stringify({ status: 'PREPARED; capture not run', origin, backend, desktop: routes, mobile: ['dashboard', 'stock'], themes: ['light', 'dark'], states: ['real-runtime', 'isolated-empty', 'MOCKED-provider-error'], commands: ['--serve-isolated', '--test [Playwright options]', '--capture (implementation-complete gate required)'] }, null, 2))
}
main().catch(error => { console.error(error.message); process.exitCode = 1 })
