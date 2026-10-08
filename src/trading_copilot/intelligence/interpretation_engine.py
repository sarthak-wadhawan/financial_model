"""Interpretation Engine — deterministic synthesis of structured evidence into interpretations.

Zero-LLM core: all functionality works with LLM_ENABLED=false.
Optional local AI may enhance wording/synthesis only.
"""
from __future__ import annotations

import logging
from datetime import date, datetime, timezone
from typing import Any, Optional

from trading_copilot.events.store import EventStore
from trading_copilot.models.events import EventType, MarketEvent
from trading_copilot.models.interpretation import (
    Interpretation,
    InterpretationRequest,
    ImpactDirection,
    ImpactMagnitude,
    TimeHorizon,
    StockBias,
    Scenario,
    ScenarioType,
    CompanyImpact,
    StockImpact,
    Scenario,
    ViewChangeTrigger,
    EvidenceRef,
    ImpactDirection,
    ImpactMagnitude,
    TimeHorizon,
    StockBias,
)

logger = logging.getLogger(__name__)


class InterpretationEngine:
    """
    Deterministic synthesis engine that converts structured evidence into
    structured interpretations.

    All logic is deterministic. No LLM required for core functionality.
    Optional local LLM may enhance wording only.
    """

    def __init__(
        self,
        event_store: EventStore,
        llm_enabled: bool = False,
        llm_provider: Optional[Any] = None,
    ):
        self.event_store = event_store
        self.llm_enabled = llm_enabled
        self.llm_provider = llm_provider
        self._version = "1.0"

    def _get_evidence_refs(self, events: list[MarketEvent]) -> list:
        """Convert events to evidence references."""
        refs = []
        for event in events:
            refs.append(
                type('EvidenceRef', (), {
                    'evidence_id': event.event_id,
                    'source_type': event.source,
                    'description': event.title,
                    'url': event.source_url,
                    'timestamp': event.released_at or event.scheduled_at,
                })()
            )
        return refs

    def _extract_quant_context(self, symbol: str, as_of: Optional[datetime] = None) -> dict:
        """Extract quant context for a symbol from stored features/events."""
        # This would integrate with the quant scanner pipeline
        # For now, return empty context - to be filled by pipeline integration
        return {
            "quant_score": None,
            "trend": None,
            "momentum": None,
        }

    def _analyze_earnings_events(self, symbol: str, events: list) -> dict:
        """Analyze earnings-related events for interpretation."""
        result = {
            "has_earnings": False,
            "eps_surprise": None,
            "revenue_surprise": None,
            "guidance_direction": None,
            "reaction": None,
        }
        for event in events:
            if event.event_type.value == "earnings_result":
                result["has_earnings"] = True
                result["eps_surprise"] = event.metadata.get("eps_surprise")
                result["revenue_surprise"] = event.metadata.get("revenue_surprise")
            elif event.event_type.value == "earnings_guidance":
                result["guidance_direction"] = event.metadata.get("guidance_change")
            elif event.event_type.value == "earnings_reaction":
                windows = event.metadata.get("windows", {})
                result["reaction"] = {
                    "immediate_ah": windows.get("immediate_ah", {}).get("change_pct"),
                    "next_session": windows.get("next_session", {}).get("change_pct"),
                    "session_5": windows.get("session_5", {}).get("change_pct"),
                }
        return result

    def _analyze_macro_events(self, events: list) -> dict:
        """Analyze macro events for interpretation."""
        result = {
            "cpi_surprise": None,
            "nfp_surprise": None,
            "fomc_action": None,
            "rate_direction": None,
        }
        for event in events:
            if event.event_type.value == "macro":
                if "cpi" in event.title.lower():
                    result["cpi_surprise"] = event.metadata.get("surprise")
                elif "nfp" in event.title.lower() or "payroll" in event.title.lower():
                    result["nfp_surprise"] = event.metadata.get("surprise")
                elif "fomc" in event.title.lower():
                    result["fomc_action"] = event.metadata.get("action")
                    result["rate_direction"] = event.metadata.get("rate_change")
        return result

    def _analyze_sec_events(self, symbol: str, events: list) -> dict:
        """Analyze SEC filing events for interpretation."""
        result = {
            "leadership_change": None,
            "material_filing": None,
            "insider_signals": [],
        }
        for event in events:
            if event.event_type.value == "leadership":
                result["leadership_change"] = event.metadata.get("changes")
            elif event.event_type.value == "sec_filing":
                result["material_filing"] = event.metadata.get("items")
            elif event.event_type.value == "insider":
                result["insider_signals"].append(event.metadata)
        return result

    def _analyze_management_statements(self, symbol: str) -> list:
        """Analyze management statements from Phase 8."""
        # This would query the management statements from event store
        # For now, return empty - to be integrated with Phase 8 data
        return []

    def _analyze_news_claims(self, symbol: str) -> list:
        """Analyze news evidence claims from Phase 8."""
        # This would query evidence claims from event store
        # For now, return empty - to be integrated with Phase 8 data
        return []

    def _determine_company_impact(self, symbol: str, all_evidence: dict) -> tuple:
        """Determine company impact from all evidence."""
        reasons = []
        evidence_refs = []
        direction = ImpactDirection.UNKNOWN
        magnitude = ImpactMagnitude.UNKNOWN
        horizon = TimeHorizon.UNKNOWN
        confidence = 0.3

        earnings = all_evidence.get("earnings", {})
        macro = all_evidence.get("macro", {})
        sec = all_evidence.get("sec", {})
        management = all_evidence.get("management", [])
        news = all_evidence.get("news", [])

        # Earnings-based impact
        if earnings.get("has_earnings"):
            eps_surprise = earnings.get("eps_surprise")
            rev_surprise = earnings.get("revenue_surprise")
            guidance_dir = earnings.get("guidance_direction")

            if eps_surprise is not None:
                try:
                    eps_val = float(eps_surprise)
                    if eps_val > 0:
                        reasons.append(f"EPS beat by ${eps_val:.2f}")
                        direction = ImpactDirection.POSITIVE
                        magnitude = ImpactMagnitude.MEDIUM
                        horizon = TimeHorizon.MEDIUM_TERM
                    elif eps_val < 0:
                        reasons.append(f"EPS miss by ${abs(eps_val):.2f}")
                        direction = ImpactDirection.NEGATIVE
                        magnitude = ImpactMagnitude.MEDIUM
                        horizon = TimeHorizon.MEDIUM_TERM
                except ValueError:
                    pass

            if rev_surprise is not None:
                try:
                    rev_val = float(rev_surprise)
                    if rev_val > 0:
                        reasons.append(f"Revenue beat by ${rev_val:,.0f}")
                        if direction != ImpactDirection.NEGATIVE:
                            direction = ImpactDirection.POSITIVE
                            magnitude = ImpactMagnitude.MEDIUM
                    elif rev_val < 0:
                        reasons.append(f"Revenue miss by ${abs(rev_val):,.0f}")
                        if direction != ImpactDirection.POSITIVE:
                            direction = ImpactDirection.NEGATIVE
                            magnitude = ImpactMagnitude.MEDIUM
                except ValueError:
                    pass

            if guidance_dir:
                reasons.append(f"Guidance {guidance_dir}")
                if guidance_dir == "raised":
                    direction = ImpactDirection.POSITIVE
                    magnitude = ImpactMagnitude.HIGH
                elif guidance_dir == "lowered":
                    direction = ImpactDirection.NEGATIVE
                    magnitude = ImpactMagnitude.HIGH

        # SEC-based impact
        if sec.get("leadership_change"):
            reasons.append(f"Leadership change: {sec['leadership_change']}")
            if direction == ImpactDirection.UNKNOWN:
                direction = ImpactDirection.MIXED
                magnitude = ImpactMagnitude.MEDIUM

        # Macro impact
        if macro.get("rate_direction") is not None:
            try:
                rate_change = float(macro["rate_direction"])
                if rate_change < 0:
                    reasons.append("Rate cut supportive")
                    if direction != ImpactDirection.NEGATIVE:
                        direction = ImpactDirection.POSITIVE
                        magnitude = ImpactMagnitude.LOW
                elif rate_change > 0:
                    reasons.append("Rate hike headwind")
                    if direction != ImpactDirection.POSITIVE:
                        direction = ImpactDirection.NEGATIVE
                        magnitude = ImpactMagnitude.LOW
            except ValueError:
                pass

        # Set default confidence based on evidence richness
        evidence_count = sum([
            1 if earnings.get("has_earnings") else 0,
            1 if macro.get("cpi_surprise") else 0,
            1 if sec.get("leadership_change") else 0,
            1 if management else 0,
            1 if news else 0,
        ])
        confidence = min(0.3 + evidence_count * 0.15, 0.9)

        return CompanyImpact(
            direction=direction,
            magnitude=magnitude,
            horizon=horizon if horizon != TimeHorizon.UNKNOWN else TimeHorizon.MEDIUM_TERM,
            reasons=reasons,
            evidence_refs=evidence_refs,
            confidence=confidence,
        )

    def _determine_stock_impact(self, symbol: str, all_evidence: dict, company_impact: CompanyImpact) -> tuple:
        """Determine stock impact from evidence and company impact."""
        reasons = []
        evidence_refs = []
        bias = StockBias.UNKNOWN
        magnitude = ImpactMagnitude.UNKNOWN
        horizon = TimeHorizon.UNKNOWN

        earnings = all_evidence.get("earnings", {})
        macro = all_evidence.get("macro", {})
        reaction = earnings.get("reaction", {})

        # Reaction-based stock impact (most direct signal)
        if reaction:
            next_session_change = reaction.get("next_session", {}).get("change_pct")
            session_5_change = reaction.get("session_5", {}).get("change_pct")

            if next_session_change is not None:
                try:
                    change = float(next_session_change)
                    if change > 2.0:
                        bias = StockBias.BULLISH
                        magnitude = ImpactMagnitude.HIGH
                        horizon = TimeHorizon.SHORT_TERM
                        reasons.append(f"Next-session reaction +{change:.1f}%")
                    elif change > 0.5:
                        bias = StockBias.BULLISH
                        magnitude = ImpactMagnitude.MEDIUM
                        horizon = TimeHorizon.SHORT_TERM
                        reasons.append(f"Next-session reaction +{change:.1f}%")
                    elif change < -2.0:
                        bias = StockBias.BEARISH
                        magnitude = ImpactMagnitude.HIGH
                        horizon = TimeHorizon.SHORT_TERM
                        reasons.append(f"Next-session reaction {change:.1f}%")
                    elif change < -0.5:
                        bias = StockBias.BEARISH
                        magnitude = ImpactMagnitude.MEDIUM
                        horizon = TimeHorizon.SHORT_TERM
                        reasons.append(f"Next-session reaction {change:.1f}%")
                except ValueError:
                    pass

            if session_5_change is not None:
                try:
                    change = float(session_5_change)
                    if change > 5.0:
                        if bias != StockBias.BULLISH:
                            bias = StockBias.BULLISH
                        magnitude = ImpactMagnitude.HIGH
                        horizon = TimeHorizon.MEDIUM_TERM
                        reasons.append(f"5-session reaction +{change:.1f}%")
                    elif change < -5.0:
                        if bias != StockBias.BEARISH:
                            bias = StockBias.BEARISH
                        magnitude = ImpactMagnitude.HIGH
                        horizon = TimeHorizon.MEDIUM_TERM
                        reasons.append(f"5-session reaction {change:.1f}%")
                except ValueError:
                    pass

        # If no reaction data, infer from company impact and expectations
        if bias == StockBias.UNKNOWN:
            earnings = all_evidence.get("earnings", {})
            eps_surprise = earnings.get("eps_surprise")
            rev_surprise = earnings.get("revenue_surprise")
            guidance_dir = earnings.get("guidance_direction")

            # Check for expectation divergence
            if eps_surprise is not None:
                try:
                    eps_val = float(eps_surprise)
                    if eps_val > 0.5:
                        # Strong beat - but check if stock reacted negatively (sell the news)
                        bias = StockBias.BULLISH
                        magnitude = ImpactMagnitude.MEDIUM
                        horizon = TimeHorizon.SHORT_TERM
                        reasons.append(f"Strong EPS beat (+${eps_val:.2f})")
                    elif eps_val > 0:
                        bias = StockBias.BULLISH
                        magnitude = ImpactMagnitude.LOW
                        horizon = TimeHorizon.SHORT_TERM
                        reasons.append(f"EPS beat (+${eps_val:.2f})")
                    elif eps_val < -0.5:
                        bias = StockBias.BEARISH
                        magnitude = ImpactMagnitude.MEDIUM
                        horizon = TimeHorizon.SHORT_TERM
                        reasons.append(f"EPS miss (-${abs(eps_val):.2f})")
                    elif eps_val < 0:
                        bias = StockBias.BEARISH
                        magnitude = ImpactMagnitude.LOW
                        horizon = TimeHorizon.SHORT_TERM
                        reasons.append(f"EPS miss (-${abs(eps_val):.2f})")
                except ValueError:
                    pass

            if guidance_dir:
                if guidance_dir == "raised":
                    if bias != StockBias.BEARISH:
                        bias = StockBias.BULLISH
                        magnitude = ImpactMagnitude.HIGH
                        horizon = TimeHorizon.MEDIUM_TERM
                        reasons.append("Guidance raised")
                elif guidance_dir == "lowered":
                    if bias != StockBias.BULLISH:
                        bias = StockBias.BEARISH
                        magnitude = ImpactMagnitude.HIGH
                        horizon = TimeHorizon.MEDIUM_TERM
                        reasons.append("Guidance lowered")

        # Macro influence on stock bias
        if macro.get("rate_direction") is not None:
            try:
                rate_change = float(macro["rate_direction"])
                if rate_change < 0:
                    if bias != StockBias.BEARISH:
                        bias = StockBias.BULLISH if bias != StockBias.BEARISH else StockBias.MIXED
                    reasons.append("Rate cut supportive")
                elif rate_change > 0:
                    if bias != StockBias.BULLISH:
                        bias = StockBias.BEARISH if bias != StockBias.BULLISH else StockBias.MIXED
                    reasons.append("Rate hike headwind")
            except ValueError:
                pass

        # Company vs stock divergence check
        if company_impact.direction == ImpactDirection.POSITIVE and bias == StockBias.BEARISH:
            reasons.append("Divergence: positive fundamentals but negative market reaction")
        elif company_impact.direction == ImpactDirection.NEGATIVE and bias == StockBias.BULLISH:
            reasons.append("Divergence: negative fundamentals but positive market reaction")

        # Default values if still unknown
        if bias == StockBias.UNKNOWN:
            bias = StockBias.NEUTRAL
        if magnitude == ImpactMagnitude.UNKNOWN:
            magnitude = ImpactMagnitude.LOW
        if horizon == TimeHorizon.UNKNOWN:
            horizon = TimeHorizon.SHORT_TERM

        confidence = min(0.3 + len(reasons) * 0.1, 0.85)

        return StockImpact(
            bias=bias,
            magnitude=magnitude,
            horizon=horizon,
            reasons=reasons,
            evidence_refs=[],
            confidence=confidence,
        )

    def _generate_scenarios(self, symbol: str, all_evidence: dict, company_impact: CompanyImpact, stock_impact: StockImpact) -> tuple:
        """Generate base/bull/bear scenarios."""
        base_reasons = []
        bull_reasons = []
        bear_reasons = []
        bull_conditions = []
        bear_conditions = []

        earnings = all_evidence.get("earnings", {})
        macro = all_evidence.get("macro", {})
        sec = all_evidence.get("sec", {})
        reaction = earnings.get("reaction", {})

        # Base case - most likely continuation
        if all_evidence.get("earnings", {}).get("has_earnings"):
            eps_surprise = earnings.get("eps_surprise")
            guidance_dir = earnings.get("guidance_direction")
            if eps_surprise is not None:
                try:
                    eps_val = float(eps_surprise)
                    if eps_val > 0:
                        base_reasons.append(f"EPS beat continues to support valuation")
                    elif eps_val < 0:
                        base_reasons.append(f"EPS miss creates near-term overhang")
                except ValueError:
                    base_reasons.append("Earnings result mixed")
        base_reasons.append("Current trajectory continues absent new catalysts")

        # Bull case
        if all_evidence.get("earnings", {}).get("guidance_direction") == "raised":
            bull_reasons.append("Raised guidance provides upside support")
            bull_conditions.append("Guidance remains intact")
        if all_evidence.get("macro", {}).get("rate_direction", 0) < 0:
            bull_reasons.append("Rate cuts provide valuation support")
            bull_conditions.append("Fed continues easing cycle")
        bull_reasons.append("Positive earnings momentum continues")
        bull_conditions.append("Earnings momentum sustains")

        # Bear case
        if all_evidence.get("earnings", {}).get("guidance_direction") == "lowered":
            bear_reasons.append("Lowered guidance signals deterioration")
            bear_conditions.append("Guidance further reduced")
        if all_evidence.get("macro", {}).get("rate_direction", 0) > 0:
            bear_reasons.append("Rate hikes compress valuations")
            bear_conditions.append("Fed continues tightening")
        if all_evidence.get("earnings", {}).get("eps_surprise"):
            try:
                eps_val = float(all_evidence["earnings"]["eps_surprise"])
                if eps_val < 0:
                    bear_reasons.append("EPS miss indicates weakening fundamentals")
                    bear_conditions.append("Fundamentals deteriorate further")
            except ValueError:
                pass
        bear_reasons.append("Negative macro shock or guidance cut")
        bear_conditions.append("Guidance cut or negative macro surprise")

        base_case = Scenario(
            scenario_type=ScenarioType.BASE,
            description="Current trajectory continues; valuation reflects current expectations",
            required_conditions=base_reasons,
            evidence_refs=[],
            probability_band="40-60%",
        )

        bull_case = Scenario(
            scenario_type=ScenarioType.BULL,
            description="Positive fundamentals and supportive macro drive multiple expansion",
            required_conditions=bull_conditions,
            evidence_refs=[],
            probability_band="20-30%",
        )

        bear_case = Scenario(
            scenario_type=ScenarioType.BEAR,
            description="Fundamental deterioration or macro headwinds compress multiple",
            required_conditions=bear_conditions,
            evidence_refs=[],
            probability_band="15-25%",
        )

        return base_case, bull_case, bear_case

    def _generate_view_change_triggers(self, symbol: str, all_evidence: dict) -> list:
        """Generate specific triggers that would change the current view."""
        triggers = []

        earnings = all_evidence.get("earnings", {})
        macro = all_evidence.get("macro", {})
        sec = all_evidence.get("sec", {})

        # Earnings-related triggers
        if earnings.get("has_earnings"):
            next_earnings = "Next earnings result (surprise vs consensus)"
            triggers.append(ViewChangeTrigger(
                trigger=next_earnings,
                description="Next quarterly EPS vs consensus will validate or invalidate current trajectory",
                evidence_refs=[]
            ))

        # Guidance triggers
        if earnings.get("guidance_direction"):
            triggers.append(ViewChangeTrigger(
                trigger="Guidance revision",
                description="Any guidance revision will materially change outlook",
                evidence_refs=[]
            ))

        # Macro triggers
        if macro.get("cpi_surprise") is not None:
            triggers.append(ViewChangeTrigger(
                trigger="CPI release",
                description="CPI surprise vs consensus will drive rate expectations",
                evidence_refs=[]
            ))

        if macro.get("nfp_surprise") is not None:
            triggers.append(ViewChangeTrigger(
                trigger="NFP release",
                description="Payroll surprise will shift rate path expectations",
                evidence_refs=[]
            ))

        if macro.get("fomc_action"):
            triggers.append(ViewChangeTrigger(
                trigger="FOMC decision",
                description="Rate decision and forward guidance",
                evidence_refs=[]
            ))

        # SEC triggers
        if sec.get("leadership_change"):
            triggers.append(ViewChangeTrigger(
                trigger="Leadership change",
                description="CEO/CFO change signals strategic shift",
                evidence_refs=[]
            ))

        return triggers

    def _build_what_happened(self, symbol: str, all_evidence: dict) -> str:
        """Build factual 'what happened' summary."""
        parts = []
        earnings = all_evidence.get("earnings", {})
        macro = all_evidence.get("macro", {})
        sec = all_evidence.get("sec", {})

        if earnings.get("has_earnings"):
            eps_surprise = earnings.get("eps_surprise")
            rev_surprise = earnings.get("revenue_surprise")
            guidance_dir = earnings.get("guidance_direction")

            parts.append(f"Reported earnings")
            if eps_surprise is not None:
                try:
                    eps_val = float(eps_surprise)
                    if eps_val >= 0:
                        parts.append(f"EPS beat by ${eps_val:.2f}")
                    else:
                        parts.append(f"EPS miss by ${abs(eps_val):.2f}")
                except ValueError:
                    pass
            if rev_surprise is not None:
                try:
                    rev_val = float(rev_surprise)
                    if rev_val >= 0:
                        parts.append(f"revenue beat by ${rev_val:,.0f}")
                    else:
                        parts.append(f"revenue miss by ${abs(rev_val):,.0f}")
                except ValueError:
                    pass
            if guidance_dir:
                parts.append(f"guidance {guidance_dir}")

        if macro.get("cpi_surprise") is not None:
            parts.append(f"CPI {macro['cpi_surprise']} vs consensus")
        if macro.get("nfp_surprise") is not None:
            parts.append(f"NFP {macro['nfp_surprise']} vs consensus")
        if macro.get("fomc_action"):
            parts.append(f"FOMC {macro['fomc_action']}")

        if sec.get("leadership_change"):
            parts.append(f"leadership change: {sec['leadership_change']}")

        if not parts:
            return "No material new events in period"

        return "; ".join(parts)

    def _build_what_it_means(self, symbol: str, all_evidence: dict, company_impact: CompanyImpact, stock_impact: StockImpact) -> str:
        """Build 'what it means' mechanistic explanation."""
        parts = []

        if company_impact.direction == ImpactDirection.POSITIVE:
            parts.append("Fundamental business strengthening")
        elif company_impact.direction == ImpactDirection.NEGATIVE:
            parts.append("Fundamental business weakening")
        else:
            parts.append("Fundamental business stable")

        if company_impact.magnitude == ImpactMagnitude.HIGH:
            parts.append("with high conviction")
        elif company_impact.magnitude == ImpactMagnitude.MEDIUM:
            parts.append("with moderate conviction")

        if stock_impact.bias == StockBias.BULLISH:
            parts.append("Market reaction likely positive")
        elif stock_impact.bias == StockBias.BEARISH:
            parts.append("Market reaction likely negative")
        elif stock_impact.bias == StockBias.MIXED:
            parts.append("Market reaction mixed; conflicting signals")

        # Check for divergence
        if (company_impact.direction == ImpactDirection.POSITIVE and
            stock_impact.bias in [StockBias.BEARISH, StockBias.NEUTRAL]):
            parts.append("Divergence: strong fundamentals but muted/negative market reaction suggests expectations were higher or macro headwinds")
        elif (company_impact.direction == ImpactDirection.NEGATIVE and
              stock_impact.bias in [StockBias.BULLISH, StockBias.NEUTRAL]):
            parts.append("Divergence: weak fundamentals but positive market reaction suggests oversold relief or short covering")

        return " ".join(parts)

    def _build_why_it_matters(self, symbol: str, all_evidence: dict) -> str:
        """Build 'why it matters' significance explanation."""
        parts = []
        earnings = all_evidence.get("earnings", {})
        macro = all_evidence.get("macro", {})

        if earnings.get("has_earnings"):
            eps_surprise = earnings.get("eps_surprise")
            guidance_dir = earnings.get("guidance_direction")
            if eps_surprise is not None:
                try:
                    val = float(eps_surprise)
                    if val > 1.0:
                        parts.append("Large EPS beat signals strong execution and potential multiple expansion")
                    elif val > 0:
                        parts.append("EPS beat supports near-term sentiment")
                    elif val < -1.0:
                        parts.append("Large EPS miss raises fundamental concerns")
                    elif val < 0:
                        parts.append("EPS miss creates near-term overhang")
                except ValueError:
                    pass

            if guidance_dir == "raised":
                parts.append("Raised guidance signals management confidence in forward outlook")
            elif guidance_dir == "lowered":
                parts.append("Lowered guidance signals management caution on forward outlook")

        if macro.get("rate_direction") is not None:
            try:
                rate = float(macro["rate_direction"])
                if rate < 0:
                    parts.append("Rate cuts provide valuation support for growth/equity multiples")
                elif rate > 0:
                    parts.append("Rate hikes compress equity valuations, especially growth/tech")
            except ValueError:
                pass

        if not parts:
            parts.append("No material catalyst in current period; monitoring for next catalyst")

        return " ".join(parts)

    def generate_interpretation(self, request: InterpretationRequest) -> Interpretation:
        """Generate a complete interpretation for a symbol."""
        symbol = request.symbol.upper()
        as_of = request.as_of or datetime.now(timezone.utc)

        # Fetch all relevant events
        events = self.event_store.events_for_symbol(
            symbol=symbol,
            event_types=None,
            limit=500,
        )

        # Filter by as_of if provided
        if request.as_of:
            events = [e for e in events if (e.released_at or e.scheduled_at) and
                     (e.released_at or e.scheduled_at) <= request.as_of]

        # Filter by focus events if provided
        if request.focus_events:
            events = [e for e in events if e.event_id in request.focus_events]

        # Categorize evidence
        all_evidence = {
            "earnings": self._analyze_earnings_events(symbol, [e for e in events if e.event_type.value.startswith("earnings")]),
            "macro": self._analyze_macro_events([e for e in events if e.event_type.value == "macro"]),
            "sec": self._analyze_sec_events(symbol, [e for e in events if e.event_type.value in ["sec_filing", "leadership", "insider"]]),
            "management": self._analyze_management_statements(symbol),
            "news": self._analyze_news_claims(symbol),
            "quant": self._extract_quant_context(symbol, request.as_of),
        }

        # Add event objects to evidence for reference
        all_evidence["events"] = events

        # Generate interpretation components
        company_impact = self._determine_company_impact(symbol, all_evidence)
        stock_impact = self._determine_stock_impact(symbol, all_evidence, company_impact)
        base_case, bull_case, bear_case = self._generate_scenarios(symbol, all_evidence, company_impact, stock_impact)
        view_change_triggers = self._generate_view_change_triggers(symbol, all_evidence)

        what_happened = self._build_what_happened(symbol, all_evidence)
        what_it_means = self._build_what_it_means(symbol, all_evidence, company_impact, stock_impact)
        why_it_matters = self._build_why_it_matters(symbol, all_evidence)

        # Build evidence references
        evidence_refs = self._get_evidence_refs(events)

        # Overall confidence
        confidence = min(company_impact.confidence, stock_impact.confidence)

        return Interpretation(
            symbol=symbol,
            as_of=as_of,
            headline=self._build_headline(symbol, all_evidence),
            what_happened=what_happened,
            what_it_means=what_it_means,
            why_it_matters=why_it_matters,
            company_impact=company_impact,
            stock_impact=stock_impact,
            base_case=base_case,
            bull_case=bull_case,
            bear_case=bear_case,
            what_would_change_view=view_change_triggers,
            confidence=confidence,
            confidence_reasons=["Based on deterministic evidence synthesis"],
            missing_information=self._identify_missing_information(all_evidence),
            supporting_evidence=evidence_refs,
            generated_at=datetime.now(timezone.utc),
            engine_version=self._version,
        )

    def _build_headline(self, symbol: str, all_evidence: dict) -> str:
        """Build a concise headline."""
        earnings = all_evidence.get("earnings", {})
        if earnings.get("has_earnings"):
            eps_surprise = earnings.get("eps_surprise")
            guidance_dir = earnings.get("guidance_direction")
            parts = [f"{symbol} earnings"]
            if eps_surprise is not None:
                try:
                    val = float(eps_surprise)
                    if val >= 0:
                        parts.append(f"beats by ${val:.2f}")
                    else:
                        parts.append(f"misses by ${abs(val):.2f}")
                except ValueError:
                    parts.append("reports")
            if guidance_dir:
                parts.append(f"{guidance_dir} guidance")
            return " ".join(parts)
        return f"{symbol}: Market update"

    def _identify_missing_information(self, all_evidence: dict) -> list:
        """Identify missing information that would improve confidence."""
        missing = []
        earnings = all_evidence.get("earnings", {})
        if not earnings.get("has_earnings"):
            missing.append("No recent earnings result available")
        if earnings.get("eps_consensus") is None:
            missing.append("No consensus EPS estimate for comparison")
        if earnings.get("guidance_direction") is None:
            missing.append("No forward guidance available")
        if not all_evidence.get("macro", {}).get("cpi_surprise"):
            missing.append("No recent CPI surprise for macro context")
        if not all_evidence.get("management"):
            missing.append("No recent management statements")
        if not all_evidence.get("news"):
            missing.append("No recent news evidence")
        return missing


