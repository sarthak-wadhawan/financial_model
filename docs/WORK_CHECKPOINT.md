# Trading Copilot — portable UX checkpoint

## Resume
- Branch: **`work/trading-copilot-ux`**. No main merge, Phase12, retraining or live trading.
- Exact checkpoint SHA: `git log -1 --format=%H -- docs/WORK_CHECKPOINT.md` (a commit cannot embed its own hash).
- Last verified source push: `e6371260e019e631a03eed692d99cc770f485fbd` (SEC retry budget). Earlier recovery WIP `9855c4ba`, UX1 `e86624d6`, chart integration `0564696f`. All were pushed; remote SHAs confirmed for recovery/source checkpoints.
- Resume command: `git fetch origin && git switch work/trading-copilot-ux && git pull --ff-only origin work/trading-copilot-ux`; preserve local changes before switching. Read the existing UX section of `current_task_graph.md`; do not recreate the DAG.

## Completed / verified
- **UX0 plan/recovery**, **UX1 shell/navigation/search/history/themes**, independently verified and pushed.
- **UX2a identity: PASS**, bounded to SEC-backed names, exchanges, CIK and attributed optional SIC facts. Malformed cache, singleflight and provenance defects fixed; unbounded SEC retry waits fixed. Provider/focused reviewer:103 tests +4 original reproductions PASS. Dedicated Security Reviewer:138 focused tests PASS. Counts overlap; do not add them.
- Normal stack was gracefully restarted with all reviewed backend fixes. Independent provider verified20 direct/proxied detail/search GETs for AAPL/MSFT/TMO/V/LLY. Parent Chromium verified all5 official company headings after restart, zero uncaught errors. Sector/description remain unknown, not invented.

## Incomplete / active
- **UX2b schedules/feed bridge, UX2c bars contract, UX2d per-symbol coverage remain open. Full UX2 is NOT PASS.** Source investigation is saved in `UX_DATA_CONTRACT_AUDIT.md`.
- **UX3a/b chart implementation/integration exists**, including Lightweight Charts5.2.1 and real daily range requests. Initial real-browser review verified all5 symbols/ranges and interactions but returned PARTIAL on presentation/provider link/touch guidance.
- Chart polish is implemented but **not independently accepted yet**: collapsed source details/link, coordinated palette, touch guidance, horizontal mobile tabs, truthful updated E2E identity-heading assertions.38 targeted chart/StockPage tests, TS/scoped lint PASS. Current uncommitted chart files: component TSX/CSS/test, StockPage.css, e2e stock-page.spec.ts and normal-runtime.spec.ts. Preserve; do not rebuild.
- Current agent: chart Reviewer `ses_eb8ff6435ffe0RH53KNvHUC0qe` performing narrow recheck. Other prior BUILD/audit sessions are finished. Session IDs are machine-local; repository files are the portable memory.
- **UX4–UX9 and remaining stock-summary/earnings/actions requirements remain incomplete.** No overall overhaul completion claim or final broad regression yet.

## Exact next action
1. Push this verified UX2a/checkpoint update and confirm remote SHA.
2. Consume chart recheck; fix only findings. Selectively checkpoint chart code/tests and truthful leaf status, then push/verify.
3. Continue existing UX2c bounded bars/range metadata and UX2b schedule-source implementation with nonoverlapping ownership. Keep main.py edits serialized. Maximum2 agents. Independent provider/security/reviewer gates before node PASS.
4. One broad regression near final UX8 only; preserve valid targeted evidence now.

## Runtime / evidence / limits
- Normal app is running from `npm --prefix frontend run dev`, Node22.23.3/Python3.10, loopback3000→8000, intended original database; no test/demo override. Log `/tmp/opencode/ux-identity-verified-dev.log`. Do not start a second backend. After reboot start this single command; installs per START_HERE.
- Evidence `/tmp/opencode/ux-identity-restarted-runtime.json`, `ux-identity-final-browser.json`, `/tmp/opencode/ux-chart-review/` is local/temporary, not portable proof by itself. Permanent source/tests and audit contracts are committed; no private artifacts in Git.
- Prior chart BUILD connection refusal occurred during the controlled parent restart; the app is now running. This is not an unresolved provider failure.
- BLS/news external limits persist. V official announcement verifies2026-10-27 AMC; TMO2026-10-21 is an earnings **call only**. Not yet bridged into next-earnings API. Daily-only/raw/IEX chart cannot fabricate1D intraday or all-lifetime coverage.
- Original DB, `.env`, caches, node_modules/dist/logs and unrelated user scripts remain excluded/preserved. Local skills are untracked user files; portable task contracts are in the DAG. No blanket add/reset/cleanup.
- Referenced `MODEL_AND_DEPLOYMENT_ARCHITECTURE.md` is absent. Requested `model-a-prototype` path absent; sibling `model-a` README/artifact names inspected read-only, no model loaded/copied/validated or predictions enabled.
