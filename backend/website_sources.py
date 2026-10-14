"""Bounded, explicit provider refresh using Phase 4/6/7/8 service paths.

Only external read operations. Local writes go through EventStore revision upsert.
Unsafe fixture/default-time paths are deliberately not used in real mode.
"""
from datetime import datetime, timedelta, timezone
from trading_copilot.models.events import MarketEvent, EventType, EventStatus
from trading_copilot.providers.filing_provider import SECFilingProvider
from trading_copilot.providers.earnings_intelligence import EarningsIntelligenceProvider
from trading_copilot.providers.macro_calendar import MacroCalendarProvider
from trading_copilot.providers.news_rss_provider import NewsRSSProvider


class DatedRSSProvider(NewsRSSProvider):
    def _parse_entry(self, feed_name, entry, from_date, to_date):
        # Upstream currently substitutes now() when no publication date exists.
        if not any(entry.get(k) for k in ["published_parsed", "updated_parsed", "created_parsed"]):
            return None
        return super()._parse_entry(feed_name, entry, from_date, to_date)


class WebsiteSourceAdapter:
    def __init__(self, store, settings):
        self.store, self.settings = store, settings
        self.state = {p: {"status": "not_refreshed", "retrieved_at": None, "reason": "Provider refresh not requested"} for p in ["sec", "earnings", "macro", "news"]}
        self.state.update({p: {"status":"unavailable", "retrieved_at":None, "reason":reason} for p, reason in {
            "bea":"Existing BEA response parser is incomplete; no live observations available",
            "census":"Existing Census response parser is incomplete; no live observations available",
            "earnings_calendar":"Existing calendar defaults to fixtures; no verified future earnings source configured"}.items()})

    def _run(self, name, operation):
        try:
            counts = operation()
            errors = counts.get("ERROR", 0)
            self.state[name] = {"status": "partial" if errors else "available" if counts.get("NEW", 0) + counts.get("UNCHANGED", 0) + counts.get("CHANGED", 0) else "empty",
                                "counts": counts, "retrieved_at": datetime.now(timezone.utc).isoformat(), "reason": "Some source requests failed" if errors else None}
        except Exception:
            self.state[name] = {"status": "provider_error", "retrieved_at": datetime.now(timezone.utc).isoformat(), "reason": "Source provider request failed"}

    def refresh(self, symbols):
        if self.settings.sec_user_agent:
            for name, cls in [("sec", SECFilingProvider), ("earnings", EarningsIntelligenceProvider)]:
                def operation(cls=cls):
                    provider = cls(self.store, user_agent=self.settings.sec_user_agent)
                    try:
                        return provider.refresh(symbols, lookback_days=45, max_per_symbol=4)
                    finally:
                        provider.close()
                self._run(name, operation)
        else:
            for name in ["sec", "earnings"]:
                self.state[name] = {"status":"unavailable", "reason":"SEC operator identity missing", "retrieved_at":None}
        self._run("macro", self._macro)
        self._run("news", lambda: self._news(symbols))
        return self.state

    def _macro(self):
        provider = MacroCalendarProvider(self.store)
        counts = {"NEW":0,"CHANGED":0,"UNCHANGED":0,"ERROR":0}
        try:
            # No current-year fixtures and no fabricated 18:00 decision/minutes times.
            try:
                for raw in provider._fetch_fomc_from_fed(datetime.now(timezone.utc).year):
                    raw["scheduled_at"] = None
                    raw["metadata"].pop("minutes_date", None)
                    raw["metadata"].update(event_date=raw["metadata"]["meeting_end"], time_precision="date", retrieved_at=datetime.now(timezone.utc).isoformat())
                    raw["description"] = f"Federal Reserve calendar: meeting {raw['metadata']['meeting_start']} to {raw['metadata']['meeting_end']}; exact decision time unknown"
                    counts[self.store.upsert_event(provider._create_market_event(raw)).value] += 1
            except Exception:
                counts["ERROR"] += 1
            for key in ["cpi", "core_cpi", "nfp", "unemployment_rate", "ppi", "jolts"]:
                series = provider.MACRO_EVENTS[key].metadata.get("series_id")
                if not series:
                    continue
                try:
                    observations = provider.fetch_bls_series(series, start_year=datetime.now(timezone.utc).year-1)
                    if not observations:
                        continue
                    latest = max(observations, key=lambda row: row["date"])
                    # Reference month is NOT publication date. Preserve it explicitly.
                    event = MarketEvent(event_type=EventType.MACRO, title=f"BLS {key} observation", actual=str(latest["value"]),
                        status=EventStatus.UNKNOWN, source="bls", source_url="https://www.bls.gov/data/", source_id=f"bls:{series}:{latest['date']}",
                        metadata={"series_id":series, "observation_period":latest["date"].strftime("%Y-%m"), "time_precision":"unknown",
                                  "retrieved_at":datetime.now(timezone.utc).isoformat(), "data_kind":"observation_not_release"})
                    counts[self.store.upsert_event(event).value] += 1
                except Exception:
                    counts["ERROR"] += 1
        finally:
            provider.close()
        return counts

    def _news(self, symbols):
        provider = DatedRSSProvider(timeout=10)
        documents = provider.fetch_news(symbols, from_date=(datetime.now(timezone.utc)-timedelta(days=7)).date())
        counts = {"NEW":0,"CHANGED":0,"UNCHANGED":0,"ERROR":len(provider.errors)}
        for document in documents:
            event = MarketEvent(event_type=EventType.NEWS, symbol=document.symbol, title=document.headline,
                description=document.body, released_at=document.published_at, status=EventStatus.RELEASED,
                source=document.publisher, source_url=document.source_url, source_id=document.document_id,
                metadata={"document":document.model_dump(mode="json"), "retrieved_at":document.retrieved_at.isoformat(), "claim_type":"attributed_statement"})
            counts[self.store.upsert_event(event).value] += 1
        return counts
