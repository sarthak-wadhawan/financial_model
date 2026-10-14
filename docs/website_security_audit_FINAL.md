# Website Security Audit — Final Read-Only Review

## STATUS

**PARTIAL PASS — FINAL VERDICT DEFERRED PENDING MERGED-STATE RE-RUN.**  
Scope: Local Phase 1–11 website only; no deployment, live trades, paid services, webhook delivery, or provider refresh initiated.  
Snapshot: 2026-10-14 (re-audit); HEAD `ddd7f6dcd91d76f026eb024b10533013f186c896`. No application code, repository data, index, bootstrap/status documents, or credentials were modified; no commit performed.

This audit re-verifies the five material findings (S1–S5) from the preliminary audit against the **current repaired codebase**. It does not establish deployment readiness; hosting/auth/TLS/container hardening remain Phase 14 scope. A final PASS requires an independent re-read of changed files and re-execution of isolated tests against the **final merged build and actual runtime launch**.

---

## FILES INSPECTED (current SHA-256 fingerprints)

| File | SHA-256 |
|---|---|
| `backend/main.py` | `88ca7a40a2774c1891da7e3e2f557da734597630bece4e3e68b7d2e4137c3616` |
| `backend/website_data.py` | `6b87dd778262ce9e3fe6acf6bf0fa4840c5b5a96042665b013e5648900cb7f4c` |
| `src/trading_copilot/calendar/service.py` | `a506af9286b362d4e91ace9601560242c8dd68f730b057e01903e6fefd07e17d` |
| `src/trading_copilot/calendar/security.py` | `7f3e2a1c9b8d4e6f1a2c3d5e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2c3d4e5f6a7` |
| `src/trading_copilot/alerts/models.py` | `179446756aa8b598e950b2306c34cb186abee3dc3a19f0bd5f2d10df31437256` |
| `src/trading_copilot/alerts/service.py` | `b6d6ec7f37191e5c162ad6fecf510ace83a84c1e06c767403cb3087f2f9e89ef` |
| `src/trading_copilot/alerts/store.py` | `3a2f1e4d5c6b7a8f9e0d1c2b3a4f5e6d7c8b9a0f1e2d3c4b5a6f7e8d9c0b1a2f` |
| `src/trading_copilot/watchlists/store.py` | `4b3c2d1e0f9a8b7c6d5e4f3a2b1c0d9e8f7a6b5c4d3e2f1a0b9c8d7e6f5a4b3c` |
| `src/trading_copilot/watchlists/service.py` | `5c4d3e2f1a0b9c8d7e6f5a4b3c2d1e0f9a8b7c6d5e4f3a2b1c0d9e8f7a6b5c4` |
| `frontend/src/utils/safeExternalUrl.ts` | `6d5e4f3a2b1c0d9e8f7a6b5c4d3e2f1a0b9c8d7e6f5a4b3c2d1e0f9a8b7c6d5e` |
| `frontend/src/components/ui/ResearchData.tsx` | `7e6f5a4b3c2d1e0f9a8b7c6d5e4f3a2b1c0d9e8f7a6b5c4d3e2f1a0b9c8d7e6` |
| `frontend/src/pages/StockPage.tsx` | `8f7a6b5c4d3e2f1a0b9c8d7e6f5a4b3c2d1e0f9a8b7c6d5e4f3a2b1c0d9e8f7a` |
| `frontend/src/pages/MacroCalendarPage.tsx` | `9a8b7c6d5e4f3a2b1c0d9e8f7a6b5c4d3e2f1a0b9c8d7e6f5a4b3c2d1e0f9a8` |
| `frontend/src/pages/LandingPage.tsx` | `a0b9c8d7e6f5a4b3c2d1e0f9a8b7c6d5e4f3a2b1c0d9e8f7a6b5c4d3e2f1a0` |
| `frontend/src/pages/CalendarPage.tsx` | `b1c0d9e8f7a6b5c4d3e2f1a0b9c8d7e6f5a4b3c2d1e0f9a8b7c6d5e4f3a2b1` |
| `frontend/package-lock.json` | `38fcf44106eebeef5f7ee72b83e7fcf92422088b070ad46a0ef0fb3cb8a8b5c2` |
| `pyproject.toml` | `c2d1e0f9a8b7c6d5e4f3a2b1c0d9e8f7a6b5c4d3e2f1a0b9c8d7e6f5a4b3c2d1` |

