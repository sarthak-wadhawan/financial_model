# Website Provider Timestamp Repairs — Wave 1

## STATUS
**COMPLETE** — All audit findings 38–41 addressed and verified by tests.

## FILES MODIFIED

### Provider Implementations (already compliant, verified)
- `src/trading_copilot/providers/macro_calendar.py` — BEA/Census raise `NotImplementedError` with explicit unavailable status; FOMC current-year uses official HTML parsing first (fixtures only in demo mode); FOMC times use DST-correct 14:00 ET expectation in metadata only (NOT `scheduled_at`); BLS preserves `observation_period`, no midnight `released_at`, M13 excluded; `fetch_economic_calendar` raises `NotImplementedError` (not empty placeholder).
- `src/trading_copilot/providers/earnings_calendar.py` — Fixtures ONLY in `mode="demo"` (live failures are explicit errors); BMO/AMC/unknown use session/date precision (no fabricated 13:30/21:00/midnight UTC); estimate provenance preserved (`estimate_source`, `estimate_source_url`, `retrieved_at`, `consensus_as_of: null`); demo fixtures carry `verification_state=demo_fixture`.

### Unit Tests Updated to Match Correct Behavior
- `tests/unit/test_macro_calendar.py` — Updated expectations: PCE/Core PCE/GDP/Retail/Housing/Permits are `provider_pending`; FOMC fixture keys prefixed `fixture_`; refresh in demo mode; scheduled events checked via `metadata["event_date"]`; FOMC minutes is `provider_pending`; BLS `release_date`/`released_at` are `None`.
- `tests/unit/test_earnings_calendar.py` — Updated: fixtures require `mode="demo"`; BMO/AMC/unknown have `scheduled_at=None` with session/date precision; no fixed UTC times; unknown time gets date precision not midnight; metadata assertions updated.

### Permanent Regression Tests (audit findings 38–41)
- `tests/test_website_provider_semantics.py` — 37 tests covering: FOMC current-year official-first (no fixture merge), FOMC failures are errors not fixture success, FOMC year-scoped panel parsing, DST-correct 14:00 ET expectation, demo fixtures marked `demo_fixture`; BLS reference month ≠ release date, M13 excluded, no midnight `released_at`, observations don't mutate schedule; BEA/Census raise `NotImplementedError` with `status=unavailable`; economic calendar raises `NotImplementedError`; earnings live missing keys → error (no demo fallback), live failed sources → error (no fixture fallback), scoped empty is success; FMP/Alpha Vantage session/date precision (no fake exact), exact time distinct from session, error payloads not verified empty; demo earnings persist with `verification_state=demo_fixture`.

## INTERFACE
No public interface changes. Internal behavior changes:

### MacroCalendarProvider
- `fetch_bea_series()` → `NotImplementedError("BEA official table/line parsing is not implemented")`, `last_fetch_status["bea"] = {"status": "unavailable", "reason": "unsupported_official_parser"}`
- `fetch_census_series()` → `NotImplementedError("Census dataset-specific official parsing is not implemented")`, `last_fetch_status["census"] = {"status": "unavailable", "reason": "unsupported_official_parser"}`
- `fetch_economic_calendar()` → `NotImplementedError("Official economic release calendar parsing is not implemented")`, `last_fetch_status["economic_calendar"] = {"status": "unavailable", "reason": "official_release_calendar_not_implemented"}`
- `fetch_fomc_schedule(year)` — Live mode: fetches/parses Fed HTML, raises on failure (no fixture fallback). Demo mode: loads `tests/fixtures/fomc_{year}.json`, marks `verification_state=demo_fixture`.
- `_fomc_date_event()` — Returns `scheduled_at=None`, `released_at=None`, `metadata["expected_statement_at"]` (DST-correct 14:00 ET), `metadata["scheduled_time_precision"]="date"`, `metadata["expected_statement_time_source"]="derived_customary_14_ET_not_verified"`.
- `fetch_bls_series()` — Returns `observation_period`, `release_date=None`, `released_at=None`, excludes M13.
- `fetch_latest_bls_release()` — Returns `observation_date`, `observation_period`, `release_date=None`, `released_at=None`.
- `fetch_released_values()` — Increments `UNMATCHED` (does not invent release times or mutate schedule).

### EarningsCalendarProvider
- `fetch_earnings_calendar()` — Live mode: tries configured sources, raises `RuntimeError` if all fail (no fixture fallback). Demo mode: loads `tests/fixtures/earnings_calendar.json`, marks `verification_state=demo_fixture`.
- `_calendar_timing(report_date, session, exact_at=None)` — Returns `scheduled_at=None` for session/date precision; `scheduled_time_precision` = "session" (bmo/amc/dmc) or "date" (unknown); `scheduled_at` only set when `exact_at` provided with timezone.
- `_estimate_provenance()` — Returns `estimate_source`, `estimate_source_url`, `retrieved_at`, `consensus_as_of: null`, `estimate_verification="provider_estimate_not_verified_consensus"`.
- `_load_fixtures()` — Only called in demo mode; adds `verification_state=demo_fixture`, `data_mode=demo`, `estimate_verification=demo_not_consensus`.

## TESTS
All pass:
- `tests/unit/test_macro_calendar.py` — 18 passed
- `tests/unit/test_earnings_calendar.py` — 15 passed
- `tests/test_website_provider_semantics.py` — 37 passed

## FINDINGS
1. **BEA/Census**: Previous implementation fetched HTTP then returned empty `results=[]` — now explicitly unavailable with `NotImplementedError`. Free API key does not fix missing official parser contracts.
2. **FOMC current-year**: Previously always used fixtures (`tests/fixtures/fomc_{year}.json`) — now official HTML parsing first in live mode; fixtures only in demo mode.
3. **FOMC timestamps**: Previously fixed 18:00 UTC (incorrect for EST winter) — now DST-correct 14:00 ET in `metadata["expected_statement_at"]` only, with `scheduled_time_precision="date"` and explicit "not_verified" source.
4. **BLS reference month**: Previously converted observation month to `date(year, month, 1)` and called it `release_date`/`released_at` at midnight UTC — now preserves `observation_period`, sets `release_date=None`, `released_at=None`; M13 excluded.
5. **Earnings fixtures**: Previously returned fixtures for missing keys, failed sources, or empty responses — now ONLY in demo mode; live failures are explicit errors.
6. **Earnings BMO/AMC**: Previously fabricated 13:30/21:00 UTC — now session semantics only (`scheduled_at=None`, `scheduled_time_precision="session"`).
7. **Earnings unknown time**: Previously fabricated midnight UTC — now date precision only (`scheduled_time_precision="date"`).
8. **Estimate provenance**: Now preserved in metadata (`estimate_source`, `estimate_source_url`, `retrieved_at`, `consensus_as_of: null`).

## BLOCKERS
None. All changes are backward-compatible with the corrected semantics. No Phase 12 work required. No live trades, no paid services, no credentials exposed.