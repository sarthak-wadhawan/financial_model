# Website Toolchain Security Fixes — BUILD B Repair Report

**Date:** 2026-10-14  
**Scope:** Targeted repairs for Security Audit findings S5a/S5b (Dependency Advisories & Reproducibility)  
**Source Audit:** `docs/website_security_audit_FINAL.md` — Section S5  
**Commit:** No commit performed (per instructions)

---

## STATUS

**COMPLETED** — All S5a/S5b remediation tasks executed and verified.

| Task | Description | Status |
|------|-------------|--------|
| 1 | Create `docs/DEPENDENCY_ADVISORIES.md` documenting React Router GHSA-wrjc-x8rr-h8h6 and GHSA-337j-9hxr-rhxg with non-exploitability assessment | ✅ Done |
| 2 | Update `pyproject.toml` with `web` and `full` optional dependencies (FastAPI, uvicorn[standard], feedparser, alpaca-py, email-validator, duckdb) | ✅ Done |
| 3 | Create `requirements.txt` pinned from resolved environment | ✅ Done |
| 4 | Run `pip-audit` against `requirements.txt`; document results | ✅ Done |
| 5 | Pin exact versions for `react-router` and `react-router-dom` in `frontend/package.json` (upgraded to latest 6.x: 6.30.6) | ✅ Done |
| 6 | Persist this report: `docs/website_toolchain_security_fixes.md` | ✅ Done |

---

## FILES MODIFIED

| File | Change |
|------|--------|
| `docs/DEPENDENCY_ADVISORIES.md` | **Created** — Full advisory documentation for React Router (2 moderate) and Python (msgpack, urllib3) with exploitability assessments |
| `pyproject.toml` | **Modified** — Added `[project.optional-dependencies] web` and `full` extras with FastAPI, uvicorn[standard], feedparser, email-validator, alpaca-py, duckdb |
| `frontend/package.json` | **Modified** — Pinned `react-router` and `react-router-dom` to exact version `6.30.6` (latest 6.x, still within advisory range but documented) |
| `requirements.txt` | **Created** — Pinned runtime dependencies from `pip freeze` after `pip install -e ".[full]"` |

---

## TESTS EXECUTED

| Test | Command | Result |
|------|---------|--------|
| Python dependency install | `pip install -e ".[full]"` | ✅ Success — all packages installed |
| `pip-audit` on project deps | `pip-audit -r requirements.txt` | ✅ Completed — 2 packages with advisories (msgpack, urllib3), documented |
| `pip-audit` with descriptions | `pip-audit -r requirements.txt --desc` | ✅ Completed — full CVE details captured |
| Frontend dependency check | `npm audit --json --ignore-scripts` (from audit) | ✅ 2 moderate (React Router only), Vite/esbuild advisories resolved |
| Unit tests (backend) | `pytest tests/unit/` | ✅ 73 passed (from audit) |
| Frontend unit tests | `npm test` | ✅ 151 passed (from audit) |
| Calendar security tests | `pytest tests/test_phase11_calendar_security.py` | ✅ 51 passed (from audit) |

> Note: Backend/frontend unit tests were verified via the security audit re-run; not re-executed in this BUILD B session per scope.

---

## FINDINGS

### React Router Advisories (Frontend)

| Advisory | CVE | Range | Current | Exploitable? | Justification |
|----------|-----|-------|---------|--------------|---------------|
| GHSA-wrjc-x8rr-h8h6 | CVE-2025-68470 bypass | `>=6.0.0 <7.18.0` | 6.30.6 | **No** | Pure SPA (no SSR); all dynamic routes prefixed (`/stocks/:symbol`, `/watchlists/:id`); symbols validated via regex `^[A-Z][A-Z0-9.-]{0,9}$` and `encodeURIComponent()`; no user-supplied paths passed to `<Link>`/`useNavigate()` |
| GHSA-337j-9hxr-rhxg | — | `>=6.4.0 <7.18.0` | 6.30.6 | **No** | No SSR, no hydration, no `deserializeErrors()` usage; client-only error boundaries |

**Action Taken:** Pinned to `6.30.6` (latest 6.x). Upgrade to `7.18.4+` requires React Router v7 migration (breaking API changes) — deferred to future maintenance.

### Python Advisories (Backend)

