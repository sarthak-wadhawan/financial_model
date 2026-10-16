# Dependency Security Advisories — Trading Copilot

This document records known security advisories for project dependencies, their applicability assessment, and mitigation status.

**2026-10-15 independent security recheck:** PASS for the local Phase 1–11 website, not deployment approval. The advisories below are nonblocking maintenance risks; no applicable application execution path was identified. This is not a claim that dependencies are vulnerability-free.

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

**Applicability Assessment: No applicable path identified in this SPA**

1. **No SSR / No Hydration Path** — This is a pure client-side SPA. Server-side rendering (SSR) and `deserializeErrors()` hydration paths are not used.
2. **Prefixed Internal Routes Only** — All dynamic navigation uses internal routes with explicit prefixes:
   - `/stocks/:symbol` — symbol validated via `encodeURIComponent()` and regex `^[A-Z][A-Z0-9.-]{0,9}$`
   - `/watchlists/:id` — application-generated opaque ID from database
   - `/calendar` — static
   - `/macro` — static
3. **No User-Supplied Paths to `<Link>`** — No component passes unsanitized user input directly to `<Link to={...}>` or `useNavigate()`. All navigation targets are constructed internally from validated symbols or known route constants.
4. **Symbol boundaries** — Dynamic stock routes use validated symbol values; encoding provides an additional boundary where used. This does not justify accepting arbitrary navigation destinations.

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

**Applicability Assessment: No applicable path identified in this SPA**

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
web = ["fastapi>=0.115", "uvicorn[standard]>=0.32", "feedparser>=6.0", "email-validator>=2.1"]
# full also includes web dependencies, alpaca-py and duckdb.
```

### Runtime Installation and Locking Boundary

Website runtime dependencies are declared in the `web`/`full` extras. Install from the repository root with `python3 -m pip install -e '.[web,dev]'`; the optional `alpaca` extra supplies the SDK where needed. The website's historical-bars adapter itself uses HTTPX.

| Package | Purpose | Used In |
|---------|---------|---------|
| `fastapi` | Web framework | `backend/main.py` |
| `uvicorn[standard]` | ASGI server | `backend/main.py` entrypoint |
| `feedparser` | RSS/Atom parsing | `backend/website_sources.py` |
| `alpaca-py` | Optional Alpaca SDK | `alpaca` / `full` extras |
| `email-validator` | Email validation (Pydantic) | `web` / `full` extras |

The pre-existing, untracked `requirements.txt` is a selected environment snapshot, **not a complete transitive lock or the release installation contract**. It contains an unused legacy `alpaca-trade-api==3.2.0` entry; no application import was found. Preserve that pre-session file rather than silently adopting it. Recommended separate cleanup: remove the unused legacy SDK from the snapshot, resolve dependencies again, and re-audit. Do not force incompatible transitive upgrades beneath it. Exact Python transitive locking remains maintenance work.

### Python Advisory Audit — `pip-audit` Results (2026-10-14)

The independent 2026-10-15 recheck of `pip-audit -r requirements.txt` reported **14 advisory records, including duplicates**, across legacy msgpack/urllib3 dependencies in that snapshot. It is not an audit of a freshly resolved `web` extra:

| Package | Version | Advisory | Fixed In | Severity | Exploitable Here? |
|---------|---------|----------|----------|----------|-------------------|
| `msgpack` | 1.0.3 | PYSEC-2026-3625 (Out-of-bounds read / DoS on Unpacker reuse after error) | 1.2.1 | Moderate | No applicable website path identified. The unused legacy `alpaca-trade-api` constrains this old version; the application does not use its streaming unpacker. |
| `urllib3` | 1.26.20 | Multiple advisory records: redirects, decompression, header forwarding and proxy handling | 2.5.0–2.8.0 | Moderate–High | No applicable website path identified. The old dependency is introduced through unused legacy `alpaca-trade-api`, **not feedparser**. Active website HTTP paths use HTTPX. |

**Note:** System-level packages (cryptography, pillow, paramiko, etc.) reported by global `pip-audit` are excluded — they are OS-managed and not project dependencies.

**Recommendation:** Remove the unused legacy SDK from the separate environment snapshot before re-resolution; audit the actual resolved installation. Trusted feed URLs alone are not a dependency-security mitigation. Remaining advisories and incomplete locking are documented, not waived for future deployment.

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
3. Snapshot exists locally; it is untracked and not a full dependency lock.
4. ✅ Independently audit the snapshot; distinguish that result from the declared web installation.
5. 🔄 Consider `react-router-dom@7.x` upgrade in future (major migration; breaking changes).
6. ✅ Pin exact version for `react-router-dom` and `react-router` in `package.json` (now `6.30.6`, latest 6.x).
7. 🔄 Separately remove the unused legacy SDK, re-resolve, audit and introduce a complete lock if required.

---

*Updated: 2026-10-15 | Current verification: FULL_SYSTEM_AUDIT.md | Scope: local Phase 1–11 website; no Phase 12 or deployment approval.*
