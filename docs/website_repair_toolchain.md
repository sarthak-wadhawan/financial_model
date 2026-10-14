# Website repair — BUILD A/B/C evidence

Owner: GPT-6.1 Sol, 2026-10-14. Scope: styles and frontend startup/package/test-toolchain configuration only. No commit. Other owners retain pages, API, shared components and consolidated tests.

## Baseline (before any edits)

- Read START_HERE, status, active DAG 344+, requirements/architecture/roadmap and local repository/UI/accessibility/backend/test skills.
- Existing root-start API PID 4110955 owns 8000; existing Vite PIDs 4111146/3232425/3373517 own 5173/3001/3002. Preserve these processes. 3000 refused connection.
- Browser artifacts: `/tmp/opencode/website-toolchain/before.json`, `before-desktop.png` (1440×900), `before-mobile.png` (375×812). Chromium real 5173 runtime; CSS request 200, 38 rules, app-layout/header/metrics-grid display block, hero padding 0. Mobile scrollWidth 648. Console: React Router future warnings; no page exceptions. API overview claims operational/ready while symbols_tracked=0.
- Baseline logs in same directory: build-before.log PASS; tsc-before.log PASS; lint-before.log FAIL (31 errors); unit-before.log FAIL (five ERR_REQUIRE_ESM jsdom startup errors, no tests).
- Tracked node_modules caches and other dirty/untracked work pre-exist; never reset/stage them. Production DB untouched.

## Coordination / class contract

- Plain CSS, no Tailwind compiler. Existing semantic class names remain supported, including app/header/sidebar/footer, hero, section, grids/cards/tables, btn variants, modal, tabs, form, alert/toast, loading/error/empty states.
- Page owners may reuse `.section`, `.section-header`, `.metrics-grid`, `.metric-card`, `.features-grid`, `.feature-card`, `.impact-grid`, `.impact-card`, `.scenarios-grid`, `.scenario-card`, `.events-list`, `.event-item`, `.empty-state`, `.error-state`, `.muted`, `.form-group`, `.form-row`, `.btn` and existing variant names.
- Shared-component owner should prefer semantic classes; legacy finite utility names receive compatibility styles, not a broad utility pipeline. New semantic classes must be coordinated with C.
- Theme tokens honor explicit html/app `.light` and `.dark` regardless of system preference. Mobile sidebar becomes a wrapping navigation strip; no hidden critical navigation. Tables scroll within their containers.
- B owns package.json/lock/Vite/Playwright/Vitest config. Consolidated-test owner: request dependency changes through B, owns test bodies. B supplied the missing minimal setup after the dependency repair exposed that next blocker. jsdom 26 and normal forks replace the experimental VM/ESM workaround.

## Verification after repair

## Implemented / owned files

- `frontend/src/styles/index.css`: responsive shell and all existing semantic page/shared styles, black/white/green tokens, explicit themes, focus/skip link, menu/popover/dialog, bounded table scrolling, states, reduced-motion, finite legacy utility compatibility. Shared owner's new semantic badge/modal-size/term/menu classes also covered.
- `frontend/vite.config.ts`: strict 3000 dev/preview, loopback host and IPv4 API proxy (avoids localhost IPv6 ambiguity).
- `frontend/playwright.config.ts`: same explicit 3000; existing-server reuse requires `PLAYWRIGHT_REUSE_SERVER=1`, rather than silently using arbitrary stale code.
- `frontend/package.json`, `frontend/package-lock.json`, `frontend/.nvmrc`: jsdom 26.1, supported Node engine >=20.19, recommended Node 22 via nvm. Available temporary Node 20.17 was used for reproduction/verification; dependency installation warns about modern lint/type-package engine requirements. Do not confuse that temporary installation with a durable supported environment.
- `frontend/vitest.config.ts`, `frontend/vitest.config.minimal.ts`: normal forks, real shared setup; old minimal workaround now delegates to the real suite.
- `frontend/src/test/setup.tsx`: jest-dom/vitest, real RTL cleanup, matchMedia/ResizeObserver shims. No global fake API/router/query results and no restoration of the `.bak` mocks.

## Verified results (2026-10-14, concurrent integration snapshot)

All artifacts below are in `/tmp/opencode/website-toolchain/`. Commands ran from frontend with `PATH=/tmp/node-v20.17.0-linux-x64/bin:$PATH`.

