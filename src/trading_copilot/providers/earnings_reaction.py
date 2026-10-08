"""Earnings Reaction Provider — measures raw market behavior around earnings events."""
from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from typing import Any, Optional

import pandas as pd

from trading_copilot.models.events import EventImportance, EventStatus, EventType, MarketEvent
from trading_copilot.models.market import DailyBar
from trading_copilot.providers.base import MarketDataProvider

logger = logging.getLogger(__name__)


def _json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


# NYSE/NASDAQ regular trading hours in UTC
MARKET_OPEN_UTC = time(13, 30)  # 8:30 AM ET
MARKET_CLOSE_UTC = time(20, 0)  # 3:00 PM ET

# After-hours trading window (approximate)
AH_START_UTC = time(20, 0)   # 4:00 PM ET
AH_END_UTC = time(0, 0)      # 8:00 PM ET (next day UTC)


@dataclass
class ReactionWindow:
    """Represents a single reaction window measurement."""
    name: str
    start: datetime
    end: datetime
    open_price: float | None = None
    close_price: float | None = None
    change_pct: float | None = None
    volume: int | None = None
    bars_available: bool = False


@dataclass
class BenchmarkReaction:
    """Benchmark (SPY) reaction for comparison."""
    symbol: str = "SPY"
    session_5_change_pct: float | None = None


