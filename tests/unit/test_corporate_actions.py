"""Unit tests for CorporateActionsProvider."""

from __future__ import annotations

import json
import tempfile
from datetime import date, datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from trading_copilot.models.events import EventImportance, EventStatus, EventType
from trading_copilot.providers.corporate_actions import CorporateActionsProvider


MOCK_CORPORATE_ACTIONS_RESPONSE = {
    "corporate_actions": {
        "cash_dividends": [
            {
                "cusip": "037833100",
                "ex_date": "2026-10-05",
                "foreign": False,
                "id": "div_001",
                "payable_date": "2026-10-06",
                "process_date": "2026-10-06",
                "rate": 0.25,
                "record_date": "2026-10-05",
                "special": False,
                "symbol": "AAPL"
            }
        ],
        "reverse_splits": [
            {
                "ex_date": "2026-10-06",
                "id": "split_001",
                "new_cusip": "123456789",
                "new_rate": 1,
                "old_cusip": "987654321",
                "old_rate": 10,
                "payable_date": "2026-10-06",
                "process_date": "2026-10-06",
                "record_date": "2026-10-06",
                "symbol": "TEST"
            }
        ],
        "cash_mergers": [
            {
                "acquiree_cusip": "111111111",
                "acquiree_symbol": "TARGET",
                "effective_date": "2026-10-05",
                "id": "merger_001",
                "payable_date": "2026-10-06",
                "process_date": "2026-10-06",
                "rate": 50.0
            }
        ],
        "spin_offs": [
            {
                "ex_date": "2026-09-15",
                "id": "spinoff_001",
                "new_cusip": "999999999",
                "new_rate": 0.5,
                "new_symbol": "SPIN",
                "payable_date": "2026-10-06",
                "process_date": "2026-10-06",
                "record_date": "2026-09-15",
                "source_cusip": "888888888",
                "source_rate": 1,
                "source_symbol": "PARENT"
            }
        ],
        "stock_and_cash_mergers": [
            {
                "acquiree_cusip": "74736K101",
                "acquiree_rate": 1,
                "acquiree_symbol": "QRVO",
                "acquirer_cusip": "83088M102",
                "acquirer_rate": 0.96,
                "acquirer_symbol": "SWKS",
                "cash_rate": 32.5,
                "effective_date": "2026-10-05",
                "id": "scm_001",
                "payable_date": "2026-10-06",
                "process_date": "2026-10-06"
            }
        ],
        "stock_dividends": [],
        "worthless_removals": [],
        "rights_distributions": [],
        "name_changes": [],
        "forward_splits": [],
        "stock_splits": [],
    },
    "next_page_token": None
}


