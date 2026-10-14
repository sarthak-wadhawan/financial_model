# Website repair acceptance boundaries — Phases 1–11

2026-10-14 · PLAN clarification for Shepherd/BUILD, **not a PASS audit**. No Phase 12, deployment, implementation changes, cleanup, staging or commit is authorized by this note. Shepherd owns `docs/current_task_graph.md`.

## Authority and missing document

- `docs/DEVELOPMENT_ROADMAP_UPDATED.md:117–122` requires watchlists, meaningful change alerts and `.ics` export; **scheduled refresh/notifications are later work**. The roadmap's Phase 14 covers deployment hardening. Do not require or build a hosted scheduler/email service to finish this local repair.
- `docs/FINAL_PRODUCT_REQUIREMENTS.md:305–357,385–393` requires usable website workflows and evidence/time fidelity; unavailable evidence must not become invented facts.
- `docs/MODEL_AND_DEPLOYMENT_ARCHITECTURE.md` is referenced by AGENTS/START_HERE but absent. Repository-wide filename discovery (including hidden paths), tracked-path inspection and a separate search under `trading-copilot/` found no alternative copy with that name/pattern.
- Existing related documents are `docs/SYSTEM_ARCHITECTURE_UPDATED.md`, `docs/02_SYSTEM_ARCHITECTURE.md`, `docs/PHASE7_ARCHITECTURE.md`, `docs/PHASE8_ARCHITECTURE.md`. These are **not a discovered substitute** for the missing model/deployment document. Do not invent its contents or claim approval based on its reference. Record the missing reference for documentation reconciliation.
- Guidance read: `skills/documentation-reconciliation/SKILL.md`, `skills/deployment-readiness-audit/SKILL.md`. This clarification does not update the authoritative roadmap or declare deployment readiness.

## Phase 11: honest local alerts, not promised delivery

| Capability | Required behavior / acceptable UI wording |
|---|---|
| Rule configuration | Create/edit/activate/deactivate/delete supported rules, validate type/condition combinations, preserve configuration across reload. Unsupported types must be explicitly unavailable or rejected, not silently accepted as working. |
| Local evaluation | Provide a real evaluation path using available backend observations, with observation time/source and evaluation time. Example: “Evaluate now — local backend; no background monitoring.” Do not imply continuous monitoring or closed-browser execution. |
| Meaningful changes | Supported threshold/change/crossing rules must actually evaluate their documented semantics; crossings require prior observations, not merely a current value above/below the threshold. Persist relevant state/cooldown and genuine triggers; expose history and acknowledgment. |
| Missing observations | Show “Cannot evaluate: current [price/event/etc.] unavailable” or “Previous observation required”; unknown is not “condition false,” “no changes” or “alert successful.” Stale observations must be labeled. |
| Dry run | Use the real evaluation logic without sending notifications or mutating trigger/cooldown/history state. Distinguish test result from a stored trigger. Never return a fabricated sample result as current evaluation. |
| In-app | Say “Stored in-app trigger/history” only when actual persistence works. Show last evaluation and “Not evaluated yet” when applicable. No claim of push delivery without a working channel. |
| Email/webhook | Display “Unavailable — delivery infrastructure not implemented” and disable/reject unsupported delivery choices. Existing configurations may remain visible with an unsupported-channel warning; saving them must not claim delivery. Never send a webhook/email just to prove the UI. |
| Scheduled monitoring | Say “Scheduled evaluation and external notifications are not available in this release.” These are deferred, not a hidden success claim. Local evaluation must still work; deferral is not permission to leave every alert path a stub. |

Watchlist CRUD/default/item notes/reordering must persist; calendar export must work with filters, source links and valid ICS. Preserve exact supplied times/timezones, date-only precision, and BMO/AMC descriptions. An undated event cannot be assigned today's date; a known date with unknown time can be all-day. An actual midnight timestamp is not automatically date-only. No fake external-channel delivery or generated financial values.

## Missing data versus mandatory runtime workflows

**Acceptable honest unavailability:** missing provider credentials, unsupported feed/instrument/session, genuinely absent source evidence or consensus, empty current date window, unavailable extended-hours data, unparsed leadership, or stale retained observations. Explain the specific limitation; expose available provenance/as-of timestamps; isolate failure by section; keep known zero values as zero. “Cause unclear” is better than unsupported attribution.

