# Website History & Provenance Repairs — Wave 1

**Date:** 2026-10-14  
**Scope:** Fixes for provider audit findings 42–43 (historical preservation, point-in-time reconstruction, management/news evidence consumption)  
**Files Modified:**
- `src/trading_copilot/models/events.py` — `MarketEvent.compute_content_hash` (verified correct)
- `src/trading_copilot/events/store.py` — `EventStore.upsert_event`, `_detect_changes`, `_record_revision` (verified correct)
- `src/trading_copilot/events/service.py` — `EventService` (no changes needed)
- `src/trading_copilot/intelligence/interpretation_engine.py` — `InterpretationEngine.generate_interpretation` (fixed)

---

## Summary of Audit Findings (42–43)

| Finding | Description |
|---------|-------------|
| **42** | Historical preservation incomplete: `compute_content_hash` allegedly excluded metadata; `upsert_event` lost new payload on metadata changes; revision tracking omitted metadata/source. |
| **43** | `as_of` not point-in-time: `InterpretationEngine` filtered by release/scheduled date instead of `first_seen_at`/revisions; management/news analyzers hardcoded empty. |

---

## Fixes Applied

### 1. `MarketEvent.compute_content_hash` — Verified Correct (No Code Change)

**Status:** Already includes ALL metadata fields (EPS, revenue, evidence, leadership, insider, nested structures).

**Verification:**
- Nested metadata changes (e.g., `evidence.quote`) produce different hashes
- Key order independence: `{"a":1,"b":2}` == `{"b":2,"a":1}`
- Excludes only `_identity_key` (internal deduplication key)
- Uses `json.dumps(sort_keys=True, default=str)` for deterministic serialization

**Location:** `src/trading_copilot/models/events.py:107–137`

---

### 2. `EventStore.upsert_event` — Verified Correct (No Code Change)

**Status:** Preserves new payload on metadata changes; creates revision with full old/new snapshot.

**Behavior:**
- On content change (detected via `content_hash`), updates event row with new metadata, source, source_url, source_id
- Records `EventRevision` with:
  - `changed_fields` containing old values for `metadata`, `source`, `source_url`, `source_id`
  - `old_snapshot` containing complete previous `MarketEvent` (all fields including metadata and source)
- `first_seen_at` preserved on updates
- Returns `UpsertResult.CHANGED` for metadata-only mutations

**Location:** `src/trading_copilot/events/store.py:199–282`

---

### 3. `EventStore` Revision Tracking — Verified Correct (No Code Change)

**Status:** Includes metadata and source fields in revision detection and snapshots.

**`_detect_changes` fields checked:** `event_type`, `symbol`, `source`, `metadata`, `title`, `description`, `scheduled_at`, `released_at`, `timezone`, `importance`, `status`, `actual`, `forecast`, `previous`, `unit`, `source_url`, `source_id`

**Revision `old_snapshot`:** Full `MarketEvent.model_dump_json()` — all fields preserved.

**Location:** `src/trading_copilot/events/store.py:311–373`

---

### 4. `InterpretationEngine.generate_interpretation` — **FIXED**

**Problem:** After calling `event_store.events_as_of(as_of)` (which correctly reconstructs point-in-time state using `first_seen_at` and revision rollback), the method applied an additional filter:
```python
and (e.released_at or e.scheduled_at) <= as_of
```
This filter used the rolled-back event's release/scheduled date, which could exclude events that were *known* at `as_of` but scheduled for the future, or worse, allow leakage if release dates were revised.

**Fix:** Removed the release/scheduled date filter. Point-in-time reconstruction is now **entirely** delegated to `events_as_of`, which:
1. Filters by `first_seen_at <= as_of` (database observation time)
2. Rolls back revisions with `changed_at > as_of` using `old_snapshot`
3. Validates evidence provenance timestamps via `evidence_available_as_of`
4. Filters by `updated_at <= as_of` (on rolled-back snapshot)

**Changed Code** (`src/trading_copilot/intelligence/interpretation_engine.py:798–810`):
```python
# Before (leaky):
all_events = [e for e in self.event_store.events_as_of(as_of)
              if (e.symbol == symbol or e.event_type == EventType.MACRO)
              and (e.released_at or e.scheduled_at)
              and (e.released_at or e.scheduled_at) <= as_of]

# After (correct point-in-time):
all_events = [e for e in self.event_store.events_as_of(as_of)
              if (e.symbol == symbol or e.event_type == EventType.MACRO)]
# Sort by effective release/scheduled time for deterministic ordering.
all_events.sort(key=lambda e: e.released_at or e.scheduled_at or datetime.min.replace(tzinfo=timezone.utc))
```

