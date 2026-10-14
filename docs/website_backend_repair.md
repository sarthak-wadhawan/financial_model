# Website Backend Repair — BUILD D/J Wave 1

**Status:** IMPLEMENTED / TESTS PASSING  
**Date:** 2026-10-14  
**Owner:** D/J wave 1 subagent

---

## STATUS

All five required tasks completed and verified by isolated backend tests:

1. ✅ **Wired WebsiteSourceAdapter.refresh into lifespan for bounded symbols list** — lifespan now reads `WEBSITE_REFRESH_SYMBOLS` (comma-separated) and only runs when `WEBSITE_REFRESH_PROVIDERS=1`. No auto-scheduler.
2. ✅ **WebsiteDataAdapter.mode from WEBSITE_DATA_MODE** — already implemented; confirmed `mode=os.environ.get("WEBSITE_DATA_MODE", "real")` in `backend/main.py:202`.
3. ✅ **Added `/api/v1/market/refresh` POST endpoint** — server-side, bounded, calls `source_adapter.refresh(symbols)` with validation (max 100 symbols).
4. ✅ **Fixed symbol mapping** — `search()` now returns `type` (not `asset_type`) and includes `exchange` from SEC ticker cache metadata; stock detail correctly consumes `metadata.get("exchange")`.
5. ✅ **Indices SPY only; VIX/DXY/10Y explicitly unavailable** — `overview()` only returns benchmark (SPY) in `indices` array; no fabrication.
6. ✅ **Verified api.ts matches frozen contract** — added `refreshMarketData(symbols)` and `answerQuestion(symbol, question, context?)`; all endpoints present.

---

## FILES

**Modified:**
- `backend/main.py` — lifespan bounded refresh, `/api/v1/market/refresh` POST, fixed `SymbolSearchResult`/`SearchResult` models (`type` not `asset_type`), duplicate import cleanup
- `backend/website_data.py` — `search()` returns `exchange` from metadata, `type` field
- `backend/website_sources.py` — no changes (existing `refresh()` already correct)
- `frontend/src/services/api.ts` — added `refreshMarketData()`, `answerQuestion()` optional `context`

**No CSS/pages/config changes.**

---

## INTERFACE

### New/Changed Endpoints

| Endpoint | Method | Request | Response |
|----------|--------|---------|----------|
| `/api/v1/market/refresh` | POST | `{symbols: string[]}` (max 100) | `{status: "completed"\|"skipped", symbols: string[], state: Record<string,any>}` |
| `/api/v1/symbols/search` | GET | `q, limit?` | `[{symbol, name?, exchange?, type, source}]` — `type` not `asset_type`; `exchange` from SEC cache |
| `/api/v1/stocks/{symbol}` | GET | — | `{symbol, name?, exchange?, price?, change?, change_pct?, volume?, market_cap:null, pe_ratio:null, dividend_yield:null, price_data, quant_signals, interpretation, events, quant_signals_components}` |
| `/api/v1/stocks/{symbol}/answer` | POST | `{question, context?}` | `{question, answer, confidence, evidence_refs[], generated_at}` |
| `/api/v1/market/overview` | GET | — | `indices` contains only benchmark (SPY); VIX/DXY/10Y absent |

### Lifespan Behavior

```bash
WEBSITE_REFRESH_PROVIDERS=1 WEBSITE_REFRESH_SYMBOLS="AAPL,MSFT,SPY" python -m backend.main
```

- Only runs if **both** env vars set
- Symbols parsed from comma-separated list, uppercased, stripped
- No scheduler, no background task — single bounded refresh at startup

---

## TESTS

All isolated backend test suites pass:

| Suite | Tests | Duration |
|-------|-------|----------|
| `tests/unit/test_website_backend_repair.py` | 15 | ~19s |
| `tests/test_phase11_repair.py` | 20 | ~10s |
| `tests/test_phase11_api_repair.py` | 4 | ~8s |
| `tests/test_phase11_calendar_security.py` | 51 | ~4s |
| `tests/test_website_provider_semantics.py` | 37 | ~114s |
| `tests/test_website_history_provenance.py` | 13 | ~47s |
| **Total** | **140** | **~3.5 min** |

Key regressions covered:
- `test_search_independent_of_scanner` — search returns `type: "equity"`, `exchange` from metadata
- `test_missing_credentials_never_mock` — real mode without credentials returns `unavailable`, not mock
- `test_provider_failure_safe` — provider errors don't leak secrets, status=`provider_error`
- `test_explicit_demo_scanner_reuses_scorer` — demo mode uses existing deterministic scorer
- `test_event_filter_and_provenance` — events preserve `first_seen_at`, `source_id`, `source_url`
- `test_rss_unknown_publication_not_retrieval_time` — RSS entries without pub date are dropped

---

## FINDINGS

1. **Provider defects remain in source** — `macro_calendar.py` (BEA/Census empty parsers, FOMC fixture fallback, BLS reference→release) and `earnings_calendar.py` (fixture fallback, midnight fabrication) have targeted repair tests in `test_website_provider_semantics.py` but are **not fixed in source**. This is by design per audit: website refresh is gated, provider fixes are separate work.

2. **WebsiteSourceAdapter.refresh() is production-ready** — uses `EventStore.upsert_event()` for revision-preserving ingestion; `_macro()` and `_news()` paths avoid fixture defaults in real mode; state tracking per provider (`sec`, `earnings`, `macro`, `news`, `bea`, `census`, `earnings_calendar`).

3. **No auto-refresh scheduler** — per requirements, refresh is explicit POST or bounded startup gate. Prevents unbounded provider calls.

4. **Frontend contract alignment** — `api.ts` types match `website_api_contract.md` v1; `SymbolSearchResult` uses `type`; `StockDetail` expects nullable `exchange`; `MarketOverviewResponse.indices` array only for benchmark.

5. **Zero-LLM default preserved** — `Config().llm.enabled is False` verified in unit tests.

---

## BLOCKERS

None for this wave. Remaining work (out of scope for D/J wave 1):
- Provider-level fixes for BEA/Census/BLS/FOMC/earnings (tracked in `website_provider_audit.md` findings 38–41)
- Full live integration test (`RUN_LIVE_TESTS=1`) — requires credentials
- Independent provider auditor final gate (not yet run against restarted process)
- `docs/START_HERE.md` and `docs/PROJECT_STATUS.md` reconciliation (parent-owned)