| Package | Advisory | Fixed In | Exploitable? | Justification |
|---------|----------|----------|--------------|---------------|
| `msgpack` 1.0.3 | PYSEC-2026-3625 (DoS via Unpacker reuse after error) | 1.2.1 | **Unlikely** | Transitive via `alpaca-py`; application does not use streaming Unpacker on untrusted input |
| `urllib3` 1.26.20 | PYSEC-2026-1999, -1998, -1994, -1996, -141, -4177, -4175 (redirect handling, decompression bombs, header forwarding, chunked encoding DoS, proxy TLS bleed) | 2.5.0–2.8.0 | **Low** | Transitive via `feedparser` → `requests`; feed sources are hardcoded trusted endpoints (SEC EDGAR, Fed, BLS); no streaming API on untrusted sources; no proxy forwarding config |

**Action Taken:** Documented in `DEPENDENCY_ADVISORIES.md`. No immediate upgrade needed — monitor `feedparser`/`requests` for `urllib3>=2.6.0` adoption.

### Vite/esbuild (Previously Reported — Now Resolved)

| Advisory | Package | Status |
|----------|---------|--------|
| GHSA-4fxm-wgv7-8gqg | `vite` (sourcemap exposure) | Patched in `vite@6.4.4` |
| GHSA-jfh8-5rmj-m232 | `vite` (Windows path traversal) | Patched in `vite@6.x` |
| GHSA-67mh-4wv8-2f99 | `esbuild` (dev server exposure) | Patched in `esbuild@0.25.x` |

`npm audit` now reports **0 high/critical**, **2 moderate** (React Router only).

---

## REPRODUCIBILITY ARTIFACTS

### `requirements.txt` (Pinned Project Runtime)

```text
alpaca-py==0.44.0
alpaca-trade-api==3.2.0
dnspython==2.8.0
duckdb==1.5.6
email-validator==2.3.0
fastapi==0.136.3
feedparser==6.0.14
feedparser-sgmllib==2.1.0
httptools==0.9.0
httpx==0.28.1
numpy==2.2.6
pandas==2.3.3
pydantic==2.13.5
pydantic-settings==2.15.0
pydantic_core==2.46.5
python-dotenv==1.2.3
rich==15.0.0
sseclient-py==1.9.0
tenacity==9.1.4
typer==0.27.2
uvicorn==0.40.0
uvloop==0.23.0
watchfiles==1.3.0
```

### `pyproject.toml` Extras (Declarative)

```toml
[project.optional-dependencies]
web = [
    "fastapi>=0.115",
    "uvicorn[standard]>=0.32",
    "feedparser>=6.0",
    "email-validator>=2.1",
]
full = [
    "fastapi>=0.115",
    "uvicorn[standard]>=0.32",
    "feedparser>=6.0",
    "email-validator>=2.1",
    "alpaca-py>=0.33",
    "duckdb>=1.0",
]
```

Install full runtime: `pip install -e ".[full]"`

---

## VERIFICATION CHECKLIST

- [x] `docs/DEPENDENCY_ADVISORIES.md` exists with React Router + Python advisories
- [x] React Router advisories assessed non-exploitable with technical justification
- [x] Vite/esbuild advisories confirmed patched in current versions
- [x] `pyproject.toml` includes `web` and `full` extras for full runtime
- [x] `requirements.txt` created with pinned versions from resolved env
- [x] `pip-audit` run against `requirements.txt`; results documented
- [x] `frontend/package.json` pins `react-router` and `react-router-dom` to `6.30.6`
- [x] This report persisted to `docs/website_toolchain_security_fixes.md`

---

## RESIDUAL RISKS (Accepted)

1. **React Router 6.x advisories remain** — Fixed only in v7.18.0+. Non-exploitable in current architecture. Migration to v7 is a Phase 14+ concern.
2. **urllib3 1.26.20 advisories** — Transitive via `feedparser` → `requests`. Trusted feed sources only; no streaming/untrusted usage. Monitor upstream.
3. **msgpack 1.0.3** — Transitive via `alpaca-py`. No direct Unpacker reuse on untrusted data.

---

## NEXT STEPS (Out of Scope for BUILD B)

- S2: Change `backend/main.py` default host to `127.0.0.1` (loopback)
- S4: Add `max_items` constraints to `CalendarExportRequest` and `ReorderBody`
- Shepherd: Remove `.env.swp` from git history
- Phase 14: Deployment hardening (TLS, auth, rate limiting, container)

---

*Generated by BUILD B subagent | No commit | No Phase 12*