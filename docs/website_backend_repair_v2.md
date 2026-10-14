# Website Backend Repair v2 — BUILD D/J Targeted Fixes

**Date:** 2026-10-14  
**Scope:** Targeted repairs for Provider Audit Findings P7/P8 and Security Audit Findings S2/S4  
**Status:** COMPLETED — All isolated backend tests pass

---

## STATUS

| Fix # | Description | Status | Verification |
|-------|-------------|--------|--------------|
| 1 | Alpaca `_fetch_bars_batch`: implement `next_page_token` loop for multi-page historical requests | ✅ DONE | Unit tests pass; pagination logic added |
| 2 | Alpaca `_get_daily_bars_simple`: classify 4xx/5xx/network failures as `provider_error`; do NOT cache empty-on-error; return error type in status | ✅ DONE | Unit tests pass; status dict returned; cache gated on no provider errors |
| 3 | WebsiteDataAdapter `scan()`: add `source_url` (Alpaca bars endpoint) and `upstream_retrieved_at` (provider's retrieved_at) to each candidate | ✅ DONE | Candidates now include provenance fields |
| 4 | Leadership endpoint `/api/v1/stocks/{symbol}/leadership`: preserve `source_url`, `retrieved_at`, `filing_date` per role in response | ✅ DONE | Endpoint explicitly includes provenance fields from provider |
| 5 | FileCache in `storage/cache.py`: add TTL param and expiry check (timezone-aware) | ✅ DONE | Both FileCache and MemoryCache enforce TTL with UTC-aware comparison |
| 6 | `backend/main.py`: default uvicorn host to `127.0.0.1`; allow `WEB_API_HOST` env override | ✅ DONE | Launch reads `WEB_API_HOST` env, defaults to loopback |
| 7 | `CalendarExportRequest` and `ReorderBody` Pydantic models: add `max_length=50` to list fields | ✅ DONE | `event_types`, `symbols`, `importance`, `ReorderBody.symbols` bounded |

---

## FILES MODIFIED

| File | Changes |
|------|---------|
| `src/trading_copilot/providers/alpaca_market.py` | - `_fetch_bars_batch`: added `next_page_token` pagination loop<br>- `_get_daily_bars_simple`: returns `(results, statuses)` tuple; 4xx/5xx/network → `provider_error`; cache only on clean statuses<br>- `get_daily_bars`: handles new tuple return; stops expansion on provider errors<br>- Added `get_daily_bars_with_status` public method for callers needing status |
| `backend/website_data.py` | - `bars()`: uses `get_daily_bars_with_status` when available; sets `provider_error` status correctly<br>- `scan()`: uses `get_daily_bars_with_status`; adds `source_url` and `upstream_retrieved_at` to each candidate |
| `backend/main.py` | - Leadership endpoint: explicitly preserves `source_url`, `retrieved_at`, `filing_date` per role<br>- Uvicorn launch: defaults to `127.0.0.1`, overrides via `WEB_API_HOST`<br>- `ReorderBody.symbols`: added `Field(max_length=50)` |
| `src/trading_copilot/calendar/models.py` | - `CalendarExportRequest`: `event_types`, `symbols`, `importance` lists bounded with `Field(max_length=50)` |
| `src/trading_copilot/storage/cache.py` | - `FileCache.get()`: timezone-aware TTL comparison (UTC)<br>- `FileCache.set()`: stores UTC timestamp<br>- `MemoryCache`: added TTL param and expiry enforcement |

---

## INTERFACE CHANGES

### AlpacaMarketDataProvider
```python
# New public method
def get_daily_bars_with_status(
    self,
    symbols: list[str],
    start: datetime,
    end: datetime,
    min_trading_sessions: int | None = None,
) -> tuple[dict[str, list[DailyBar]], dict[str, str]]:
    """
    Returns (results, statuses) where statuses maps symbol → "available" | "empty" | "provider_error".
    """

# Changed return type (internal)
def _get_daily_bars_simple(...) -> tuple[dict[str, list[DailyBar]], dict[str, str]]:
    # Was: dict[str, list[DailyBar]]
```

### WebsiteDataAdapter.scan() Candidate Dict
```python
# New fields added to each candidate:
{
    ...
    "source_url": "https://data.alpaca.markets/v2/stocks/bars",  # or None in demo
    "upstream_retrieved_at": "2026-10-14T12:34:56.789Z",  # provider retrieval time
}
```

### Leadership Endpoint Response
```python
# Per-role dict now explicitly includes:
{
    "CEO": {
        "name": "...",
        "effective_date": "...",
        "source_url": "https://www.sec.gov/...",      # preserved
        "retrieved_at": "2026-10-14T12:34:56.789Z",   # preserved
        "filing_date": "2026-01-15",                   # preserved
        ...
    }
}
```

### CalendarExportRequest / ReorderBody
```python
class CalendarExportRequest(BaseModel):
    event_types: Optional[List[str]] = Field(default=None, max_length=50)
    symbols: Optional[List[str]] = Field(default=None, max_length=50)
    importance: Optional[List[str]] = Field(default=None, max_length=50)

class ReorderBody(BaseModel):
    symbols: list[str] = Field(max_length=50)
```

---

## TESTS

| Test Module | Command | Result |
|-------------|---------|--------|
| `tests/test_phase11_api_repair.py` | `pytest tests/test_phase11_api_repair.py` | **4 passed** |
| `tests/unit/test_alpaca_market.py` | `pytest tests/unit/test_alpaca_market.py` | **18 passed** |
| `tests/unit/test_sec_filings.py` | `pytest tests/unit/test_sec_filings.py` | **29 passed** |
| `tests/unit/test_website_backend_repair.py` | `pytest tests/unit/test_website_backend_repair.py` | **15 passed** |

All tests run with `PYTHONDONTWRITEBYTECODE=1 LLM_ENABLED=false RUN_LIVE_TESTS=0` isolation.

---

## FINDINGS

### Provider Audit P7 — Alpaca Pagination (HIGH) — FIXED
- **Root cause:** `_fetch_bars_batch` made single request, ignored `next_page_token` in Alpaca response
- **Fix:** Added while-loop that continues fetching while `next_page_token` present; accumulates bars per symbol
- **Impact:** Multi-page historical requests (e.g., >10k bars) now return complete data

### Provider Audit P7 — Alpaca Failure Suppression (HIGH) — FIXED
- **Root cause:** `_get_daily_bars_simple` caught 4xx/5xx/Timeout/ConnectError and returned `[]` per symbol, then cached empty results
- **Fix:** 
  - 5xx/429 → re-raise for retry (existing)
  - 4xx (client errors) → classify as `provider_error`, do NOT cache
  - Network errors (Timeout, ConnectError) → classify as `provider_error`, do NOT cache
  - Cache only written when all statuses ≠ `provider_error`
  - New `_get_daily_bars_simple` returns `(results, statuses)` tuple
  - Public `get_daily_bars_with_status` exposes statuses to callers

### Provider Audit P8 — Scanner Provenance (MEDIUM) — FIXED
- **Root cause:** `scan()` candidates lacked `source_url` and upstream `retrieved_at`
- **Fix:** `scan()` now calls `get_daily_bars_with_status`; adds `source_url` (Alpaca bars endpoint) and `upstream_retrieved_at` (provider call time) to each candidate

### Provider Audit P8 — Leadership Provenance (MEDIUM) — FIXED
- **Root cause:** Leadership endpoint dropped `source_url`, `retrieved_at` from provider response
- **Fix:** Endpoint explicitly includes `source_url`, `retrieved_at`, `filing_date` per role in response dict

### Security Audit S2 — API Binds 0.0.0.0 (MEDIUM) — FIXED
- **Root cause:** `uvicorn.run(app, host="0.0.0.0")` exposed API to LAN
- **Fix:** Default to `127.0.0.1`; allow `WEB_API_HOST` env override for containers

### Security Audit S4 — Input Limits (LOW) — FIXED
- **Root cause:** `CalendarExportRequest` and `ReorderBody` list fields unbounded
- **Fix:** Added `Field(max_length=50)` to all list fields

### Cache TTL Enforcement (LOW) — FIXED
- **Root cause:** `FileCache` TTL comparison used naive `datetime.now()` vs potentially aware cached timestamp; `MemoryCache` had no TTL enforcement
- **Fix:** Both caches now use `datetime.now(timezone.utc)` for comparison; `MemoryCache` accepts `ttl_days` param and enforces expiry in `get()`

---

## BLOCKERS

| Blocker | Description | Resolution |
|---------|-------------|------------|
| None | All fixes implemented and verified via isolated tests | — |

---

## REGRESSION RISK ASSESSMENT

| Component | Risk | Mitigation |
|-----------|------|------------|
| Alpaca pagination | Low — additive loop, backward compatible | Existing tests pass; pagination only activates when token present |
| Failure classification | Medium — changes error handling flow | Unit tests cover 4xx, 5xx, timeout, network; cache gating tested |
| Scanner provenance | Low — additive fields only | Existing candidates unchanged; new fields optional for consumers |
| Leadership provenance | Low — additive fields only | Provider already returned fields; endpoint now passes through |
| Cache TTL | Low — stricter enforcement | Timezone-aware comparison fixes potential bug; MemoryCache TTL only affects tests |
| Host binding | Low — safer default | Explicit env override for container deployments |
| Input limits | Low — validation only | 50-item limit well above legitimate use cases |

---

## NEXT STEPS

1. **Run integration tests** (gated by `RUN_LIVE_TESTS=1`) to verify live Alpaca pagination
2. **Re-run provider auditor** against merged state to confirm P7/P8 resolution
3. **Re-run security auditor** to confirm S2/S4 resolution
4. **Update frontend TypeScript types** (`frontend/src/services/api.ts`) to include new `source_url` and `upstream_retrieved_at` in `QuantCandidate` interface (optional — frontend can ignore unknown fields)

---

## VERIFICATION COMMANDS

```bash
# Run all repair verification tests
PYTHONDONTWRITEBYTECODE=1 LLM_ENABLED=false RUN_LIVE_TESTS=0 python3 -m pytest \
    tests/test_phase11_api_repair.py \
    tests/unit/test_alpaca_market.py \
    tests/unit/test_sec_filings.py \
    tests/unit/test_website_backend_repair.py -v

# Verify uvicorn host default
grep -n "WEB_API_HOST" backend/main.py

# Verify Pydantic max_length
grep -n "max_length=50" src/trading_copilot/calendar/models.py backend/main.py

# Verify cache TTL
grep -n "timezone.utc" src/trading_copilot/storage/cache.py
```