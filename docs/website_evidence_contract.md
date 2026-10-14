# Website Evidence Adapter — Contract & Verification

**Status:** IMPLEMENTED / VERIFIED (2026-10-14)
**Files:** `backend/website_evidence.py`, `tests/test_website_evidence.py` (16 tests passing)

---

## Interface Contract

```python
from backend.website_evidence import WebsiteEvidenceAdapter, RefreshReport

# Factory
adapter = WebsiteEvidenceAdapter(
    config: Config,
    settings: Settings,
    event_store: EventStore,
    status_path: Path | None = None,  # optional JSON persistence
)

# Bounded refresh for explicit symbols
report: RefreshReport = adapter.refresh(symbols: list[str])

# Status query
status: dict = adapter.status(scope: str | None = None)
```

### RefreshReport Fields
| Field | Type | Description |
|-------|------|-------------|
| `started_at` | ISO timestamp | Refresh cycle start |
| `completed_at` | ISO timestamp | Refresh cycle end |
| `symbols` | `list[str]` | Symbols requested (uppercased) |
| `overall_status` | `str` | `success` / `partial` / `unavailable` / `failed` |
| `outcomes` | `list[ProviderOutcome]` | Per-provider details |
| `errors` | `list[dict]` | Cycle-level errors |

### ProviderOutcome Fields
| Field | Type | Description |
|-------|------|-------------|
| `provider` | `str` | Provider name (see below) |
| `status` | `str` | `success` / `real_empty` / `unavailable` / `provider_error` |
| `count_new` | `int` | New events upserted |
| `count_unchanged` | `int` | Existing events unchanged |
| `count_changed` | `int` | Events with content changes |
| `count_errors` | `int` | Provider-level errors |
| `reason` | `str | None` | Human-readable reason for non-success |
| `retrieved_at` | `str | None` | ISO timestamp of this provider's attempt |
| `details` | `dict` | Provider-specific metadata |

### Provider Names (7 total)
1. `sec_filings` — SEC filings (45-day lookback, leadership, Form 4)
2. `earnings_intelligence` — Extracted EPS/revenue/consensus/guidance/surprise from SEC
3. `macro_calendar` — Fed FOMC schedules + BLS released values
4. `earnings_calendar` — Scheduled earnings (requires API key)
5. `news_rss` — Financial news RSS (7 days, normalized to events)
6. `ir_releases` — Company IR press releases
7. `sec_exhibits` — 8-K exhibits 99.1/99.2/99.3 (requires SEC_USER_AGENT)

---

## Behavioral Guarantees

| Guarantee | Implementation |
|-----------|----------------|
| **Real mode only** | Fixtures never used in live mode; `EarningsCalendarProvider` raises `RuntimeError` if no keys; `MacroCalendarProvider` raises `NotImplementedError` for economic calendar |
| **Credentials missing = unavailable** | SEC providers return `unavailable` with reason when `SEC_USER_AGENT` missing; earnings calendar returns `unavailable` when no keys configured |
| **Per-provider outcomes** | Each provider runs independently; one failure doesn't block others; aggregated in `RefreshReport` |
| **Provenance preserved** | Events upserted with `source`, `source_url`, `source_id`, `retrieved_at`, `observation_period`, `time_precision`; raw document metadata stored |
| **No fixture contamination** | `_is_synthetic()` helper filters test/fixture/demo rows by `source`, `verification_state`, `data_mode`; events stored but excluded from website results |
| **Lightweight sync status** | JSON file at `artifacts/cache/website_evidence_status.json` (configurable); does NOT edit event store |
| **No background jobs** | Synchronous `refresh()` only; no scheduler, no auto-refresh |
| **Rate limits respected** | Underlying providers enforce their own limits (SECTransport 8 req/s) |

---

## Test Coverage (16 tests, all passing)

| Test | Verifies |
|------|----------|
| `test_refresh_success_sec_filings_earnings_intelligence` | SEC providers succeed with valid credentials; provenance recorded |
| `test_refresh_unavailable_without_sec_user_agent` | SEC filings & earnings intelligence → `unavailable` without credentials |
| `test_refresh_macro_calendar` | Macro calendar runs without credentials (Fed HTML + BLS) |
| `test_refresh_earnings_calendar_unavailable_no_keys` | Earnings calendar → `unavailable` when no API keys |
| `test_refresh_news_rss` | News RSS normalized to events with evidence timestamps |
| `test_refresh_ir_releases` | IR releases normalized to events with provenance |
| `test_refresh_sec_exhibits_unavailable_without_credentials` | SEC exhibits → `unavailable` without credentials |
| `test_status_not_refreshed` | Fresh adapter returns `not_refreshed` |
| `test_status_after_refresh` | Status reflects last `RefreshReport` |
| `test_filter_synthetic_fixture_rows` | Synthetic/test/fixture rows filtered non-destructively |
| `test_provenance_preserved` | Outcomes include `retrieved_at` and details |
| `test_gated_live_smoke` | Live calls only when `WEBSITE_LIVE_EVIDENCE=1` |
| `test_constructor_signature` | Correct factory signature |
| `test_refresh_returns_refresh_report` | Report structure matches contract |
| `test_provider_outcome_fields` | All required provenance fields present |
| `test_overall_status_logic` | `success`/`partial`/`unavailable`/`failed` aggregation |

