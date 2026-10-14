"""Backend API for Trading Copilot Website."""
from __future__ import annotations

import os
from contextlib import asynccontextmanager
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Optional

from fastapi import FastAPI, HTTPException, Query, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from backend.website_data import WebsiteDataAdapter
from backend.website_sources import WebsiteSourceAdapter

from trading_copilot.config import Config, load_config, load_settings
from trading_copilot.events.store import EventStore
from trading_copilot.events.service import EventService
from trading_copilot.intelligence.interpretation_engine import InterpretationEngine, InterpretationRequest
from trading_copilot.answers.answer_engine import AnswerEngine, AnswerRequest
from trading_copilot.terms.term_service import TermDefinitionService, get_term_service
from trading_copilot.terms.term_service import TermDefinition
from trading_copilot.models.interpretation import (
    Interpretation,
    Answer,
    InterpretationRequest,
    AnswerRequest,
)
from trading_copilot.models.events import EventType, MarketEvent
from trading_copilot.providers import create_market_data_provider

# Phase 11 imports
from trading_copilot.watchlists.store import WatchlistStore
from trading_copilot.watchlists.service import WatchlistService
from trading_copilot.watchlists.models import (
    Watchlist,
    WatchlistCreate,
    WatchlistUpdate,
    WatchlistItem,
    WatchlistItemCreate,
    WatchlistItemUpdate,
    WatchlistWithItems,
)
from trading_copilot.calendar.service import CalendarService
from trading_copilot.calendar.models import (
    CalendarExportRequest,
    CalendarExportResponse,
)
from trading_copilot.alerts.store import AlertStore
from trading_copilot.alerts.service import AlertService
from trading_copilot.alerts.models import (
    Alert,
    AlertCreate,
    AlertUpdate,
    AlertTrigger,
    AlertTestRequest,
    AlertTestResponse,
)


# Global instances (initialized at startup)
config: Config = None  # type: ignore
event_store: EventStore = None  # type: ignore
event_service: EventService = None  # type: ignore
interpretation_engine: "InterpretationEngine" = None  # type: ignore
answer_engine: "AnswerEngine" = None  # type: ignore
term_service: "TermDefinitionService" = None  # type: ignore
settings: Any = None
market_adapter: WebsiteDataAdapter = None  # type: ignore
source_adapter: WebsiteSourceAdapter = None  # type: ignore

# Phase 11
watchlist_store: "WatchlistStore" = None  # type: ignore
watchlist_service: "WatchlistService" = None  # type: ignore
calendar_service: "CalendarService" = None  # type: ignore
alert_store: "AlertStore" = None  # type: ignore
alert_service: "AlertService" = None  # type: ignore


class HealthResponse(BaseModel):
    status: str = "healthy"
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    version: str = "1.0.0"


class MarketOverviewResponse(BaseModel):
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    symbols_tracked: int
    quant_scanner_status: str
    market_data_status: str


class SymbolSearchResult(BaseModel):
    symbol: str
    name: str | None
    exchange: str | None
    type: str
    source: str


class MarketOverviewData(BaseModel):
    spy_price: Optional[float] = None
    spy_change_pct: Optional[float] = None
    spy_timestamp: Optional[datetime] = None
    vix: Optional[float] = None
    dxy: Optional[float] = None


class MacroEventResponse(BaseModel):
    event_id: str
    title: str
    event_type: str
    scheduled_at: Optional[datetime] = None
    released_at: Optional[datetime] = None
    actual: Optional[str] = None
    forecast: Optional[str] = None
    previous: Optional[str] = None
    importance: str
    status: str
    source: str
    source_url: Optional[str] = None


class CompanyEventResponse(BaseModel):
    event_id: str
    symbol: str
    title: str
    event_type: str
    scheduled_at: Optional[datetime] = None
    released_at: Optional[datetime] = None
    importance: str
    status: str
    source: str
    source_url: Optional[str] = None
    metadata: dict = Field(default_factory=dict)


class SearchResult(BaseModel):
    symbol: str
    name: str | None
    type: str
    exchange: str | None


