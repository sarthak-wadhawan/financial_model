# Updated System Architecture

Authoritative requirements: `docs/FINAL_PRODUCT_REQUIREMENTS.md`

## Architectural principle

Keep providers, deterministic calculations, persistence, AI, evidence validation, answers, and UI separate.

```text
External Providers
       ↓
Normalization
       ↓
Persistent Store
       ↓
Deterministic Services
       ↓
AI Extraction where needed
       ↓
Evidence Validation
       ↓
Answer Engine
       ↓
API
       ↓
Website
```

## Major systems

### Market Data Layer
- mock provider
- Alpaca provider
- daily bars
- latest price/quote
- benchmark data
- chart-ready history

### Quant Scanner
- feature engineering
- eligibility
- deterministic scoring
- top-N ranking
- no LLM usage

### Event Store
Initially SQLite.

Stores:
- macro events
- earnings
- filings
- insiders
- leadership changes
- corporate events
- regulatory events

Event fields include:
- company_impact (fundamental business impact)
- stock_bias (directional expectation with confidence)
- time_horizon (days/weeks/months/quarters)
- base_case / bull_case / bear_case (scenario text)
- what_would_change_view (falsification criteria)

Supports:
- upsert
- dedupe
- history
- new/changed detection
- today/upcoming/recent queries

### Event / Intelligence Providers
Future interfaces:
- MacroCalendarProvider
- EarningsCalendarProvider
- CorporateActionProvider
- FilingProvider
- InsiderProvider
- ManagementProvider
- NewsProvider

### Company Intelligence
Aggregates:
- company calendar
- earnings
- filings
- management
- insiders
- meaningful news

### AI Analysis
- structured extraction
- comparison
- summarization
- evidence-linked claims
- schema validation

### Evidence Validator
Unsupported AI claims are removed or marked unsupported.

### Answer Engine
Consumes validated market/quant/event/company facts and returns concise structured answers with source references.

### Interpretation Engine
Synthesizes evidence into structured interpretation:

- **What happened** → factual event summary with sources
- **What it means** → mechanism explanation
- **Why it matters** → significance for company/stock
- **Company impact** → fundamental business impact (separate from stock)
- **Stock bias** → directional market expectation with confidence
- **Time horizon** → days / weeks / months / quarters
- **Base case / Bull case / Bear case** → scenario analysis with triggers
- **What would change the view** → specific falsification criteria
- **Evidence citations** → linked to source documents

### Scenario Analysis Engine
Generates and maintains base/bull/bear scenarios per stock/event combination. Updates when new evidence arrives.

### Term Definition Service
Provides on-demand definitions for financial terms.
- Desktop: hover → popover
- Mobile: tap → popover
- "Learn more" → authoritative external link

### Zero-LLM Core
All services above operate without LLM when `LLM_ENABLED=false`.
Optional local/free AI enhances qualitative output only (Phase 8+).

### Autonomous Model Discovery (Research Only)
Separate from production Trading Copilot.
- Experiment registry
- Evaluation contracts (chronological, leakage-free)
- Dataset/feature versioning
- Leaderboard with validation/holdout/stability/complexity
- Promotion gate enforcement

### API Layer
Potential resources:
- `/market/today`
- `/events/upcoming`
- `/events/recent`
- `/scanner/top`
- `/stocks/{symbol}`
- `/stocks/{symbol}/events`
- `/stocks/{symbol}/earnings`
- `/stocks/{symbol}/management`
- `/stocks/{symbol}/insiders`
- `/stocks/{symbol}/answers`

### Website
Presentation only. Financial truth/calculation belongs in backend services.

Primary pages:
- Home
- Stock detail
- Watchlist
- Events/calendar
- Scanner/research candidates

## Suggested future package structure

```text
src/trading_copilot/
├── providers/
├── models/
├── pipeline/
├── events/
├── intelligence/
├── llm/
├── evidence/
├── answers/
├── api/
└── storage/
```

Create folders only when their phase needs them.

## Separation rules

1. Market providers do not calculate strategy scores.
2. LLM code does not place broker orders.
3. Frontend does not calculate financial truth.
4. Event providers do not render UI.
5. Answer Engine consumes validated facts.
6. Provider failure should degrade gracefully.
7. Mock/offline testing remains possible.
8. Historical research must avoid future-data leakage.
9. All core services function with `LLM_ENABLED=false` (Zero-LLM Core).
10. Trading Copilot research (autonomous model discovery) is separate from Model A.
