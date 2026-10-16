"""Frozen, isolated regression coverage for provider audit findings 42–43."""
import sqlite3
from datetime import datetime, timedelta, timezone

import pytest

from trading_copilot.events.service import EventService
from trading_copilot.events.store import EventStore
from trading_copilot.intelligence.interpretation_engine import InterpretationEngine
from trading_copilot.models.events import EventType, MarketEvent, UpsertResult
from trading_copilot.models.interpretation import InterpretationRequest

T0 = datetime(2026, 10, 1, 12, tzinfo=timezone.utc)
T1 = T0 + timedelta(days=1)
T2 = T1 + timedelta(days=1)


@pytest.fixture
def history(tmp_path):
    clock = [T0]
    store = EventStore(tmp_path / "isolated.db", now=lambda: clock[0])
    return store, clock


def event(**kwargs):
    fields = dict(event_type=EventType.EARNINGS_RESULT, symbol="TEST", title="Results",
                  released_at=T0, source="SEC", source_url="https://www.sec.gov/original",
                  first_seen_at=T0, created_at=T0, updated_at=T0, last_seen_at=T0,
                  metadata={"eps_surprise": "1", "retrieved_at": T0.isoformat()})
    fields.update(kwargs)
    return MarketEvent(**fields)


def interpret(store, at):
    return InterpretationEngine(store).generate_interpretation(InterpretationRequest(symbol="TEST", as_of=at))


def test_metadata_only_mutation_rehashes_and_preserves_full_revision(history):
    store, clock = history
    original = event(metadata={"eps_surprise": "1", "evidence": {"quote": "old"}})
    assert store.upsert_event(original) == UpsertResult.NEW
    old_hash = original.content_hash
    clock[0] = T1
    changed = store.get_event(original.event_id)
    changed.metadata["eps_surprise"] = "-2"
    changed.metadata["evidence"]["quote"] = "new"
    assert EventService(store=store).upsert_event(changed) == UpsertResult.CHANGED
    current = store.get_event(original.event_id)
    assert current.content_hash != old_hash
    assert current.metadata["eps_surprise"] == "-2"
    assert current.first_seen_at == T0
    revision = store.get_revisions(original.event_id)[0]
    assert revision.changed_at == T1
    assert revision.changed_fields["metadata"]["evidence"]["quote"] == "old"
    assert revision.old_snapshot["source_url"] == original.source_url
    assert store.events_as_of(T0)[0].metadata["eps_surprise"] == "1"
    assert "beat by $1.00" in interpret(store, T0).what_happened
    assert "miss by $2.00" in interpret(store, T1).what_happened


def test_source_and_multiple_revisions_reconstruct_boundary(history):
    store, clock = history
    original = event()
    store.upsert_event(original)
    clock[0] = T1
    changed = store.get_event(original.event_id)
    changed.source = "company_ir"
    changed.source_url = "https://example.org/revised"
    changed.source_id = "release-2"
    changed.metadata["eps_surprise"] = "2"
    assert store.upsert_event(changed) == UpsertResult.CHANGED
    clock[0] = T2
    changed.metadata["eps_surprise"] = "3"
    assert store.upsert_event(changed) == UpsertResult.CHANGED
    historic = store.events_as_of(T0)[0]
    assert historic.source == "SEC"
    assert historic.source_id is None
    assert historic.metadata["eps_surprise"] == "1"
    assert store.events_as_of(T1)[0].metadata["eps_surprise"] == "2"
    refs = interpret(store, T0).supporting_evidence
    assert refs[0].url == original.source_url
    assert store.get_revisions(original.event_id)[1].changed_fields["source"] == "SEC"


def test_repeated_payload_does_not_revision_and_key_order_is_irrelevant(history):
    store, clock = history
    original = event(metadata={"a": 1, "b": 2})
    store.upsert_event(original)
    clock[0] = T1
    replay = event(metadata={"b": 2, "a": 1})
    assert store.upsert_event(replay) == UpsertResult.UNCHANGED
    assert store.get_revisions(original.event_id) == []
    assert store.get_event(original.event_id).last_seen_at == T1
    assert store.events_as_of(T0)[0].metadata["a"] == 1
    assert store.events_as_of(T0)[0].last_seen_at == T0


def test_datetime_metadata_hash_is_stable_after_storage(history):
    store, clock = history
    original = event(metadata={"retrieved_at": T0})
    store.upsert_event(original)
    clock[0] = T1
    assert store.upsert_event(original) == UpsertResult.UNCHANGED


