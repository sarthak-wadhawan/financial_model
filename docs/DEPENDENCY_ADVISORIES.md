# Dependency Security Advisories — Trading Copilot

This document records known security advisories for project dependencies, their applicability assessment, and mitigation status.

---

## Frontend Advisories (npm)

### GHSA-wrjc-x8rr-h8h6 — React Router Open Redirect via Backslash

| Field | Value |
|-------|-------|
| **Package** | `react-router` / `react-router-dom` |
| **Affected Range** | `>=6.0.0 <7.18.0` |
| **Current Version** | `6.30.6` |
| **CVE** | CVE-2025-68470 bypass |
| **Severity** | Moderate (CVSS 6.5) |
| **Description** | `<Link to="...">` and `useNavigate()` treat a leading backslash (`\`) as a same-origin path, enabling open redirect when user-supplied input is passed directly to navigation APIs. |

**Applicability Assessment: NOT EXPLOITABLE**

1. **No SSR / No Hydration Path** — This is a pure client-side SPA. Server-side rendering (SSR) and `deserializeErrors()` hydration paths are not used.
2. **Prefixed Internal Routes Only** — All dynamic navigation uses internal routes with explicit prefixes:
   - `/stocks/:symbol` — symbol validated via `encodeURIComponent()` and regex `^[A-Z][A-Z0-9.-]{0,9}$`
   - `/watchlists/:id` — numeric ID from database
   - `/calendar` — static
   - `/macro` — static
3. **No User-Supplied Paths to `<Link>`** — No component passes unsanitized user input directly to `<Link to={...}>` or `useNavigate()`. All navigation targets are constructed internally from validated symbols or known route constants.
4. **`encodeURIComponent()` on Symbols** — Stock symbols are encoded before being used in route parameters, neutralizing backslash and other special characters.

**Mitigation:** Documented non-exploitability. Upgrade to `react-router-dom@7.18.4` (React Router v7) is a major version migration requiring code changes; deferred to future maintenance window.

---

### GHSA-337j-9hxr-rhxg — React Router SSR Hydration Constructor Injection

| Field | Value |
|-------|-------|
| **Package** | `react-router` / `react-router-dom` |
| **Affected Range** | `>=6.4.0 <7.18.0` |
| **Current Version** | `6.30.6` |
| **Severity** | Moderate |
| **Description** | During SSR hydration, `deserializeErrors()` can be invoked with attacker-controlled serialized error objects, leading to prototype pollution / constructor injection. |

**Applicability Assessment: NOT EXPLOITABLE**

1. **No SSR** — The application is built as a static SPA (`vite build` outputs `frontend/dist/`). No server-side rendering, no hydration, no `deserializeErrors()` call path exists.
2. **No Error Serialization Boundary** — The app does not use React Router's error serialization/deserialization features (e.g., `ErrorResponse`, `useRouteError` with serialized transport).
3. **Client-Only Error Handling** — Errors are handled via React error boundaries and local state; no cross-boundary error serialization occurs.

**Mitigation:** Documented non-exploitability. Same upgrade path as above.

---

### Vite / esbuild Advisories (Previously Reported — Now Resolved)

| Advisory | Package | Status |
|----------|---------|--------|
| GHSA-4fxm-wgv7-8gqg | `vite` (sourcemap exposure) | **Patched** in `vite@6.4.4` (current) |
| GHSA-jfh8-5rmj-m232 | `vite` (Windows path traversal) | **Patched** in `vite@6.x` |
| GHSA-67mh-4wv8-2f99 | `esbuild` (dev server exposure) | **Patched** in `esbuild@0.25.x` (transitive via Vite) |

**Current Status:** `npm audit --json --ignore-scripts` reports **0 high/critical**, **2 moderate** (React Router only). Vite/esbuild advisories no longer appear.

---

## Backend Advisories (Python)

### Current `pyproject.toml` Dependencies

The project declares core dependencies in `pyproject.toml` with optional extras:

```toml
dependencies = [
    "pydantic>=2.8",
    "pydantic-settings>=2.4",
    "pyyaml>=6.0",
    "typer>=0.12",
    "rich>=13.7",
    "pandas>=2.2",
    "numpy>=1.26",
    "httpx>=0.27",
    "python-dotenv>=1.0",
    "tenacity>=8.5",
]

[project.optional-dependencies]
dev = ["pytest>=8.2", "pytest-cov>=5.0", "ruff>=0.4", "mypy>=1.10"]
alpaca = ["alpaca-py>=0.33"]
duckdb = ["duckdb>=1.0"]
```

### Runtime Dependencies Not Declared (Gap)

The following packages are **used at runtime** but not declared in `pyproject.toml` (pulled via implicit environment or optional extras not activated):

| Package | Purpose | Used In |
|---------|---------|---------|
| `fastapi` | Web framework | `backend/main.py` |
| `uvicorn[standard]` | ASGI server | `backend/main.py` entrypoint |
| `feedparser` | RSS/Atom parsing | `backend/website_sources.py` |
| `alpaca-py` | Alpaca Markets API | `trading_copilot/providers/alpaca.py` (via `alpaca` extra) |
| `sqlalchemy` | ORM (if used) | Not currently used — SQLite via `sqlite3` stdlib |
| `email-validator` | Email validation (Pydantic) | Transitive via `pydantic[email]` |

### Python Advisory Audit — `pip-audit` Results (2026-10-14)

`pip-audit -r requirements.txt` against pinned project dependencies:

| Package | Version | Advisory | Fixed In | Severity | Exploitable Here? |
|---------|---------|----------|----------|----------|-------------------|
| `msgpack` | 1.0.3 | PYSEC-2026-3625 (Out-of-bounds read / DoS on Unpacker reuse after error) | 1.2.1 | Moderate | **Unlikely** — Not used directly; transitive via `alpaca-py` → `msgpack`. App does not use streaming Unpacker on untrusted input. |
| `urllib3` | 1.26.20 | Multiple (PYSEC-2026-1999, -1998, -1994, -1996, -141, -4177, -4175) — redirect handling, decompression bombs, header forwarding on cross-origin redirects, chunked encoding DoS, proxy TLS config bleed | 2.5.0–2.8.0 | Moderate–High | **Low** — `httpx` (our HTTP client) uses its own HTTP/2 stack; `urllib3` is transitive via `feedparser` → `requests` → `urllib3`. Feed parsing targets hardcoded trusted feeds (SEC, Fed, BLS). No streaming API usage on untrusted sources. No proxy forwarding config. |

**Note:** System-level packages (cryptography, pillow, paramiko, etc.) reported by global `pip-audit` are excluded — they are OS-managed and not project dependencies.

**Recommendation:** Monitor for `feedparser`/`requests` updates that pull `urllib3>=2.6.0`. No immediate action required given trusted feed sources and no streaming/untrusted usage patterns.

---

## Summary Table

| Advisory | Package | Current Version | Fixed Version | Exploitable Here? | Status |
|----------|---------|-----------------|---------------|-------------------|--------|
| GHSA-wrjc-x8rr-h8h6 | react-router-dom | 6.30.6 | 7.18.4 | **No** (SPA, prefixed routes, encoding) | Documented, pinned to latest 6.x |
| GHSA-337j-9hxr-rhxg | react-router-dom | 6.30.6 | 7.18.4 | **No** (No SSR) | Documented |
| GHSA-4fxm-wgv7-8gqg | vite | 6.4.4 | 6.4.4+ | N/A | Patched |
| GHSA-jfh8-5rmj-m232 | vite | 6.4.4 | 6.x | N/A | Patched |
| GHSA-67mh-4wv8-2f99 | esbuild | 0.25.x | 0.25+ | N/A | Patched |
| PYSEC-2026-3625 | msgpack | 1.0.3 | 1.2.1 | Unlikely (transitive, no Unpacker reuse) | Monitor |
| PYSEC-2026-1999 et al | urllib3 | 1.26.20 | 2.5.0–2.8.0 | Low (trusted feeds, no streaming) | Monitor |
| (Python) | fastapi | 0.136.3 | — | — | Declared in `web`/`full` extras |
| (Python) | uvicorn[standard] | 0.40.0 | — | — | Declared in `web`/`full` extras |
| (Python) | feedparser | 6.0.14 | — | — | Declared in `web`/`full` extras |
| (Python) | email-validator | 2.3.0 | — | — | Declared in `web`/`full` extras |

---

## Action Items

1. ✅ Document React Router advisories with non-exploitability justification (this document).
2. ✅ Add `fastapi`, `uvicorn[standard]`, `feedparser`, `email-validator` to `pyproject.toml` optional dependencies (`web` and `full` extras).
3. ✅ Create `requirements.txt` pinned from resolved environment for reproducibility.
4. ✅ Run `pip-audit` against resolved environment; document results here.
5. 🔄 Consider `react-router-dom@7.x` upgrade in future (major migration; breaking changes).
6. ✅ Pin exact version for `react-router-dom` and `react-router` in `package.json` (now `6.30.6`, latest 6.x).
7. 🔄 Monitor `feedparser`/`requests` for `urllib3>=2.6.0` upgrade.

---

*Generated: 2026-10-14 | Audit: website_security_audit_FINAL.md | Scope: Phase 1–11 Website*