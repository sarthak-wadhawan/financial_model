"""Read-only website adapter over the existing deterministic market pipeline.

No fixture fallback in real mode, no LLM, no broker/order endpoints.
"""
from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone
from threading import RLock
from pathlib import Path
import json

from trading_copilot.config import get_alpaca_config
from trading_copilot.providers.alpaca_market import create_market_data_provider
from trading_copilot.pipeline.universe import MockUniverseProvider
from trading_copilot.pipeline.features import FeatureEngine
from trading_copilot.pipeline.eligibility import EligibilityFilter
from trading_copilot.pipeline.quant_score import QuantScorer


class WebsiteDataAdapter:
    def __init__(self, config, settings, provider=None, mode="real"):
        if mode not in {"real", "demo"}:
            raise ValueError("Invalid website data mode")
        self.config, self.mode = config, mode
        self.source = "mock (explicit demo)" if mode == "demo" else "Alpaca IEX"
        self.source_url = None if mode == "demo" else "https://data.alpaca.markets/v2/stocks/bars"
        self.provider = provider
        self.reason = None
        if provider is None:
            credentials = get_alpaca_config(settings)
            if mode == "real" and not all(credentials.values()):
                self.reason = "Alpaca credentials missing; real market data unavailable"
            else:
                self.provider = create_market_data_provider("mock" if mode == "demo" else "alpaca", credentials if mode == "real" else None)
        self._lock = RLock()
        self._bar_cache = {}
        self._candidates = []
        self._scanned_at = None
        self._scan_status = "unavailable"
        self._scan_reason = self.reason or "Scanner has not run"
        # A fixed ticker-only universe is legitimate; mock company names/exchanges are NOT.
        symbols = MockUniverseProvider.DEFAULT_SYMBOLS
        if config.universe.symbols_file:
            symbols = [s.strip().upper() for s in Path(config.universe.symbols_file).read_text().splitlines() if s.strip() and not s.startswith("#")]
        self.symbols = sorted(set(symbols))
        self.metadata = {}
        # Read previously retrieved official map without network/startup credential disclosure.
        cache = Path("artifacts/cache/sec_cik/company_tickers.json")
        if cache.exists():
            try:
                self.metadata = json.loads(cache.read_text()).get("mapping", {})
            except (ValueError, OSError):
                pass

    def _meta(self, status, reason=None, retrieved_at=None, market_timestamp=None):
        return dict(status=status, reason=reason, mode=self.mode, source=self.source,
                    source_url=self.source_url, retrieved_at=retrieved_at, market_timestamp=market_timestamp)

    def bars(self, symbol, start=None, end=None, limit=500):
        now = datetime.now(timezone.utc)
        start = start or (now - timedelta(days=max(400, self.config.market.history_days))).date()
        end = min(end or now.date(), now.date())
        if start > end:
            raise ValueError("start must not be after end")
        key = (symbol, start, end)
        with self._lock:
            cached = self._bar_cache.get(key)
            if cached and (now - cached[0]).total_seconds() < 300:
                return {**cached[1], "bars": cached[1]["bars"][-limit:]}
            result = dict(symbol=symbol, timeframe="1Day", bars=[], **self._meta("unavailable", self.reason))
            if self.provider is None:
                return result
            try:
                # Use get_daily_bars_with_status if available to get per-symbol status
                if hasattr(self.provider, "get_daily_bars_with_status"):
                    data, statuses = self.provider.get_daily_bars_with_status(
                        [symbol],
                        datetime.combine(start, time.min, timezone.utc),
                        datetime.combine(end + timedelta(days=1), time.min, timezone.utc)
                    )
                    symbol_status = statuses.get(symbol, "empty")
                else:
                    data = self.provider.get_daily_bars([symbol], datetime.combine(start, time.min, timezone.utc), datetime.combine(end + timedelta(days=1), time.min, timezone.utc))
                    symbol_status = "available" if data.get(symbol) else "empty"

                # Daily bars for the current session can be incomplete. Exclude them.
                bars = sorted([b for b in data.get(symbol, []) if start <= b.timestamp.date() <= end and b.timestamp.date() < now.date()], key=lambda b: b.timestamp)
                result["bars"] = [dict(t=b.timestamp.isoformat(), o=b.open, h=b.high, l=b.low, c=b.close, v=b.volume) for b in bars]
                timestamp = bars[-1].timestamp if bars else None

                # Determine status based on provider status and data
                if symbol_status == "provider_error":
                    status = "provider_error"
                    reason = "Market provider request failed"
                elif not bars:
                    status = "empty"
                    reason = "No bars returned; symbol coverage or provider failure unknown"
                else:
                    status = "stale" if timestamp and now - timestamp > timedelta(days=5) else "available"
                    reason = None

                provenance = getattr(self.provider, "last_retrieval_metadata", {}).get(symbol, {})
                result.update(self._meta(status, reason, provenance.get("retrieved_at"), timestamp.isoformat() if timestamp else None))
                result["source_url"] = provenance.get("source_url", self.source_url)
            except Exception:
                # Never serialize exception text: upstream requests can contain credentials.
                result.update(self._meta("provider_error", "Market provider request failed", now.isoformat()))
            self._bar_cache[key] = (now, result)
            return {**result, "bars": result["bars"][-limit:]}

    def search(self, q, limit=10):
        q = q.strip().upper()
        symbols = set(self.symbols) | set(self.metadata)
        matches = [s for s in symbols if q in s or q in self.metadata.get(s, {}).get("title", "").upper()]
        return [dict(
            symbol=s,
            name=self.metadata.get(s, {}).get("title"),
            exchange=self.metadata.get(s, {}).get("exchange"),
            type="equity",
            source="SEC ticker cache" if s in self.metadata else "configured ticker universe"
        ) for s in sorted(matches, key=lambda s: (s != q, s))[:limit]]

    def price(self, symbol):
        result = self.bars(symbol, limit=2)
        bars = result["bars"]
        price = bars[-1]["c"] if bars else None
        previous = bars[-2]["c"] if len(bars) > 1 else None
        return dict(price=price, change=price-previous if previous is not None else None,
                    change_pct=(price/previous-1)*100 if previous else None,
                    volume=bars[-1]["v"] if bars else None,
                    **{k: v for k, v in result.items() if k not in {"bars", "symbol", "timeframe"}}, price_kind="completed_daily_close")

    def scan(self, n=20):
        with self._lock:
            now = datetime.now(timezone.utc)
            if self._scanned_at and (now-self._scanned_at).total_seconds() < 300:
                return self._candidates[:n]
            if self.provider is None:
                return []
            try:
                symbols = sorted(set(self.symbols) | {self.config.market.benchmark})
                start = now-timedelta(days=max(400, self.config.market.history_days))
                # Use get_daily_bars_with_status to get per-symbol status and upstream retrieval time
                if hasattr(self.provider, "get_daily_bars_with_status"):
                    fetched, statuses = self.provider.get_daily_bars_with_status(symbols, start, now)
                else:
                    fetched = self.provider.get_daily_bars(symbols, start, now)
                    statuses = {s: "available" if fetched.get(s) else "empty" for s in symbols}
                provenance = dict(getattr(self.provider, "last_retrieval_metadata", {}))
                failed = [s for s in symbols if statuses.get(s) == "provider_error"]

                market = {s: sorted([b for b in fetched.get(s, []) if start <= b.timestamp <= now and b.timestamp.date() < now.date()], key=lambda b: b.timestamp) for s in symbols}
                benchmark = market.get(self.config.market.benchmark, [])
                if not hasattr(self.provider, "get_daily_bars_with_status") and hasattr(self.provider, "get_benchmark_bars"):
                    benchmark = sorted([b for b in self.provider.get_benchmark_bars(self.config.market.benchmark, start, now) if start <= b.timestamp <= now and b.timestamp.date() < now.date()], key=lambda b: b.timestamp)
                if len(benchmark) < 220:
                    self._scan_status = "provider_error" if self.config.market.benchmark in failed else "partial" if failed else "unavailable"
                    self._scan_reason = "Benchmark unavailable; relative-return scores not calculated"
                    self._candidates = []
                    self._scanned_at = now
                    return []
                benchmark_dates = {b.timestamp.date() for b in benchmark}
                features = EligibilityFilter(self.config.eligibility).apply(FeatureEngine().compute({s: market[s] for s in self.symbols if len(market[s]) >= self.config.eligibility.min_history_days and all(b.timestamp.date() in benchmark_dates for b in market[s][-126:])}, benchmark))
                by_symbol = {r.symbol: r for r in features}
                scores = QuantScorer(self.config.scoring.quant).score(features)
                self._candidates = [dict(symbol=s.symbol, rank=i+1, quant_score=s.quant_score,
                    momentum_score=s.momentum_score, trend_score=s.trend_score, liquidity_score=s.liquidity_score,
                    volume_score=s.volume_score, volatility_quality_score=s.volatility_score, components=s.components,
                    price=by_symbol[s.symbol].price, avg_dollar_volume_20d=by_symbol[s.symbol].avg_dollar_volume_20d,
                    calculated_at=now.isoformat(), market_timestamp=market[s.symbol][-1].timestamp.isoformat(),
                    source=self.source, mode=self.mode,
                    source_url=provenance.get(s.symbol, {}).get("source_url", self.source_url),
                    upstream_retrieved_at=provenance.get(s.symbol, {}).get("retrieved_at")) for i, s in enumerate(scores)]
                self._scan_status = ("partial" if scores else "provider_error") if failed else "stale" if any(now-market[s.symbol][-1].timestamp > timedelta(days=5) for s in scores) else "available" if scores else "empty"
                self._scan_reason = "Some market provider requests failed" if failed else None if scores else "No eligible symbols with sufficient completed daily history"
                self._scanned_at = now
            except Exception:
                self._scan_status, self._scan_reason = "provider_error", "Scanner market request failed"
                self._candidates = []
            return self._candidates[:n]

    def status(self):
        timestamps = [candidate["market_timestamp"] for candidate in self._candidates
                      if candidate.get("source") == self.source and candidate.get("mode") == self.mode
                      and candidate.get("market_timestamp")]
        return dict(status=self._scan_status, reason=self._scan_reason, source=self.source, mode=self.mode,
                    market_timestamp=max(timestamps, key=lambda value: datetime.fromisoformat(value.replace("Z", "+00:00"))) if timestamps else None,
                    calculated_at=self._scanned_at.isoformat() if self._scanned_at else None, universe_size=len(self.symbols))

    def quant(self, symbol):
        candidates = self.scan(len(self.symbols))
        candidate = next((s for s in candidates if s["symbol"] == symbol), None)
        return {**self.status(), "symbol": symbol, "quant_score": None, "rank": None, "components": {}, "signals": {}, "market_timestamp": None, **(candidate or {}), "reason": self._scan_reason if not candidate else None, "signals": candidate["components"] if candidate else {}}

    def overview(self):
        price = self.price(self.config.market.benchmark)
        now = datetime.now(timezone.utc).isoformat()
        indices = [dict(symbol=self.config.market.benchmark, **price)]
        for symbol, name in [("VIX", "Volatility index"), ("DXY", "US dollar index"), ("10Y", "US Treasury 10-year yield")]:
            indices.append(dict(
                symbol=symbol, price=None, change=None, change_pct=None, volume=None,
                status="unsupported", reason=f"{name} is not supported by the connected stock daily-bars provider; no proxy instrument is substituted",
                mode=self.mode, source=None, source_url=None, retrieved_at=None,
                market_timestamp=None, price_kind=None,
            ))
        return dict(timestamp=now, snapshot_time=price["retrieved_at"], market_status="unknown", symbols_tracked=len(self.symbols),
                    market_data_status=price["status"], quant_scanner_status=self._scan_status, reason=price["reason"],
                    mode=self.mode, source=self.source, source_url=self.source_url,
                    indices=indices,
                    top_gainers=[], top_losers=[], most_active=[])

    def close(self):
        if self.provider and hasattr(self.provider, "close"):
            self.provider.close()
