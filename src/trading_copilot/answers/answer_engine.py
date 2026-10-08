"""Answer Engine — deterministic Q&A using structured evidence and interpretations.

Zero-LLM core: all functionality works with LLM_ENABLED=false.
Optional local AI may enhance wording/synthesis only.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Optional

from trading_copilot.events.store import EventStore
from trading_copilot.models.events import EventType
from trading_copilot.models.interpretation import (
    Answer,
    AnswerRequest,
    EvidenceRef,
    Interpretation,
    InterpretationRequest,
)
from trading_copilot.intelligence.interpretation_engine import InterpretationEngine

logger = logging.getLogger(__name__)


class AnswerEngine:
    """
    Deterministic Q&A engine that answers specific questions using
    structured evidence and interpretations.

    All logic is deterministic. No LLM required for core functionality.
    """

    def __init__(
        self,
        event_store: EventStore,
        interpretation_engine: Optional[Any] = None,
        llm_enabled: bool = False,
        llm_provider: Optional[Any] = None,
    ):
        self.event_store = event_store
        self.interpretation_engine = interpretation_engine or InterpretationEngine(event_store)
        self.llm_enabled = llm_enabled

    def _format_evidence_ref(self, ref: EvidenceRef) -> str:
        """Format evidence reference for display."""
        parts = [f"[{ref.source_type}]"]
        if ref.description:
            parts.append(ref.description)
        if ref.url:
            parts.append(f"({ref.url})")
        if ref.timestamp:
            parts.append(f"@{ref.timestamp.isoformat()}")
        return " ".join(parts)

    def _format_evidence_list(self, refs: list[EvidenceRef]) -> str:
        """Format list of evidence references."""
        if not refs:
            return "No specific evidence cited"
        return "\n".join(f"  - {self._format_evidence_ref(r)}" for r in refs)

    def _answer_why_moving(self, symbol: str, interpretation) -> Answer:
        """Answer: Why is SYMBOL moving?"""
        parts = []
        evidence = interpretation.supporting_evidence

        if interpretation.stock_impact.bias != "unknown":
            parts.append(f"{symbol} is {interpretation.stock_impact.bias} ({interpretation.stock_impact.magnitude})")
            parts.append(f"Horizon: {interpretation.stock_impact.horizon}")

        if interpretation.stock_impact.reasons:
            parts.append("Key drivers:")
            for reason in interpretation.stock_impact.reasons:
                parts.append(f"  - {reason}")

        if interpretation.company_impact.direction != "unknown":
            parts.append(f"\nCompany fundamentals: {interpretation.company_impact.direction} ({interpretation.company_impact.magnitude})")
            if interpretation.company_impact.reasons:
                for reason in interpretation.company_impact.reasons:
                    parts.append(f"  - {reason}")

        # Check for divergence
        if (interpretation.company_impact.direction == "positive" and
            interpretation.stock_impact.bias in ["bearish", "neutral"]):
            parts.append("\n⚠️ Divergence: Positive fundamentals but muted/negative stock reaction")
        elif (interpretation.company_impact.direction == "negative" and
              interpretation.stock_impact.bias in ["bullish", "neutral"]):
            parts.append("\n⚠️ Divergence: Negative fundamentals but positive stock reaction")

        answer_text = "\n".join(parts)

        return Answer(
            question=f"Why is {symbol} moving?",
            answer=answer_text,
            evidence_refs=evidence,
            confidence=interpretation.confidence,
            generated_at=datetime.now(timezone.utc),
        )

    def _answer_what_happened(self, symbol: str, interpretation) -> Answer:
        """Answer: What happened?"""
        parts = [f"What happened with {symbol}:", interpretation.what_happened]

        if interpretation.what_it_means:
            parts.append(f"\nWhat it means: {interpretation.what_it_means}")

        if interpretation.why_it_matters:
            parts.append(f"\nWhy it matters: {interpretation.why_it_matters}")

        answer_text = "\n".join(parts)

        return Answer(
            question=f"What happened with {symbol}?",
            answer=answer_text,
            evidence_refs=interpretation.supporting_evidence,
            confidence=interpretation.confidence,
            generated_at=datetime.now(timezone.utc),
        )

    def _answer_why_it_matters(self, symbol: str, interpretation) -> Answer:
        """Answer: Why does it matter?"""
        parts = [f"Why {symbol} matters:", interpretation.why_it_matters]

        if interpretation.company_impact.reasons:
            parts.append("\nCompany impact drivers:")
            for reason in interpretation.company_impact.reasons:
                parts.append(f"  - {reason}")

        if interpretation.stock_impact.reasons:
            parts.append("\nStock impact drivers:")
            for reason in interpretation.stock_impact.reasons:
                parts.append(f"  - {reason}")

        answer_text = "\n".join(parts)

        return Answer(
            question=f"Why does {symbol} matter?",
            answer=answer_text,
            evidence_refs=interpretation.supporting_evidence,
            confidence=interpretation.confidence,
            generated_at=datetime.now(timezone.utc),
        )

    def _answer_company_impact(self, symbol: str, interpretation) -> Answer:
        """Answer: What is the company impact?"""
        ci = interpretation.company_impact
        parts = [
            f"Company Impact for {symbol}:",
            f"Direction: {ci.direction} ({ci.magnitude})",
            f"Horizon: {ci.horizon}",
            f"Confidence: {ci.confidence:.0%}",
        ]

        if ci.reasons:
            parts.append("\nReasons:")
            for reason in ci.reasons:
                parts.append(f"  - {reason}")

        if ci.evidence_refs:
            parts.append(f"\nEvidence:\n{self._format_evidence_list(ci.evidence_refs)}")

        answer_text = "\n".join(parts)

        return Answer(
            question=f"What is {symbol}'s company impact?",
            answer=answer_text,
            evidence_refs=ci.evidence_refs,
            confidence=ci.confidence,
            generated_at=datetime.now(timezone.utc),
        )

    def _answer_stock_impact(self, symbol: str, interpretation) -> Answer:
        """Answer: What is the stock impact?"""
        si = interpretation.stock_impact
        parts = [
            f"Stock Impact for {symbol}:",
            f"Bias: {si.bias} ({si.magnitude})",
            f"Horizon: {si.horizon}",
            f"Confidence: {si.confidence:.0%}",
        ]

        if si.reasons:
            parts.append("\nReasons:")
            for reason in si.reasons:
                parts.append(f"  - {reason}")

        if si.evidence_refs:
            parts.append(f"\nEvidence:\n{self._format_evidence_list(si.evidence_refs)}")

        # Check for divergence
        ci = interpretation.company_impact
        if (ci.direction == "positive" and si.bias in ["bearish", "neutral"]):
            parts.append("\n⚠️ Divergence: Positive fundamentals but muted/negative stock reaction")
        elif (ci.direction == "negative" and si.bias in ["bullish", "neutral"]):
            parts.append("\n⚠️ Divergence: Negative fundamentals but positive stock reaction")

        answer_text = "\n".join(parts)

        return Answer(
            question=f"What is {symbol}'s stock impact?",
            answer=answer_text,
            evidence_refs=si.evidence_refs,
            confidence=si.confidence,
            generated_at=datetime.now(timezone.utc),
        )

    def _answer_scenarios(self, symbol: str, interpretation) -> Answer:
        """Answer: What are the scenarios?"""
        parts = [f"Scenario Analysis for {symbol}:"]

        for scenario in [interpretation.base_case, interpretation.bull_case, interpretation.bear_case]:
            parts.append(f"\n{scenario.scenario_type.value.upper()} CASE:")
            parts.append(f"  {scenario.description}")
            if scenario.required_conditions:
                parts.append("  Required conditions:")
                for cond in scenario.required_conditions:
                    parts.append(f"    - {cond}")
            if scenario.probability_band:
                parts.append(f"  Probability band: {scenario.probability_band}")

        answer_text = "\n".join(parts)

        return Answer(
            question=f"What are the scenarios for {symbol}?",
            answer=answer_text,
            evidence_refs=interpretation.supporting_evidence,
            confidence=interpretation.confidence,
            generated_at=datetime.now(timezone.utc),
        )

    def _answer_what_changed(self, symbol: str, interpretation) -> Answer:
        """Answer: What changed?"""
        parts = [f"What changed for {symbol}:"]

        if interpretation.what_happened:
            parts.append(interpretation.what_happened)

        if interpretation.what_would_change_view:
            parts.append("\nWhat would change this view:")
            for trigger in interpretation.what_would_change_view:
                parts.append(f"  - {trigger.trigger}: {trigger.description}")

        if interpretation.missing_information:
            parts.append("\nMissing information (would improve confidence):")
            for info in interpretation.missing_information:
                parts.append(f"  - {info}")

        answer_text = "\n".join(parts)

        return Answer(
            question=f"What changed for {symbol}?",
            answer=answer_text,
            evidence_refs=interpretation.supporting_evidence,
            confidence=interpretation.confidence,
            generated_at=datetime.now(timezone.utc),
        )

    def _answer_next_event(self, symbol: str, interpretation) -> Answer:
        """Answer: What is the next important event?"""
        if not interpretation.what_would_change_view:
            return Answer(
                question=f"What is the next important event for {symbol}?",
                answer="No specific upcoming events identified in current evidence.",
                evidence_refs=[],
                confidence=0.3,
                generated_at=datetime.now(timezone.utc),
            )

        parts = [f"Next important events for {symbol}:"]
        for trigger in interpretation.what_would_change_view:
            parts.append(f"  - {trigger.trigger}: {trigger.description}")

        answer_text = "\n".join(parts)

        return Answer(
            question=f"What is the next important event for {symbol}?",
            answer=answer_text,
            evidence_refs=interpretation.supporting_evidence,
            confidence=0.7,
            generated_at=datetime.now(timezone.utc),
        )

    def _answer_investor_concerns(self, symbol: str, interpretation) -> Answer:
        """Answer: What are investors worried about?"""
        parts = [f"Investor concerns for {symbol}:"]

        # Bear case concerns
        if interpretation.bear_case.required_conditions:
            parts.append("\nDownside risks:")
            for cond in interpretation.bear_case.required_conditions:
                parts.append(f"  - {cond}")

        # Missing information
        if interpretation.missing_information:
            parts.append("\nInformation gaps (reduce confidence):")
            for info in interpretation.missing_information:
                parts.append(f"  - {info}")

        # Divergence warning
        ci = interpretation.company_impact
        si = interpretation.stock_impact
        if (ci.direction == "positive" and si.bias in ["bearish", "neutral"]):
            parts.append("\n⚠️ Positive fundamentals but stock not responding - expectations may be too high")
        elif (ci.direction == "negative" and si.bias in ["bullish", "neutral"]):
            parts.append("\n⚠️ Negative fundamentals but stock holding - possible short squeeze or relief rally")

        if not interpretation.missing_information and not interpretation.bear_case.required_conditions:
            parts.append("\nNo specific concerns identified in current evidence.")

        answer_text = "\n".join(parts)

        return Answer(
            question=f"What are investors worried about for {symbol}?",
            answer=answer_text,
            evidence_refs=[],
            confidence=0.7,
            generated_at=datetime.now(timezone.utc),
        )

    def _answer_investor_interest(self, symbol: str, interpretation) -> Answer:
        """Answer: Why are investors interested?"""
        parts = [f"Why investors are interested in {symbol}:"]

        # Bull case drivers
        if interpretation.bull_case.required_conditions:
            parts.append("\nUpside drivers:")
            for cond in interpretation.bull_case.required_conditions:
                parts.append(f"  - {cond}")

        # Company impact drivers
        if interpretation.company_impact.reasons:
            parts.append("\nFundamental drivers:")
            for reason in interpretation.company_impact.reasons:
                parts.append(f"  - {reason}")

        # Stock impact drivers
        if interpretation.stock_impact.reasons:
            parts.append("\nStock drivers:")
            for reason in interpretation.stock_impact.reasons:
                parts.append(f"  - {reason}")

        if not interpretation.company_impact.reasons and not interpretation.bull_case.required_conditions:
            parts.append("\nNo specific interest drivers identified in current evidence.")

        answer_text = "\n".join(parts)

        return Answer(
            question=f"Why are investors interested in {symbol}?",
            answer=answer_text,
            evidence_refs=[],
            confidence=0.7,
            generated_at=datetime.now(timezone.utc),
        )

    def _answer_catalysts(self, symbol: str, interpretation) -> Answer:
        """Answer: What are the catalysts?"""
        parts = [f"Catalysts for {symbol}:"]

        if interpretation.what_would_change_view:
            parts.append("\nUpcoming catalysts:")
            for trigger in interpretation.what_would_change_view:
                parts.append(f"  - {trigger.trigger}: {trigger.description}")

        # Earnings-based catalysts
        parts.append("\nPotential catalysts:")
        parts.append("  - Next earnings result (surprise vs consensus)")
        parts.append("  - Guidance revision")
        parts.append("  - Macro data (CPI, NFP, FOMC)")
        parts.append("  - Guidance revision")

        answer_text = "\n".join(parts)

        return Answer(
            question=f"What are the catalysts for {symbol}?",
            answer=answer_text,
            evidence_refs=[],
            confidence=0.7,
            generated_at=datetime.now(timezone.utc),
        )

    def _answer_risks(self, symbol: str, interpretation) -> Answer:
        """Answer: What are the risks?"""
        parts = [f"Risks for {symbol}:"]

        if interpretation.bear_case.required_conditions:
            parts.append("\nDownside scenario triggers:")
            for cond in interpretation.bear_case.required_conditions:
                parts.append(f"  - {cond}")

        if interpretation.missing_information:
            parts.append("\nInformation gaps:")
            for info in interpretation.missing_information:
                parts.append(f"  - {info}")

        if interpretation.company_impact.direction == "negative":
            parts.append("\n⚠️ Company fundamentals are weakening")

        if interpretation.stock_impact.bias == "bearish":
            parts.append("Stock bias is bearish")

        answer_text = "\n".join(parts)

        return Answer(
            question=f"What are the risks for {symbol}?",
            answer=answer_text,
            evidence_refs=[],
            confidence=0.7,
            generated_at=datetime.now(timezone.utc),
        )

    def _answer_next_event(self, symbol: str, interpretation) -> Answer:
        """Answer: What is the next important event?"""
        return self._answer_next_event(symbol, interpretation)

    def _answer_generic(self, symbol: str, question: str, interpretation) -> Answer:
        """Handle generic questions by providing full interpretation summary."""
        parts = [
            f"Summary for {symbol}:",
            f"Headline: {interpretation.headline}",
            f"\nWhat happened: {interpretation.what_happened}",
            f"\nWhat it means: {interpretation.what_it_means}",
            f"\nWhy it matters: {interpretation.why_it_matters}",
            f"\nCompany impact: {interpretation.company_impact.direction} ({interpretation.company_impact.magnitude})",
            f"Stock impact: {interpretation.stock_impact.bias} ({interpretation.stock_impact.magnitude})",
            f"\nBase case: {interpretation.base_case.description}",
            f"Bull case: {interpretation.bull_case.description}",
            f"Bear case: {interpretation.bear_case.description}",
            f"\nConfidence: {interpretation.confidence:.0%}",
        ]

        if interpretation.what_would_change_view:
            parts.append("\nWhat would change the view:")
            for trigger in interpretation.what_would_change_view:
                parts.append(f"  - {trigger.trigger}: {trigger.description}")

        answer_text = "\n".join(parts)

        return Answer(
            question=question,
            answer=answer_text,
            evidence_refs=interpretation.supporting_evidence,
            confidence=interpretation.confidence,
            generated_at=datetime.now(timezone.utc),
        )

    def _detect_question_type(self, question: str) -> str:
        """Detect the type of question to route to appropriate handler."""
        question_lower = question.lower()

        if "why" in question_lower and "mov" in question_lower:
            return "why_moving"
        elif "what happened" in question_lower or "what happen" in question_lower:
            return "what_happened"
        elif "why it matter" in question_lower or "why does it matter" in question_lower:
            return "why_it_matters"
        elif "company impact" in question_lower:
            return "company_impact"
        elif "stock impact" in question_lower or "stock bias" in question_lower:
            return "stock_impact"
        elif "scenario" in question_lower or "base case" in question_lower or "bull case" in question_lower or "bear case" in question_lower:
            return "scenarios"
        elif "what changed" in question_lower or "what change" in question_lower:
            return "what_changed"
        elif "next" in question_lower and ("event" in question_lower or "catalyst" in question_lower):
            return "next_event"
        elif "worried" in question_lower or "concern" in question_lower or "risk" in question_lower:
            return "investor_concerns"
        elif "interested" in question_lower or "why invest" in question_lower:
            return "investor_interest"
        elif "catalyst" in question_lower:
            return "catalysts"
        elif "risk" in question_lower:
            return "risks"
        elif "next" in question_lower and "event" in question_lower:
            return "next_event"
        else:
            return "generic"

    def answer_question(self, request: AnswerRequest) -> Answer:
        """Answer a specific question about a symbol."""
        symbol = request.symbol.upper()
        question = request.question

        # Generate interpretation
        interp_request = InterpretationRequest(
            symbol=symbol,
            as_of=request.context.get("as_of") if request.context else None,
            force_refresh=request.context.get("force_refresh", False) if request.context else False,
        )

        interpretation = self.interpretation_engine.generate_interpretation(interp_request)

        # Route to appropriate handler
        question_type = self._detect_question_type(question)

        handlers = {
            "why_moving": self._answer_why_moving,
            "what_happened": self._answer_what_happened,
            "why_it_matters": self._answer_why_it_matters,
            "company_impact": self._answer_company_impact,
            "stock_impact": self._answer_stock_impact,
            "scenarios": self._answer_scenarios,
            "what_changed": self._answer_what_changed,
            "next_event": self._answer_next_event,
            "investor_concerns": self._answer_investor_concerns,
            "investor_interest": self._answer_investor_interest,
            "catalysts": self._answer_catalysts,
            "risks": self._answer_risks,
            "next_event": self._answer_next_event,
            "generic": self._answer_generic,
        }

        handler = handlers.get(question_type, self._answer_generic)
        return handler(symbol, interpretation)


def create_answer_engine(event_store) -> AnswerEngine:
    """Factory function to create answer engine."""
    interpretation_engine = InterpretationEngine(event_store)
    return AnswerEngine(event_store, interpretation_engine)


if __name__ == "__main__":
    # Quick test
    from trading_copilot.events.store import EventStore
    from trading_copilot.models.events import MarketEvent, EventType, EventStatus, EventImportance

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

        # Create engine and answer
        engine = AnswerEngine(store)
        
        # Test various questions
        questions = [
            "Why is AAPL moving?",
            "What happened with AAPL?",
            "What is AAPL's company impact?",
            "What is AAPL's stock impact?",
            "What are the scenarios for AAPL?",
            "What are the risks for AAPL?",
            "What is the next important event for AAPL?",
        ]

        for q in questions:
            request = AnswerRequest(symbol="AAPL", question=q)
            answer = engine.answer_question(request)
            print(f"\n{'='*60}")
            print(f"Q: {q}")
            print(f"A: {answer.answer}")
            print(f"Confidence: {answer.confidence:.0%}")
        
        store.close()