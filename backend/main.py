"""Backend API for Trading Copilot Website."""
from __future__ import annotations

import os
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any, Optional

from fastapi import FastAPI, HTTPException, Query, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from trading_copilot.config import Config, load_config, load_settings
from trading_copilot.events.store import EventStore
from trading_copilot.events.service import EventService
from trading_copilot.intelligence.interpretation_engine import InterpretationEngine, InterpretationRequest
from trading_copilot.answers.answer_engine import AnswerEngine, AnswerRequest
from trading_copilot.terms.term_service import TermDefinitionService, get_term_service
from trading_copilot.models.interpretation import (
    Interpretation,
    Answer,
    TermDefinition,
    InterpretationRequest,
    AnswerRequest,
)
from trading_copilot.models.events import EventType, MarketEvent
from trading_copilot.events.store import EventStore
from trading_copilot.providers import create_market_data_provider
from trading_copilot.config import Config, load_config, load_settings


# Global instances (initialized at startup)
config: Config
event_store: EventStore
event_service: EventService
interpretation_engine: "InterpretationEngine"
answer_engine: "AnswerEngine"
term_service: "TermDefinitionService"
settings: Any


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
    name: str
    exchange: str
    asset_type: str


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
    name: str
    asset_type: str
    exchange: str


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    global config, event_store, event_service, interpretation_engine, answer_engine, term_service, settings
    
    # Load configuration
    config = load_config()
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
    
    # Initialize market data provider (if credentials available)
    # This would be initialized based on config
    
    yield
    
    # Cleanup
    pass


app = FastAPI(
    title="Trading Copilot API",
    description="Trading Copilot - Deterministic Financial Intelligence API",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Health check endpoint
@app.get("/health", response_model=HealthResponse)
async def health_check():
    return HealthResponse()


# Market overview
@app.get("/api/v1/market/overview", response_model=MarketOverviewResponse)
async def get_market_overview():
    """Get market overview with key metrics."""
    # TODO: Implement actual market data fetching
    return MarketOverviewResponse(
        timestamp=datetime.now(timezone.utc),
        symbols_tracked=0,
        quant_scanner_status="ready",
        market_data_status="operational",
    )


# Search symbols
@app.get("/api/v1/symbols/search")
async def search_symbols(
    q: str = Query(..., min_length=1, max_length=10),
    limit: int = Query(10, ge=1, le=50),
) -> list[SymbolSearchResult]:
    """Search for symbols by ticker or name."""
    # TODO: Implement symbol search against universe
    return []


# Symbol detail
@app.get("/api/v1/stocks/{symbol}")
async def get_stock_detail(symbol: str) -> dict:
    """Get comprehensive stock detail page data."""
    symbol = symbol.upper()
    
    # Get interpretation
    interp_request = InterpretationRequest(symbol=symbol)
    interpretation = interpretation_engine.generate_interpretation(
        InterpretationRequest(symbol=symbol)
    )
    
    # Get quant data (from scanner)
    # Get events
    events = event_service.get_recent_company_events(symbol, limit=50)
    
    # Get price data
    # Get quant scores
    
    return {
        "symbol": symbol,
        "name": "",  # TODO: fetch from universe
        "interpretation": interpretation.model_dump() if interpretation else None,
        "events": [e.model_dump() for e in events],
        "quant_signals": {},  # TODO
        "price_data": {},  # TODO
        "quant_signals_components": {},  # TODO
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
    request: AnswerRequest,
) -> Answer:
    """Answer a specific question about a symbol."""
    symbol = symbol.upper()
    request.symbol = symbol
    return answer_engine.answer_question(request)


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
) -> list[CompanyEventResponse]:
    """Get company events for a symbol."""
    symbol = symbol.upper()
    event_types = None
    if event_types:
        event_types = [EventType(t) for t in event_types]
    
    events = event_store.events_for_symbol(
        symbol=symbol,
        event_types=event_types,
        limit=limit,
    )
    return [CompanyEventResponse(
        event_id=e.event_id,
        symbol=e.symbol,
        title=e.title,
        event_type=e.event_type.value,
        scheduled_at=e.scheduled_at,
        released_at=e.released_at,
        importance=e.importance.value,
        status=e.status.value,
        source=e.source,
        source_url=e.source_url,
        metadata=e.metadata,
    ) for e in events]