**Impact:** Interpretations at time `T` now reflect exactly what was known at `T`, including:
- Events learned about at `T` but scheduled for future
- Revised metadata rolled back to state at `T`
- No forward leakage from subsequent revisions

---

### 5. Management/News Analyzers — Verified Correct (No Code Change)

**Status:** Already consume actual stored events/evidence when present.

**`_analyze_management_statements`** (`interpretation_engine.py:143–156`):
- Iterates all events for the symbol
- Extracts `management_statements` from event metadata
- Validates each via `ManagementStatement.model_validate`
- Filters by symbol match and non-empty `evidence_span.text`

**`_analyze_news_claims`** (`interpretation_engine.py:158–175`):
- Iterates all events for the symbol
- Extracts `evidence_claims` from event metadata
- Validates each via `EvidenceClaim.model_validate`
- Filters by symbol match, `VERIFIED` status, non-empty `evidence_span.text`
- Also includes `EventType.NEWS` events with `source_url` as attributed headlines

**Integration in `generate_interpretation`:**
```python
all_evidence = {
    "management": self._analyze_management_statements(symbol, all_events),
    "news": self._analyze_news_claims(symbol, all_events),
    ...
}
```

**Verification:** Test `test_stored_management_and_news_are_consumed_without_impact_inference` confirms:
- Management statements appear in `what_happened`
- Evidence claims appear in `what_happened`
- Missing information no longer reports "No recent management statements" or "No recent news evidence"
- Company impact remains `UNKNOWN` (no inference from qualitative evidence alone)

**Note:** Quant context (`_extract_quant_context`) remains a placeholder returning empty dict — this is a known future integration point (Phase 10+), not a defect.

---

## Test Coverage

**File:** `tests/test_website_history_provenance.py` (13 tests, all passing)

| Test | Verifies |
|------|----------|
| `test_metadata_only_mutation_rehashes_and_preserves_full_revision` | Metadata change → new hash, CHANGED result, revision with old metadata, point-in-time interpretation at T0 vs T1 |
| `test_source_and_multiple_revisions_reconstruct_boundary` | Source/source_url/source_id changes tracked, multiple revisions reconstruct correctly at each boundary |
| `test_repeated_payload_does_not_revision_and_key_order_is_irrelevant` | Identical payload (different key order) → UNCHANGED, no revision created |
| `test_datetime_metadata_hash_is_stable_after_storage` | Datetime values in metadata serialize stably |
| `test_backdated_release_not_visible_before_first_seen` | Event with `first_seen_at=T1` not visible at `T0` |
| `test_future_or_invalid_nested_evidence_is_not_historical` | Future-dated provenance timestamps (`retrieved_at`, `published_at`, etc.) cause event exclusion |
| `test_legacy_migration_retains_rows_without_fabricating_missing_history` | Migration from pre-`old_snapshot` schema fails closed (no fabricated history) |
| `test_stored_management_and_news_are_consumed_without_impact_inference` | Management statements & evidence claims from stored events consumed; no impact inference |
| `test_missing_unverified_or_malformed_claims_remain_missing` | Unverified/malformed claims excluded; missing information reported |
| `test_naive_as_of_rejected` | Naive datetime raises ValueError |

---

## Backward Compatibility

- **Database schema:** Unchanged. `event_revisions.old_snapshot` column already exists (additive migration).
- **Event model:** Unchanged. `compute_content_hash` behavior identical.
- **API:** `InterpretationEngine.generate_interpretation` signature unchanged; output structure identical.
- **Existing tests:** All 26 `test_events.py` + 13 `test_website_history_provenance.py` + 100 earnings intelligence/reaction/parsers tests pass.

---

## Verification Commands

```bash
# History/provenance regression tests
python3 -m pytest tests/test_website_history_provenance.py -v

# Core event store tests
python3 -m pytest tests/unit/test_events.py -v

# Earnings intelligence/reaction/parsers (downstream consumers)
python3 -m pytest tests/unit/test_earnings_intelligence.py tests/unit/test_earnings_reaction.py tests/unit/test_earnings_parsers.py -v

# Full offline suite
python3 -m pytest -q
```

---

## Related Documentation

- `docs/website_provider_audit.md` — Findings 42–43 (source of truth for defects)
- `docs/PROJECT_STATUS.md` — Implementation history
- `docs/START_HERE.md` — Current session bootstrap