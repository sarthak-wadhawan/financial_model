import { mkdir, writeFile } from 'node:fs/promises'
import { spawnSync } from 'node:child_process'
import { fileURLToPath } from 'node:url'
import path from 'node:path'

// This runner deliberately has no webServer: the operator owns both listeners.
if (process.env.RUN_NORMAL_RUNTIME_SMOKE !== '1') {
  console.log('SKIPPED normal runtime smoke: set RUN_NORMAL_RUNTIME_SMOKE=1; start the documented normal backend and Vite first.')
  process.exit(0)
}
const frontend = fileURLToPath(new URL('../', import.meta.url))
const directory = '/tmp/opencode/runtime-integration-20261016'
await mkdir(directory, { recursive: true })
const config = path.join(directory, 'normal-runtime.playwright.config.mjs')
await writeFile(config, `export default ${JSON.stringify({
  testDir: path.join(frontend, 'src/test/e2e'),
  testMatch: 'normal-runtime.spec.ts',
  workers: 1,
  retries: 0,
  preserveOutput: 'never',
  timeout: 120000,
  expect: { timeout: 45000 },
  reporter: [['list']],
  outputDir: path.join(directory, 'playwright-output'),
  use: {
    baseURL: 'http://127.0.0.1:3000',
    browserName: 'chromium',
    viewport: { width: 1440, height: 1000 },
    // Normal DB can contain private user data: never retain HAR, traces or screenshots.
    trace: 'off', screenshot: 'off', video: 'off',
  },
})}\n`)
const result = spawnSync(process.execPath, [path.join(frontend, 'node_modules/@playwright/test/cli.js'), 'test', '--config', config], {
  cwd: frontend, env: process.env, stdio: 'inherit',
})
process.exit(result.status ?? 1)
