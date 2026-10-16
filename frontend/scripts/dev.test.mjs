import test from 'node:test'
import assert from 'node:assert/strict'
import { EventEmitter } from 'node:events'
import { readFile } from 'node:fs/promises'
import { apiHealthy, runDev, root, frontend, validateArgs } from './dev.mjs'

function harness(overrides = {}) {
  const signals = new EventEmitter()
  const calls = []
  const options = {
    signals, args: [], env: { PYTHON: '/selected/python', TRADING_COPILOT_DB_PATH: '/explicit/events.db' },
    portFree: async () => {}, log: () => {}, healthy: async () => true,
    sleep: async () => { signals.emit('SIGTERM') },
    launch: (command, args, opts) => {
      const child = new EventEmitter()
      child.kill = signal => { child.kills.push(signal); child.emit('exit', 0, signal) }
      child.kills = []
      calls.push({ command, args, opts, child })
      return child
    },
    ...overrides,
  }
  return { calls, options, signals }
}

test('canonical startup gates Vite on API health, preserves DB, cleans only children', async () => {
  const h = harness()
  h.options.healthy = async () => { assert.equal(h.calls.length, 1); return true }
  assert.equal(await runDev(h.options), 0)
  assert.equal(h.calls.length, 2)
  assert.equal(h.calls[0].command, '/selected/python')
  assert.deepEqual(h.calls[0].args, ['-m', 'backend.main'])
  assert.equal(h.calls[0].opts.cwd, root)
  assert.equal(h.calls[0].opts.env.WEB_API_HOST, '127.0.0.1')
  assert.equal(h.calls[0].opts.env.LLM_ENABLED, 'false')
  assert.equal(h.calls[0].opts.env.TRADING_COPILOT_DB_PATH, '/explicit/events.db')
  assert.equal(h.calls[1].opts.cwd, frontend)
  assert.deepEqual(h.calls[1].args.slice(1), ['--host', '127.0.0.1', '--port', '3000', '--strictPort'])
  assert.ok(h.calls.every(call => call.child.kills.join() === 'SIGTERM'))
  assert.equal(h.signals.listenerCount('SIGTERM'), 0)
})

test('normal startup never substitutes a temporary database', async () => {
  const h = harness({ env: {} })
  await runDev(h.options)
  assert.equal('TRADING_COPILOT_DB_PATH' in h.calls[0].opts.env, false)
})

test('occupied port refuses adoption before launching any child', async () => {
  const h = harness({ portFree: async port => { if (port === 8000) throw new Error('occupied') } })
  await assert.rejects(runDev(h.options), /occupied/)
  assert.equal(h.calls.length, 0)
})

test('backend startup failure is actionable and never launches Vite', async () => {
  const h = harness({ healthy: async () => false })
  h.options.sleep = async () => { h.calls[0].child.emit('exit', 1, null) }
  await assert.rejects(runDev(h.options), /Backend exited.*pip install/)
  assert.equal(h.calls.length, 1)
})

test('backend timeout stops owned backend without starting Vite', async () => {
  const h = harness({ healthy: async () => false, startupTimeout: 0 })
  await assert.rejects(runDev(h.options), /health timed out/)
  assert.equal(h.calls.length, 1)
  assert.deepEqual(h.calls[0].child.kills, ['SIGTERM'])
})

test('missing Python fails clearly without Vite or signaling an unstarted child', async () => {
  const h = harness({ healthy: async () => false })
  h.options.sleep = async () => { h.calls[0].child.emit('error', new Error('ENOENT')) }
  await assert.rejects(runDev(h.options), /Backend could not start.*PYTHON/)
  assert.equal(h.calls.length, 1)
  assert.deepEqual(h.calls[0].child.kills, [])
})

test('Vite failure also stops the owned backend', async () => {
  const h = harness()
  h.options.sleep = async () => { h.calls[1].child.emit('exit', 1, null) }
  await assert.rejects(runDev(h.options), /Vite exited/)
  assert.deepEqual(h.calls[0].child.kills, ['SIGTERM'])
  assert.deepEqual(h.calls[1].child.kills, [])
})

