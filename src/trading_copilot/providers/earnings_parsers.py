"""Deterministic earnings extraction from SEC filings; unknown is preferable to invented facts."""
from __future__ import annotations

import re
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any


def extract_eps_revenue(text: str) -> dict[str, Any]:
    """
    Extract EPS and revenue actuals/consensus from earnings release text (8-K Item 2.02, 10-Q, 10-K).

    Only extracts when explicit numeric values with clear labels are present.
    Does NOT infer or calculate missing values.
    """
    result = {
        "eps_actual": None,
        "eps_consensus": None,
        "revenue_actual": None,
        "revenue_consensus": None,
        "guidance": None,
    }

    # Normalize whitespace
    text = re.sub(r"\s+", " ", text)

    # Patterns for EPS actual - more specific to avoid matching consensus text
    # Require result-indicating verbs or sentence-start contexts
    eps_actual_patterns = [
        r"(?:reported|announced|posted)\s+(?:diluted\s+)?earnings\s+per\s+share\s+(?:of|:)\s*\$?(?P<value>\d+\.?\d*)",
        r"(?:reported|announced|posted)\s+(?:diluted\s+)?EPS\s+(?:of|:)\s*\$?(?P<value>\d+\.?\d*)",
        r"(?:diluted\s+)?earnings\s+per\s+share\s+(?:was|of|:)\s*\$?(?P<value>\d+\.?\d*)",  # "earnings per share of" is usually actual
        r"(?:basic\s+)?earnings\s+per\s+share\s+(?:was|of|:)\s*\$?(?P<value>\d+\.?\d*)",    # same
        r"(?:^|\.|\n)\s*(?:diluted\s+)?EPS\s+(?:was|:)\s*\$?(?P<value>\d+\.?\d*)",      # sentence start, no "of"
        r"net\s+income\s+per\s+(?:diluted\s+)?share\s+(?:was|of|:)\s*\$?(?P<value>\d+\.?\d*)",
        # Table format: "Diluted earnings per share: $1.55"
        r"(?:diluted\s+)?earnings\s+per\s+share\s*:\s*\$?(?P<value>\d+\.?\d*)",
        r"(?:basic\s+)?earnings\s+per\s+share\s*:\s*\$?(?P<value>\d+\.?\d*)",
        r"(?:diluted\s+)?EPS\s*:\s*\$?(?P<value>\d+\.?\d*)",
        # "EPS of $2.30" in result context (not consensus)
        r"(?:^|\.|\n)\s*EPS\s+of\s*\$?(?P<value>\d+\.?\d*)",
    ]

    # Patterns for EPS consensus/estimate
    eps_consensus_patterns = [
        r"(?:consensus|estimate)\s+(?:EPS|earnings\s+per\s+share)\s+(?:was|were|of|:)\s*\$?(?P<value>\d+\.?\d*)",
        r"(?:analysts?\s+)?(?:expected|forecast)\s+(?:EPS|earnings\s+per\s+share)\s+(?:of|at|:)\s*\$?(?P<value>\d+\.?\d*)",
        r"consensus\s+estimate\s+(?:of|:)?\s*\$?(?P<value>\d+\.?\d*)",
        # "compared to $1.42 consensus estimate" - value before consensus
        r"(?:vs|versus|compared to)\s+\$?(?P<value>\d+\.?\d*)\s+(?:consensus|estimate)",
        # "Consensus estimates [for period] were EPS of $1.42"
        r"consensus\s+estimates?\s+(?:for\s+.+?)?(?:was|were)\s+(?:EPS|earnings\s+per\s+share)\s+(?:of|:)\s*\$?(?P<value>\d+\.?\d*)",
    ]

    # Patterns for revenue actual - prefer full dollar amounts over abbreviated
    revenue_actual_patterns = [
        # Table format: "Revenue: $89,500,000,000" (most specific, try first)
        r"(?:total\s+)?revenue\s*:\s*\$?(?P<value>\d{1,3}(?:,\d{3})+(?:\.\d+)?)",
        # Full dollar amounts with "of/was/were" 
        r"(?:total\s+)?revenue\s+(?:was|were|of)\s*\$?(?P<value>\d{1,3}(?:,\d{3})+(?:\.\d+)?)",
        r"net\s+sales\s+(?:was|were|of)\s*\$?(?P<value>\d{1,3}(?:,\d{3})+(?:\.\d+)?)",
        # Fallback for any number format with colon
        r"(?:total\s+)?revenue\s*:\s*\$?(?P<value>\d+(?:,\d{3})*(?:\.\d+)?)",
        # Fallback for any number format with of/was/were
        r"(?:total\s+)?revenue\s+(?:was|were|of)\s*\$?(?P<value>\d+(?:,\d{3})*(?:\.\d+)?)",
        r"net\s+sales\s+(?:was|were|of)\s*\$?(?P<value>\d+(?:,\d{3})*(?:\.\d+)?)",
    ]

    # Patterns for revenue consensus - prefer full dollar amounts
    revenue_consensus_patterns = [
        # Full dollar amounts first
        r"(?:consensus|estimate)\s+revenue\s+(?:was|were|of|:)\s*\$?(?P<value>\d{1,3}(?:,\d{3})+(?:\.\d+)?)",
        r"(?:analysts?\s+)?(?:expected|forecast)\s+revenue\s+(?:of|at|:)\s*\$?(?P<value>\d{1,3}(?:,\d{3})+(?:\.\d+)?)",
        r"consensus\s+revenue\s+(?:of|:)?\s*\$?(?P<value>\d{1,3}(?:,\d{3})+(?:\.\d+)?)",
        r"(?:vs|versus|compared to)\s+\$?(?P<value>\d{1,3}(?:,\d{3})+(?:\.\d+)?)\s+revenue\s+(?:consensus|estimate)",
        # "Consensus estimates [for period] were revenue of $X"
        r"consensus\s+estimates?\s+(?:for\s+.+?)?(?:was|were)\s+revenue\s+(?:of|:)\s*\$?(?P<value>\d{1,3}(?:,\d{3})+(?:\.\d+)?)",
        # "Consensus estimates [for period] were EPS of $X and revenue of $Y"
        r"consensus\s+estimates?\s+(?:for\s+.+?)?(?:was|were)\s+(?:EPS|earnings\s+per\s+share)\s+(?:of|:)\s*\$?(?:\d+\.?\d*)\s+and\s+revenue\s+(?:of|:)\s*\$?(?P<value>\d{1,3}(?:,\d{3})+(?:\.\d+)?)",
        # "Revenue of $X, compared to $Y consensus estimate" - match $Y in revenue context
        r"revenue\s+(?:of|:)\s*\$?(?:\d+(?:,\d{3})*(?:\.\d+)?)[^.]*?(?:vs|versus|compared to)\s+\$?(?P<value>\d{1,3}(?:,\d{3})+(?:\.\d+)?)\s+consensus\s+estimate",
        # Abbreviated: "$89.2 billion" or "$89.2B"
        r"(?:consensus|estimate)\s+revenue\s+(?:was|were|of|:)\s*\$?(?P<value>\d+(?:\.\d+)?)\s*(?:billion|B)\b",
        r"(?:analysts?\s+)?(?:expected|forecast)\s+revenue\s+(?:of|at|:)\s*\$?(?P<value>\d+(?:\.\d+)?)\s*(?:billion|B)\b",
        r"consensus\s+revenue\s+(?:of|:)?\s*\$?(?P<value>\d+(?:\.\d+)?)\s*(?:billion|B)\b",
        r"consensus\s+estimates?\s+(?:for\s+.+?)?(?:was|were)\s+revenue\s+(?:of|:)\s*\$?(?P<value>\d+(?:\.\d+)?)\s*(?:billion|B)\b",
        # "and revenue of $X billion" in consensus sentence
        r"and\s+revenue\s+(?:of|:)\s*\$?(?P<value>\d+(?:\.\d+)?)\s*(?:billion|B)\b",
        # "and revenue of $X" full dollar amount
        r"and\s+revenue\s+(?:of|:)\s*\$?(?P<value>\d{1,3}(?:,\d{3})+(?:\.\d+)?)",
        # Fallback
        r"(?:consensus|estimate)\s+revenue\s+(?:was|were|of|:)\s*\$?(?P<value>\d+(?:,\d{3})*(?:\.\d+)?)",
        r"(?:analysts?\s+)?(?:expected|forecast)\s+revenue\s+(?:of|at|:)\s*\$?(?P<value>\d+(?:,\d{3})*(?:\.\d+)?)",
        r"consensus\s+revenue\s+(?:of|:)?\s*\$?(?P<value>\d+(?:,\d{3})*(?:\.\d+)?)",
        r"(?:vs|versus|compared to)\s+\$?(?P<value>\d+(?:,\d{3})*(?:\.\d+)?)\s+revenue\s+(?:consensus|estimate)",
        r"consensus\s+estimates?\s+(?:for\s+.+?)?(?:was|were)\s+revenue\s+(?:of|:)\s*\$?(?P<value>\d+(?:,\d{3})*(?:\.\d+)?)",
    ]

    # Patterns for guidance
    guidance_patterns = [
        # Broader guidance capture first: "expects Q4 FY2026 EPS of $1.60 to $1.70 and revenue..."
        r"(?:expects?|anticipate|project)\s+(?:Q\d\s+)?(?:FY\d{4}|fiscal\s+\d{4})\s*.{0,500}",
        r"guidance\s+(?:for\s+)?(?:Q\d\s+)?(?:FY\d{4}|fiscal\s+\d{4})\s*:?\s*(?P<text>.{0,500})",
        r"(?:expects?|anticipate|project)\s+(?:Q\d\s+)?(?:FY\d{4}|fiscal\s+\d{4})\s+(?:EPS|earnings\s+per\s+share)\s+(?:of\s+)?\$?(?P<eps>\d+\.?\d*)",
        r"(?:expects?|anticipate|project)\s+(?:Q\d\s+)?(?:FY\d{4}|fiscal\s+\d{4})\s+revenue\s+(?:of\s+)?\$?(?P<rev>\d+(?:,\d{3})*(?:\.\d+)?)",
    ]

    def find_first(patterns: list[str]) -> str | None:
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                value = match.group("value") if "value" in match.groupdict() else match.group(0)
                # Check if the match included billion/B suffix
                full_match = match.group(0).lower()
                if 'billion' in full_match or re.search(r'\b[bB]\b', full_match):
                    try:
                        num = Decimal(value.replace(",", ""))
                        return str(int(num * Decimal("1000000000")))
                    except (InvalidOperation, ValueError):
                        pass
                return value
        return None

    def parse_number(value: str) -> str | None:
        """Parse number string, handling commas and converting to plain string."""
        try:
            cleaned = value.replace(",", "")
            # Validate it's a valid number
            Decimal(cleaned)
            return cleaned
        except (InvalidOperation, ValueError):
            return None

    eps_actual = find_first(eps_actual_patterns)
    if eps_actual:
        result["eps_actual"] = parse_number(eps_actual)

    eps_consensus = find_first(eps_consensus_patterns)
    if eps_consensus:
        result["eps_consensus"] = parse_number(eps_consensus)

    revenue_actual = find_first(revenue_actual_patterns)
    if revenue_actual:
        result["revenue_actual"] = parse_number(revenue_actual)

    revenue_consensus = find_first(revenue_consensus_patterns)
    if revenue_consensus:
        result["revenue_consensus"] = parse_number(revenue_consensus)

    # Extract guidance text (preserve raw text for later processing)
    for pattern in guidance_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            result["guidance"] = match.group("text").strip() if "text" in match.groupdict() else match.group(0).strip()
            break

    return result