**Not acceptable as a finished workflow:** hard-coded dashes despite available backend data, TODO APIs returning empty arrays unconditionally, false “operational” health, broken API contracts, exceptions/500s on normal navigation, a chart never wired to bars, ignored filters, test records represented as live, or inaccessible/unstyled controls. An empty state is a rendering requirement, not evidence that ingestion or integration works.

Minimum runtime acceptance:
- Explicit/reproducible `localhost:3000` startup and working API proxy; no validation against an unrelated stale/alternate-port process.
- Styled responsive desktop/mobile navigation, forms, cards/tables, themes and keyboard/tap interactions; loading, empty, stale and provider-error states remain distinct.
- Search and direct stock navigation work outside scanner candidates. Home/stock/chart/scanner/event sections consume the actual agreed API contracts and display supported data, not frontend-generated financial truth.
- Reuse the deterministic scanner and Phase 9 interpretation/answer layer; show separate company/stock impacts, scenarios, change-view criteria and expandable evidence without claiming unsupported certainty.
- Working watchlist → stock → local alert evaluation/history → filtered calendar export workflow, including reload persistence, missing-data and invalid-input cases.
- Deterministic isolated fixtures may prove supported workflows offline **only when explicitly test/demo-labeled**. Real-provider smoke is separately gated and reported; demo data never silently fills live mode. A whole page showing unavailable data cannot alone prove its populated workflow.
- Tests must execute; real Chromium desktop/mobile screenshots and console/network/API checks complement build/lint/unit/API/E2E results. WebKit system-library failure can be documented separately, not generalized to app PASS. No LLM required (`LLM_ENABLED=false`), no trades or paid services.

## Preserve pre-session and concurrent work

At PLAN entry, these were already dirty: `data/events.db`, `docs/PROJECT_STATUS.md`, `docs/current_task_graph.md`; untracked `skills/`, `frontend/audit_screenshots.cjs`, `frontend/screenshots/`. PLAN subsequently appended the repair graph during its initial assignment. Preserve all of this and concurrent BUILD edits; do not infer ownership merely from current git status. Do not overwrite screenshot artifacts or delete DB test-looking records without an explicit, reviewed preservation plan. Use isolated test databases/artifacts.

## Safe eventual staging — recommendation only

Tracked-path inspection confirms **19,548 `frontend/node_modules/` files**, including **200 `.vite/` files**; also **34 `frontend/dist/` files**, **187 `artifacts/` files** and the events DB. `.gitignore` ignores artifacts but lacks frontend dependency/build exclusions; ignored paths already tracked remain tracked. Dependency repair is currently producing large tracked dependency/cache churn. Counts/status are a moving snapshot while BUILD runs, not a fixed release inventory. Index was empty at this inspection.

1. Never use `git add -A`, `git add .`, `git add frontend`, `git add -u`, or blanket generated-directory staging for this repair. Do not reset/restore/clean to obtain a “clean tree.” Generated unstaged churn can remain documented without entering the repair commit.
2. Shepherd inventories ownership and reviews exact changed paths/hunks after verification. Stage only named, intended source/test/config/docs files. Review dependency changes in `frontend/package.json` **together with** `frontend/package-lock.json`; reproduce their installation/build/tests in an isolated workspace before accepting them. Do not vendor thousands of installed package/cache mutations as a side effect.
3. For shared/pre-session documents, review and stage only agreed hunks (e.g. interactive `git add -p -- docs/PROJECT_STATUS.md` when appropriate). Do not include the DB, pre-existing audit script/screenshots or untracked skills merely because they are visible; obtain ownership/intent confirmation through Shepherd's ledger.
4. Before any later authorized commit, inspect `git diff --cached --name-status`, `git diff --cached --stat`, `git diff --cached --check` and the staged diff. Ensure no dependency/build/cache/database/credential paths slipped in. Verify package/lock reproducibility, not just the presently installed node_modules tree. Review secret findings by location/type without printing values.
5. Removing tracked dependencies/builds/caches from the index is a **separate explicitly authorized repository-hygiene change**, not an automatic repair step. Adding ignore rules alone cannot fix existing tracking. Do not execute untracking/removal/history rewriting here; preserve current files and record exclusions/remaining churn honestly.

PLAN adds only this document in this clarification. No implementation/ledger edits, filesystem cleanup, git staging, reset, removal or commit performed. This document sets acceptance boundaries; independent review and verified release evidence remain outstanding.