# For backward compatibility
def create_interpretation_engine(event_store: EventStore) -> InterpretationEngine:
    """Factory function to create interpretation engine."""
    return InterpretationEngine(event_store)


if __name__ == "__main__":
    # Quick test
    from trading_copilot.events.store import EventStore
    from trading_copilot.models.events import MarketEvent, EventType, EventStatus, EventImportance

    # Create test event store
    import tempfile
    with tempfile.TemporaryDirectory() as tmpdir:
        store = EventStore(tmpdir + "/test_events.db")

        # Create test earnings event
        event = MarketEvent(
            event_type=EventType.EARNINGS_RESULT,
            symbol="AAPL",
            title="AAPL Q3 Earnings",
            description="{}",
            released_at=datetime(2026, 10, 29, 21, 0, tzinfo=timezone.utc),
            importance=EventImportance.HIGH,
            status=EventStatus.RELEASED,
            source="sec_edgar",
            source_url="https://sec.gov/...",
            source_id="test:earnings",
            metadata={
                "eps_actual": "1.55",
                "eps_consensus": "1.42",
                "eps_surprise": "0.13",
                "revenue_actual": "89500000000",
                "revenue_consensus": "89200000000",
                "revenue_surprise": "300000000",
                "guidance_change": "raised",
            },
        )
        store.upsert_event(event)

        # Create engine and generate interpretation
        engine = InterpretationEngine(store)
        request = type('InterpretationRequest', (), {
            'symbol': 'AAPL',
            'as_of': None,
            'force_refresh': False,
            'focus_events': None,
            'include_quant_context': True,
        })()

        interpretation = engine.generate_interpretation(request)

        print(f"Symbol: {interpretation.symbol}")
        print(f"Headline: {interpretation.headline}")
        print(f"What happened: {interpretation.what_happened}")
        print(f"What it means: {interpretation.what_it_means}")
        print(f"Why it matters: {interpretation.why_it_matters}")
        print(f"Company Impact: {interpretation.company_impact.direction.value} ({interpretation.company_impact.magnitude.value})")
        print(f"Stock Impact: {interpretation.stock_impact.bias.value} ({interpretation.stock_impact.magnitude.value})")
        print(f"Base: {interpretation.base_case.description}")
        print(f"Bull: {interpretation.bull_case.description}")
        print(f"Bear: {interpretation.bear_case.description}")
        print(f"Confidence: {interpretation.confidence}")
        print(f"Triggers: {[t.trigger for t in interpretation.what_would_change_view]}")

    store.close()