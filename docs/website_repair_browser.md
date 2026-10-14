# Website repair K/L browser harness — prepared, not approved

Scope: new regression file and standalone capture script only. Local test-generation,
frontend-ui-audit and accessibility-responsive-audit skills and active DAG K/L read.
No application/config/package edits, no commit, no final screenshots yet. Other
workers own implementation; parent owns status/START_HERE reconciliation.

## Discovery and execution

Actual current `frontend/playwright.config.ts` testDir is `./src/test/e2e`, so the
new spec is `frontend/src/test/e2e/website-repair.spec.ts`, not an undiscovered
`frontend/e2e` file. Existing startup currently points at 3001; B owns alignment.
The spec explicitly targets 3000 (override `WEBSITE_REPAIR_FRONTEND_URL` only for
an intentional runtime). Do not treat the existing config's fallback port as approval.

From `frontend/`, with Node/npm available:

```bash
node website_repair_capture.cjs                  # print planned matrix; no capture
node website_repair_capture.cjs --serve-isolated # leave running
```

The second command starts a new loopback Python backend on 18080 with a unique
`/tmp/opencode/website-repair-*/events.db`. It overrides only the in-process
configuration loader **before lifespan**; all event/watchlist/alert stores currently
share `config.events.db_path`. No SQLite connection, SQL, event writes, trigger writes,
or production DB copy occurs in the harness. Its temporary environment file is printed.
Use `source /tmp/opencode/website-repair-<printed-id>/environment.sh` in another terminal.
An already occupied backend cannot pass the random isolation token handshake.
Ctrl-C stops the disposable backend; artifacts remain for inspection.

```bash
npx playwright test website-repair.spec.ts --project=chromium --project=mobile-chrome --workers=1
# Explicit already-running runtime; temporary config/results outside repository:
node website_repair_capture.cjs --test
# Only AFTER the implementation workers finish and B fixes startup:
WEBSITE_REPAIR_IMPLEMENTATION_COMPLETE=1 node website_repair_capture.cjs --capture
```

Python defaults to `python3`, overridable with `WEBSITE_REPAIR_PYTHON`. Backend imports
and installed dependencies must already work. The isolated server retains the current
provider configuration; it is **not a synthetic market-data server** and does not
refresh providers, initiate paid services or trade. LLM is disabled.

`--test` creates only an ephemeral `/tmp/opencode/website-repair-runner-*` config,
with desktop/mobile Chromium, traces and failure screenshots. It does not start or
reuse a server silently: the explicit frontend URL must already be running, and its
URL/artifact directory is printed. Extra arguments after `--test` go to Playwright.
This supports preliminary runs when the shared strict-port startup rejects an
already-occupied port; it does not replace B's final startup verification.

## Regression contracts

- Dashboard accessible search → AAPL stock → real Phase 9 response comparison,
  distinct company/stock impact, scenarios, missing-information rendering and honest
  missing price. Unhandled page errors/NaN/overflow/duplicate main landmarks fail.
- Watchlist UI create/read, symbol notes, default update, reload persistence,
  symbol removal, UI deletion; supported API verification/owned-ID cleanup only.
- Alert UI create/delete, active toggle reload persistence, UI dry-run with actual
  API response; trigger count and last-trigger time must remain unchanged.
- Calendar UI filtered export and downloaded ICS content/filename/count matching
  actual response, including valid empty calendar. No fabricated scheduled events.
- **MOCKED transport only:** trigger acknowledgement state and provider failure.
  These are UI regressions, not claims that real trigger ingestion or provider failure
  was observed. Real acknowledgement workflow is blocked by absence of a supported
  API for seeding/evaluating triggers in the fresh database. Do not insert SQLite rows
  or pretend dry-run creates notifications. Parent/H must supply supported setup if
  full real-trigger acknowledgement evidence is required.

## Screenshot evidence

Desktop 1440×1000: dashboard, scanner, stock, watchlists, calendar, alerts (plus
search/macro). Mobile 375×812: dashboard/stock. Each runs dark/light in:

1. `real-runtime`: actual frontend/backend routing, no interception; read-only.
2. `isolated-empty`: requests forwarded to the verified fresh backend, actual empty
   event/user stores; market providers can still return real data or be unavailable.
3. `MOCKED-provider-error`: market/scanner/stock/event requests receive explicitly
   mocked 503 responses; other reads use the isolated backend. Each PNG contains a
   visible mock banner. Not evidence of an actual external provider outage.

Files are uniquely written under `/tmp/opencode/website-repair-browser-*`, separate
from prior `frontend/screenshots`. Additional disclosure/dialog screenshots are
captured where controls exist; dialogs never submitted. `metadata.json` records URL,
timestamp, Chromium version, viewport/theme/state, screenshot paths, headings,
computed shell/card CSS, main landmarks, overflow, visible text, page/console errors,
network statuses/failures and mocked paths. Query strings are excluded from network
URLs. Screenshots/text can contain normal runtime user content: keep local and review
before sharing. No API credentials or environment dump is recorded.

Nonzero capture exit indicates page errors or overflow, **not** a complete audit.
Console/network failures, theme correctness, contrast, keyboard focus, tap term UX,
exact backend values and before/after screenshots still need independent review.
The empty DB cannot substantiate populated evidence/ICS/reorder workflows; real
runtime and additional supported fixtures must cover those before L approval.

## Preparation status

Prepared only. Final run waits B/C/D/E/F/G/H/I/J completion; no PASS/approval claim.
Frozen API v1 read from `docs/website_api_contract.md`. Preliminary commands/results
are reported in the subagent handoff, not historical project completion documents.

Preliminary verification: Node syntax and dry matrix succeed; shared configuration
discovers 18 cases. Initial targeted calendar/explicitly mocked acknowledgement run:
4 passed. Full disposable desktop/mobile run: 8 passed, 4 failed; artifacts
`/tmp/opencode/website-repair-runner-IHu8Dj`. The watchlist detail link navigated to
the app 404 (missing App route, I-owned). Alert dry-run correctly returned nullable
`would_trigger` with unavailable status per H's updated model; the test was corrected
to require null, explicit missing AAPL/current-values-empty/UI unavailable for that
contract, not false reassurance. Targeted alert rerun subsequently passed both desktop
and mobile (2 passed, `/tmp/opencode/website-repair-runner-9fXADI`). Earlier broad
failures from changed button labels were corrected to the actual repaired semantic
controls. Full rerun remains pending; this runtime was actively changing during
implementation. Node syntax/diff whitespace checks pass. The owned disposable
backend was stopped after preliminary testing. No final capture ran.
