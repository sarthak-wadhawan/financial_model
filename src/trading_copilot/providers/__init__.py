"""Providers package exports."""

from trading_copilot.providers.base import (
    UniverseProvider,
    MarketDataProvider,
    NewsProvider,
    FilingProvider,
    OptionsProvider,
    BaseProvider,
)
from trading_copilot.providers.mock import MockMarketDataProvider
from trading_copilot.providers.alpaca_market import AlpacaMarketDataProvider, create_market_data_provider
from trading_copilot.providers.macro_calendar import MacroCalendarProvider
from trading_copilot.providers.earnings_calendar import EarningsCalendarProvider
from trading_copilot.providers.earnings_intelligence import EarningsIntelligenceProvider
from trading_copilot.providers.earnings_reaction import EarningsReactionProvider
from trading_copilot.providers.earnings_parsers import extract_eps_revenue, extract_guidance_details, compute_surprise
from trading_copilot.providers.corporate_actions import CorporateActionsProvider
from trading_copilot.providers.filing_provider import SECFilingProvider
from trading_copilot.providers.sec_cik_map import SECCIKMap
from trading_copilot.providers.sec_exhibit_provider import SECExhibitProvider
from trading_copilot.providers.ir_release_provider import IRReleaseProvider
from trading_copilot.providers.news_rss_provider import NewsRSSProvider
from trading_copilot.providers.management_extractor import ManagementExtractor, COMMON_EXECUTIVES
from trading_copilot.providers.llm_provider import LLMProvider, DisabledLLMProvider, LocalLLMProvider, create_llm_provider
from trading_copilot.providers.evidence_claims import EvidenceClaimGenerator, DeduplicationEngine, create_evidence_claim_generator, create_deduplication_engine
from trading_copilot.intelligence.interpretation_engine import InterpretationEngine, create_interpretation_engine
from trading_copilot.answers.answer_engine import AnswerEngine, create_answer_engine
from trading_copilot.terms.term_service import TermDefinitionService, get_term_service, get_term_definition

__all__ = [
    "UniverseProvider",
    "MarketDataProvider",
    "NewsProvider",
    "FilingProvider",
    "OptionsProvider",
    "BaseProvider",
    "MockMarketDataProvider",
    "AlpacaMarketDataProvider",
    "create_market_data_provider",
    "MacroCalendarProvider",
    "EarningsCalendarProvider",
    "EarningsIntelligenceProvider",
    "EarningsReactionProvider",
    "extract_eps_revenue",
    "extract_guidance_details",
    "compute_surprise",
    "CorporateActionsProvider",
    "SECFilingProvider",
    "SECCIKMap",
    "SECExhibitProvider",
    "IRReleaseProvider",
    "NewsRSSProvider",
    "ManagementExtractor",
    "COMMON_EXECUTIVES",
    "LLMProvider",
    "DisabledLLMProvider",
    "LocalLLMProvider",
    "create_llm_provider",
    "EvidenceClaimGenerator",
    "DeduplicationEngine",
    "create_evidence_claim_generator",
    "create_deduplication_engine",
    "InterpretationEngine",
    "create_interpretation_engine",
    "AnswerEngine",
    "create_answer_engine",
    "TermDefinitionService",
    "get_term_service",
    "get_term_definition",
]
