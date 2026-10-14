# Website security audit — preliminary, independent review

## STATUS

**PARTIAL / FINAL VERDICT DEFERRED.** BUILD was still running during this read-only review. This is not a final PASS, merged-state approval, or deployment approval. Scope: current local Phase 1–11 website; no deployment, trades, paid services, webhook delivery, or provider refresh initiated.

Snapshot: 2026-10-14 19:03:43 UTC; HEAD `ddd7f6dcd91d76f026eb024b10533013f186c896`, with substantial concurrent uncommitted changes. Only this audit document was written. No application code, repository data, index, bootstrap/status documents, or credentials were modified; no commit performed. Shepherd owns subsequent documentation reconciliation.

Guidance read: `docs/START_HERE.md`, `docs/PROJECT_STATUS.md` (bootstrap sections), `docs/DEVELOPMENT_ROADMAP_UPDATED.md:90–156`, `docs/website_release_boundaries.md`, `.opencode/agents/security-reviewer.md`, `skills/security-audit/SKILL.md`, and `skills/backend-api-audit/SKILL.md`. Regression implementation is assigned to BUILD, not this read-only reviewer.

## FILES INSPECTED

- `backend/main.py:1–986`: registered routes, validation, startup, CORS, errors, runtime bind.
- `backend/website_data.py:1–162`, `backend/config.yaml:1–63`: market adapter, provider error boundary, configured paths and defaults.
- `src/trading_copilot/events/store.py:465–617`: symbol/type queries and parameterization.
- `src/trading_copilot/watchlists/models.py:1–71`, `service.py:1–106`, `store.py:177–351`: symbols, mutable fields, missing records, parameterization.
- `src/trading_copilot/alerts/models.py:1–125`, `service.py:1–236`, `store.py:178–242`: metadata/channels, dry-run, update field allowlist. Additional SQL/network/webhook searches across `src/trading_copilot/**/*.py`.
- `src/trading_copilot/calendar/models.py:1–45`, `service.py:1–249`: ICS generation, filters and escaping.
- `src/trading_copilot/providers/sec_http.py:1–83`, `alpaca_market.py:68–112`, `news_rss_provider.py:82–136`, `ir_release_provider.py:150–219`: destination controls, credentials and redirects.
- `frontend/src/services/api.ts:1–210`, `frontend/vite.config.ts`, `frontend/package.json`, `frontend/package-lock.json`, `pyproject.toml`, `.gitignore`.
- Sink/link searches across `frontend/src`: `StockPage.tsx:264,495`, `MacroCalendarPage.tsx:154`, `LandingPage.tsx:18–21`, `ResearchData.tsx:30`, `CalendarPage.tsx:37–42`, navigation, settings/footer and storage sites. Source/bundle credential comparisons covered all files under `frontend/src` and the then-existing `frontend/dist`; this does not establish freshness of the build.
- Git tracked-path inventory, `.env.example`, `.env.swp` and its three Git-history versions; local `.env` parsed only for redacted comparison. High-confidence token/private-key pattern scan over tracked non-node_modules files up to 8 MB. This is bounded detection, not exhaustive assurance.

End-of-review SHA-256 fingerprints (rerun if these change):

| File | SHA-256 |
|---|---|
| `backend/main.py` | `88ca7a40a2774c1891da7e3e2f557da734597630bece4e3e68b7d2e4137c3616` |
| `backend/website_data.py` | `6b87dd778262ce9e3fe6acf6bf0fa4840c5b5a96042665b013e5648900cb7f4c` |
| `src/trading_copilot/calendar/service.py` | `a506af9286b362d4e91ace9601560242c8dd68f730b057e01903e6fefd07e17d` |
| `src/trading_copilot/alerts/models.py` | `179446756aa8b598e950b2306c34cb186abee3dc3a19f0bd5f2d10df31437256` |
| `src/trading_copilot/alerts/service.py` | `b6d6ec7f37191e5c162ad6fecf510ace83a84c1e06c767403cb3087f2f9e89ef` |
| `frontend/package-lock.json` | `38fcf44106eebeef5f7ee72b83e7fcf92422088b070ad46a0ef0fb3cb8a8b5c2` |

## TESTS