def test_backdated_release_not_visible_before_first_seen(history):
    store, clock = history
    clock[0] = T1
    late = event()  # Caller-provided first_seen cannot backdate database observation.
    store.upsert_event(late)
    assert store.get_event(late.event_id).first_seen_at == T1
    assert store.events_as_of(T0) == []
    assert interpret(store, T0).supporting_evidence == []
    assert "Reported earnings" not in interpret(store, T0).what_happened


@pytest.mark.parametrize("key,value", [("retrieved_at", T2.isoformat()),
                                       ("published_at", T2.isoformat()),
                                       ("consensus_as_of", "invalid"),
                                       ("retrieved_at", "2026-10-01T00:00:00")])
def test_future_or_invalid_nested_evidence_is_not_historical(history, key, value):
    store, _ = history
    store.upsert_event(event(metadata={"eps_surprise": "99", "evidence": [{key: value}]}))
    assert store.events_as_of(T1) == []
    assert interpret(store, T1).supporting_evidence == []


def test_legacy_migration_retains_rows_without_fabricating_missing_history(history):
    store, clock = history
    original = event()
    store.upsert_event(original)
    clock[0] = T1
    changed = store.get_event(original.event_id)
    changed.actual = "2"
    store.upsert_event(changed)
    # Recreate only the revision table using the pre-migration schema, in isolated DB.
    with sqlite3.connect(store.db_path) as conn:
        conn.executescript("""
            ALTER TABLE event_revisions RENAME TO old_revisions;
            CREATE TABLE event_revisions (revision_id TEXT PRIMARY KEY, event_id TEXT NOT NULL,
                changed_at TEXT NOT NULL, changed_fields TEXT NOT NULL, changed_by TEXT NOT NULL);
            INSERT INTO event_revisions SELECT revision_id, event_id, changed_at, changed_fields,
                changed_by FROM old_revisions;
            DROP TABLE old_revisions;
        """)
    migrated = EventStore(store.db_path, now=lambda: T2)
    assert migrated.count_events() == 1
    revisions = migrated.get_revisions(original.event_id)
    assert len(revisions) == 1
    assert revisions[0].changed_fields == {"actual": None}
    assert revisions[0].old_snapshot is None
    assert migrated.events_as_of(T0) == []
    assert migrated.events_as_of(T1)[0].actual == "2"
    assert EventStore(store.db_path).count_events() == 1  # Idempotent migration.


def test_stored_management_and_news_are_consumed_without_impact_inference(history):
    store, _ = history
    statement = dict(statement_id="s1", symbol="TEST", speaker="Alex Executive",
                     statement="Demand remains strong", statement_type="demand",
                     source_document_id="d1", source_url="https://example.org/release",
                     published_at=T0.isoformat(), retrieved_at=T0.isoformat(),
                     source_type="company_ir", provider_id="ir",
                     evidence_span={"start": 0, "end": 21, "text": "Demand remains strong"})
    claim = dict(claim_id="c1", symbol="TEST", claim="Factory opened",
                 category="other", claim_type="fact", source_document_id="d2",
                 source_url="https://example.org/news", published_at=T0.isoformat(),
                 source_type="news_rss", provider_id="rss", verification_status="verified",
                 evidence_span={"start": 0, "end": 14, "text": "Factory opened"})
    store.upsert_event(event(event_type=EventType.NEWS, title="Company release",
                             metadata={"management_statements": [statement], "evidence_claims": [claim]}))
    result = interpret(store, T0)
    assert "Alex Executive stated: Demand remains strong" in result.what_happened
    assert "Factory opened" in result.what_happened
    assert "No recent management statements" not in result.missing_information
    assert "No recent news evidence" not in result.missing_information
    assert result.company_impact.direction.value == "unknown"
    assert len(result.supporting_evidence) == 1


def test_missing_unverified_or_malformed_claims_remain_missing(history):
    store, _ = history
    store.upsert_event(event(event_type=EventType.OTHER, metadata={
        "management_statements": [{"statement": "invented speaker"}],
        "evidence_claims": [{"claim": "unsupported"}],
    }))
    result = interpret(store, T0)
    assert "unsupported" not in result.what_happened
    assert "No recent management statements" in result.missing_information
    assert "No recent news evidence" in result.missing_information


def test_naive_as_of_rejected(history):
    store, _ = history
    with pytest.raises(ValueError, match="timezone-aware"):
        store.events_as_of(datetime(2026, 10, 1))