| Check | Result / evidence |
|---|---|
| Normal-user API startup from root | Existing API preserved; second normal uvicorn command imports/starts lifespan, then exits 1 because 8000 already owned. `backend-start-before.log`. Existing read-only AAPL endpoint 500, overview operational/0 symbols, scanner empty reproduced before edits. |
| Frontend startup | `npm run dev -- --host 127.0.0.1 --port 3000 --strictPort` starts at 3000 (`vite-start.log`). Chromium also opened the user's exact `http://localhost:3000/` URL, found the hero, and fetched relative overview API with status 200. **Owned dev PID 472687 is left running for parent/browser owners.** Existing 5173/3001/3002/8000 processes not killed. |
| Strict-port regression | Second plain `npm run dev` exits 1 with `Port 3000 is already in use`; no alternate-port fallback (`strict-port.log`). |
| Production build / TypeScript | `npm run build` PASS; `npx tsc --noEmit` PASS (`build-final.log`, `tsc-final.log`). |
| Dev / preview proxy and production assets | 3000 read-only API proxy reachable. Preview tested on explicit isolated override 3004 (not claimed as default-port acceptance); JS/CSS assets and overview/scanner proxy 200. `proxy-preview-modal.json`, `preview-start.log`. Owned preview PID 494192 stopped afterward. |
| Lint | FAIL: 19 errors in MacroCalendarPage/API/types/safeExternalUrl at latest snapshot (`lint-final.log`), all outside A/B/C ownership; baseline 31. Rules not weakened. |
| Vitest executable | Startup repaired: real tests now execute, no ERR_REQUIRE_ESM/missing-setup failure. Latest full suite **85 passed / 43 failed, 9 files** (`unit-final.log`); five legacy page suites need query providers/updated assertions (LandingPage uses a local stand-in), not hidden mocks. |
| New actual-component suites | Targeted RepairPages + Phase11Repair + RepairComponents PASS: 11 tests (`unit-targeted.log`). These tests belong to other owners and were not edited by B. |
| Playwright config discovery | `npx playwright test --list` PASS: 171 tests/6 files. Discovery only, not E2E execution (`playwright-list.log`). Mutation-capable E2E requires the isolated backend harness; not run against production DB. |
| CSS browser assertions | PASS: desktop/mobile flex shell/header, real metrics grid, nonzero hero padding, opposite-system explicit light/dark tokens, mobile menu bounds, Settings no document overflow (`css-assertions.json`). Mobile width repaired from 648 to 375. |
| Real screenshot matrix | `capture-after.mjs`, `after.json`, `browser-after.log`, `after-<route>-<desktop/mobile>-<light/dark>.png` capture 9 routes × 2 viewports × 2 themes, console/network/computed styles. Every measured document width equals 1440 or 375 after Settings tab fix. Macro crash snapshots are **not** successful route evidence. Captures are concurrent integration snapshots, not L's final acceptance run. |
| Modal / theme interaction | Mobile real create-watchlist dialog opened without save/mutation: fixed flex overlay, dialog width 351, scrollWidth 375. Escape dismissed; theme click changed tokens and persisted across reload. `after-modal-mobile.png`, `proxy-preview-modal.json`; menu screenshot `after-mobile-menu.png`. |
| Owned diff | `git diff --check` PASS for package/config/CSS. No commit, no history changes, no production record mutation. Existing tracked node_modules caches were already dirty; npm/Vite also update generated dependency caches. Do not bulk-stage them. |

## Findings / handoff blockers

- `/macro`: runtime `getFilteredEvents is not a function` (hook/page contract, I/page owner); screenshot being overflow-free does not make a blank/crashed page acceptable.
- Existing API process still returns AAPL/other 500s and false ready/operational empty-data status. D/J must coordinate their own backend restart and final runtime verification; B never killed that pre-existing server.
- Settings uses `<option selected>` and emits a React warning; page owner must repair semantics. Shared ownership restrictions respected.
- Unit toolchain is executable but legacy tests still fail honestly; K must convert stand-ins and add real providers/fixtures without weakening assertions. Consolidated green gate remains outstanding.
- Snapshot CSS/port assertions PASS; meaningful phase acceptance remains PARTIAL until L/M/N/O independent review and semantic/API/test blockers are resolved. P owns START_HERE/status/DAG reconciliation; this document avoids conflicting concurrent edits to those files.

Graph summary: A reproduction completed before changes; B startup/toolchain implementation completed and locally verified, global lint/unit gates pending external owners; C implementation + computed-style/screenshot verification complete, final independent browser acceptance pending. Owner GPT-6.1 Sol; approximately 18:54–19:12 UTC (18 minutes); no retries that weakened tests, no Phase12 work.