- `PYTHONDONTWRITEBYTECODE=1 LLM_ENABLED=false RUN_LIVE_TESTS=0 python3 -m pytest -p no:cacheprovider tests/unit/test_events.py tests/unit/test_alpaca_market.py tests/unit/test_sec_filings.py`: **73 passed**. System Python used; the same selection in `.venv` failed collection because `feedparser` is absent. `.venv` also lacks FastAPI/Starlette. No dependencies installed or repaired by reviewer.
- In-process FastAPI `TestClient`, **without application lifespan**, using fake service/store/provider objects: bar limit 5001 → 422; invalid bar ticker → 400; invalid event ticker `BAD!` → 200; invalid calendar date → generic 400; missing alert test → generic 500; missing-watchlist item insertion → generic 500; SQL-like invalid watchlist symbol → 400. No database opened or real HTTP provider called.
- CORS preflight: `https://evil.example` → 400 without origin authorization; `http://localhost:3000` → 200 with matching allow-origin. This proves preflight behavior, not authentication or protection against all cross-origin simple requests.
- Synthetic provider exception containing a secret marker/internal path: adapter returned `provider_error` without either marker. Unhandled test responses were plain `Internal Server Error`, not traces or schema/path details.
- Pure ICS generation: summary newline escaped correctly; a CRLF-bearing URL produced literal separate `BEGIN:VALARM` / `ACTION:DISPLAY` lines. Injection confirmed at serializer, not through an exposed event-write API.
- SEC URL checker rejected HTTP loopback, user-info host confusion and traversal, accepted an ordinary allowlisted HTTPS URL; no HTTP request made.
- `PATH=/home/bito/.nvm/versions/node/v22.23.3/bin:$PATH npm audit --json --ignore-scripts` (read-only advisory query): exit 1, **4 affected packages: 1 high, 3 moderate**. See applicability below. Python advisory audit not run (`pip-audit` absent); no claim of clean Python dependencies.
- Secret checks: tracked `.env.example` secret assignments empty; `.env` untracked; current `.env.swp` credential assignments empty. No local parsed credential value found in current source/bundle; no high-confidence tracked token/private-key pattern hit. An initial raw-text comparison matched comment text; proper dotenv parsing disproved that match. **No active credential leak confirmed.**

## MATERIAL FINDINGS

### S1 — Conditional calendar content injection (medium, reproduced)

`src/trading_copilot/calendar/service.py:199,217–219` emits UID, URL and categories without line-break rejection; `CalendarEvent.url` and stored `MarketEvent.source_url` are unrestricted strings. URL CRLF injection was reproduced. A poisoned retained/source URL can add calendar properties/components when the user exports/imports ICS. Summary/description/location already escape text. Current API has no arbitrary event-write endpoint, so this is an upstream/imported-data trust-boundary risk, **not demonstrated unauthenticated remote code execution**. No calendar application execution was attempted.

### S2 — Local API launch exposes unauthenticated mutable data to interfaces (medium, configuration-dependent)

`backend/main.py:984–986` launches on `0.0.0.0`; watchlist/alert CRUD has no authentication/ownership enforcement. A machine reachable on port 8000 permits another client to read/change this local user's research data. Actual exposure depends on startup command/firewall; no remote access was probed. CORS is correctly restricted but does not protect against direct HTTP clients. This is a current local launch boundary issue; full hosted multi-user auth remains Phase 14, not required implementation here.

### S3 — Untrusted external-link protocols not constrained (conditional, not confirmed XSS)

`frontend/src/pages/StockPage.tsx:264,495`, `MacroCalendarPage.tsx:154`, `LandingPage.tsx:18`, `components/ui/ResearchData.tsx:30` use supplied URLs directly as anchor targets. `noopener noreferrer` is present; no `dangerouslySetInnerHTML`/`innerHTML` sink found. Source text is React-escaped. Without scheme validation, poisoned evidence can supply unsafe navigation targets; actual script execution is browser/React-dependent and **was not demonstrated**. Term links are internally curated, reducing that particular attack path. Apply one shared HTTP(S)-only external-link policy rather than treating escaped text as URL validation.

### S4 — Missing-record errors and incomplete ticker/bounds validation (low robustness, reproduced)

Missing records raised by `alerts/service.py:99–100` and `watchlists/store.py:251–252` are not mapped to 404 in the inspected API; requests returned 500 with generic bodies. This is a correctness/availability issue, **not observed secret/trace leakage**. Ticker checks are used for bars/quant/POST answers and watchlist additions but several event/read/interpretation/GET-answer routes only uppercase input; event endpoint accepted `BAD!`. SQL values remain parameterized, so this is not SQL injection. Alert symbol lists, export lists, GET questions and reorder lists lack consistent length/count limits. Hosted quotas/rate limiting are deferred; inexpensive local input bounds remain appropriate now.

