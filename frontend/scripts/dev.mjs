// Canonical local startup: npm run dev (from frontend/).
// Never load backend .env into Node/Vite, reuse an API, or alter the database path.
import { spawn } from 'node:child_process'
import { createServer } from 'node:net'
import { fileURLToPath } from 'node:url'
import { resolve } from 'node:path'
import { setTimeout as delay } from 'node:timers/promises'

export const frontend = fileURLToPath(new URL('../', import.meta.url))
export const root = resolve(frontend, '..')
const installHint = "From the repository root run: python3 -m pip install -e '.[web,dev]'. Set PYTHON to that interpreter if needed."

export function validateArgs(args) {
  // Playwright's existing webServer command passes these exact Vite flags.
  for (let i = 0; i < args.length; i++) {
    const arg = args[i]
    if (arg === '--strictPort') continue
    if (arg === '--host' && args[++i] === '127.0.0.1') continue
    if (arg === '--port' && args[++i] === '3000') continue
    throw new Error('Dev startup uses fixed loopback ports. Use npm run dev without overrides.')
  }
}

export function assertPortFree(port) {
  return new Promise((resolvePromise, reject) => {
    const server = createServer()
    server.once('error', () => reject(new Error(
      `127.0.0.1:${port} is unavailable. Identify and stop its owner explicitly, then rerun npm run dev. No existing process was reused or stopped.`,
    )))
    server.listen({ host: '127.0.0.1', port, exclusive: true }, () => server.close(resolvePromise))
  })
}

export async function apiHealthy(url, request = fetch) {
  try {
    const response = await request(url, { signal: AbortSignal.timeout(1500) })
    if (!response.ok) return false
    const body = await response.json()
    return ['ready', 'degraded'].includes(body.status)
      && body.database === 'connected' && body.event_store === 'connected'
      && body.llm_enabled === false
  } catch {
    return false
  }
}

export async function runDev({
  args = [], env = process.env, launch = spawn, portFree = assertPortFree,
  healthy = apiHealthy, sleep = delay, log = console.log, signals = process,
  startupTimeout = 60000, monitorInterval = 5000, shutdownTimeout = 5000,
} = {}) {
  validateArgs(args)
  // Check both before spawning anything; unknown listeners are never adopted.
  await portFree(8000)
  await portFree(3000)
  const children = []
  let stopping = false
  let failure
  let interrupted = false
  let notifyStop
  const stopped = new Promise(resolvePromise => { notifyStop = resolvePromise })
  const waitController = new AbortController()
  const stop = () => {
    stopping = true
    notifyStop()
    waitController.abort()
  }
  const wait = promise => Promise.race([promise, stopped])
  const pause = ms => wait(sleep(ms, undefined, { signal: waitController.signal }))
  const handlers = ['SIGINT', 'SIGTERM'].map(signal => {
    const handler = () => { interrupted = true; stop() }
    signals.on(signal, handler)
    return [signal, handler]
  })
  const start = (name, command, argv, options) => {
    const child = launch(command, argv, { stdio: 'inherit', ...options })
    const record = { child, exited: false }
    children.push(record)
    child.once('error', () => {
      record.exited = true
      failure = new Error(`${name} could not start. ${installHint}`)
      stop()
    })
    child.once('exit', (code, signal) => {
      record.exited = true
      if (!stopping) {
        failure = new Error(`${name} exited (${signal || code}). ${name === 'Backend' ? installHint : 'Run npm ci in frontend/ and retry.'}`)
        stop()
      }
    })
  }
  const check = () => {
    if (failure) throw failure
    return !stopping
  }
  try {
    start('Backend', env.PYTHON || 'python3', ['-m', 'backend.main'], {
      cwd: root, env: { ...env, WEB_API_HOST: '127.0.0.1', LLM_ENABLED: 'false' },
    })
    const deadline = Date.now() + startupTimeout
    const healthURL = 'http://127.0.0.1:8000/api/v1/health/detailed'
    let ready = false
    while (check()) {
      ready = await wait(healthy(healthURL))
      if (!check() || ready) break
      if (Date.now() >= deadline) throw new Error(`Backend health timed out on port 8000; Vite was not started. Check backend logs. ${installHint}`)
      await pause(250)
    }
    if (!check()) return interrupted ? 0 : 1
    if (!ready) throw new Error('Backend is unavailable; Vite was not started.')
    log('[dev] Backend ready on http://127.0.0.1:8000 (provider degradation is reported separately).')
    start('Vite', process.execPath, [resolve(frontend, 'node_modules/vite/bin/vite.js'), '--host', '127.0.0.1', '--port', '3000', '--strictPort'], {
      cwd: frontend, env: { ...env },
    })
    let consecutiveFailures = 0
    const failureThreshold = 3
    while (check()) {
      await pause(monitorInterval)
      if (!check()) break
      const healthyNow = await wait(healthy(healthURL))
      if (!check()) break
      if (healthyNow) {
        if (consecutiveFailures) log('[dev] Backend health recovered; consecutive failure count reset. Dev servers remain running.')
        consecutiveFailures = 0
      } else {
        consecutiveFailures++
        log(`[dev] Backend health probe failed (${consecutiveFailures}/${failureThreshold}); API may be busy. Check backend logs; retrying before stopping owned servers.`)
        if (consecutiveFailures >= failureThreshold) throw new Error('Backend health lost after 3 consecutive failed probes; stopping owned dev servers. Check backend logs and rerun npm run dev.')
      }
    }
    check()
    return 0
  } finally {
    stop()
    await Promise.all(children.map(async record => {
      if (record.exited) return
      const exited = new Promise(resolvePromise => record.child.once('exit', resolvePromise))
      record.child.kill('SIGTERM')
      let timer
      await Promise.race([exited, new Promise(resolvePromise => { timer = setTimeout(resolvePromise, shutdownTimeout) })])
      clearTimeout(timer)
      if (!record.exited) record.child.kill('SIGKILL')
    }))
    for (const [signal, handler] of handlers) signals.removeListener(signal, handler)
  }
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  runDev({ args: process.argv.slice(2) }).then(code => { process.exitCode = code }).catch(error => {
    console.error(`[dev] ${error.message}`)
    process.exitCode = 1
  })
}
