"""Corporate actions provider using Alpaca API."""

from __future__ import annotations

import json
import logging
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Optional

import httpx

from trading_copilot.config import get_alpaca_config, load_settings
from trading_copilot.models.events import EventImportance, EventStatus, EventType, MarketEvent
from trading_copilot.providers.base import BaseProvider


logger = logging.getLogger(__name__)


class CorporateActionsProvider(BaseProvider):
    """Provider for corporate actions using Alpaca API.

    Fetches dividends, splits, mergers, spin-offs, and other corporate actions
    from Alpaca and upserts them into the event store.
    """

    # Alpaca corporate action types to EventType mapping
    ACTION_TYPE_MAP = {
        "cash_dividends": EventType.DIVIDEND,
        "stock_dividends": EventType.DIVIDEND,
        "reverse_splits": EventType.STOCK_SPLIT,
        "forward_splits": EventType.STOCK_SPLIT,
        "stock_splits": EventType.STOCK_SPLIT,
        "cash_mergers": EventType.MERGER_ACQUISITION,
        "stock_mergers": EventType.MERGER_ACQUISITION,
        "stock_and_cash_mergers": EventType.MERGER_ACQUISITION,
        "spin_offs": EventType.SPINOFF,
        "rights_distributions": EventType.CORPORATE_ACTION,
        "worthless_removals": EventType.CORPORATE_ACTION,
        "name_changes": EventType.CORPORATE_ACTION,
    }

    # Importance mapping
    IMPORTANCE_MAP = {
        "cash_dividends": EventImportance.LOW,
        "stock_dividends": EventImportance.MEDIUM,
        "reverse_splits": EventImportance.HIGH,
        "forward_splits": EventImportance.HIGH,
        "stock_splits": EventImportance.HIGH,
        "cash_mergers": EventImportance.CRITICAL,
        "stock_mergers": EventImportance.CRITICAL,
        "stock_and_cash_mergers": EventImportance.CRITICAL,
        "spin_offs": EventImportance.CRITICAL,
        "rights_distributions": EventImportance.MEDIUM,
        "worthless_removals": EventImportance.LOW,
        "name_changes": EventImportance.LOW,
    }

    def __init__(
        self,
        event_store: Any,
        cache_dir: str | Path = "artifacts/cache/corporate_actions",
        timeout: float = 30.0,
        api_key: str | None = None,
        api_secret: str | None = None,
        base_url: str = "https://data.alpaca.markets",
        feed: str = "iex",
    ):
        super().__init__()
        self.event_store = event_store
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.timeout = timeout
        self.base_url = base_url
        self.feed = feed

        # Load credentials
        settings = load_settings()
        alpaca_config = get_alpaca_config(settings)
        self.api_key = api_key or alpaca_config["api_key"]
        self.api_secret = api_secret or alpaca_config["api_secret"]

        if not self.api_key or not self.api_secret:
            raise ValueError(
                "Alpaca API credentials not provided. "
                "Set APCA_API_KEY_ID and APCA_API_SECRET_KEY environment variables."
            )

        self.client = httpx.Client(
            base_url=self.base_url,
            headers=self._auth_headers(),
            timeout=timeout,
        )

    def _auth_headers(self) -> dict[str, str]:
        """Return authentication headers for Alpaca API."""
        return {
            "APCA-API-KEY-ID": self.api_key,
            "APCA-API-SECRET-KEY": self.api_secret,
        }

    def fetch_corporate_actions(
        self,
        symbols: list[str] | None = None,
        ex_date: date | None = None,
        action_types: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        """Fetch corporate actions from Alpaca API.

        Args:
            symbols: Optional list of symbols to filter by
            ex_date: Optional ex-date to filter by (YYYY-MM-DD)
            action_types: Optional list of action types to filter by

        Returns:
            List of normalized corporate action events
        """
        all_actions = {}
        next_token = None
        endpoint = "/v1/corporate-actions"

        # Fetch all pages
        while True:
            url = endpoint if next_token is None else f"{endpoint}?page_token={next_token}"
            try:
                resp = self.client.get(url)
                resp.raise_for_status()
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 401:
                    logger.error("Alpaca API authentication failed - check credentials")
                elif e.response.status_code == 429:
                    logger.warning("Alpaca API rate limited")
                raise

            data = resp.json()
            corp_actions = data.get("corporate_actions", {})

            for key, items in corp_actions.items():
                if key not in all_actions:
                    all_actions[key] = []
                all_actions[key].extend(items)

            next_token = data.get("next_page_token")
            if not next_token:
                break

        # Normalize actions
        events = []
        for action_type, items in all_actions.items():
            if action_types and action_type not in action_types:
                continue

            event_type = self.ACTION_TYPE_MAP.get(action_type)
            if not event_type:
                logger.debug(f"Unknown action type: {action_type}")
                continue

            importance = self.IMPORTANCE_MAP.get(action_type, EventImportance.MEDIUM)

            for item in items:
                # Filter by symbols if provided
                symbol = item.get("symbol", "").upper()
                if symbols and symbol not in [s.upper() for s in symbols]:
                    continue

                # Filter by ex_date if provided
                item_ex_date = item.get("ex_date") or item.get("effective_date") or item.get("process_date")
                if ex_date and item_ex_date:
                    try:
                        item_date = datetime.fromisoformat(item_ex_date.replace("Z", "+00:00")).date()
                        if item_date != ex_date:
                            continue
                    except (ValueError, TypeError):
                        pass

                try:
                    event = self._normalize_action(action_type, item, event_type, importance)
                    if event:
                        events.append(event)
                except Exception as e:
                    logger.warning(f"Failed to normalize action {action_type} for {symbol}: {e}")
                    continue

        return events

    def _normalize_action(
        self,
        action_type: str,
        item: dict[str, Any],
        event_type: EventType,
        importance: EventImportance,
    ) -> Optional[dict[str, Any]]:
        """Normalize a corporate action item to our standard format."""
        # Different action types have different symbol fields
        if action_type in ("cash_mergers", "stock_mergers", "stock_and_cash_mergers"):
            symbol = item.get("acquiree_symbol", "").upper()
        elif action_type == "spin_offs":
            symbol = item.get("source_symbol", "").upper()
        else:
            symbol = item.get("symbol", "").upper()
        
        action_id = item.get("id", "")

        # Determine scheduled date
        scheduled_date_str = item.get("ex_date") or item.get("effective_date") or item.get("process_date")
        if not scheduled_date_str:
            return None

        try:
            scheduled_at = datetime.fromisoformat(scheduled_date_str.replace("Z", "+00:00"))
            if scheduled_at.tzinfo is None:
                scheduled_at = scheduled_at.replace(tzinfo=timezone.utc)
        except (ValueError, TypeError):
            scheduled_at = datetime.now(timezone.utc)

        # Build title and description based on action type
        if action_type in ("cash_dividends", "stock_dividends"):
            rate = item.get("rate", 0)
            title = f"{symbol} Dividend: ${rate:.4f}/share"
            description = f"Cash dividend of ${rate:.4f} per share"
            if action_type == "stock_dividends":
                title = f"{symbol} Stock Dividend: {rate:.4f}%"
                description = f"Stock dividend of {rate:.4f}%"
        elif action_type in ("reverse_splits", "forward_splits", "stock_splits"):
            old_rate = item.get("old_rate", 0)
            new_rate = item.get("new_rate", 0)
            ratio = f"{old_rate}:{new_rate}" if old_rate and new_rate else "unknown"
            title = f"{symbol} {action_type.replace('_', ' ').title()}: {ratio}"
            description = f"{action_type.replace('_', ' ').title()} with ratio {ratio}"
        elif action_type in ("cash_mergers", "stock_mergers", "stock_and_cash_mergers"):
            acquiree = item.get("acquiree_symbol", "")
            acquirer = item.get("acquirer_symbol", "")
            title = f"{acquiree} acquired by {acquirer}" if acquiree and acquirer else f"{symbol} Merger"
            description = f"Merger: {acquiree} acquired by {acquirer}"
        elif action_type == "spin_offs":
            source = item.get("source_symbol", "")
            new_sym = item.get("new_symbol", "")
            title = f"{source} Spin-off: {new_sym}"
            description = f"Spin-off of {new_sym} from {source}"
        else:
            title = f"{symbol} {action_type.replace('_', ' ').title()}"
            description = f"Corporate action: {action_type.replace('_', ' ')}"

        # Source ID for deduplication
        source_id = f"alpaca_{action_type}_{symbol}_{action_id}"

        # Build metadata preserving raw data
        metadata = {
            "event_subtype": action_type,
            "provider_action_id": action_id,
            "provider": "alpaca",
        }
        # Preserve key fields
        for key in ("rate", "old_rate", "new_rate", "ex_date", "payable_date", "record_date", "process_date",
                    "effective_date", "special", "foreign", "cusip", "new_cusip", "old_cusip",
                    "acquiree_symbol", "acquirer_symbol", "cash_rate", "new_symbol", "source_symbol"):
            if key in item:
                metadata[key] = item[key]

        return {
            "symbol": symbol,
            "title": title,
            "description": description,
            "scheduled_at": scheduled_at,
            "released_at": None,
            "importance": importance,
            "status": EventStatus.SCHEDULED,
            "source": "alpaca",
            "source_url": "https://data.alpaca.markets",
            "source_id": source_id,
            "metadata": metadata,
            "event_type": event_type,
        }

    def _create_market_event(self, event_data: dict[str, Any]) -> MarketEvent:
        """Create a MarketEvent from normalized action data."""
        return MarketEvent(
            event_type=event_data["event_type"],
            symbol=event_data.get("symbol"),
            title=event_data["title"],
            description=event_data.get("description", ""),
            scheduled_at=event_data.get("scheduled_at"),
            released_at=event_data.get("released_at"),
            timezone="UTC",
            importance=event_data.get("importance", EventImportance.MEDIUM),
            status=event_data.get("status", EventStatus.SCHEDULED),
            actual=event_data.get("actual"),
            forecast=event_data.get("forecast"),
            previous=event_data.get("previous"),
            unit=event_data.get("unit"),
            source=event_data.get("source", "alpaca"),
            source_url=event_data.get("source_url"),
            source_id=event_data.get("source_id"),
            metadata=event_data.get("metadata", {}),
        )

    def refresh(
        self,
        symbols: list[str] | None = None,
        action_types: list[str] | None = None,
    ) -> dict[str, int]:
        """Refresh corporate actions: fetch and upsert to store.

        Returns counts of NEW/UNCHANGED/CHANGED events.
        """
        counts = {"NEW": 0, "UNCHANGED": 0, "CHANGED": 0, "ERROR": 0}

        events = self.fetch_corporate_actions(symbols, action_types=action_types)
        for event_data in events:
            try:
                event = self._create_market_event(event_data)
                result = self.event_store.upsert_event(event)
                counts[result.value] += 1
            except Exception as e:
                logger.error(f"Failed to upsert corporate action: {e}")
                counts["ERROR"] += 1

        return counts

    def get_upcoming_actions(
        self,
        symbol: str | None = None,
        days_ahead: int = 30,
        action_types: list[str] | None = None,
    ) -> list[MarketEvent]:
        """Get upcoming corporate actions."""
        from datetime import timedelta
        from datetime import date
        start = datetime.now(timezone.utc)
        # Use start of today for date comparison
        start_date = start.date()
        end_date = start_date + timedelta(days=days_ahead)

        if symbol:
            events = self.event_store.events_for_symbol(
                symbol=symbol,
                event_types=[EventType.DIVIDEND, EventType.STOCK_SPLIT, EventType.MERGER_ACQUISITION,
                             EventType.SPINOFF, EventType.CORPORATE_ACTION],
                limit=100,
            )
        else:
            # Get all corporate action types
            events = []
            for et in [EventType.DIVIDEND, EventType.STOCK_SPLIT, EventType.MERGER_ACQUISITION,
                       EventType.SPINOFF, EventType.CORPORATE_ACTION]:
                events.extend(self.event_store.events_by_type(et, limit=100))

        filtered = []
        for e in events:
            if e.scheduled_at:
                event_date = e.scheduled_at.date()
                if start_date <= event_date <= end_date:
                    filtered.append(e)

        return sorted(filtered, key=lambda x: x.scheduled_at or datetime.max.replace(tzinfo=timezone.utc))

    def close(self) -> None:
        """Close HTTP client."""
        self.client.close()

    def health_check(self) -> bool:
        """Check if provider is available."""
        try:
            resp = self.client.get("/v1/corporate-actions", timeout=5.0)
            return resp.status_code == 200
        except Exception:
            return False


if __name__ == "__main__":
    # Quick test
    from trading_copilot.events.store import EventStore
    import tempfile
    import os

    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    store = EventStore(db_path)
    with tempfile.TemporaryDirectory() as tmpdir:
        provider = CorporateActionsProvider(store, cache_dir=tmpdir)
        counts = provider.refresh()
        print(f"Refresh counts: {counts}")

        # Check events
        events = store.events_by_type(EventType.DIVIDEND, limit=10)
        print(f"Total dividend events: {len(events)}")
        for e in events[:5]:
            print(f"  {e.symbol}: {e.scheduled_at} - {e.title}")

        events = store.events_by_type(EventType.STOCK_SPLIT, limit=10)
        print(f"Total split events: {len(events)}")
        for e in events[:5]:
            print(f"  {e.symbol}: {e.scheduled_at} - {e.title}")

        provider.close()
    store.close()
    os.unlink(db_path)