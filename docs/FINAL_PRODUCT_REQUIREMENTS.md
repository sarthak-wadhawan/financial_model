# Financial Prediction / Financial Intelligence Platform
## Final Product Requirements

This document is the authoritative final-product specification.

The product is a user-friendly stock research website that combines:
- live/latest market data,
- the existing deterministic quantitative scanner,
- market-wide event intelligence,
- company-specific event intelligence,
- earnings intelligence,
- management and insider intelligence,
- SEC filings,
- news and management statements,
- evidence-backed AI explanations,
- strategy research,
- watchlists, calendars, and alerts.

The product should feel like a modern stocks app, but go beyond price display by answering:

> What matters, why does it matter, what changed, and what should I know next?

Correctness, freshness, evidence, and clarity are more important than flashy AI or information density.

## Core principles

1. Answers first, details second.
2. Every important factual claim should be traceable to evidence.
3. Prefer primary sources where practical.
4. Distinguish verified fact, calculated market data, attributed explanation, AI summary, and inference.
5. If a cause is unclear, say it is unclear.
6. AI must not invent facts, dates, numbers, or causes.
7. The deterministic quant scanner remains independent of the AI.
8. Preserve historical state so the system can answer what changed since the prior run.
9. No automatic trade placement in the current product scope.
10. Human review remains the final decision point.

## Live market data

Support:
- current/latest stock price,
- daily change and percentage change,
- historical OHLCV,
- volume,
- benchmark/index context,
- chart-ready history,
- timestamps,
- replaceable provider abstraction.

The first real provider is Alpaca. Mock mode stays available for offline tests.

## Deterministic scanner

Preserve the current transparent score:
- Momentum 40%
- Trend 25%
- Liquidity 15%
- Volume confirmation 10%
- Volatility quality 10%

Support universe scanning, eligibility filtering, deterministic ranking, top-N candidates, and reproducible artifacts. The LLM must not alter these calculations.

## Strategy research

Preserve the original research direction:
- cross-sectional momentum,
- trend following,
- post-earnings announcement drift,
- event-driven opportunities,
- short-term mean reversion,
- volatility/options-premium strategies,
- cash-secured puts / covered calls / defined-risk premium workflows,
- Model A / microstructure signals as a later filter.

Keep these independently testable. Do not merge them into an opaque AI score.

## Market-wide event intelligence

Track major market-wide events including:
- FOMC meetings and rate decisions,
- Fed press conferences and projections,
- CPI / Core CPI,
- PPI,
- PCE / Core PCE,
- Employment Situation / nonfarm payrolls,
- unemployment rate,
- average hourly earnings,
- GDP,
- JOLTS,
- initial jobless claims,
- retail sales,
- ISM Manufacturing / Services,
- consumer confidence / sentiment,
- durable goods,
- housing starts,
- new/existing home sales,
- Employment Cost Index,
- trade balance,
- other configurable macro events.

Each event should store:
- event ID,
- event type,
- title,
- scheduled date/time and timezone,
- importance,
- status,
- actual,
- consensus/forecast where available,
- previous,
- source and source URL,
- retrieval timestamp,
- last-updated timestamp.

Refresh authoritative schedules on application runs while preserving previously known events.

## Unified event memory

Use one persistent event architecture, initially SQLite.

Event categories:
- macro,
- earnings,
- corporate,
- dividend,
- split,
- M&A,
- leadership,
- insider,
- SEC filing,
- regulatory,
- investor event,
- product/company announcement,
- other.

Runtime flow:

```text
load stored events
→ refresh providers
→ compare old vs new state
→ add new events
→ update changed events
→ mark released events
→ expose today/upcoming/recent events
```

## Company event intelligence

Track where available:
- next earnings date/time,
- previous earnings,
- dividends/ex-dividend/payment dates,
- stock splits,
- M&A/spin-offs,
- investor days,
- major conferences,
- material regulatory events,
- corporate actions,
- important company announcements.

## Earnings intelligence

Capture where available:
- scheduled date/time,
- EPS actual/consensus,
- revenue actual/consensus,
- guidance and guidance change,
- management commentary,
- price before release,
- after-hours reaction,
- next-session reaction,
- 5-session reaction,
- historical earnings reaction,
- source documents.

Answer:
- when next earnings is,
- what happened last earnings,
- whether guidance changed,
- how the stock reacted,
- why shares reacted, using evidence.