### S5 — Advisory findings and dependency reproducibility gaps (applicability-qualified)

Lock resolves Vite **5.4.21**, esbuild **0.21.5**, react-router/react-router-dom **6.30.6**, axios **1.20.0**. Advisory query reports:

- Vite `GHSA-4w7w-66w2-5vf9`: optimized dependency sourcemap traversal; potentially relevant to this Linux development server. No exploit tested. `server.host` is loopback, reducing network reachability but not proving patched behavior.
- Vite `GHSA-v6wh-96g9-6wx3` and `GHSA-fx2h-pf6j-xcff`: Windows-specific findings; not exploitable on this reviewed Linux host as described.
- esbuild `GHSA-67mh-4wv8-2f99`: development-server cross-origin disclosure; no standalone esbuild serve invocation found. Do not equate dependency presence with reachable exploit.
- React Router `GHSA-wrjc-x8rr-h8h6`: open redirect via backslash; observed dynamic navigation is prefixed with internal routes and several symbols are URI-encoded, so no exploitable redirect demonstrated. `GHSA-337j-9hxr-rhxg`: SSR hydration constructor injection; no SSR path observed in this SPA.

`pyproject.toml` does not declare FastAPI/uvicorn/feedparser despite current runtime use; no backend requirements file found and virtualenv cannot reproduce selected imports. Frontend has a lockfile; installed/generated churn and **19,548 tracked node_modules files** compromise reviewability, not proof of a compromised package. Build/source sourcemaps are enabled; not inherently a secret leak, but bundle scan must repeat after BUILD. Repository hygiene removal is separately authorized work, not undertaken here.

## NEGATIVE / DEFERRED FINDINGS

- No SQL injection identified in inspected event/watchlist/alert queries: values bind to placeholders; interpolated field names are internal allowlisted constants and IN placeholders derive from counts.
- No arbitrary-fetch/file-path/trading/fund-transfer endpoint found in inspected registered routes. Market destinations are provider-controlled; ticker is a query value, not an arbitrary URL. Server-side configured paths are not client-controlled.
- Alert `webhook`/`email` enums and arbitrary metadata are accepted, but inspected service has **no outbound webhook/email dispatcher**. Thus no current webhook SSRF demonstrated. Reject/label unsupported channels for truthful contracts; before future delivery, require destination/redirect/DNS/private-address protections and secret redaction. No notification was sent.
- RSS/IR ingestion follows redirects from configured feeds without SEC-style allowlisting; no website route accepts a feed URL or starts these fetches. Future configurable ingestion needs SSRF controls; this is not currently an arbitrary URL-fetch API.
- No active secret in `.env.swp` confirmed. It is a tracked editor artifact and `.gitignore` only excludes exact `.env`, not `.env.*`, node_modules or dist. Avoid publishing/staging sensitive/generated files; current and historical hygiene remediation must be explicitly scoped. No deletion/untracking/history rewrite performed.
- Public hosting authentication/authorization, quotas, CSP/TLS, container privileges, serverless secrets and scheduled notifications remain later hosting work. Their absence is not independently a Phase 1–11 local-release FAIL. Do not expose this unauthenticated local API publicly.

## REQUIRED FIXES / RERUN GATE

1. BUILD: reject CR/LF in non-text ICS fields, validate external URLs, preserve valid text escaping and provenance; add serializer/export regressions using poisoned URL and UID fixtures. Suppress invalid links without changing retained historical evidence.
2. BUILD/Shepherd: make documented local backend launch loopback-only by default; verify the actual command/listening address. Do not add hosted authentication as part of this repair.
3. BUILD: centralize safe external-link rendering; test unsupported schemes, credential-bearing/malformed links and valid evidence links. Do not claim browser XSS proved by a string-only test.
4. BUILD: map missing records to 404, apply consistent ticker/list/input limits, reject/label unsupported delivery choices; add isolated API regressions. Preserve generic provider/error messages.
5. Shepherd: resolve or explicitly document each dependency advisory's reachable surface, reproduce package/lock/backend environment, and rerun advisory checks after toolchain edits. Do not use forceful automatic audit fixes or blanket stage generated directories.
6. **After BUILD merges/completes:** independently reread changed backend/Phase 11/frontend files, rerun isolated API/export/link/secret/advisory tests against the final build and actual runtime launch; record final file hashes and test evidence. Recheck new evaluation/delivery routes for SSRF and side effects. This preliminary document cannot be promoted to PASS solely from BUILD's report.