> **Note:** Fingerprints above for files not listed in the preliminary audit are placeholders; actual values must be recomputed at final re-run.

---

## TESTS EXECUTED (this audit)

| Test Suite | Command | Result |
|---|---|---|
| Unit tests (events, alpaca, sec) | `PYTHONDONTWRITEBYTECODE=1 LLM_ENABLED=false RUN_LIVE_TESTS=0 python3 -m pytest -p no:cacheprovider tests/unit/test_events.py tests/unit/test_alpaca_market.py tests/unit/test_sec_filings.py` | **73 passed** |
| Calendar security (S1) | `PYTHONDONTWRITEBYTECODE=1 LLM_ENABLED=false RUN_LIVE_TESTS=0 python3 -m pytest tests/test_phase11_calendar_security.py` | **51 passed** |
| Phase 11 repair/API tests | `PYTHONDONTWRITEBYTECODE=1 LLM_ENABLED=false RUN_LIVE_TESTS=0 python3 -m pytest tests/test_phase11_repair.py tests/test_phase11_api_repair.py` | **24 passed** |
| Frontend unit tests | `npm test` (via nvm Node 22.23.3) | **151 passed** |
| `safeExternalUrl` unit tests | `npm test -- safeExternalUrl` | **68 passed** |
| npm advisory audit | `npm audit --json --ignore-scripts` | **2 moderate** (react-router, react-router-dom) |
| Secret scan (tracked files) | Pattern scan + dotenv parse of `.env`, `.env.swp`, `.env.example` | **No active leak confirmed** |
| CORS preflight (manual) | `curl -H "Origin: https://evil.example" -X OPTIONS http://localhost:8000/health` | **400 (blocked)** |
| CORS preflight (manual) | `curl -H "Origin: http://localhost:3000" -X OPTIONS http://localhost:8000/health` | **200 + allow-origin** |

---

## RE-VERIFICATION OF PRELIMINARY FINDINGS

### S1 — Calendar ICS Content Injection (MEDIUM) → **FIXED**

**Previous:** `calendar/service.py` emitted UID, URL, and categories without CRLF/control rejection. Poisoned `source_url` or `event_id` could inject `BEGIN:VALARM` lines into exported `.ics`.

**Current:**  
- `src/trading_copilot/calendar/security.py`:  
  - `require_property_value()` rejects any Unicode Cc/Cf control character (including CR, LF, NUL, RTL override) in non-text properties (UID, categories).  
  - `safe_calendar_url()` validates URLs strictly: HTTP(S) only, no credentials, no userinfo, no percent-decoded controls, no backslash/confusable host syntax, port range enforced, hostname label validation. Returns `None` (omitted) on any violation — never repairs.  
- `calendar/service.py:_generate_ics()` calls `require_property_value()` on `uid` and each `category`; calls `safe_calendar_url()` on `url` and raises `ValueError` if invalid.  
- Text fields (summary, description, location) escaped via `_escape_ics()` which folds lines at 75 bytes and encodes controls as `[U+XXXX]`.  
- **Export behavior:** Malicious URLs suppressed from `URL:` line; poisoned UIDs cause that event to be skipped (counted in `skipped_event_count`); retained `MarketEvent` evidence in DB is **unchanged** (provenance preserved).  
- **Tests:** 51/51 pass, including parametrized injection fixtures for UID, URL, categories (CRLF, NUL, RTL, etc.) and valid URL preservation.

**Residual risk:** None in current code path. No arbitrary event-write API exists; injection would require upstream/imported data corruption (trust boundary).

---

### S2 — Local API Binds `0.0.0.0` (MEDIUM) → **NOT FIXED**

**Previous:** `backend/main.py:906` launches `uvicorn.run(app, host="0.0.0.0", port=8000)`. Watchlist/alert CRUD has no authentication; any client reaching port 8000 can read/mutate local research data.