class QuestionBody(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    context: Optional[dict[str, Any]] = None


class ReorderBody(BaseModel):
    symbols: list[str] = Field(max_length=50)


def validate_symbol(symbol: str) -> str:
    import re
    symbol = symbol.strip().upper()
    if not re.fullmatch(r"[A-Z][A-Z0-9.-]{0,9}", symbol):
        raise HTTPException(400, "Invalid ticker symbol")
    return symbol


def event_time(event):
    value = event.scheduled_at or event.released_at
    return value.replace(tzinfo=timezone.utc) if value and value.tzinfo is None else value or datetime.min.replace(tzinfo=timezone.utc)


def filter_events(events, from_date=None, to_date=None, importance=None):
    if from_date and to_date and from_date > to_date:
        raise HTTPException(400, "from_date must not be after to_date")
    if importance and importance not in {"low", "medium", "high", "critical"}:
        raise HTTPException(400, "Invalid importance")
    return [e for e in events if (not from_date or (e.scheduled_at or e.released_at) and event_time(e).date() >= from_date)
            and (not to_date or (e.scheduled_at or e.released_at) and event_time(e).date() <= to_date)
            and (not importance or e.importance.value == importance)]


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    global config, event_store, event_service, interpretation_engine, answer_engine, term_service, settings, market_adapter, source_adapter
    
    # Load configuration
    config = load_config(Path(__file__).parent / "config.yaml")
    config.events.db_path = os.environ.get("TRADING_COPILOT_DB_PATH", str(Path(__file__).resolve().parents[1] / config.events.db_path))
    settings = load_settings()
    
    # Initialize event store
    event_store = EventStore(config.events.db_path)
    event_service = EventService(event_store)
    
    # Initialize intelligence engines
    from trading_copilot.intelligence.interpretation_engine import InterpretationEngine
    interpretation_engine = InterpretationEngine(event_store)
    
    from trading_copilot.answers.answer_engine import AnswerEngine
    answer_engine = AnswerEngine(event_store, interpretation_engine)
    
    term_service = get_term_service()
    
    market_adapter = WebsiteDataAdapter(config, settings, mode=os.environ.get("WEBSITE_DATA_MODE", "real"))
    source_adapter = WebsiteSourceAdapter(event_store, settings)
    # Bounded refresh at startup if explicitly enabled; no auto-scheduler.
    refresh_symbols_env = os.environ.get("WEBSITE_REFRESH_SYMBOLS")
    if os.environ.get("WEBSITE_REFRESH_PROVIDERS") == "1" and refresh_symbols_env:
        from starlette.concurrency import run_in_threadpool
        symbols = [s.strip().upper() for s in refresh_symbols_env.split(",") if s.strip()]
        if symbols:
            await run_in_threadpool(source_adapter.refresh, symbols)
    
    # Phase 11: Initialize watchlist, calendar, and alert services
    global watchlist_store, watchlist_service, calendar_service, alert_store, alert_service
    
    watchlist_store = WatchlistStore(config.events.db_path)
    watchlist_service = WatchlistService(watchlist_store)
    
    calendar_service = CalendarService(event_store)
    
    alert_store = AlertStore(config.events.db_path)
    alert_service = AlertService(alert_store)
    
    yield
    
    market_adapter.close()
    event_store.close()


app = FastAPI(
    title="Trading Copilot API",
    description="Trading Copilot - Deterministic Financial Intelligence API",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(ValueError)
async def invalid_service_input(request, exc):
    return JSONResponse(status_code=400, content={"detail": "Invalid request or service precondition"})


@app.exception_handler(KeyError)
async def missing_service_entity(request, exc):
    return JSONResponse(status_code=404, content={"detail": "Requested entity not found"})


# Health check endpoint
@app.get("/health", response_model=HealthResponse)
async def health_check():
    return HealthResponse()


# Market overview
@app.get("/api/v1/market/overview")
def get_market_overview():
    """Get market overview with key metrics."""
    return market_adapter.overview()


# Market refresh (bounded, server-side)
class RefreshRequest(BaseModel):
    symbols: list[str] = Field(default_factory=list, max_length=100)


@app.post("/api/v1/market/refresh")
async def refresh_market_data(request: RefreshRequest):
    """Trigger bounded provider refresh for specified symbols."""
    if not request.symbols:
        return {"status": "skipped", "reason": "No symbols provided", "state": source_adapter.state}
    symbols = [s.strip().upper() for s in request.symbols if s.strip()]
    if not symbols:
        return {"status": "skipped", "reason": "No valid symbols provided", "state": source_adapter.state}
    from starlette.concurrency import run_in_threadpool
    state = await run_in_threadpool(source_adapter.refresh, symbols)
    return {"status": "completed", "symbols": symbols, "state": state}


# Search symbols
@app.get("/api/v1/symbols/search")
def search_symbols(
    q: str = Query(..., min_length=1, max_length=10),
    limit: int = Query(10, ge=1, le=50),
) -> list[dict]:
    """Search for symbols by ticker or name."""
    return market_adapter.search(q, limit)


# Symbol detail
@app.get("/api/v1/stocks/{symbol}")
def get_stock_detail(symbol: str) -> dict:
    """Get comprehensive stock detail page data."""
    symbol = validate_symbol(symbol)
    
    # Get interpretation
    interpretation = interpretation_engine.generate_interpretation(
        InterpretationRequest(symbol=symbol)
    )
    
    # Get quant data (from scanner)
    # Get events
    events = event_store.events_for_symbol(symbol, limit=50)
    price = market_adapter.price(symbol)
    quant = market_adapter.quant(symbol)
    metadata = next((s for s in market_adapter.search(symbol, 50) if s["symbol"] == symbol), {})
    
    # Get price data
    # Get quant scores
    
    return {
        "symbol": symbol,
        "name": metadata.get("name"), "exchange": metadata.get("exchange"),
        "price": price["price"], "change": price["change"], "change_pct": price["change_pct"], "volume": price["volume"],
        "market_cap": None, "pe_ratio": None, "dividend_yield": None,
        "interpretation": interpretation.model_dump() if interpretation else None,
        "events": [e.model_dump() for e in events],
        "quant_signals": quant,
        "price_data": price,
        "quant_signals_components": quant["components"],
    }


# Interpretation endpoint
@app.get("/api/v1/stocks/{symbol}/interpretation")
async def get_interpretation(
    symbol: str,
    as_of: Optional[datetime] = None,
) -> Interpretation:
    """Get structured interpretation for a symbol."""
    symbol = symbol.upper()
    request = InterpretationRequest(symbol=symbol, as_of=as_of)
    interpretation = interpretation_engine.generate_interpretation(InterpretationRequest(symbol=symbol, as_of=as_of))
    return interpretation


# Answer engine
@app.post("/api/v1/stocks/{symbol}/answer")
async def answer_question(
    symbol: str,
    request: QuestionBody,
) -> Answer:
    """Answer a specific question about a symbol."""
    symbol = symbol.upper()
    return answer_engine.answer_question(AnswerRequest(symbol=validate_symbol(symbol), question=request.question, context=request.context))


# Q&A endpoint (GET for convenience)
@app.get("/api/v1/stocks/{symbol}/answer")
async def answer_question_get(
    symbol: str,
    question: str = Query(...),
) -> Answer:
    """Answer a specific question about a symbol."""
    symbol = symbol.upper()
    request = AnswerRequest(symbol=symbol, question=question)
    return answer_engine.answer_question(request)


# Earnings endpoint
@app.get("/api/v1/stocks/{symbol}/earnings")
async def get_earnings(symbol: str) -> list[dict]:
    """Get earnings history for a symbol."""
    symbol = symbol.upper()
    events = event_store.events_for_symbol(
        symbol=symbol,
        event_types=[EventType.EARNINGS, EventType.EARNINGS_RESULT, EventType.EARNINGS_GUIDANCE, EventType.EARNINGS_REACTION],
        limit=100,
    )
    return [e.model_dump() for e in events]


# Events endpoint
@app.get("/api/v1/stocks/{symbol}/events")
async def get_company_events(
    symbol: str,
    event_types: Optional[list[str]] = Query(None),
    limit: int = Query(50, ge=1, le=200),
) -> list[MarketEvent]:
    """Get company events for a symbol."""
    symbol = symbol.upper()
    if event_types:
        try:
            event_types = [EventType(t) for item in event_types for t in item.split(",")]
        except ValueError:
            raise HTTPException(400, "Invalid event type")
    
    events = event_store.events_for_symbol(
        symbol=symbol,
        event_types=event_types,
        limit=limit,
    )
    return events


# Macro events
@app.get("/api/v1/events/macro")
async def macro_events(
    from_date: Optional[date] = Query(None),
    to_date: Optional[date] = Query(None),
    importance: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=500),
) -> list[MarketEvent]:
    """Get macro events."""
    events = event_store.events_by_type(
        event_type=EventType.MACRO,
        limit=10000,
    )
    
    return filter_events(events, from_date, to_date, importance=importance)[:limit]


# Company events (earnings, corporate actions)
@app.get("/api/v1/events/company")
async def get_company_events(
    symbol: Optional[str] = Query(None),
    event_type: Optional[str] = Query(None),
    from_date: Optional[date] = Query(None),
    to_date: Optional[date] = Query(None),
    limit: int = Query(100, ge=1, le=500),
) -> list[MarketEvent]:
    """Get company events (earnings, corporate actions, etc.)."""
    event_types = None
    if event_type:
        try:
            event_types = [EventType(event_type)]
        except ValueError:
            raise HTTPException(400, f"Invalid event type: {event_type}")
    
    if symbol:
        events = event_store.events_for_symbol(
            symbol=symbol.upper(),
            event_types=event_types,
            limit=10000,
        )
    else:
        # Get all company events across all symbols
        events = []
        for et in event_types or [t for t in EventType if t != EventType.MACRO]:
            events.extend(event_store.events_by_type(et, limit=10000))
    
    # Filter on known event date, including scheduled events.
    if symbol:
        events = [e for e in events if e.symbol == symbol.upper()]
    
    events = filter_events(events, from_date, to_date)
    events.sort(key=lambda e: event_time(e), reverse=True)
    events = events[:limit]
    
    return [e for e in events if e.symbol is not None]


# News endpoint
@app.get("/api/v1/stocks/{symbol}/news")
async def get_news(
    symbol: str,
    limit: int = Query(20, ge=1, le=100),
    from_date: Optional[date] = Query(None),
    to_date: Optional[date] = Query(None),
) -> list[dict]:
    """Get news for a symbol."""
    symbol = symbol.upper()
    events = event_store.events_for_symbol(
        symbol=symbol,
        event_types=[EventType.NEWS],
        limit=limit,
    )
    
    if from_date:
        events = [e for e in events if e.released_at and e.released_at.date() >= from_date]
    if to_date:
        events = [e for e in events if e.released_at and e.released_at.date() <= to_date]
    
    return [e.model_dump() for e in events[:limit]]


# Insider activity
@app.get("/api/v1/stocks/{symbol}/insiders")
async def get_insider_activity(
    symbol: str,
    limit: int = Query(50, ge=1, le=200),
) -> list[dict]:
    """Get insider transactions for a symbol."""
    symbol = symbol.upper()
    events = event_store.events_for_symbol(
        symbol=symbol,
        event_types=[EventType.INSIDER],
        limit=limit,
    )
    return [e.model_dump() for e in events]


# Leadership
@app.get("/api/v1/stocks/{symbol}/leadership")
async def get_leadership(symbol: str) -> dict:
    """Get current leadership for a symbol."""
    symbol = symbol.upper()
    events = event_store.events_for_symbol(
        symbol=symbol,
        event_types=[EventType.LEADERSHIP],
        limit=10,
    )
    
    from trading_copilot.providers.filing_provider import SECFilingProvider
    provider = SECFilingProvider(event_store, user_agent=settings.sec_user_agent)
    try:
        state = provider.get_current_leadership(symbol)
    finally:
        provider.close()
    leadership = {}
    for role in ["CEO", "CFO"]:
        change = state.get(role)
        if change:
            evidence = next((e for e in events if e.source_id == change.get("source_id")), None)
            leadership[role] = {
                **change,
                "event_id": evidence.event_id if evidence else None,
                "released_at": evidence.released_at.isoformat() if evidence and evidence.released_at else None,
                # Explicitly preserve provenance fields from provider
                "source_url": change.get("source_url"),
                "retrieved_at": change.get("retrieved_at"),
                "filing_date": change.get("filing_date"),
            }
    
    return {
        "symbol": symbol,
        "leadership": leadership,
        "coverage": state["coverage"],
        "as_of": state["as_of"],
    }


# Filings
@app.get("/api/v1/stocks/{symbol}/filings")
async def get_filings(
    symbol: str,
    limit: int = Query(20, ge=1, le=100),
) -> list[dict]:
    """Get SEC filings for a symbol."""
    symbol = symbol.upper()
    events = event_store.events_for_symbol(
        symbol=symbol,
        event_types=[EventType.SEC_FILING],
        limit=limit,
    )
    return [e.model_dump() for e in events]


# Quant signals
@app.get("/api/v1/stocks/{symbol}/quant")
def get_quant_signals(symbol: str) -> dict:
    """Get quant signals for a symbol."""
    return market_adapter.quant(validate_symbol(symbol))


# Quant scanner top N
@app.get("/api/v1/scanner/top")
def get_scanner_top(
    n: int = Query(20, ge=1, le=100),
) -> list[dict]:
    """Get top N symbols from quant scanner."""
    return market_adapter.scan(n)


@app.get("/api/v1/scanner/status")
def get_scanner_status():
    return market_adapter.status()


# Term definition
@app.get("/api/v1/terms/search")
async def term_search(q: str = Query(..., min_length=2), limit: int = Query(10, ge=1, le=50)):
    return get_term_service().search_terms(q)[:limit]


@app.get("/api/v1/terms/{term}")
async def get_term_definition(term: str) -> TermDefinition:
    """Get definition for a financial term."""
    term_service = get_term_service()
    definition = term_service.get_definition(term)
    if not definition:
        raise HTTPException(404, f"Term '{term}' not found")
    return definition


# Upcoming events (macro + company)
@app.get("/api/v1/events/upcoming")
async def get_upcoming_events(
    days: int = Query(30, ge=1, le=90),
    limit: int = Query(50, ge=1, le=200),
) -> list[dict]:
    """Get upcoming scheduled events within the next N days."""
    from datetime import timedelta
    now = datetime.now(timezone.utc)
    cutoff = datetime.now(timezone.utc) + timedelta(days=days)
    
    events = event_store.upcoming_events(
        from_date=datetime.now(timezone.utc),
        to_date=cutoff,
        limit=limit,
    )
    return [e.model_dump() for e in events]


# Recent events
@app.get("/api/v1/events/recent")
async def get_recent_events(
    days: int = Query(7, ge=1, le=90),
    limit: int = Query(50, ge=1, le=200),
) -> list[dict]:
    """Get recently released events."""
    from datetime import timedelta
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    
    events = event_store.events_released_since(
        since=cutoff,
        limit=limit,
    )
    return [e.model_dump() for e in events]


# Market data proxy (for charting)
@app.get("/api/v1/market/bars/{symbol}")
def get_bars(
    symbol: str,
    timeframe: str = Query("1Day", pattern="^(1Min|5Min|15Min|1Hour|1Day|1Week|1Month)$"),
    start: Optional[date] = Query(None),
    end: Optional[date] = Query(None),
    limit: int = Query(500, ge=1, le=5000),
):
    """Get price bars for charting."""
    if timeframe != "1Day":
        raise HTTPException(400, "Only daily bars are supported by the current provider")
    return market_adapter.bars(validate_symbol(symbol), start, end, limit)


# Health check with detailed info
@app.get("/api/v1/health/detailed")
async def detailed_health() -> dict:
    """Detailed health check."""
    return {
        "status": "degraded" if market_adapter.provider is None else "ready",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "version": "1.0.0",
        "database": "connected",
        "event_store": "connected",
        "market": market_adapter.status(),
        "providers": source_adapter.state,
        "llm_enabled": False,
    }


# =============================================================================
# Phase 11: Watchlists + Calendar + Alerts
# =============================================================================

# --- Watchlists ---

@app.post("/api/v1/watchlists", response_model=Watchlist, status_code=201)
async def create_watchlist(watchlist: WatchlistCreate) -> Watchlist:
    """Create a new watchlist."""
    return watchlist_service.create_watchlist(watchlist)


@app.get("/api/v1/watchlists", response_model=list[Watchlist])
async def get_watchlists() -> list[Watchlist]:
    """Get all watchlists."""
    return watchlist_service.get_all_watchlists()


@app.get("/api/v1/watchlists/default", response_model=Watchlist)
async def get_default_watchlist() -> Watchlist:
    """Get the default watchlist."""
    watchlist = watchlist_service.get_default_watchlist()
    if not watchlist:
        raise HTTPException(404, "No default watchlist set")
    return watchlist


@app.get("/api/v1/watchlists/{watchlist_id}", response_model=WatchlistWithItems)
async def get_watchlist(watchlist_id: str) -> WatchlistWithItems:
    """Get a watchlist with all its items."""
    watchlist = watchlist_service.get_watchlist_with_items(watchlist_id)
    if not watchlist:
        raise HTTPException(404, "Watchlist not found")
    return watchlist


@app.patch("/api/v1/watchlists/{watchlist_id}", response_model=Watchlist)
async def update_watchlist(watchlist_id: str, update: WatchlistUpdate) -> Watchlist:
    """Update a watchlist."""
    watchlist = watchlist_service.update_watchlist(watchlist_id, update)
    if not watchlist:
        raise HTTPException(404, "Watchlist not found")
    return watchlist


@app.delete("/api/v1/watchlists/{watchlist_id}", status_code=204)
async def delete_watchlist(watchlist_id: str):
    """Delete a watchlist."""
    if not watchlist_service.delete_watchlist(watchlist_id):
        raise HTTPException(404, "Watchlist not found")


@app.post("/api/v1/watchlists/{watchlist_id}/set-default", response_model=Watchlist)
async def set_default_watchlist(watchlist_id: str) -> Watchlist:
    """Set a watchlist as the default."""
    watchlist = watchlist_service.set_default_watchlist(watchlist_id)
    if not watchlist:
        raise HTTPException(404, "Watchlist not found")
    return watchlist


# Watchlist Items

@app.get("/api/v1/watchlists/{watchlist_id}/items", response_model=list[WatchlistItem])
async def get_watchlist_items(watchlist_id: str) -> list[WatchlistItem]:
    """Get all items in a watchlist."""
    return watchlist_service.get_items(watchlist_id)


@app.post("/api/v1/watchlists/{watchlist_id}/items", response_model=WatchlistItem, status_code=201)
async def add_watchlist_item(watchlist_id: str, item: WatchlistItemCreate) -> WatchlistItem:
    """Add a symbol to a watchlist."""
    return watchlist_service.add_item(watchlist_id, item)


@app.get("/api/v1/watchlists/{watchlist_id}/items/{symbol}", response_model=WatchlistItem)
async def get_watchlist_item(watchlist_id: str, symbol: str) -> WatchlistItem:
    """Get a specific watchlist item."""
    item = watchlist_service.get_item(watchlist_id, symbol)
    if not item:
        raise HTTPException(404, "Item not found in watchlist")
    return item


@app.patch("/api/v1/watchlists/{watchlist_id}/items/{symbol}", response_model=WatchlistItem)
async def update_watchlist_item(watchlist_id: str, symbol: str, update: WatchlistItemUpdate) -> WatchlistItem:
    """Update a watchlist item."""
    item = watchlist_service.update_item(watchlist_id, symbol, update)
    if not item:
        raise HTTPException(404, "Item not found in watchlist")
    return item


@app.delete("/api/v1/watchlists/{watchlist_id}/items/{symbol}", status_code=204)
async def remove_watchlist_item(watchlist_id: str, symbol: str):
    """Remove a symbol from a watchlist."""
    if not watchlist_service.remove_item(watchlist_id, symbol):
        raise HTTPException(404, "Item not found in watchlist")


@app.post("/api/v1/watchlists/{watchlist_id}/reorder")
async def reorder_watchlist_items(watchlist_id: str, request: ReorderBody):
    """Reorder watchlist items."""
    if not watchlist_service.get_watchlist_with_items(watchlist_id):
        raise HTTPException(404, "Watchlist not found")
    watchlist_service.reorder_items(watchlist_id, request.symbols)
    return {"status": "ok"}


@app.get("/api/v1/watchlists/{watchlist_id}/symbols", response_model=list[str])
async def get_watchlist_symbols(watchlist_id: str) -> list[str]:
    """Get just the symbols in a watchlist."""
    return watchlist_service.get_symbols(watchlist_id)


@app.get("/api/v1/watchlists/symbol/{symbol}", response_model=list[Watchlist])
async def get_watchlists_for_symbol(symbol: str) -> list[Watchlist]:
    """Get all watchlists containing a symbol."""
    return watchlist_service.get_watchlists_for_symbol(symbol)


# --- Calendar Export ---

@app.post("/api/v1/calendar/export", response_model=CalendarExportResponse)
async def export_calendar(request: CalendarExportRequest) -> CalendarExportResponse:
    """Export events to calendar format (.ics)."""
    return calendar_service.export_events(request)


@app.get("/api/v1/calendar/export")
async def export_calendar_get(
    format: str = Query("ics", pattern="^ics$"),
    event_types: Optional[str] = Query(None),
    symbols: Optional[str] = Query(None),
    from_date: Optional[datetime] = Query(None),
    to_date: Optional[datetime] = Query(None),
    importance: Optional[str] = Query(None),
) -> CalendarExportResponse:
    """Export events to calendar format (.ics) via GET."""
    from trading_copilot.calendar.models import CalendarExportFormat, CalendarExportRequest
    from datetime import datetime
    
    request = CalendarExportRequest(
        format=CalendarExportFormat(format),
        event_types=event_types.split(",") if event_types else None,
        symbols=symbols.split(",") if symbols else None,
        from_date=from_date,
        to_date=to_date,
        importance=importance.split(",") if importance else None,
    )
    return calendar_service.export_events(request)


# --- Alerts ---

@app.post("/api/v1/alerts", response_model=Alert, status_code=201)
async def create_alert(alert: AlertCreate) -> Alert:
    """Create a new alert."""
    return alert_service.create_alert(alert)


@app.get("/api/v1/alerts", response_model=list[Alert])
async def get_alerts(active_only: bool = Query(False)) -> list[Alert]:
    """Get all alerts."""
    return alert_service.get_all_alerts(active_only=active_only)


@app.get("/api/v1/alerts/{alert_id}", response_model=Alert)
async def get_alert(alert_id: str) -> Alert:
    """Get an alert by ID."""
    alert = alert_service.get_alert(alert_id)
    if not alert:
        raise HTTPException(404, "Alert not found")
    return alert


@app.patch("/api/v1/alerts/{alert_id}", response_model=Alert)
async def update_alert(alert_id: str, update: AlertUpdate) -> Alert:
    """Update an alert."""
    alert = alert_service.update_alert(alert_id, update)
    if not alert:
        raise HTTPException(404, "Alert not found")
    return alert


@app.delete("/api/v1/alerts/{alert_id}", status_code=204)
async def delete_alert(alert_id: str):
    """Delete an alert."""
    if not alert_service.delete_alert(alert_id):
        raise HTTPException(404, "Alert not found")


@app.post("/api/v1/alerts/{alert_id}/activate", response_model=Alert)
async def activate_alert(alert_id: str) -> Alert:
    """Activate an alert."""
    alert = alert_service.activate_alert(alert_id)
    if not alert:
        raise HTTPException(404, "Alert not found")
    return alert


@app.post("/api/v1/alerts/{alert_id}/deactivate", response_model=Alert)
async def deactivate_alert(alert_id: str) -> Alert:
    """Deactivate an alert."""
    alert = alert_service.deactivate_alert(alert_id)
    if not alert:
        raise HTTPException(404, "Alert not found")
    return alert


@app.post("/api/v1/alerts/test", response_model=AlertTestResponse)
async def test_alert(request: AlertTestRequest) -> AlertTestResponse:
    """Test an alert against current data."""
    return alert_service.test_alert(request)


# Alert Triggers

@app.get("/api/v1/alerts/{alert_id}/triggers", response_model=list[AlertTrigger])
async def get_alert_triggers(
    alert_id: str,
    limit: int = Query(100, ge=1, le=500),
    unacknowledged_only: bool = Query(False),
) -> list[AlertTrigger]:
    """Get triggers for an alert."""
    return alert_service.get_triggers(alert_id=alert_id, limit=limit, unacknowledged_only=unacknowledged_only)


@app.get("/api/v1/alerts/triggers/recent", response_model=list[AlertTrigger])
async def get_recent_alert_triggers(
    hours: int = Query(24, ge=1, le=168),
    limit: int = Query(50, ge=1, le=200),
) -> list[AlertTrigger]:
    """Get recent alert triggers across all alerts."""
    return alert_service.get_recent_triggers(hours=hours, limit=limit)


@app.post("/api/v1/alerts/triggers/{trigger_id}/acknowledge")
async def acknowledge_alert_trigger(trigger_id: str):
    """Acknowledge an alert trigger."""
    if not alert_service.acknowledge_trigger(trigger_id):
        raise HTTPException(404, "Trigger not found")
    return {"status": "acknowledged"}


@app.post("/api/v1/alerts/{alert_id}/triggers/acknowledge-all")
async def acknowledge_all_alert_triggers(alert_id: str):
    """Acknowledge all triggers for an alert."""
    count = alert_service.acknowledge_all_for_alert(alert_id)
    return {"acknowledged": count}


if __name__ == "__main__":
    import uvicorn
    host = os.environ.get("WEB_API_HOST", "127.0.0.1")
    uvicorn.run(app, host=host, port=8000)
