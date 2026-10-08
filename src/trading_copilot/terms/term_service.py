"""Term Definition Service — on-demand financial term definitions with authoritative references.

Zero-LLM core: all functionality works with LLM_ENABLED=false.
Definitions are deterministic and sourced from authoritative references.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional

from pydantic import BaseModel, Field


class TermDefinition(BaseModel):
    """Structured term definition with authoritative reference."""
    term: str
    short_definition: str
    long_definition: Optional[str] = None
    external_reference_url: Optional[str] = None
    reference_type: str = "official"  # official | educational | wikipedia
    category: str = "general"
    related_terms: list[str] = Field(default_factory=list)


class TermDefinitionService:
    """
    Deterministic term definition service providing on-demand definitions
    with authoritative external references.

    Zero-LLM core: all definitions are pre-loaded and deterministic.
    """

    def __init__(self, definitions_path: Optional[str] = None):
        self.definitions: dict[str, TermDefinition] = {}
        self._load_definitions(definitions_path)

    def _load_definitions(self, definitions_path: Optional[str] = None):
        """Load term definitions from embedded data or external file."""
        # Embedded authoritative definitions
        self._load_embedded_definitions()

        # Optionally load from external JSON file
        if definitions_path:
            try:
                with open(definitions_path, 'r') as f:
                    external = json.load(f)
                    for term_data in external:
                        self.definitions[term_data['term'].lower()] = TermDefinition(**term_data)
            except Exception as e:
                print(f"Warning: Could not load external definitions: {e}")

    def _load_embedded_definitions(self):
        """Load authoritative embedded term definitions."""
        definitions = [
            # Core Financial Metrics
            TermDefinition(
                term="EPS",
                short_definition="Earnings Per Share: Net income divided by outstanding shares. Measures profitability per share.",
                long_definition="Earnings Per Share (EPS) is calculated as (Net Income - Preferred Dividends) / Weighted Average Shares Outstanding. Basic EPS uses actual shares outstanding; Diluted EPS includes potential dilution from options, warrants, and convertible securities.",
                external_reference_url="https://www.sec.gov/fast-answers/answerseps.htm",
                reference_type="official",
                category="profitability",
                related_terms=["Diluted EPS", "Basic EPS", "Net Income", "P/E Ratio"]
            ),
            TermDefinition(
                term="Revenue",
                short_definition="Total income generated from business operations before expenses. Also called 'top line'.",
                long_definition="Revenue (or sales) is the total amount of money generated from selling goods or services before any expenses are deducted. It appears at the top of the income statement. Net revenue subtracts returns, allowances, and discounts.",
                external_reference_url="https://www.sec.gov/fast-answers/answersrevenue.htm",
                reference_type="official",
                category="income_statement",
                related_terms=["Net Revenue", "Gross Revenue", "Sales", "Top Line"]
            ),
            TermDefinition(
                term="Guidance",
                short_definition="Company's forward-looking estimates for future financial performance, typically for next quarter or fiscal year.",
                long_definition="Guidance (or outlook) is management's public estimate of future financial results, typically including expected revenue, EPS, and sometimes margins. Companies may raise, lower, maintain, or withdraw guidance. Guidance changes are closely watched as they signal management's confidence.",
                external_reference_url="https://www.sec.gov/rules/interp/2002/33-8176.htm",
                reference_type="official",
                category="forward_looking",
                related_terms=["Outlook", "Forward Guidance", "EPS Guidance", "Revenue Guidance"]
            ),
            TermDefinition(
                term="Consensus",
                short_definition="Average analyst estimate for a financial metric (EPS, revenue, etc.) from major sell-side analysts.",
                long_definition="Consensus estimate is the mean or median of all analyst forecasts for a specific metric (typically EPS or revenue) for a given period. It represents Wall Street's collective expectation. Beats/misses vs consensus drive short-term price movements.",
                external_reference_url="https://www.investopedia.com/terms/c/consensus-estimate.asp",
                reference_type="educational",
                category="analyst_estimates",
                related_terms=["Analyst Estimate", "Earnings Surprise", "Beat/Miss", "Whisper Number"]
            ),
            TermDefinition(
                term="Surprise",
                short_definition="Difference between actual reported value and consensus estimate. Positive surprise = beat; negative = miss.",
                long_definition="Earnings surprise = Actual EPS - Consensus EPS. Revenue surprise = Actual Revenue - Consensus Revenue. Surprise percentage = (Actual - Consensus) / |Consensus| * 100. Surprises drive immediate price reactions as markets reprice expectations.",
                external_reference_url="https://www.investopedia.com/terms/e/earnings-surprise.asp",
                reference_type="educational",
                category="earnings",
                related_terms=["Beat", "Miss", "Consensus", "Earnings Call"]
            ),
            TermDefinition(
                term="P/E Ratio",
                short_definition="Price-to-Earnings Ratio: Stock price divided by earnings per share. Measures valuation relative to earnings.",
                long_definition="P/E Ratio = Stock Price / EPS. Trailing P/E uses trailing 12-month EPS; Forward P/E uses next 12-month consensus EPS. Higher P/E suggests higher growth expectations or overvaluation; lower P/E suggests undervaluation or low growth expectations.",
                external_reference_url="https://www.investopedia.com/terms/p/price-earningsratio.asp",
                reference_type="educational",
                category="valuation",
                related_terms=["Forward P/E", "Trailing P/E", "PEG Ratio", "Earnings Yield"]
            ),
            TermDefinition(
                term="Free Cash Flow",
                short_definition="Cash generated from operations minus capital expenditures. Cash available for dividends, buybacks, debt paydown, or acquisitions.",
                long_definition="FCF = Operating Cash Flow - Capital Expenditures. Unlevered FCF excludes interest payments. FCF is preferred over earnings for valuation as it's harder to manipulate and represents actual cash generation. FCF yield = FCF / Market Cap.",
                external_reference_url="https://www.investopedia.com/terms/f/freecashflow.asp",
                reference_type="educational",
                category="cash_flow",
                related_terms=["Operating Cash Flow", "CapEx", "FCF Yield", "Unlevered FCF"]
            ),
            TermDefinition(
                term="Gross Margin",
                short_definition="Gross profit divided by revenue. Measures production profitability before operating expenses.",
                long_definition="Gross Margin = (Revenue - COGS) / Revenue. COGS = Cost of Goods Sold. Higher gross margin indicates pricing power or cost efficiency. Software companies typically have 70-90% gross margins; retailers 20-40%.",
                external_reference_url="https://www.investopedia.com/terms/g/grossmargin.asp",
                reference_type="educational",
                category="profitability",
                related_terms=["Operating Margin", "Net Margin", "COGS", "Contribution Margin"]
            ),
            TermDefinition(
                term="Operating Margin",
                short_definition="Operating income divided by revenue. Measures core business profitability after operating expenses.",
                long_definition="Operating Margin = Operating Income / Revenue. Operating Income = Gross Profit - Operating Expenses (R&D, SG&A, D&A). Excludes interest and taxes. Better measure of core operational efficiency than net margin.",
                external_reference_url="https://www.investopedia.com/terms/o/operatingmargin.asp",
                reference_type="educational",
                category="profitability",
                related_terms=["Gross Margin", "Net Margin", "EBIT Margin", "EBITDA Margin"]
            ),
            TermDefinition(
                term="P/E Ratio",
                short_definition="Price-to-Earnings Ratio: Stock price divided by earnings per share. Measures valuation relative to earnings.",
                long_definition="P/E Ratio = Stock Price / EPS. Trailing P/E uses trailing 12-month EPS; Forward P/E uses next 12-month consensus EPS. Higher P/E suggests higher growth expectations or overvaluation; lower P/E suggests undervaluation or low growth expectations.",
                external_reference_url="https://www.investopedia.com/terms/p/price-earningsratio.asp",
                reference_type="educational",
                category="valuation",
                related_terms=["Forward P/E", "Trailing P/E", "PEG Ratio", "Earnings Yield"]
            ),
            TermDefinition(
                term="PEG Ratio",
                short_definition="Price/Earnings-to-Growth Ratio: P/E ratio divided by expected earnings growth rate. Adjusts P/E for growth.",
                long_definition="PEG Ratio = P/E Ratio / Expected EPS Growth Rate (%). PEG < 1 suggests undervaluation relative to growth; PEG > 1 suggests overvaluation. Useful for comparing companies with different growth rates.",
                external_reference_url="https://www.investopedia.com/terms/p/peg.asp",
                reference_type="educational",
                category="valuation",
                related_terms=["P/E Ratio", "Forward P/E", "Growth Rate"]
            ),
            TermDefinition(
                term="EV/EBITDA",
                short_definition="Enterprise Value to EBITDA: Enterprise value divided by EBITDA. Capital structure-neutral valuation multiple.",
                long_definition="EV/EBITDA = (Market Cap + Debt - Cash) / EBITDA. EBITDA = Earnings Before Interest, Taxes, Depreciation, Amortization. Removes capital structure and depreciation policy differences. Lower = cheaper. Commonly used for M&A and cross-border comparisons.",
                external_reference_url="https://www.investopedia.com/terms/e/ev-ebitda.asp",
                reference_type="educational",
                category="valuation",
                related_terms=["EV", "EBITDA", "Enterprise Value", "EBITDA Margin"]
            ),
            TermDefinition(
                term="Relative Strength",
                short_definition="Stock's price performance relative to a benchmark (typically S&P 500) over a period. Measures outperformance/underperformance.",
                long_definition="Relative Strength = (Stock Return - Benchmark Return) over period. Positive = outperformance; Negative = underperformance. Often measured over 1, 3, 6, 12 months. Used in momentum strategies and to gauge relative momentum.",
                external_reference_url="https://www.investopedia.com/terms/r/relativestrength.asp",
                reference_type="educational",
                category="technical",
                related_terms=["RSI", "Momentum", "Alpha", "Beta"]
            ),
            TermDefinition(
                term="Volatility",
                short_definition="Statistical measure of price dispersion around the mean. Higher volatility = larger price swings, higher risk.",
                long_definition="Typically measured as standard deviation of log returns, annualized. Realized volatility uses historical prices; Implied volatility derives from option prices. Higher vol = higher risk/return potential. VIX measures implied S&P 500 volatility.",
                external_reference_url="https://www.investopedia.com/terms/v/volatility.asp",
                reference_type="educational",
                category="risk",
                related_terms=["Implied Volatility", "Realized Volatility", "VIX", "Beta", "Standard Deviation"]
            ),
            TermDefinition(
                term="Beta",
                short_definition="Measure of a stock's volatility relative to the overall market (usually S&P 500). Beta > 1 = more volatile than market; Beta < 1 = less volatile.",
                long_definition="Beta = Covariance(Stock, Market) / Variance(Market). Beta of 1.5 means stock moves 1.5x the market. High beta stocks amplify market moves; low beta stocks dampen them. Used in CAPM for cost of equity.",
                external_reference_url="https://www.investopedia.com/terms/b/beta.asp",
                reference_type="educational",
                category="risk",
                related_terms=["Alpha", "CAPM", "Correlation", "Volatility"]
            ),
            TermDefinition(
                term="Form 4",
                short_definition="SEC filing reporting insider transactions (purchases, sales, exercises) by officers, directors, and 10%+ owners. Filed within 2 business days.",
                long_definition="Form 4 reports changes in beneficial ownership. Key fields: transaction code (P=Purchase, S=Sale, M=Exercise, A=Award, G=Gift, F=Tax withholding), shares, price, holdings after, 10b5-1 indicator. Open-market purchases by CEOs/CFOs are strongest bullish signals; routine sales/diversification less meaningful.",
                external_reference_url="https://www.sec.gov/forms/form4.pdf",
                reference_type="official",
                category="sec_filings",
                related_terms=["Form 3", "Form 5", "10b5-1", "Insider Trading", "Beneficial Ownership"]
            ),
            TermDefinition(
                term="8-K",
                short_definition="SEC current report for material events shareholders should know about. Filed within 4 business days of event.",
                long_definition="8-K items include: 1.01 (Entry into material agreement), 2.01 (Completion of acquisition), 2.02 (Results of operations/earnings), 4.01 (Changes in auditor), 5.02 (Departure of directors/officers), 7.01 (Regulation FD disclosure). Item 2.02 (earnings) and 5.02 (leadership) are most watched.",
                external_reference_url="https://www.sec.gov/files/form8-k.pdf",
                reference_type="official",
                category="sec_filings",
                related_terms=["10-Q", "10-K", "Form 4", "Item 2.02", "Item 5.02", "Regulation FD"]
            ),
            TermDefinition(
                term="10-Q",
                short_definition="SEC quarterly report with unaudited financial statements, MD&A, risk factors, and controls. Filed 40-45 days after quarter end.",
                long_definition="10-Q includes: Part I - Financial Statements (Balance Sheet, Income Statement, Cash Flow), Part II - MD&A, Risk Factors, Legal Proceedings, Controls & Procedures. Less detailed than 10-K but more timely. Filed 3x/year.",
                external_reference_url="https://www.sec.gov/forms/form10-q.pdf",
                reference_type="official",
                category="sec_filings",
                related_terms=["10-K", "8-K", "MD&A", "Quarterly Report"]
            ),
            TermDefinition(
                term="10-K",
                short_definition="SEC annual report with audited financial statements, comprehensive MD&A, risk factors, executive compensation, and corporate governance. Filed 60-90 days after fiscal year end.",
                long_definition="10-K includes: Business, Risk Factors, Properties, Legal Proceedings, MD&A, Financial Statements (audited), Executive Compensation, Corporate Governance, Exhibits. Most comprehensive periodic filing. Filed annually.",
                external_reference_url="https://www.sec.gov/forms/form10-k.pdf",
                reference_type="official",
                category="sec_filings",
                related_terms=["10-Q", "8-K", "Annual Report", "Proxy Statement"]
            ),
            TermDefinition(
                term="FOMC",
                short_definition="Federal Open Market Committee: The Fed's monetary policy committee that sets interest rate policy. Meets 8x/year.",
                long_definition="FOMC sets the federal funds rate target, conducts open market operations, and communicates forward guidance via Statement, Minutes (3 weeks later), and Summary of Economic Projections (SEP/Dot Plot) quarterly. Decisions drive global rates, currencies, and risk assets.",
                external_reference_url="https://www.federalreserve.gov/monetarypolicy/fomc.htm",
                reference_type="official",
                category="macro",
                related_terms=["Federal Funds Rate", "Dot Plot", "Fed Funds Futures", "Monetary Policy"]
            ),
            TermDefinition(
                term="CPI",
                short_definition="Consumer Price Index: Measures average price change for a basket of consumer goods/services. Primary inflation gauge.",
                long_definition="CPI measures price changes for urban consumers (CPI-U). Core CPI excludes food/energy. Reported monthly by BLS. Year-over-year % change is headline inflation. Fed targets 2% PCE inflation (similar to CPI).",
                external_reference_url="https://www.bls.gov/cpi/",
                reference_type="official",
                category="macro",
                related_terms=["Core CPI", "PCE", "PPI", "Inflation", "Real Wages"]
            ),
            TermDefinition(
                term="PCE",
                short_definition="Personal Consumption Expenditures Price Index: Fed's preferred inflation measure. Broader basket than CPI, includes employer-paid healthcare.",
                long_definition="PCE Price Index measures price changes for goods/services consumed by households. Core PCE excludes food/energy. Fed's 2% target refers to Core PCE. PCE weights update monthly vs CPI's annual update; PCE captures substitution effects better.",
                external_reference_url="https://www.bea.gov/data/personal-consumption-expenditures-price-index",
                reference_type="official",
                category="macro",
                related_terms=["Core PCE", "CPI", "PCE Deflator", "Inflation Target"]
            ),
            TermDefinition(
                term="NFP",
                short_definition="Nonfarm Payrolls: Monthly count of US jobs added/lost excluding farm, government, private household, and nonprofit employees. Key labor market indicator.",
                long_definition="NFP (from Establishment Survey) measures net job creation. Released first Friday monthly by BLS. Average hourly earnings and unemployment rate (from Household Survey) released simultaneously. Strong NFP = economic strength = potential rate hikes.",
                external_reference_url="https://www.bls.gov/cps/faq.htm#Ques5",
                reference_type="official",
                category="macro",
                related_terms=["Unemployment Rate", "Average Hourly Earnings", "Labor Force Participation", "JOLTS"]
            ),
            TermDefinition(
                term="10b5-1 Plan",
                short_definition="Pre-arranged trading plan allowing insiders to trade on a set schedule, providing affirmative defense against insider trading claims.",
                long_definition="Rule 10b5-1 allows insiders to pre-arrange trades when not in possession of MNPI. Must be in good faith, not modified, executed by independent broker. Provides legal defense but doesn't prevent all scrutiny. Plans often set up quarterly/annually.",
                external_reference_url="https://www.sec.gov/rules/final/33-8298.htm",
                reference_type="official",
                category="insider",
                related_terms=["Form 4", "MNPI", "Insider Trading", "Affirmative Defense"]
            ),
            TermDefinition(
                term="Buyback",
                short_definition="Share repurchase: Company buys back its own shares from the open market, reducing share count and increasing EPS.",
                long_definition="Buybacks return capital to shareholders tax-efficiently (vs dividends). Reduces share count, boosting EPS. Can signal management believes stock is undervalued. Authorized amount and expiration disclosed in 10-K/Q. ASR (Accelerated Share Repurchase) executes immediately via bank.",
                external_reference_url="https://www.investopedia.com/terms/s/share-repurchase.asp",
                reference_type="educational",
                category="corporate_action",
                related_terms=["Dividend", "ASR", "EPS", "Capital Allocation", "Treasury Stock"]
            ),
            TermDefinition(
                term="Dividend",
                short_definition="Cash distribution to shareholders from profits. Expressed as $/share or yield (dividend/price).",
                long_definition="Dividends are typically paid quarterly. Key dates: Declaration, Ex-dividend (buyer after doesn't get dividend), Record, Payment. Qualified dividends taxed at lower rates. Payout ratio = Dividends / Net Income. High payout (>80%) may be unsustainable.",
                external_reference_url="https://www.investopedia.com/terms/d/dividend.asp",
                reference_type="educational",
                category="corporate_action",
                related_terms=["Ex-Dividend Date", "Payout Ratio", "Yield", "Qualified Dividend", "Buyback"]
            ),
            TermDefinition(
                term="Stock Split",
                short_definition="Increases share count proportionally while reducing price proportionally. No change to market cap or shareholder value.",
                long_definition="Forward split (2:1) doubles shares, halves price. Reverse split (1:10) reduces shares, increases price (often to avoid delisting). No fundamental change; improves liquidity/accessibility. Fractional shares handled by broker.",
                external_reference_url="https://www.investopedia.com/terms/s/stocksplit.asp",
                reference_type="educational",
                category="corporate_action",
                related_terms=["Reverse Split", "Fractional Shares", "Liquidity", "Market Cap"]
            ),
            TermDefinition(
                term="SPY",
                short_definition="SPDR S&P 500 ETF Trust: ETF tracking the S&P 500 index. Most liquid ETF; benchmark for US large-cap equity performance.",
                long_definition="SPY holds all 503 S&P 500 constituents weighted by market cap. Expense ratio 0.0945%. Highly liquid with tight spreads. Used as market proxy, hedging instrument, and benchmark for relative performance.",
                external_reference_url="https://www.spdrs.com/product/fund.seam/ticker/spy",
                reference_type="educational",
                category="etf",
                related_terms=["S&P 500", "ETF", "Benchmark", "QQQ", "IWM"]
            ),
            TermDefinition(
                term="Quant Score",
                short_definition="Deterministic composite score (0-100) combining momentum (40%), trend (25%), liquidity (15%), volume (10%), volatility quality (10%). Higher = more attractive.",
                long_definition="Momentum = cross-sectional percentile of weighted returns (21d/63d/126d). Trend = deterministic rules (SMA crossovers, distance from averages). Liquidity = dollar volume percentile. Volume = relative volume percentile. Vol Quality = piecewise mapping of realized vol percentile. Tie-break: quant_score desc, dollar_volume desc, symbol asc.",
                external_reference_url="",
                reference_type="internal",
                category="quant",
                related_terms=["Momentum", "Trend", "Liquidity", "Volume", "Volatility Quality"]
            ),
        ]

        for defn in definitions:
            self.definitions[defn.term.lower()] = defn

    def get_definition(self, term: str) -> Optional[TermDefinition]:
        """Get definition for a term (case-insensitive)."""
        return self.definitions.get(term.lower())

    def search_terms(self, query: str) -> list[TermDefinition]:
        """Search terms by query string (case-insensitive substring match)."""
        query = query.lower()
        return [d for term, d in self.definitions.items() if query in term]

    def get_all_terms(self) -> list[str]:
        """Get all defined term names."""
        return sorted(self.definitions.keys())

    def get_terms_by_category(self, category: str) -> list[TermDefinition]:
        """Get all terms in a category."""
        return [d for d in self.definitions.values() if d.category == category]


# Global singleton instance
_term_service: Optional[TermDefinitionService] = None


def get_term_service() -> TermDefinitionService:
    """Get singleton term definition service instance."""
    global _term_service
    if _term_service is None:
        _term_service = TermDefinitionService()
    return _term_service


def get_term_definition(term: str) -> Optional[TermDefinition]:
    """Convenience function to get a term definition."""
    return get_term_service().get_definition(term)


if __name__ == "__main__":
    # Quick test
    service = TermDefinitionService()
    print(f"Total terms: {len(service.definitions)}")

    # Test lookups
    for term in ["EPS", "P/E Ratio", "CPI", "FOMC", "Form 4", "10b5-1 Plan"]:
        defn = service.get_definition(term)
        if defn:
            print(f"\n{defn.term}: {defn.short_definition}")
            if defn.external_reference_url:
                print(f"  Reference: {defn.external_reference_url}")

    # Search test
    results = service.search_terms("margin")
    print(f"\nSearch 'margin': {[r.term for r in results]}")

    # Category test
    macro_terms = service.get_terms_by_category("macro")
    print(f"\nMacro terms: {[t.term for t in macro_terms]}")