---

## Integration Points

### Backend Lifespan (main.py)
```python
from backend.website_evidence import create_website_evidence_adapter

@asynccontextmanager
async def lifespan(app: FastAPI):
    # ... existing init ...
    evidence_adapter = create_website_evidence_adapter(config, settings, event_store)
    
    if os.environ.get("WEBSITE_REFRESH_PROVIDERS") == "1":
        from starlette.concurrency import run_in_threadpool
        await run_in_threadpool(evidence_adapter.refresh, ["AAPL"])
    
    yield
    
    # ... cleanup ...
```

### API Endpoint
```python
@app.post("/api/v1/market/refresh")
async def refresh_market_data(request: RefreshRequest):
    if not request.symbols:
        return {"status": "skipped", "reason": "No symbols provided"}
    symbols = [s.strip().upper() for s in request.symbols if s.strip()]
    from starlette.concurrency import run_in_threadpool
    report = await run_in_threadpool(evidence_adapter.refresh, symbols)
    return {"status": "completed", "symbols": symbols, "report": report.to_dict()}
```

---

## Provider Details

### SEC Filings & Earnings Intelligence
- **Credentials:** `SEC_USER_AGENT` (required)
- **Lookback:** 45 days (configurable via `config.sources.filings_lookback_days`)
- **Max per symbol:** 4 (configurable via `config.sources.max_filings_per_symbol`)
- **Provenance:** `retrieved_at`, `source_id` (accession), `source_url`, filing metadata (items, form, dates)

### Macro Calendar
- **Credentials:** None required (Fed HTML, BLS public API)
- **Fed:** Current + next year parsed from official HTML; no fixtures in live mode; 14:00 ET expectation in metadata only
- **BLS:** Observation periods preserved; no midnight `released_at` fabrication; M13 excluded
- **Provenance:** `retrieved_at`, `observation_period`, `time_precision="unknown"`, `data_kind="observation_not_release"`

### Earnings Calendar
- **Credentials:** At least one of Alpha Vantage / FMP / Polygon / Twelve Data API keys
- **Mode:** Live only; fixtures only in explicit `demo` mode
- **Timing:** BMO/AMC/unknown as session/date precision; no 13:30/21:00/midnight fabrication
- **Provenance:** `estimate_source`, `estimate_source_url`, `retrieved_at`, `consensus_as_of=None`

### News RSS / IR Releases / SEC Exhibits
- **Credentials:** None (RSS/IR); SEC exhibits require `SEC_USER_AGENT`
- **Window:** 7 days (RSS/IR), 45 days (SEC exhibits)
- **Provenance:** Full document metadata stored; `claim_type` = `attributed_statement` / `company_statement`; `source_type` preserved

---

## Verification Commands

```bash
# All evidence adapter tests
LLM_ENABLED=false python3 -m pytest -o addopts='' -q tests/test_website_evidence.py

# Provider-specific regression tests
LLM_ENABLED=false python3 -m pytest -o addopts='' -q tests/test_website_provider_semantics.py

# History/provenance tests
LLM_ENABLED=false python3 -m pytest -o addopts='' -q tests/test_website_history_provenance.py

# Full backend suite
LLM_ENABLED=false python3 -m pytest -o addopts='' -q
```

---

## Blocker / Known Limitation

| Blocker | Impact | Resolution Path |
|---------|--------|-----------------|
| BEA/Census parsers incomplete | Macro providers return `unavailable` for BEA/Census | Implement official parsers against BEA/Census APIs |
| Earnings calendar needs API keys | Returns `unavailable` without keys | Configure at least one earnings API key |
| SEC exhibits require credentials | Returns `unavailable` without `SEC_USER_AGENT` | Provide valid SEC operator identity |
| Status file persistence | JSON file, not DB; manual clean between test runs | Use unique `status_path` per test (implemented) |

---

## Related Documentation

- `docs/website_provider_audit.md` — Source of audit findings 18-23
- `docs/website_provider_timestamp_repairs.md` — Provider timestamp fixes
- `docs/website_history_provenance_repairs.md` — History/provenance fixes
- `docs/website_backend_repair.md` — Backend API integration
- `docs/website_api_contract.md` — Frozen API contract v1