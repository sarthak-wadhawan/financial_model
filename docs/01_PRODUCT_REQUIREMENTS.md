# Product Requirements

## 1. Problem

A human trader cannot efficiently scan hundreds of liquid stocks, inspect recent market behavior, read relevant filings/news, calculate momentum/volatility/liquidity metrics, and reduce everything to a few research candidates each day.

The product should automate the mechanical and document-heavy parts while preserving human approval.

## 2. Primary user

A part-time individual trader/researcher who:
- wants simple workflows,
- prefers liquid U.S. equities,
- may later express views using stock or options,
- wants a small number of candidates,
- does not want to monitor charts all day.

## 3. Primary workflow

```text
Liquid stock universe
        ↓
Eligibility filters
        ↓
Deterministic feature calculation
        ↓
Quant score
        ↓
Top 20 candidates
        ↓
News / earnings / SEC source collection
        ↓
LLM structured extraction
        ↓
Catalyst + risk validation
        ↓
Final score
        ↓
Top 3 candidates
        ↓
Research brief
        ↓
Human review
```

## 4. Functional requirements

### FR-1 Universe
System shall load a configurable U.S. equity universe.

Initial default:
- liquid common stocks,
- major ETFs may be allowed,
- exclude OTC,
- exclude obvious illiquid names.

### FR-2 Market data
For every symbol, retrieve enough daily data to compute:
- 21-day return,
- 63-day return,
- 126-day return,
- relative return versus SPY,
- SMA20,
- SMA50,
- SMA200,
- 20-day realized volatility,
- 20-day average dollar volume,
- latest dollar volume,
- relative volume.

### FR-3 Eligibility
Configurable filters should include:
- minimum price,
- minimum average dollar volume,
- minimum trading-history length,
- optional minimum market cap,
- optional quote/spread filter when quote data is available.

### FR-4 Quant scoring
System shall compute a transparent score from deterministic features.

No LLM is allowed in this stage.

### FR-5 Top 20
System shall retain the top N quant candidates, default N=20.

### FR-6 Source collection
For each top-20 candidate, gather recent:
- company news,
- SEC filings,
- earnings-related material when available.

All collected records must include:
- source URL or provider identifier,
- timestamp,
- title/type,
- raw text or normalized text,
- retrieval timestamp.

### FR-7 LLM extraction
The LLM shall return structured JSON only.

It must extract:
- catalyst type,
- catalyst direction,
- factual summary,
- guidance change,
- earnings surprise context if source supports it,
- key risks,
- upcoming known event dates if supported,
- source IDs supporting every claim,
- confidence in extraction quality.

### FR-8 Hallucination protection
Any AI claim without a valid source ID must be discarded.

### FR-9 Final ranking
Final ranking shall combine:
- deterministic quant score,
- deterministic risk gates,
- structured catalyst score.

The LLM shall not directly decide the final rank.

### FR-10 Research brief
For the top 3, generate:
- symbol,
- price snapshot,
- quant score,
- catalyst score,
- final score,
- strongest supporting facts,
- main risks,
- upcoming event dates,
- invalidation conditions,
- source list.

### FR-11 Auditability
Every run must be reproducible from saved inputs.

Save:
- config,
- symbol universe,
- raw provider responses or normalized snapshots,
- computed features,
- AI prompt,
- AI response,
- parsed JSON,
- scores,
- final output.

### FR-12 Human approval
V1 shall not place orders.

## 5. Non-functional requirements

### Reliability
- Retry transient HTTP errors.
- Cache expensive source retrieval.
- Continue processing other symbols if one symbol fails.
- Record failures explicitly.

### Reproducibility
- Every run receives a unique run ID.
- Save config hash and code version if available.

### Cost control
- Run the LLM only on top-20 candidates.
- Deduplicate near-identical news.
- Truncate documents intelligently.
- Cache LLM responses by content hash.

### Performance
Target:
- Quant scan on hundreds of symbols should complete in minutes, not hours.
- Document analysis can run concurrently with a safe concurrency cap.

### Maintainability
Each external provider must implement a stable internal interface.

## 6. V1 acceptance criteria

V1 is complete when:
1. A single CLI command executes end-to-end.
2. At least 100 symbols can be scanned.
3. Top 20 are generated deterministically.
4. Sources are gathered for each available candidate.
5. AI output passes schema validation.
6. Unsupported AI claims are rejected.
7. Top 3 briefs are generated.
8. Rerunning with identical frozen inputs produces identical quant scores.
9. No brokerage order API is called.