## Management intelligence

Maintain:
- current CEO/CFO,
- relevant major executives,
- appointment/departure dates,
- replacement announcements,
- major leadership changes,
- important management statements,
- source filings/news.

Do not hard-code leadership permanently.

## Insider intelligence

Track:
- insider name and role,
- transaction date,
- filing date,
- buy/sell/other,
- shares,
- transaction price/value,
- holdings after transaction where available,
- filing/source,
- 10b5-1 indicator where available.

Classify where possible:
- open-market purchase,
- open-market sale,
- option exercise,
- grant/award,
- gift,
- tax-related disposition,
- 10b5-1 related,
- other.

Do not automatically interpret every sale as bearish.

## SEC / filing intelligence

Support:
- 8-K,
- 10-Q,
- 10-K,
- Form 4,
- other materially relevant filings.

Preserve source links, detect new filings, identify material changes, and surface leadership/guidance/corporate developments.

## News and management statements

Track material:
- company announcements,
- management interviews/statements,
- earnings-call comments,
- investor-conference comments,
- regulatory news,
- product developments,
- analyst-related developments where supported,
- industry developments relevant to the stock.

Prioritize meaningful developments, not article volume.

## Answer Engine

Create a dedicated `Answer Engine`.

It should answer:
- Why is this stock up/down today?
- Why has this stock been weak/strong recently?
- Why are investors interested?
- What are investors worried about?
- What changed since yesterday?
- What happened in the latest earnings report?
- Why did shares rise/fall after earnings?
- When is next earnings?
- What is the next important event?
- Has management changed?
- Has the CEO said anything important recently?
- Have insiders been buying/selling?
- What are the important catalysts?
- What are the main risks?
- What economic data matters today?
- What just came out?
- How did the release compare with expectations?
- What stocks currently rank highly in our scanner?

Answers should be concise by default with expandable evidence.

## Company narrative

Every stock page should support evidence-backed sections:
- Why investors are interested
- Investor concerns
- Catalysts
- Risks
- What changed recently
- Why the stock is moving

These must update with new evidence and must not become static AI opinions.

## "What Changed?" feature

Required.

Examples:

```text
NEW
- CFO Form 4 filed
- New CEO appointed
- Earnings date now 6 days away

CHANGED
- Quant score: 81 → 87
- Guidance changed

UNCHANGED
- No new major filing
```

## Website

The website is the primary final interface.

Design:
- simple,
- fast,
- answer-focused,
- minimal clutter,
- sources accessible but not overwhelming.

### Home page
- ticker/company search,
- market snapshot,
- today's important macro events,
- just-released economic data with actual/expected/previous,
- next important events,
- scanner candidates,
- watchlist,
- recent company events.

### Stock page
- ticker/company,
- latest price and daily change,
- chart,
- What You Need To Know,
- Why Is It Moving?,
- quant score/components,
- upcoming events,
- earnings,
- Why Investors Are Interested,
- Investor Concerns,
- What Changed,
- management,
- insider activity,
- catalysts,
- risks,
- filings,
- important news,
- sources.

## Calendar integration

Scheduled events should support `+ Add to Calendar`.

Initial implementation:
- standards-compliant `.ics`,
- title,
- ticker/company if relevant,
- exact date/time,
- timezone,
- description,
- source link.

## Historical event impact

Future analysis:
- SPY reaction around CPI, payrolls, FOMC, PCE, GDP, etc.,
- windows such as 5m, 1h, session, following sessions,
- individual-stock reaction around earnings, guidance, management changes, major filings.

Use actual market data, not AI estimates.

## AI role

AI may:
- extract facts,
- compare documents,
- summarize,
- identify source-supported catalysts/risks,
- explain supported relationships,
- build concise answers.

AI may not:
- invent facts/dates/causes,
- modify quant scores,
- place trades,
- silently override deterministic logic,
- manufacture an answer when evidence is insufficient.

## Correctness / source requirements

For every important answer preserve where available:
- source,
- source URL,
- source publication time,
- retrieval time.

Prefer primary sources. Preserve conflicts. If evidence is insufficient, say so.

## Interpretation Engine (Core Product Behavior)

The central value of the product is interpretation + impact. Every meaningful event must answer:

