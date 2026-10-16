"""Read-only website adapter over the existing deterministic market pipeline.

No fixture fallback in real mode, no LLM, no broker/order endpoints.
"""
from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone
from threading import RLock, Event, Thread
from pathlib import Path
import time as clock
import hashlib
import json
import os
import uuid

from trading_copilot.config import get_alpaca_config
from trading_copilot.providers.alpaca_market import create_market_data_provider
from trading_copilot.pipeline.universe import MockUniverseProvider
from trading_copilot.pipeline.features import FeatureEngine
from trading_copilot.pipeline.eligibility import EligibilityFilter
from trading_copilot.pipeline.quant_score import QuantScorer
from trading_copilot.providers.sec_cik_map import SECCIKMap, DEFAULT_CACHE_DIR, SEC_EXCHANGE_TICKERS_URL


class OfficialIdentitySnapshot:
    """Shared official identity snapshot, independent of prices and event ingestion.

    A cold lookup may start ONE background map request via the normal SEC fair-access
    transport and wait at most one second. Subsequent reads share the job. Freshness
    is 24h; errors have a five-minute cooldown. Stale evidence remains readable.
    No submissions/filings crawl occurs in GET. ``refresh`` is the explicit write/
    network contract for operators and future normal-refresh integration.
    """
    WAIT_SECONDS = 1.0
    ERROR_COOLDOWN = 300

    def __init__(self, user_agent=None, cache_dir=DEFAULT_CACHE_DIR, transport=None):
        self.cik_map = SECCIKMap(cache_dir, max_age_days=1, user_agent=user_agent,
            transport=transport, source_url=SEC_EXCHANGE_TICKERS_URL)
        # Disk reads must not mutate the writer's in-flight normalization state.
        self._cache_reader = SECCIKMap(cache_dir, max_age_days=1,
            transport=self.cik_map.transport, source_url=SEC_EXCHANGE_TICKERS_URL)
        self.enabled = bool(user_agent or transport)
        self._lock = RLock()
        self._refresh_lock = RLock()
        self._done = Event()
        self._done.set()
        self._next_attempt = 0.0
        self._error = False
        self.mapping, self.snapshot = {}, {}
        self._cache_signature = None
        self._read_cache()

    def _read_cache(self):
        """Synchronize external provider refreshes, including a formerly missing file."""
        with self._lock:
            try:
                stat = self.cik_map.cache_file.stat()
                signature = (stat.st_mtime_ns, stat.st_size)
                if signature != self._cache_signature:
                    if self._cache_reader._load_cache(allow_stale=True):
                        self.mapping = dict(self._cache_reader._mapping)
                        self.snapshot = dict(self._cache_reader.snapshot)
                        self._error = False
                    else:
                        self._error = True
                    self._cache_signature = signature
            except OSError:
                pass

    def _fresh(self):
        fetched_at = self.snapshot.get("fetched_at")
        return (isinstance(fetched_at, (float, int))
                and 0 <= clock.time() - fetched_at < self.cik_map.max_age_seconds
                and self.snapshot.get("schema_version") == 2
                and self.snapshot.get("source_url") == SEC_EXCHANGE_TICKERS_URL)

    def refresh(self):
        """One official map, preserving raw facts/history. Never raises into UI."""
        with self._refresh_lock:
            self._refresh()

    def _refresh(self):
        try:
            self.cik_map.refresh()
            self._read_cache()
            with self._lock:
                self._error = False
        except Exception:
            with self._lock:
                self._error = True
        finally:
            with self._lock:
                self._next_attempt = clock.monotonic() + self.ERROR_COOLDOWN
                self._done.set()

    def record_submissions(self, raw, retrieved_at):
        """Accept already-fetched submissions only with an actual observation time.

        This does not fetch anything or infer an as-of date from a filing date/file
        mtime. Callers can bridge existing normal refresh without a second SEC GET.
        SIC is an industry scheme, never sector/GICS or an officer roster.
        """
        cik = str(raw["cik"]).zfill(10)
        observed = datetime.fromisoformat(retrieved_at.replace("Z", "+00:00"))
        if not cik.isdigit() or len(cik) != 10 or observed.tzinfo is None:
            raise ValueError("Invalid submissions observation")
        data = dict(raw=raw, retrieved_at=observed.isoformat(),
            source_url=f"https://data.sec.gov/submissions/CIK{cik}.json")
        data["snapshot_id"] = hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()
        folder = self.cik_map.cache_dir / "snapshots"
        folder.mkdir(exist_ok=True)
        encoded = json.dumps(data)
        (folder / (data["snapshot_id"] + ".json")).write_text(encoded)
        current = self.cik_map.cache_dir / f"submissions_{cik}.json"
        temporary = current.with_suffix(f".{uuid.uuid4().hex}.tmp")
        temporary.write_text(encoded)
        os.replace(temporary, current)

    def _submissions(self, symbol, cik):
        if not cik:
            return None
        try:
            data = json.loads((self.cik_map.cache_dir / f"submissions_{cik}.json").read_text())
            digest = hashlib.sha256(json.dumps({k: v for k, v in data.items()
                if k != "snapshot_id"}, sort_keys=True).encode()).hexdigest()
            raw = data["raw"]
            if (data["snapshot_id"] != digest or str(raw["cik"]).zfill(10) != cik
                    or symbol not in raw.get("tickers", [])
                    or data["source_url"] != f"https://data.sec.gov/submissions/CIK{cik}.json"):
                return None
            return data
        except (ValueError, KeyError, OSError, TypeError):
            return None

    def read(self):
        self._read_cache()
        with self._lock:
            cold = not self.mapping
            if (self.enabled and not self._fresh() and self._done.is_set()
                    and clock.monotonic() >= self._next_attempt):
                self._done.clear()
                Thread(target=self.refresh, name="sec-identity-snapshot", daemon=True).start()
        if cold:
            self._done.wait(self.WAIT_SECONDS)
        with self._lock:
            return dict(self.mapping), dict(self.snapshot)

    def identity(self, symbol):
        mapping, snapshot = self.read()
        entry = mapping.get(symbol, {})
        observed = snapshot.get("retrieved_at")
        url = snapshot.get("source_url")
        with self._lock:
            fresh, error, pending = self._fresh(), self._error, not self._done.is_set()
        status = ("available" if fresh and observed and entry.get("exchange") else "partial" if fresh else "stale"
                  if observed else "partial") if entry else (
                  "provider_error" if error else "empty" if fresh else "not_refreshed")
        fields = {}
        for field, key in (("name", "title"), ("cik", "cik"), ("exchange", "exchange")):
            if entry.get(key) is not None:
                fields[field] = dict(source_url=url, retrieved_at=observed,
                    evidence_span=json.dumps({"ticker": symbol, key: entry[key]}),
                    source_effective_at=None, snapshot_id=snapshot.get("snapshot_id"))
        industry = None
        submissions = self._submissions(symbol, entry.get("cik"))
        if submissions:
            raw = submissions["raw"]
            if raw.get("sic") and raw.get("sicDescription"):
                industry = dict(scheme="SEC_SIC", code=str(raw["sic"]), label=raw["sicDescription"])
                fields["industry"] = dict(source_url=submissions["source_url"],
                    retrieved_at=submissions["retrieved_at"], source_effective_at=None,
                    evidence_span=json.dumps({k: raw[k] for k in ("sic", "sicDescription")}),
                    snapshot_id=submissions["snapshot_id"])
        return dict(symbol=symbol, cik=entry.get("cik"), name=entry.get("title"),
            exchange=entry.get("exchange"), sector=None, industry=industry, description=None,
            status=status, coverage="official_ticker_map" if entry else "symbol_not_verified",
            source="SEC", source_url=url, retrieved_at=observed, verified_as_of=observed if entry else None,
            verification_scope="official_snapshot", fields=fields,
            snapshot_id=snapshot.get("snapshot_id"), refresh_pending=pending,
            refresh_status="provider_error" if error else "pending" if pending else "idle")


class WebsiteDataAdapter:
    def __init__(self, config, settings, provider=None, mode="real", identity_service=None):
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
        self.identity_service = identity_service or OfficialIdentitySnapshot(
            user_agent=settings.sec_user_agent if mode == "real" else None)

    def identity(self, symbol):
        return self.identity_service.identity(symbol.upper())

    def refresh_identity(self):
        """Explicit identity-only refresh; does not mutate the private event database."""
        self.identity_service.refresh()

    @property
    def metadata(self):
        return self.identity_service.read()[0]

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
        metadata = self.metadata
        symbols = set(self.symbols) | set(metadata)
        matches = [s for s in symbols if q in s or q in metadata.get(s, {}).get("title", "").upper()]
        return [dict(
            symbol=s,
            name=metadata.get(s, {}).get("title"),
            exchange=metadata.get(s, {}).get("exchange"),
            type="equity",
            source="SEC ticker cache" if s in metadata else "configured ticker universe"
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