test('shutdown escalates only a nonresponsive owned child', async () => {
  const h = harness({ shutdownTimeout: 1 })
  const launch = h.options.launch
  h.options.launch = (...args) => {
    const child = launch(...args)
    child.kill = signal => {
      child.kills.push(signal)
      if (signal === 'SIGKILL') child.emit('exit', 0, signal)
    }
    return child
  }
  await runDev(h.options)
  assert.ok(h.calls.every(call => call.child.kills.join() === 'SIGTERM,SIGKILL'))
})

test('runtime health loss tears down both owned children', async () => {
  let checks = 0
  const h = harness({ healthy: async () => ++checks === 1, sleep: async () => {} })
  await assert.rejects(runDev(h.options), /health lost after 3 consecutive failed probes/)
  assert.equal(checks, 4) // One startup success, then three monitor failures.
  assert.ok(h.calls.every(call => call.child.kills.join() === 'SIGTERM'))
})

test('transient timeouts recover and reset the consecutive failure threshold', async () => {
  // Each false represents a completed/timeout health probe, not a child exit.
  const results = [true, false, false, true, false, false, true]
  const logs = []
  let checks = 0
  const h = harness({ log: message => logs.push(message) })
  h.options.healthy = async () => results[checks++]
  h.options.sleep = async () => {
    assert.ok(h.calls.every(call => call.child.kills.length === 0), 'no premature cleanup')
    if (checks === results.length) h.signals.emit('SIGTERM')
  }
  assert.equal(await runDev(h.options), 0)
  assert.equal(checks, results.length)
  assert.equal(logs.filter(line => line.includes('health recovered')).length, 2)
  assert.equal(logs.filter(line => line.includes('(1/3)')).length, 2)
  assert.equal(logs.some(line => line.includes('(3/3)')), false)
  assert.ok(h.calls.every(call => call.child.kills.join() === 'SIGTERM'))
})

test('actual backend exit interrupts a pending monitor probe without health grace', async () => {
  let checks = 0
  const h = harness({ sleep: async () => {} })
  h.options.healthy = async () => {
    if (++checks === 1) return true
    h.calls[0].child.emit('exit', 1, null)
    return new Promise(() => {})
  }
  await assert.rejects(runDev(h.options), /Backend exited/)
  assert.equal(checks, 2)
  assert.deepEqual(h.calls[1].child.kills, ['SIGTERM'])
})

test('signal interrupts a pending monitor sleep without waiting for another probe', async () => {
  const h = harness()
  h.options.sleep = async () => {
    h.signals.emit('SIGINT')
    return new Promise(() => {})
  }
  assert.equal(await runDev(h.options), 0)
  assert.ok(h.calls.every(call => call.child.kills.join() === 'SIGTERM'))
})

test('health validates initialized persistence and accepts honest provider degradation', async () => {
  const request = body => async () => ({ ok: true, json: async () => body })
  for (const status of ['ready', 'degraded']) {
    assert.equal(await apiHealthy('unused', request({ status, database: 'connected', event_store: 'connected', llm_enabled: false })), true)
  }
  assert.equal(await apiHealthy('unused', request({ status: 'healthy' })), false)
  assert.equal(await apiHealthy('unused', async () => { throw new Error('refused') }), false)
})

test('Playwright flags remain compatible; overrides cannot expose listeners', () => {
  validateArgs(['--host', '127.0.0.1', '--port', '3000', '--strictPort'])
  assert.throws(() => validateArgs(['--host', '0.0.0.0']), /fixed loopback/)
  assert.throws(() => validateArgs(['--port', '3001']), /fixed loopback/)
})

test('normal npm dev and Vite proxy share the fixed backend contract', async () => {
  const pkg = JSON.parse(await readFile(new URL('../package.json', import.meta.url), 'utf8'))
  assert.equal(pkg.scripts.dev, 'node scripts/dev.mjs')
  const vite = await readFile(new URL('../vite.config.ts', import.meta.url), 'utf8')
  assert.match(vite, /target: 'http:\/\/127\.0\.0\.1:8000'/)
  assert.match(vite, /strictPort: true/)
})