class EarningsReactionProvider:
    """
    Computes reaction windows for released earnings events.
    
    Uses MarketDataProvider for price/volume data.
    All windows anchored to released_at (actual earnings release timestamp).
    Lookahead-safe: windows have explicit end boundaries.
    """

    def __init__(
        self,
        event_store: Any,
        market_data_provider: MarketDataProvider,
        cache_dir: str | Path = "artifacts/cache/earnings_reaction",
        benchmark_symbol: str = "SPY",
    ):
        self.event_store = event_store
        self.market_data = market_data_provider
        self.benchmark_symbol = benchmark_symbol
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.errors: list[dict[str, str]] = []

    def _error(self, symbol: str, stage: str, source_id: str, exc: Exception):
        self.errors.append({
            "symbol": symbol,
            "stage": stage,
            "source_id": source_id,
            "error": type(exc).__name__,
            "message": str(exc)[:300],
        })

    def _is_trading_day(self, dt: datetime) -> bool:
        """Check if a date is a trading day (Mon-Fri)."""
        return dt.weekday() < 5

    def _next_trading_day(self, dt: datetime) -> date:
        """Get the next trading day after the given date."""
        next_day = dt.date() + timedelta(days=1)
        while not self._is_trading_day(datetime.combine(next_day, time.min, tzinfo=timezone.utc)):
            next_day += timedelta(days=1)
        return next_day

    def _nth_trading_day(self, start: date, n: int) -> date:
        """Get the nth trading day after start (inclusive of start if trading day)."""
        current = start
        count = 0
        while count < n:
            if self._is_trading_day(datetime.combine(current, time.min, tzinfo=timezone.utc)):
                count += 1
                if count == n:
                    return current
            current += timedelta(days=1)
        return current

    def _get_reaction_windows(
        self,
        symbol: str,
        released_at: datetime,
        report_time: str,
    ) -> list[ReactionWindow]:
        """
        Define reaction windows based on earnings release time (BMO/AMC/unknown).
        
        All windows anchored to released_at.
        """
        windows = []
        released_date = released_at.date()
        
        if report_time == "bmo":
            # Before Market Open: released before 13:30 UTC
            # pre_market: prior close (19:59 UTC previous day) -> released_at
            prior_close = datetime.combine(released_date - timedelta(days=1), MARKET_CLOSE_UTC, tzinfo=timezone.utc)
            # Adjust to prior trading day
            while not self._is_trading_day(prior_close):
                prior_close -= timedelta(days=1)
                prior_close = datetime.combine(prior_close.date(), MARKET_CLOSE_UTC, tzinfo=timezone.utc)
            
            windows.append(ReactionWindow(
                name="pre_market",
                start=prior_close,
                end=released_at,
            ))
            
            # immediate_ah: released_at -> market close same day (20:00 UTC)
            windows.append(ReactionWindow(
                name="immediate_ah",
                start=released_at,
                end=datetime.combine(released_date, MARKET_CLOSE_UTC, tzinfo=timezone.utc),
            ))
            
            # next_session: next trading day open to close
            next_trading = self._next_trading_day(released_at)
            windows.append(ReactionWindow(
                name="next_session",
                start=datetime.combine(next_trading, MARKET_OPEN_UTC, tzinfo=timezone.utc),
                end=datetime.combine(next_trading, MARKET_CLOSE_UTC, tzinfo=timezone.utc),
            ))
            
        elif report_time == "amc":
            # After Market Close: released after 20:00 UTC
            # pre_market: not applicable for AMC
            # immediate_ah: released_at -> 3 hours after (or until ~23:00 UTC)
            ah_end = released_at + timedelta(hours=3)
            windows.append(ReactionWindow(
                name="immediate_ah",
                start=released_at,
                end=ah_end,
            ))
            
            # next_session: next trading day open to close
            next_trading = self._next_trading_day(released_at)
            windows.append(ReactionWindow(
                name="next_session",
                start=datetime.combine(next_trading, MARKET_OPEN_UTC, tzinfo=timezone.utc),
                end=datetime.combine(next_trading, MARKET_CLOSE_UTC, tzinfo=timezone.utc),
            ))
            
        else:
            # Unknown time: conservative defaults
            # Try to infer from released_at time
            if released_at.time() < MARKET_OPEN_UTC:
                # Likely BMO
                prior_close = datetime.combine(released_date - timedelta(days=1), MARKET_CLOSE_UTC, tzinfo=timezone.utc)
                while not self._is_trading_day(prior_close):
                    prior_close -= timedelta(days=1)
                    prior_close = datetime.combine(prior_close.date(), MARKET_CLOSE_UTC, tzinfo=timezone.utc)
                
                windows.append(ReactionWindow(
                    name="pre_market",
                    start=prior_close,
                    end=released_at,
                ))
                windows.append(ReactionWindow(
                    name="immediate_ah",
                    start=released_at,
                    end=datetime.combine(released_date, MARKET_CLOSE_UTC, tzinfo=timezone.utc),
                ))
            else:
                # Likely AMC or during market hours
                windows.append(ReactionWindow(
                    name="immediate_ah",
                    start=released_at,
                    end=released_at + timedelta(hours=3),
                ))
            
            # next_session: next trading day open to close
            next_trading = self._next_trading_day(released_at)
            windows.append(ReactionWindow(
                name="next_session",
                start=datetime.combine(next_trading, MARKET_OPEN_UTC, tzinfo=timezone.utc),
                end=datetime.combine(next_trading, MARKET_CLOSE_UTC, tzinfo=timezone.utc),
            ))
        
        # session_5: 5 trading sessions starting from next session
        next_trading = self._next_trading_day(released_at)
        fifth_trading = self._nth_trading_day(next_trading, 5)
        windows.append(ReactionWindow(
            name="session_5",
            start=datetime.combine(next_trading, MARKET_OPEN_UTC, tzinfo=timezone.utc),
            end=datetime.combine(fifth_trading, MARKET_CLOSE_UTC, tzinfo=timezone.utc),
        ))
        
        return windows

    def _fetch_window_data(
        self,
        symbol: str,
        window: ReactionWindow,
    ) -> ReactionWindow:
        """
        Fetch price/volume data for a reaction window.
        
        Uses daily bars and computes open/close from available data.
        """
        # Fetch daily bars covering the window
        start_date = window.start.date()
        end_date = window.end.date()
        
        # Add a buffer day before and after for safety
        fetch_start = datetime.combine(start_date - timedelta(days=1), time.min, tzinfo=timezone.utc)
        fetch_end = datetime.combine(end_date + timedelta(days=1), time.max, tzinfo=timezone.utc)
        
        try:
            bars_dict = self.market_data.get_daily_bars(
                symbols=[symbol],
                start=fetch_start,
                end=fetch_end,
            )
            bars = bars_dict.get(symbol, [])
        except Exception as e:
            logger.warning(f"Failed to fetch bars for {symbol}: {e}")
            return window
        
        if not bars:
            return window
        
        # Convert to DataFrame for easier manipulation
        df = pd.DataFrame([{
            "timestamp": bar.timestamp,
            "open": bar.open,
            "high": bar.high,
            "low": bar.low,
            "close": bar.close,
            "volume": bar.volume,
        } for bar in bars])
        
        # Filter bars within window
        window_start = window.start
        window_end = window.end
        mask = (df["timestamp"] >= window_start) & (df["timestamp"] <= window_end)
        window_bars = df[mask]
        
        if window_bars.empty:
            return window
        
        # Compute window metrics
        window.open_price = float(window_bars.iloc[0]["open"])
        window.close_price = float(window_bars.iloc[-1]["close"])
        window.change_pct = ((window.close_price - window.open_price) / window.open_price) * 100
        window.volume = int(window_bars["volume"].sum())
        window.bars_available = True
        
        return window

    def _fetch_benchmark_reaction(
        self,
        released_at: datetime,
    ) -> BenchmarkReaction:
        """Fetch benchmark (SPY) reaction for 5-session window."""
        next_trading = self._next_trading_day(released_at)
        fifth_trading = self._nth_trading_day(next_trading, 5)
        
        start = datetime.combine(next_trading, MARKET_OPEN_UTC, tzinfo=timezone.utc)
        end = datetime.combine(fifth_trading, MARKET_CLOSE_UTC, tzinfo=timezone.utc)
        
        fetch_start = datetime.combine(next_trading - timedelta(days=1), time.min, tzinfo=timezone.utc)
        fetch_end = datetime.combine(fifth_trading + timedelta(days=1), time.max, tzinfo=timezone.utc)
        
        try:
            bars_dict = self.market_data.get_daily_bars(
                symbols=[self.benchmark_symbol],
                start=fetch_start,
                end=fetch_end,
            )
            bars = bars_dict.get(self.benchmark_symbol, [])
        except Exception as e:
            logger.warning(f"Failed to fetch benchmark bars: {e}")
            return BenchmarkReaction()
        
        if not bars:
            return BenchmarkReaction()
        
        df = pd.DataFrame([{
            "timestamp": bar.timestamp,
            "open": bar.open,
            "close": bar.close,
        } for bar in bars])
        
        mask = (df["timestamp"] >= start) & (df["timestamp"] <= end)
        window_bars = df[mask]
        
        if window_bars.empty:
            return BenchmarkReaction()
        
        first_open = float(window_bars.iloc[0]["open"])
        last_close = float(window_bars.iloc[-1]["close"])
        change_pct = ((last_close - first_open) / first_open) * 100
        
        return BenchmarkReaction(
            symbol=self.benchmark_symbol,
            session_5_change_pct=round(change_pct, 2),
        )

    def compute_reactions(
        self,
        symbols: list[str] | None = None,
        from_date: date | None = None,
        to_date: date | None = None,
    ) -> dict[str, int]:
        """
        Compute reaction windows for all released earnings results.
        
        Returns counts of NEW/UNCHANGED/CHANGED/ERROR events.
        """
        if self.event_store is None:
            raise ValueError("EventStore required for earnings reaction")
        
        # Get all released EARNINGS_RESULT events
        if from_date is None:
            from_date = date(2020, 1, 1)
        if to_date is None:
            to_date = datetime.now(timezone.utc).date()
        
        # Query earnings result events
        if symbols:
            all_events = []
            for symbol in symbols:
                events = self.event_store.events_for_symbol(
                    symbol=symbol,
                    event_types=[EventType.EARNINGS_RESULT],
                    limit=1000,
                )
                all_events.extend(events)
        else:
            all_events = self.event_store.events_by_type(EventType.EARNINGS_RESULT, limit=10000)
        
        # Filter by released_at date range
        filtered_events = []
        for event in all_events:
            if event.released_at:
                released_date = event.released_at.date()
                if from_date <= released_date <= to_date:
                    filtered_events.append(event)
        
        counts = {"NEW": 0, "UNCHANGED": 0, "CHANGED": 0, "ERROR": 0}
        
        for event in filtered_events:
            try:
                # Check if reaction already exists
                existing = self.event_store.get_event_by_source_id(
                    f"{event.source_id}:reaction",
                    EventType.EARNINGS_REACTION
                )
                
                # Build reaction event
                reaction_event = self._create_reaction_event(event)
                
                if reaction_event:
                    result = self.event_store.upsert_event(reaction_event)
                    counts[result.value] += 1
                else:
                    counts["UNCHANGED"] += 1  # No reaction computed, skip
                    
            except Exception as exc:
                self._error(event.symbol or "unknown", "reaction", event.source_id, exc)
                counts["ERROR"] += 1
        
        return counts

    def _create_reaction_event(self, earnings_event: MarketEvent) -> MarketEvent | None:
        """Create EARNINGS_REACTION event from EARNINGS_RESULT."""
        if not earnings_event.released_at:
            return None
        
        symbol = earnings_event.symbol
        if not symbol:
            return None
        
        # Get report_time from metadata
        report_time = earnings_event.metadata.get("report_time", "unknown")
        
        # Get reaction windows
        windows = self._get_reaction_windows(symbol, earnings_event.released_at, report_time)
        
        # Fetch data for each window
        populated_windows = {}
        for window in windows:
            populated = self._fetch_window_data(symbol, window)
            populated_windows[window.name] = {
                "start": populated.start.isoformat() if populated.start else None,
                "end": populated.end.isoformat() if populated.end else None,
                "open": populated.open_price,
                "close": populated.close_price,
                "change_pct": populated.change_pct,
                "volume": populated.volume,
                "bars_available": populated.bars_available,
            }
        
        # Fetch benchmark
        benchmark = self._fetch_benchmark_reaction(earnings_event.released_at)
        
        # Check if we have any data
        has_data = any(w.get("bars_available") for w in populated_windows.values())
        if not has_data:
            return None
        
        # Build identity key
        identity_parts = [
            EventType.EARNINGS_REACTION.value,
            symbol,
            earnings_event.source_id,
        ]
        identity_key = hashlib.sha256("|".join(identity_parts).encode()).hexdigest()[:32]
        
        # Create reaction event
        return MarketEvent(
            event_type=EventType.EARNINGS_REACTION,
            symbol=symbol,
            title=f"{symbol} Earnings Reaction: {earnings_event.metadata.get('report_date', 'Unknown')}",
            description=_json({
                "earnings_event_id": earnings_event.event_id,
                "report_time": report_time,
                "windows": populated_windows,
                "benchmark": {
                    "symbol": benchmark.symbol,
                    "session_5_change_pct": benchmark.session_5_change_pct,
                },
            }),
            released_at=earnings_event.released_at,
            importance=EventImportance.MEDIUM,
            status=EventStatus.RELEASED,
            source="alpaca_iex",
            source_url="https://alpaca.markets",
            source_id=f"{earnings_event.source_id}:reaction",
            metadata={
                "earnings_event_id": earnings_event.event_id,
                "symbol": symbol,
                "report_time": report_time,
                "windows": populated_windows,
                "benchmark": {
                    "symbol": benchmark.symbol,
                    "session_5_change_pct": benchmark.session_5_change_pct,
                },
                "calculated_at": datetime.now(timezone.utc).isoformat(),
                "market_data_retrieved_at": datetime.now(timezone.utc).isoformat(),
                "_identity_key": identity_key,
            },
        )

    def get_reaction_history(
        self,
        symbol: str,
        limit: int = 20,
    ) -> list[MarketEvent]:
        """Get earnings reaction history for a symbol."""
        if self.event_store is None:
            raise ValueError("EventStore required for reaction history query")
        
        events = self.event_store.events_for_symbol(
            symbol=symbol,
            event_types=[EventType.EARNINGS_REACTION],
            limit=limit,
        )
        return sorted(events, key=lambda e: e.released_at or datetime.min.replace(tzinfo=timezone.utc), reverse=True)

    def close(self):
        """Close any resources."""
        pass