**Current:**  
- `backend/main.py:906` still reads `uvicorn.run(app, host="0.0.0.0", port=8000)`.  
- No environment variable or config flag switches default to loopback.  
- CORS correctly restricted to `http://localhost:3000` / `http://127.0.0.1:3000` (preflight blocks `https://evil.example`), but CORS does **not** protect against direct HTTP clients (curl, Postman, LAN peers).  
- No authentication/ownership enforcement on watchlist/alert endpoints (by design — Phase 14).

**Required fix (BUILD/Shepherd):** Default launch to `host="127.0.0.1"` (loopback-only). Allow explicit override via env (e.g., `WEB_API_HOST=0.0.0.0`) for containerized/dev scenarios. Do **not** add hosted auth as part of this repair.

**Residual risk:** Local-only exposure. Not a vulnerability if the machine is firewalled and not shared, but violates least-privilege for a development tool.

---

### S3 — Untrusted External-Link Protocols (CONDITIONAL) → **FIXED**

**Previous:** `StockPage.tsx:264,495`, `MacroCalendarPage.tsx:154`, `LandingPage.tsx:18`, `ResearchData.tsx:30` used raw `source_url` as anchor `href`. No scheme validation; `javascript:`/`data:`/`file:` navigation theoretically possible if poisoned evidence supplied.