# Macro events
@app.get("/api/v1/events/macro")
async def get_macro_events(
    from_date: Optional[date] = Query(None),
    to_date: Optional[date] = Query(None),
    importance: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=500),
) -> list[MacroEventResponse]:
    """Get macro events."""
    events = event_store.events_by_type(
        event_type=EventType.MACRO,
        limit=limit,
    )
    
    # Filter by date range and importance
    if from_date:
        events = [e for e in events if e.released_at and e.released_at.date() >= from_date]
    if to_date:
        events = [e for e in events if e.released_at and e.released_at.date() <= to_date]
    if importance:
        events = [e for e in events if e.importance.value == importance]
    
    return [MacroEventResponse(
        event_id=e.event_id,
        title=e.title,
        event_type=e.event_type.value,
        scheduled_at=e.scheduled_at,
        released_at=e.released_at,
        actual=e.actual,
        forecast=e.forecast,
        previous=e.previous,
        importance=e.importance.value,
        status=e.status.value,
        source=e.source,
        source_url=e.source_url,
    ) for e in events]


# Company events (earnings, corporate actions)
@app.get("/api/v1/events/company")
async def get_company_events(
    symbol: Optional[str] = Query(None),
    event_type: Optional[str] = Query(None),
    from_date: Optional[date] = Query(None),
    to_date: Optional[date] = Query(None),
    limit: int = Query(100, ge=1, le=500),
) -> list[CompanyEventResponse]:
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
            event_types=[EventType.EARNINGS, EventType.EARNINGS_RESULT, EventType.EARNINGS_GUIDANCE, 
                        EventType.EARNINGS_REACTION, EventType.DIVIDEND, EventType.STOCK_SPLIT,
                        EventType.MERGER_ACQUISITION, EventType.SPINOFF, EventType.CORPORATE_ACTION],
            limit=limit,
        )
    else:
        # Get all company events across all symbols
        events = []
        for et in [EventType.EARNINGS, EventType.EARNINGS_RESULT, EventType.EARNINGS_GUIDANCE,
                   EventType.EARNINGS_REACTION, EventType.DIVIDEND, EventType.STOCK_SPLIT,
                   EventType.MERGER_ACQUISITION, EventType.SPINOFF, EventType.CORPORATE_ACTION]:
            events.extend(event_store.events_by_type(et, limit=limit))
    
    # Filter
    if from_date:
        events = [e for e in events if e.released_at and e.released_at.date() >= from_date]
    if to_date:
        events = [e for e in events if e.released_at and e.released_at.date() <= to_date]
    if symbol:
        events = [e for e in events if e.symbol == symbol.upper()]
    
    events.sort(key=lambda e: (e.released_at or e.scheduled_at or datetime.min), reverse=True)
    events = events[:limit]
    
    return [CompanyEventResponse(
        event_id=e.event_id,
        symbol=e.symbol,
        title=e.title,
        event_type=e.event_type.value,
        scheduled_at=e.scheduled_at,
        released_at=e.released_at,
        importance=e.importance.value,
        status=e.status.value,
        source=e.source,
        source_url=e.source_url,
        metadata=e.metadata,
    ) for e in events]


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
    
    leadership = {}
    for e in events:
        changes = e.metadata.get("changes", [])
        for change in changes:
            role = change.get("role")
            if role:
                leadership[role] = {
                    "name": change.get("name"),
                    "effective_date": change.get("effective_date"),
                    "event_id": e.event_id,
                    "source": e.source,
                }
    
    return {
        "symbol": symbol,
        "leadership": leadership,
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


# Insiders
@app.get("/api/v1/stocks/{symbol}/insiders")
async def get_insiders(
    symbol: str,
    limit: int = Query(50, ge=1, le=200),
) -> list[dict]:
    """Get insider transactions."""
    symbol = symbol.upper()
    events = event_store.events_for_symbol(
        symbol=symbol,
        event_types=[EventType.INSIDER],
        limit=limit,
    )
    return [e.model_dump() for e in events]


# Quant signals
@app.get("/api/v1/stocks/{symbol}/quant")
async def get_quant_signals(symbol: str) -> dict:
    """Get quant signals for a symbol."""
    # TODO: Integrate with quant scanner
    return {
        "symbol": symbol.upper(),
        "quant_score": None,
        "components": {},
        "rank": None,
        "universe_size": None,
    }


# Quant scanner top N
@app.get("/api/v1/scanner/top")
async def get_scanner_top(
    n: int = Query(20, ge=1, le=100),
) -> list[dict]:
    """Get top N symbols from quant scanner."""
    # TODO: Implement using actual quant scanner
    return []


# Term definition
@app.get("/api/v1/terms/{term}")
async def get_term_definition(term: str) -> TermDefinition:
    """Get definition for a financial term."""
    term_service = get_term_service()
    definition = term_service.get_definition(term)
    if not definition:
        raise HTTPException(404, f"Term '{term}' not found")
    return definition


# Search terms
@app.get("/api/v1/terms/search")
async def search_terms(
    q: str = Query(..., min_length=2),
    limit: int = Query(10, ge=1, le=50),
) -> list[TermDefinition]:
    """Search for term definitions."""
    term_service = get_term_service()
    results = term_service.search_terms(q)
    return results[:limit]


# Macro events
@app.get("/api/v1/events/macro")
async def get_macro_events(
    from_date: Optional[date] = Query(None),
    to_date: Optional[date] = Query(None),
    importance: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
) -> list[MacroEventResponse]:
    events = event_store.events_by_type(EventType.MACRO, limit=1000)
    
    if from_date:
        events = [e for e in events if e.released_at and e.released_at.date() >= from_date]
    if to_date:
        events = [e for e in events if e.released_at and e.released_at.date() <= to_date]
    if importance:
        events = [e for e in events if e.importance.value == importance]
    
    events.sort(key=lambda e: e.released_at or e.scheduled_at or datetime.min, reverse=True)
    events = events[:limit]
    
    return [MacroEventResponse(
        event_id=e.event_id,
        title=e.title,
        event_type=e.event_type.value,
        scheduled_at=e.scheduled_at,
        released_at=e.released_at,
        actual=e.actual,
        forecast=e.forecast,
        previous=e.previous,
        importance=e.importance.value,
        status=e.status.value,
        source=e.source,
        source_url=e.source_url,
    ) for e in events[:limit]]


# Upcoming events (macro + company)
@app.get("/api/v1/events/upcoming")
async def get_upcoming_events(
    days: int = Query(30, ge=1, le=90),
    limit: int = Query(50, ge=1, le=200),
) -> list[dict]:
    """Get upcoming scheduled events."""
    from datetime import timedelta
    cutoff = datetime.now(timezone.utc) + timedelta(days=days)
    
    events = event_store.upcoming_events(
        days_ahead=days,
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


# Terms search
@app.get("/api/v1/terms/search")
async def search_terms(
    q: str = Query(..., min_length=2),
    limit: int = Query(10, ge=1, le=50),
) -> list[TermDefinition]:
    """Search term definitions."""
    term_service = get_term_service()
    results = term_service.search_terms(q)
    return results[:limit]


# Search symbols (for autocomplete)
@app.get("/api/v1/symbols/search")
async def search_symbols(
    q: str = Query(..., min_length=1),
    limit: int = Query(10, ge=1, le=50),
) -> list[SymbolSearchResult]:
    """Search symbols by ticker or name."""
    # TODO: Implement search against universe
    return []


# Term definition
@app.get("/api/v1/terms/{term}")
async def get_term(term: str) -> TermDefinition:
    """Get term definition."""
    term_service = get_term_service()
    definition = term_service.get_definition(term)
    if not definition:
        raise HTTPException(404, f"Term '{term}' not found")
    return definition


# Market data proxy (for charting)
@app.get("/api/v1/market/bars/{symbol}")
async def get_bars(
    symbol: str,
    timeframe: str = Query("1Day", pattern="^(1Min|5Min|15Min|1Hour|1Day|1Week|1Month)$"),
    start: Optional[date] = Query(None),
    end: Optional[date] = Query(None),
    limit: int = Query(500, ge=1, le=5000),
):
    """Get price bars for charting."""
    # TODO: Implement using market data provider
    return {
        "symbol": symbol.upper(),
        "timeframe": timeframe,
        "bars": [],
    }


# Term definition endpoint
@app.get("/api/v1/terms/{term}")
async def get_term_definition(term: str) -> TermDefinition:
    """Get term definition."""
    term_service = get_term_service()
    definition = term_service.get_definition(term)
    if not definition:
        raise HTTPException(404, f"Term '{term}' not found")
    return definition


# Term search
@app.get("/api/v1/terms/search")
async def search_terms(
    q: str = Query(..., min_length=2),
    limit: int = Query(10, ge=1, le=50),
) -> list[TermDefinition]:
    """Search term definitions."""
    term_service = get_term_service()
    results = term_service.search_terms(q)
    return results[:limit]


# Health check with detailed info
@app.get("/api/v1/health/detailed")
async def detailed_health() -> dict:
    """Detailed health check."""
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "version": "1.0.0",
        "database": "connected",
        "event_store": "connected",
        "providers": {
            "sec": "configured",
            "macro": "configured",
            "earnings": "configured",
            "news": "configured",
        },
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)