def extract_guidance_details(text: str) -> dict[str, Any] | None:
    """
    Extract structured guidance from text. Only returns when explicit ranges/values found.

    Returns dict with:
    - guidance_type: quarterly|annual|long_term
    - period: e.g., "Q4 FY2026"
    - eps_guidance_low/high
    - revenue_guidance_low/high
    - guidance_change: raised|lowered|maintained|new
    """
    # Look for explicit guidance ranges
    # Allow optional words like "guidance", "of", "range" between EPS/revenue and the range
    eps_range_pattern = r"(?:EPS|earnings\s+per\s+share)(?:\s+(?:guidance|of|range))?\s+(?:of\s+)?\$?(?P<low>\d+\.?\d*)\s*(?:to|–|-)\s*\$?(?P<high>\d+\.?\d*)"
    revenue_range_pattern = r"revenue(?:\s+(?:guidance|of|range))?\s+(?:of\s+)?\$?(?P<low>\d+(?:,\d{3})*(?:\.\d+)?)\s*(?:to|–|-)\s*\$?(?P<high>\d+(?:,\d{3})*(?:\.\d+)?)"

    eps_match = re.search(eps_range_pattern, text, re.IGNORECASE)
    revenue_match = re.search(revenue_range_pattern, text, re.IGNORECASE)

    # Also try with $ signs on both sides
    if not eps_match:
        eps_range_pattern_alt = r"(?:EPS|earnings\s+per\s+share)\s+(?:of\s+)?\$(?P<low>\d+\.?\d*)\s*(?:to|–|-)\s*\$(?P<high>\d+\.?\d*)"
        eps_match = re.search(eps_range_pattern_alt, text, re.IGNORECASE)
    if not revenue_match:
        revenue_range_pattern_alt = r"revenue\s+(?:of\s+)?\$(?P<low>\d+(?:,\d{3})*(?:\.\d+)?)\s*(?:to|–|-)\s*\$(?P<high>\d+(?:,\d{3})*(?:\.\d+)?)"
        revenue_match = re.search(revenue_range_pattern_alt, text, re.IGNORECASE)

    if not eps_match and not revenue_match:
        return None

    def parse_num(val: str) -> str | None:
        try:
            return str(Decimal(val.replace(",", "")))
        except (InvalidOperation, ValueError):
            return None

    result = {
        "guidance_type": "quarterly",  # default, could be refined
        "period": None,
        "eps_guidance_low": None,
        "eps_guidance_high": None,
        "revenue_guidance_low": None,
        "revenue_guidance_high": None,
        "guidance_change": "new",
    }

    if eps_match:
        result["eps_guidance_low"] = parse_num(eps_match.group("low"))
        result["eps_guidance_high"] = parse_num(eps_match.group("high"))

    if revenue_match:
        result["revenue_guidance_low"] = parse_num(revenue_match.group("low"))
        result["revenue_guidance_high"] = parse_num(revenue_match.group("high"))

    # Detect guidance change language
    if re.search(r"(?:rais|increas)", text, re.IGNORECASE):
        result["guidance_change"] = "raised"
    elif re.search(r"(?:lower|decreas|reduc)", text, re.IGNORECASE):
        result["guidance_change"] = "lowered"
    elif re.search(r"(?:maintain|reaffirm|confirm)", text, re.IGNORECASE):
        result["guidance_change"] = "maintained"

    # Try to extract period
    period_match = re.search(r"(Q[1-4]\s+FY\d{4}|fiscal\s+(?:year|quarter)\s+\d{4})", text, re.IGNORECASE)
    if period_match:
        result["period"] = period_match.group(1).upper()
    else:
        # Try more flexible patterns
        period_match = re.search(r"(Q[1-4]\s+\d{4}|FY\d{4})", text, re.IGNORECASE)
        if period_match:
            result["period"] = period_match.group(1).upper()
        else:
            # Try "fiscal quarter N YYYY"
            period_match = re.search(r"fiscal\s+quarter\s+\d\s+\d{4}", text, re.IGNORECASE)
            if period_match:
                result["period"] = period_match.group(0).upper()

    return result


def compute_surprise(actual: str | None, consensus: str | None) -> tuple[str | None, str | None]:
    """
    Compute surprise (actual - consensus) and surprise percentage.

    Returns (surprise_value, surprise_pct) as strings, or (None, None) if either input missing.
    """
    if actual is None or consensus is None:
        return None, None

    try:
        actual_val = Decimal(actual)
        consensus_val = Decimal(consensus)
        surprise = actual_val - consensus_val
        if consensus_val != 0:
            surprise_pct = (surprise / consensus_val) * Decimal("100")
            return str(surprise), str(surprise_pct.quantize(Decimal("0.01")))
        return str(surprise), None
    except (InvalidOperation, ValueError, DivisionByZero):
        return None, None


# Need to import DivisionByZero
from decimal import DivisionByZero