class TestCorporateActionsProvider:
    """Tests for CorporateActionsProvider."""

    @pytest.fixture
    def event_store(self):
        """Create a temporary event store."""
        from trading_copilot.events.store import EventStore

        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name

        store = EventStore(db_path)
        yield store
        store.close()
        import os
        os.unlink(db_path)

    @pytest.fixture
    def provider(self, event_store):
        """Create a corporate actions provider with temp event store."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.dict("os.environ", {"APCA_API_KEY_ID": "test_key", "APCA_API_SECRET_KEY": "test_secret"}):
                provider = CorporateActionsProvider(event_store, cache_dir=tmpdir)
                # Mock the client
                from unittest.mock import MagicMock
                mock_client = MagicMock()
                provider.client = mock_client
                
                mock_response = MagicMock()
                mock_response.status_code = 200
                mock_response.json.return_value = MOCK_CORPORATE_ACTIONS_RESPONSE
                mock_response.raise_for_status = MagicMock()
                provider.client.get.return_value = mock_response
                
                yield provider
                provider.close()

    def test_provider_initialization(self, provider):
        """Test provider initializes correctly."""
        assert provider is not None
        assert provider.event_store is not None
        assert provider.base_url == "https://data.alpaca.markets"

    def test_action_type_mapping(self, provider):
        """Test action type to EventType mapping."""
        assert provider.ACTION_TYPE_MAP["cash_dividends"] == EventType.DIVIDEND
        assert provider.ACTION_TYPE_MAP["reverse_splits"] == EventType.STOCK_SPLIT
        assert provider.ACTION_TYPE_MAP["cash_mergers"] == EventType.MERGER_ACQUISITION
        assert provider.ACTION_TYPE_MAP["spin_offs"] == EventType.SPINOFF

    def test_importance_mapping(self, provider):
        """Test importance mapping."""
        assert provider.IMPORTANCE_MAP["cash_dividends"] == EventImportance.LOW
        assert provider.IMPORTANCE_MAP["reverse_splits"] == EventImportance.HIGH
        assert provider.IMPORTANCE_MAP["cash_mergers"] == EventImportance.CRITICAL
        assert provider.IMPORTANCE_MAP["spin_offs"] == EventImportance.CRITICAL

    def test_normalize_cash_dividend(self, provider):
        """Test normalizing cash dividend action."""
        item = {
            "cusip": "037833100",
            "ex_date": "2026-10-05",
            "foreign": False,
            "id": "div_001",
            "payable_date": "2026-10-06",
            "process_date": "2026-10-06",
            "rate": 0.25,
            "record_date": "2026-10-05",
            "special": False,
            "symbol": "AAPL"
        }

        event = provider._normalize_action("cash_dividends", item, EventType.DIVIDEND, EventImportance.LOW)

        assert event is not None
        assert event["symbol"] == "AAPL"
        assert event["event_type"] == EventType.DIVIDEND
        assert event["importance"] == EventImportance.LOW
        assert "Dividend" in event["title"]
        assert "0.25" in event["title"]
        assert event["source_id"] == "alpaca_cash_dividends_AAPL_div_001"
        assert event["metadata"]["rate"] == 0.25
        assert event["metadata"]["ex_date"] == "2026-10-05"

    def test_normalize_reverse_split(self, provider):
        """Test normalizing reverse split action."""
        item = {
            "ex_date": "2026-10-06",
            "id": "split_001",
            "new_cusip": "123456789",
            "new_rate": 1,
            "old_cusip": "987654321",
            "old_rate": 10,
            "payable_date": "2026-10-06",
            "process_date": "2026-10-06",
            "record_date": "2026-10-06",
            "symbol": "TEST"
        }

        event = provider._normalize_action("reverse_splits", item, EventType.STOCK_SPLIT, EventImportance.HIGH)

        assert event is not None
        assert event["symbol"] == "TEST"
        assert event["event_type"] == EventType.STOCK_SPLIT
        assert event["importance"] == EventImportance.HIGH
        assert "10:1" in event["title"]
        assert event["metadata"]["old_rate"] == 10
        assert event["metadata"]["new_rate"] == 1

    def test_normalize_cash_merger(self, provider):
        """Test normalizing cash merger action."""
        item = {
            "acquiree_cusip": "111111111",
            "acquiree_symbol": "TARGET",
            "acquirer_symbol": "ACQUIRER",
            "effective_date": "2026-10-05",
            "id": "merger_001",
            "payable_date": "2026-10-06",
            "process_date": "2026-10-06",
            "rate": 50.0
        }

        event = provider._normalize_action("cash_mergers", item, EventType.MERGER_ACQUISITION, EventImportance.CRITICAL)

        assert event is not None
        assert event["symbol"] == "TARGET"
        assert event["event_type"] == EventType.MERGER_ACQUISITION
        assert event["importance"] == EventImportance.CRITICAL
        assert "TARGET acquired by ACQUIRER" in event["title"]
        assert event["metadata"]["acquiree_symbol"] == "TARGET"
        assert event["metadata"]["rate"] == 50.0

    def test_normalize_spin_off(self, provider):
        """Test normalizing spin-off action."""
        item = {
            "ex_date": "2026-09-15",
            "id": "spinoff_001",
            "new_cusip": "999999999",
            "new_rate": 0.5,
            "new_symbol": "SPIN",
            "payable_date": "2026-10-06",
            "process_date": "2026-10-06",
            "record_date": "2026-09-15",
            "source_cusip": "888888888",
            "source_rate": 1,
            "source_symbol": "PARENT"
        }

        event = provider._normalize_action("spin_offs", item, EventType.SPINOFF, EventImportance.CRITICAL)

        assert event is not None
        assert event["symbol"] == "PARENT"
        assert event["event_type"] == EventType.SPINOFF
        assert event["importance"] == EventImportance.CRITICAL
        assert "SPIN" in event["title"]
        assert event["metadata"]["new_symbol"] == "SPIN"

    def test_normalize_stock_and_cash_merger(self, provider):
        """Test normalizing stock and cash merger."""
        item = {
            "acquiree_cusip": "74736K101",
            "acquiree_rate": 1,
            "acquiree_symbol": "QRVO",
            "acquirer_cusip": "83088M102",
            "acquirer_rate": 0.96,
            "acquirer_symbol": "SWKS",
            "cash_rate": 32.5,
            "effective_date": "2026-10-05",
            "id": "scm_001",
            "payable_date": "2026-10-06",
            "process_date": "2026-10-06"
        }

        event = provider._normalize_action("stock_and_cash_mergers", item, EventType.MERGER_ACQUISITION, EventImportance.CRITICAL)

        assert event is not None
        assert "QRVO" in event["title"]
        assert "SWKS" in event["title"]
        assert event["metadata"]["cash_rate"] == 32.5
        assert event["metadata"]["acquirer_symbol"] == "SWKS"

    def test_create_market_event(self, provider):
        """Test creating MarketEvent from normalized action."""
        event_data = {
            "symbol": "AAPL",
            "title": "AAPL Dividend: $0.25/share",
            "description": "Cash dividend of $0.25 per share",
            "scheduled_at": datetime(2026, 10, 5, 0, 0, tzinfo=timezone.utc),
            "released_at": None,
            "importance": EventImportance.LOW,
            "status": EventStatus.SCHEDULED,
            "source": "alpaca",
            "source_url": "https://data.alpaca.markets",
            "source_id": "alpaca_cash_dividends_AAPL_div_001",
            "metadata": {
                "event_subtype": "cash_dividends",
                "provider_action_id": "div_001",
                "provider": "alpaca",
                "rate": 0.25,
                "ex_date": "2026-10-05",
            },
            "event_type": EventType.DIVIDEND,
        }

        event = provider._create_market_event(event_data)

        assert event.event_type == EventType.DIVIDEND
        assert event.symbol == "AAPL"
        assert event.title == "AAPL Dividend: $0.25/share"
        assert event.scheduled_at == datetime(2026, 10, 5, 0, 0, tzinfo=timezone.utc)
        assert event.importance == EventImportance.LOW
        assert event.status == EventStatus.SCHEDULED
        assert event.source == "alpaca"
        assert event.source_id == "alpaca_cash_dividends_AAPL_div_001"
        assert event.metadata["event_subtype"] == "cash_dividends"
        assert event.metadata["rate"] == 0.25

    def test_refresh_from_mock(self, provider, event_store):
        """Test refresh loads events from mocked API."""
        counts = provider.refresh()

        assert counts["NEW"] > 0
        assert counts["ERROR"] == 0

        # Verify events in store
        from trading_copilot.models.events import EventType
        
        # Check dividends
        div_events = event_store.events_by_type(EventType.DIVIDEND, limit=100)
        assert len(div_events) >= 1
        for e in div_events:
            assert e.event_type == EventType.DIVIDEND

        # Check splits
        split_events = event_store.events_by_type(EventType.STOCK_SPLIT, limit=100)
        assert len(split_events) >= 1
        for e in split_events:
            assert e.event_type == EventType.STOCK_SPLIT

        # Check mergers
        merger_events = event_store.events_by_type(EventType.MERGER_ACQUISITION, limit=100)
        assert len(merger_events) >= 1
        for e in merger_events:
            assert e.event_type == EventType.MERGER_ACQUISITION

        # Check spinoffs
        spinoff_events = event_store.events_by_type(EventType.SPINOFF, limit=100)
        assert len(spinoff_events) >= 1
        for e in spinoff_events:
            assert e.event_type == EventType.SPINOFF

    def test_refresh_idempotent(self, provider, event_store):
        """Test that refresh is idempotent."""
        counts1 = provider.refresh()
        counts2 = provider.refresh()

        assert counts1["NEW"] > 0
        assert counts2["UNCHANGED"] > 0
        assert counts2["NEW"] == 0

    def test_refresh_with_symbol_filter(self, provider, event_store):
        """Test refresh with symbol filter."""
        counts = provider.refresh(symbols=["AAPL"])
        
        assert counts["NEW"] >= 1
        
        # Should only have AAPL events
        from trading_copilot.models.events import EventType
        div_events = event_store.events_by_type(EventType.DIVIDEND, limit=100)
        for e in div_events:
            assert e.symbol == "AAPL"

    def test_refresh_with_action_type_filter(self, provider, event_store):
        """Test refresh with action type filter."""
        counts = provider.refresh(action_types=["cash_dividends"])
        
        assert counts["NEW"] >= 1
        
        # Should only have dividends (no splits, mergers, etc.)
        from trading_copilot.models.events import EventType
        split_events = event_store.events_by_type(EventType.STOCK_SPLIT, limit=100)
        assert len(split_events) == 0

    def test_get_upcoming_actions(self, provider, event_store):
        """Test getting upcoming corporate actions."""
        provider.refresh()
        
        upcoming = provider.get_upcoming_actions(days_ahead=60)
        
        assert len(upcoming) >= 1
        for event in upcoming:
            assert event.scheduled_at is not None
            # Compare dates since scheduled_at is at midnight UTC
            assert event.scheduled_at.date() >= datetime.now(timezone.utc).date()

    def test_get_upcoming_actions_with_symbol(self, provider, event_store):
        """Test getting upcoming actions for specific symbol."""
        provider.refresh()
        
        upcoming = provider.get_upcoming_actions(symbol="AAPL", days_ahead=60)
        
        for event in upcoming:
            assert event.symbol == "AAPL"

    def test_action_type_filter(self, provider):
        """Test filtering by action types."""
        events = provider.fetch_corporate_actions(action_types=["cash_dividends"])
        
        for event in events:
            assert event["metadata"]["event_subtype"] == "cash_dividends"

    def test_ex_date_filter(self, provider):
        """Test filtering by ex-date."""
        events = provider.fetch_corporate_actions(ex_date=date(2026, 10, 5))
        
        for event in events:
            ex_date_str = event["metadata"].get("ex_date")
            if ex_date_str:
                ex_date = datetime.fromisoformat(ex_date_str.replace("Z", "+00:00")).date()
                assert ex_date == date(2026, 10, 5)

    def test_symbol_normalization(self, provider):
        """Test that symbols are normalized to uppercase."""
        events = provider.fetch_corporate_actions(symbols=["aapl"])
        
        for event in events:
            assert event["symbol"] == event["symbol"].upper()

    def test_metadata_preservation(self, provider, event_store):
        """Test that key metadata fields are preserved."""
        provider.refresh()
        
        from trading_copilot.models.events import EventType
        div_events = event_store.events_by_type(EventType.DIVIDEND, limit=100)
        
        for event in div_events:
            assert "event_subtype" in event.metadata
            assert "provider_action_id" in event.metadata
            assert "provider" in event.metadata
            assert event.metadata["provider"] == "alpaca"
            assert "rate" in event.metadata


if __name__ == "__main__":
    pytest.main([__file__, "-v"])