```text
WHAT HAPPENED?
WHAT DOES IT MEAN?
WHY DOES IT MATTER?
HOW DOES IT AFFECT THE COMPANY?
HOW COULD IT AFFECT THE STOCK?
WHAT IS THE TIME HORIZON?
WHAT IS THE BASE CASE?
WHAT IS THE BULL CASE?
WHAT IS THE BEAR CASE?
WHAT EVIDENCE SUPPORTS THIS?
WHAT WOULD CHANGE THE VIEW?
WHAT IS THE CONFIDENCE?
```

These are not optional UI enhancements — they are core product behavior. Every research brief, stock page section, and answer must address these questions using evidence.

### Company Impact vs Stock Impact

Store and represent separately:

- **company_impact**: Fundamental business impact (e.g., "guidance raised 5%, margin expansion likely")
- **stock_bias**: Directional market expectation (e.g., "moderately bullish", "neutral", "bearish")
- **confidence**: Low / Medium / High
- **time_horizon**: Days / Weeks / Months / Quarters

Company impact ≠ stock impact. A company may have positive fundamentals while the stock sells off (or vice versa). Both must be explicit.

### Scenario Analysis

Every interpretation must include:

- **BASE CASE**: Most likely outcome with evidence
- **BULL CASE**: Upside scenario with trigger conditions
- **BEAR CASE**: Downside scenario with trigger conditions
- **WHAT WOULD CHANGE THE VIEW**: Specific evidence that would invalidate the base case

### Term UX — Definitions on Demand

Do not use repeated question-mark icons.

- **Desktop**: Hover/focus any financial term → short local definition popover
- **Mobile**: Tap term → definition popover

Popover may include:
- **Learn more** → external reference link

External reference priority:
1. Authoritative official source (e.g., SEC.gov, FederalReserve.gov, BLS.gov)
2. Reputable educational source (e.g., Investopedia, corporate finance institute)
3. Wikipedia when appropriate

Why It Matters and Market Impact remain inside our application — they are our interpretation.

### Zero-LLM Core

All core functionality must work with:

```bash
LLM_ENABLED=false
```

Optional local/free AI may enhance qualitative explanation later (Phase 8+). The deterministic quant scanner, event store, evidence validation, answer engine, and website must function without any LLM.

### Autonomous Model Discovery (Separate from Model A)

The Trading Copilot research system is distinct from Model A (an independent SPY microstructure experiment).

Model discovery must:
- Use independent competing hypotheses (not intuition)
- Apply common chronological evaluation contract (no leakage)
- Audit for leakage before comparison
- Run reproducible experiments with frozen data/target/features
- Maintain a leaderboard with validation + holdout metrics, stability, complexity, inference cost
- Enforce promotion gate: baseline beaten, holdout positive, stability acceptable, complexity justified, reproducible, integration safe

Model A is never given preferential treatment. If tested in Trading Copilot, it enters as one candidate hypothesis among many.

## Final architecture

```text
LIVE / HISTORICAL MARKET DATA
            ↓
DETERMINISTIC QUANT SCANNER
            ↓
CANDIDATES
            ↓
EVENT INTELLIGENCE
      +
COMPANY INTELLIGENCE
            ↓
EARNINGS / SEC / MANAGEMENT / INSIDERS / NEWS
            ↓
AI EXTRACTION
            ↓
EVIDENCE VALIDATION
            ↓
ANSWER ENGINE
            ↓
RESEARCH BRIEF
            ↓
WEBSITE / WATCHLIST / CALENDAR / ALERTS
            ↓
HUMAN DECISION
```

Direct stock search must work even if a stock is not a scanner candidate.

## Final roadmap

- Phase 0–1 — Core deterministic scanner — COMPLETE
- Phase 2 — Real Alpaca market data
- Phase 3 — Unified persistent event store
- Phase 4 — Macro event intelligence
- Phase 5 — Company calendar / corporate events
- Phase 6 — SEC + leadership + insider intelligence
- Phase 7 — Earnings intelligence + reaction history
- Phase 8 — News + management-statement analysis
- Phase 9 — Evidence validation + Answer Engine + event-aware research pipeline
- Phase 10 — Website / dashboard
- Phase 11 — Watchlists + calendar + alerts
- Phase 12 — Historical event-impact analytics
- Phase 13 — Strategy evaluation / paper-trading workflows

Do not prematurely build autonomous execution, giant agent frameworks, HFT infrastructure, opaque AI scores, or a polished frontend before backend correctness.