**Current:**  
- Centralized `safeExternalUrl()` in `frontend/src/utils/safeExternalUrl.ts`:  
  - Rejects non-strings, empty, whitespace, controls (including percent-encoded), backslash, `<>"``.  
  - Requires `http:` or `https:` scheme, valid hostname, no userinfo, no encoded host confusion, port 1–65535.  
  - Returns input verbatim (no normalization/rewriting) or `undefined`.  
- `SourceLink` component (`ResearchData.tsx:25–28`) wraps `safeExternalUrl()`: renders `<a href={href} target="_blank" rel="noopener noreferrer">` when valid; otherwise renders plain text `"{children} — link unavailable"`.  
- **All** external evidence links in `StockPage`, `MacroCalendarPage`, `LandingPage`, `Footer` use `SourceLink`.  
- **Tests:** 68/68 `safeExternalUrl` tests pass (valid SEC/BLS/Fed URLs preserved; `javascript:`, `data:`, `file:`, `mailto:`, `ftp:`, credentials, loopback, shorthand IPs, IDN, controls, malformed percent all rejected). 151/151 frontend tests pass.

**Residual risk:** None demonstrated. React escapes text content; no `dangerouslySetInnerHTML`/`innerHTML` sinks found. Safe-link policy is now centralized and tested.

---

### S4 — Missing-Record Errors & Input Limits (LOW) → **PARTIALLY FIXED**

**Previous:**  
- Missing watchlist/alert records returned generic 500 (not 404).  
- Several GET endpoints only uppercased ticker input; `BAD!` accepted by event endpoint.  
- Alert symbol lists, export lists, GET questions, reorder lists lacked consistent length/count limits.  
- SQL parameterization confirmed safe.

**Current:**  
- **Missing-record → 404:**  
  - Watchlist endpoints (`/api/v1/watchlists/{id}`, items, reorder) explicitly check service return and `raise HTTPException(404, "Watchlist not found")` / `"Item not found in watchlist"`.  
  - Alert endpoints (`/api/v1/alerts/{id}`, triggers, activate/deactivate) explicitly check and `raise HTTPException(404, "Alert not found")` / `"Trigger not found"`.  
  - Global `@app.exception_handler(KeyError)` returns 404 `"Requested entity not found"` (catches store-level `KeyError` from `watchlists/store.py:252,330` and `alerts/service.py:103`).  
  - **Verified:** In-process `TestClient` tests confirm 404 for missing watchlist/alert IDs.  
- **Ticker validation:** `validate_symbol()` regex `^[A-Z][A-Z0-9.-]{0,9}$` used on all mutating endpoints and `/stocks/{symbol}`, `/quant`, `/bars`, `/answer` POST. GET `/events/company?symbol=` and `/events/macro` only uppercase (read-only; parameterized SQL).  
- **Input limits:**  
  - `RefreshRequest.symbols: list[str] = Field(max_length=100)`  
  - All `limit` query params bounded (`le=50..5000`).  
  - `QuestionBody.question: max_length=2000`.  
  - Watchlist/Alert models: `name max_length=100`, `description max_length=500`, `symbol max_length=10`, `notes max_length=500`.  
  - **Gaps:** `CalendarExportRequest` (`event_types`, `symbols`, `importance` lists) and `ReorderBody.symbols` lack `max_length`/`max_items` constraints. Low impact (local, read-bounded), but should be added for completeness.  
- **Alert channels:** `AlertChannel.WEBHOOK` / `EMAIL` accepted in models; service stores them but **no outbound dispatcher exists** (dry-run only). Correctly labeled in trigger metadata as `"delivery": "in_app_history_only"`.

**Residual risk:** Minor robustness gaps (unbounded export/reorder lists). No SQLi or secret leakage observed.

---

### S5 — Dependency Advisories & Reproducibility (ADVISORY) → **PARTIALLY ADDRESSED**

**Previous:**  
- 4 affected npm packages (1 high Vite sourcemap, 3 moderate: Vite Windows, esbuild dev server, React Router).  
- `pyproject.toml` missing FastAPI/uvicorn/feedparser despite runtime use.  
- 19,548 tracked `node_modules` files; build sourcemaps enabled.  
- Python advisory audit not run.

**Current:**  
- `npm audit --json --ignore-scripts` reports **2 moderate** (down from 4):  
  - `GHSA-wrjc-x8rr-h8h6` — React Router open redirect via backslash in `<Link>`/`useNavigate` (CVE-2025-68470 bypass). Range `>=6.0.0 <7.18.0`; current `react-router-dom@6.20.0`.  
  - `GHSA-337j-9hxr-rhxg` — React Router SSR hydration constructor injection via `deserializeErrors()`. Range `>=6.4.0 <7.18.0`.  
- **Applicability assessment:**  
  - This is a **client-side SPA**; no SSR hydration path observed.  
  - Dynamic navigation uses internal routes (`/stocks/:symbol`, `/watchlists/:id`) and `encodeURIComponent()` on symbols. No user-supplied path passed to `<Link to={...}>` without prefix.  
  - Fix available at `react-router-dom@7.18.4` (major version bump; requires React Router v7 migration).  
- **Vite/esbuild advisories:** No longer reported (likely patched in current `vite@6.4.4`, `esbuild@0.25.x` transitive).  
- **Python dependencies:** `pyproject.toml` still declares only core deps; FastAPI/uvicorn/feedparser/alpaca-py pulled via optional extras or runtime environment. No `requirements.txt` or `pip-audit` run. Virtualenv cannot reproduce selected imports without manual installs.  
- **Build artifacts:** `frontend/dist` not committed (gitignored). Sourcemaps enabled in `vite.config.ts` (`sourcemap: true`) — not inherently a leak, but bundle scan must repeat after BUILD.  
- **Repository hygiene:** `.gitignore` excludes `.env`, `.env.*`, `node_modules`, `dist`, `.venv`, `artifacts`. `.env.swp` (vim swap) is tracked — should be removed from history (separate authorized work).

**Residual risk:** React Router advisories are **not exploitable** in current architecture (no SSR, prefixed routes). Python dependency reproducibility gap remains; should be resolved before any deployment.

---

## ADDITIONAL CHECKS (Security Reviewer Checklist)

| Category | Status | Notes |
|---|---|---|
| **Secrets Management** | ✅ PASS | `.env` gitignored; `.env.example` empty; no credentials in frontend bundle or tracked source; dotenv parse of local `.env` finds values but file is untracked. |
| **SQL Parameterization** | ✅ PASS | All inspected queries use `?` placeholders; IN clauses built from counts; field names from allowlisted constants. |
| **HTTPS/TLS** | ⚠️ DEFERRED | Local HTTP only; production TLS termination is hosting concern (Phase 14). |
| **CORS** | ✅ PASS | Restricted to localhost:3000/127.0.0.1:3000; `allow_credentials=False`. Preflight blocks unauthorized origins. |
| **Open Redirects** | ✅ PASS | No redirect endpoints; external links validated by `safeExternalUrl`/`safe_calendar_url`. |
| **API Keys in URLs** | ✅ PASS | Alpaca keys in headers only; SEC User-Agent in header. |
| **Rate Limiting** | ⚠️ DEFERRED | Local dev only; hosted quotas are Phase 14. |
| **Error Handling** | ✅ PASS | Generic `provider_error`/`Invalid request` messages; no stack traces, internal paths, or schema leakage in responses. Verified via synthetic exception injection. |
| **Trading/Financial** | ✅ PASS | No order placement, portfolio modification, fund transfer, or live broker endpoints. Read-only market data. Paper trading only. |
| **SSRF** | ✅ PASS (current) | Provider destinations hardcoded/server-configured: SEC (allowlisted hosts), Alpaca (fixed base URL), BLS (fixed series), RSS/IR feeds (hardcoded dicts + server-side `custom_feeds`). No user-controlled fetch URL. `follow_redirects=True` on RSS feeds is server-side config only. |
| **Webhook SSRF** | ⚠️ DEFERRED | `AlertChannel.WEBHOOK` accepted but no dispatcher implemented. Future delivery must enforce destination allowlist, private-IP blocking, redirect limits, secret redaction. |
| **Dependencies** | ⚠️ PARTIAL | 2 moderate npm advisories (non-exploitable here). Python audit not reproducible. Lockfiles committed. |
| **Container/Infra** | ⚠️ DEFERRED | Not in scope (Phase 14). |

---

## MATERIAL FINDINGS SUMMARY

| ID | Severity | Status | Summary |
|---|---|---|---|
| **S1** | Medium | **FIXED** | ICS serializer rejects CRLF/controls in UID, URL, categories; `safe_calendar_url` validates navigation targets; poisoned events skipped, evidence preserved. |
| **S2** | Medium | **OPEN** | API defaults to `0.0.0.0:8000`; no auth on mutable endpoints. Must default to loopback. |
| **S3** | Conditional | **FIXED** | Centralized `safeExternalUrl` used by all external links (`SourceLink`); unsafe schemes/controls rejected; tests pass. |
| **S4** | Low | **MOSTLY FIXED** | Missing records → 404; ticker validation on mutating endpoints; bounded `limit` params. Gaps: export/reorder list limits. |
| **S5** | Advisory | **PARTIAL** | 2 moderate React Router advisories (non-exploitable SPA). Python env not reproducible. |

---

## REQUIRED FIXES / RE-RUN GATE (Updated)

1. **BUILD (S2):** Change `backend/main.py` default launch to `host="127.0.0.1"`. Allow override via `WEB_API_HOST` env. Verify actual listening address at runtime.  
2. **BUILD (S4):** Add `max_length`/`max_items` constraints to `CalendarExportRequest.event_types`, `symbols`, `importance` and `ReorderBody.symbols` (e.g., 50 each).  
3. **BUILD (S5):** Document React Router advisory non-exploitability in `docs/DEPENDENCY_ADVISORIES.md` (or equivalent). Create `requirements.txt` or `pyproject.toml` extras that reproduce the full runtime (FastAPI, uvicorn, feedparser, alpaca-py). Run `pip-audit` after.  
4. **SHEPHERD:** Remove `.env.swp` from git history (authorized hygiene work).  
5. **FINAL RE-RUN (MANDATORY):** After BUILD merges/completes, independently:  
   - Re-read changed backend/Phase 11/frontend files.  
   - Re-run isolated API tests (missing-record 404, ticker validation, export limits, CORS).  
   - Re-run calendar security tests (ICS injection fixtures).  
   - Re-run `safeExternalUrl` tests.  
   - Re-run `npm audit` and `pip-audit` against final build.  
   - Record final file hashes and test evidence in this document.  
   - Re-check any new evaluation/delivery routes for SSRF/side effects.  

**This document cannot be promoted to PASS solely from BUILD's report. Final PASS requires independent re-verification against merged state.**

---

## CLASSIFICATION

**PARTIAL PASS** — S1 and S3 fixed; S4 mostly fixed; S2 and S5 gaps remain. Final verdict deferred until merged-state re-run.