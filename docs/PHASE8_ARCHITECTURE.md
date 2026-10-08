# Phase 8 Architecture: News + Management Statement Analysis

## Overview

Phase 8 builds a structured evidence layer for:
- **NEWS**
- **COMPANY PRESS RELEASES**
- **MANAGEMENT STATEMENTS**
- **MATERIAL COMPANY DEVELOPMENTS**

Phase 8 is NOT the interpretation/recommendation engine (that's Phase 9). Its output feeds Phase 9 as evidence claims with full provenance.

## Architecture

```
SOURCE DOCUMENT
      ↓
FETCH / PRESERVE
      ↓
DEDUPLICATE
      ↓
STRUCTURED FACT / STATEMENT EXTRACTION
      ↓
EVIDENCE CLAIMS
      ↓
SOURCE + TIMESTAMP + PROVENANCE
      ↓
PHASE 9 INTERPRETATION + IMPACT
```

## Core Principles

| Principle | Implementation |
|-----------|----------------|
| **Zero-LLM Core** | All core functionality works with `LLM_ENABLED=false` |
| **Provenance Discipline** | Every claim traces to source with exact evidence span |
| **Source Priority** | 1. Primary company sources (SEC, IR) 2. Regulatory 3. Reputable news 4. Optional free structured |
| **No Paid Dependencies** | All providers use free official sources |
| **Deduplication** | Canonical URLs, content hashes, normalized headlines |
| **Attribution** | Speaker, role, company, statement_type, source_document |
| **Evidence Model** | CLAIM + SOURCE + SOURCE_URL + EVENT_DATE + RETRIEVED_AT + EXACT_EVIDENCE + CONFIDENCE |

## Source Priority

1. **Primary Company Sources** (reused from Phase 6/7)
   - SEC filings/exhibits already collected (8-K, 10-Q, 10-K, Form 4 exhibits)
   - Earnings releases (8-K Item 2.02, Exhibit 99.1)
   - Company investor-relations press releases
   - Official company statements

2. **Authoritative Regulatory Sources**
   - SEC EDGAR (already integrated)
   - Federal Reserve, BLS, BEA, Census (already integrated)

3. **Reputable News Sources** (RSS/Atom)
   - Company-specific RSS feeds
   - Major financial newswires with free RSS

4. **Optional Free Structured News Providers**
   - Only if already supported/configured
   - No new paid dependencies

## Provider Abstraction

```python
class NewsProvider(Protocol):
    def fetch_news(
        self,
        symbols: list[str] | None = None,
        from_date: date | None = None,
        to_date: date | None = None,
    ) -> list[NewsDocument]: ...

    def fetch_company_releases(
        self,
        symbols: list[str] | None = None,
        from_date: date | None = None,
        to_date: date | None = None,
    ) -> list[NewsDocument]: ...

class NewsDocument:
    document_id: str
    symbol: str | None
    headline: str
    body: str
    summary: str | None
    publisher: str
    published_at: datetime
    retrieved_at: datetime
    source_url: str
    source_type: str  # "sec_exhibit" | "company_ir" | "news_rss" | "structured_provider"
    author: str | None
    provider_id: str
    content_hash: str
    metadata: dict
```

## Deduplication Strategy

| Signal | Weight |
|--------|--------|
| Canonical URL match | Primary |
| Content hash (SHA-256) | Primary |
| Normalized headline + symbol + date | Secondary |
| Source ID from provider | Secondary |
| Text similarity (TF-IDF) | Tertiary |

Preserve source relationships (e.g., SEC Exhibit 99.1 → IR release → news article).

## Management Statement Extraction

Extract attributable statements with:
- `speaker` (name or UNKNOWN)
- `speaker_role` (CEO, CFO, etc.)
- `company` (symbol)
- `statement` (exact text)
- `statement_type` (guidance, demand, margins, costs, capex, competition, product, regulation, supply, pricing, strategy, risks, macro, other)
- `source_document` (NewsDocument ID)
- `source_url`
- `published_at`
- `event_date` (when statement was made)
- `retrieved_at`
- `evidence_span` (character offsets in source text)

## Zero-LLM Core (Deterministic Baseline)

- Document metadata (SEC item/exhibit structure)
- Regex/pattern rules for known statement types
- Sentence segmentation + keyword/category matching
- Attribution rules (speaker detection in SEC filings)
- Structured company press-release metadata (dateline, boilerplate)

This baseline is the fallback and comparison point.

## Optional Local AI Enhancement

If `LLM_ENABLED=true` and local model available:
- Structured JSON-schema output
- Temperature 0 where appropriate
- Strict Pydantic validation
- Bounded context window
- Explicit evidence spans required
- **Failure falls back to deterministic extraction**

Abstraction:
- `DisabledLLMProvider` (default, always returns empty)
- `LocalLLMProvider` (Ollama or similar)

No OpenAI/Anthropic API required.

## AI Extraction Contract

```python
class ExtractedClaim(BaseModel):
    claim: str
    category: str  # guidance, demand, margins, costs, capex, competition, product, regulation, supply, pricing, strategy, risks, macro, other
    speaker: str
    speaker_role: str | None
    evidence_text: str  # exact span from source
    source_document_id: str
    confidence: float  # 0.0-1.0
```

Validation rules:
- Claim must be supported by source text
- Speaker must be present or "UNKNOWN"
- Evidence span must exist in source
- Dates/numbers must agree with source
- Schema must validate

If validation fails → reject extraction. UNKNOWN better than hallucination.

## Evidence Model

Every material claim preserves:
- `claim`
- `source`
- `source_url`
- `source_date` (published_at)
- `event_date` (when statement was made)
- `retrieved_at`
- `exact_supporting_evidence` (character offsets + text)
- `confidence`
- `verification_status` (verified | pending | failed)

Distinguish:
- `FACT` (verifiable datum)
- `ATTRIBUTED_STATEMENT` (management said X)
- `DETERMINISTIC_DERIVATION` (calculated from facts)
- `AI_EXTRACTION` (from local LLM)

## News Freshness

Preserve:
- `published_at` (when source published)
- `first_seen_at` (when we first retrieved)
- `retrieved_at` (current retrieval)
- `updated_at` (when source updated, if available)

Do not make old article look current because it was just retrieved.

## Failure Isolation

- Optional AI fails → news ingestion available, management evidence = deterministic baseline, AI enhancement = unavailable
- One news provider fails → other providers continue

## New Event Types

| Event Type | Description |
|------------|-------------|
| `NEWS_ARTICLE` | News article from RSS/structured provider |
| `COMPANY_RELEASE` | Company press release (IR, SEC exhibit) |
| `MANAGEMENT_STATEMENT` | Attributable management statement |
| `EVIDENCE_CLAIM` | Structured evidence claim for Phase 9 |

## Event Metadata

### NEWS_ARTICLE
```json
{
  "event_subtype": "news_article",
  "symbol": "AAPL",
  "headline": "...",
  "publisher": "Reuters",
  "published_at": "2026-10-01T14:30:00Z",
  "source_url": "...",
  "source_type": "news_rss",
  "provider_id": "reuters_rss",
  "content_hash": "...",
  "dedup_key": "...",
  "related_sec_filing": "sec_edgar:0000320193-26-000123"
}
```

### COMPANY_RELEASE
```json
{
  "event_subtype": "company_release",
  "symbol": "AAPL",
  "headline": "Apple Reports Q3 Results",
  "publisher": "Apple Inc.",
  "published_at": "2026-10-29T21:00:00Z",
  "source_url": "https://www.apple.com/newsroom/...",
  "source_type": "company_ir",
  "provider_id": "apple_ir",
  "content_hash": "...",
  "sec_exhibit_id": "sec_edgar:0000320193-26-000123",
  "exhibit_number": "99.1"
}
```

### MANAGEMENT_STATEMENT
```json
{
  "event_subtype": "management_statement",
  "symbol": "AAPL",
  "speaker": "Tim Cook",
  "speaker_role": "CEO",
  "statement": "We expect revenue growth to accelerate...",
  "statement_type": "guidance",
  "source_document_id": "news:abc123",
  "source_url": "...",
  "published_at": "2026-10-29T21:00:00Z",
  "event_date": "2026-10-29",
  "evidence_span": {"start": 1234, "end": 1456},
  "extraction_method": "deterministic" | "llm",
  "confidence": 0.95
}
```

### EVIDENCE_CLAIM
```json
{
  "event_subtype": "evidence_claim",
  "symbol": "AAPL",
  "claim": "Management expects revenue growth to accelerate in Q4",
  "category": "guidance",
  "claim_type": "attributed_statement",
  "speaker": "Tim Cook",
  "speaker_role": "CEO",
  "source_document_id": "news:abc123",
  "source_url": "...",
  "published_at": "2026-10-29T21:00:00Z",
  "evidence_span": {"start": 1234, "end": 1456},
  "extraction_method": "deterministic",
  "confidence": 0.95,
  "verification_status": "verified"
}
```

## Acceptance Criteria

### News/Document Ingestion
- [ ] SEC Exhibit 99.1 ingestion (reuse Phase 6/7)
- [ ] Company IR RSS feed ingestion
- [ ] Reputable news RSS ingestion
- [ ] Raw source preservation (where legally appropriate)
- [ ] Content hashing for deduplication
- [ ] Deduplication across SEC/IR/news sources

### Management Statement Extraction
- [ ] Speaker detection (CEO, CFO, etc.) from SEC filings
- [ ] Statement categorization (guidance, demand, margins, etc.)
- [ ] Evidence span preservation
- [ ] Deterministic baseline extraction
- [ ] Optional local LLM enhancement

### Deduplication/Provenance
- [ ] Canonical URL deduplication
- [ ] Content hash deduplication
- [ ] Cross-source relationship preservation
- [ ] Timestamp semantics (published_at ≠ retrieved_at ≠ first_seen_at)

### Testing
- [ ] Offline fixtures for all source types
- [ ] Deduplication edge cases
- [ ] Speaker detection edge cases
- [ ] LLM disabled baseline
- [ ] Optional LLM failure isolation
- [ ] Schema validation
- [ ] Evidence span validation

### Integration
- [ ] Reuses SEC infrastructure (Phase 6/7)
- [ ] Feeds Phase 9 interpretation engine
- [ ] No Phase 9 fields in Phase 8 events

## Implementation Order (Graph Nodes)

1. **Node A** — Source/provider research & selection
2. **Node B** — News/document ingestion provider abstraction
3. **Node C** — SEC exhibit/IR release ingestion (reuses Phase 6/7)
4. **Node D** — News RSS ingestion
5. **Node E** — Management statement extraction (deterministic)
6. **Node F** — Optional local LLM extraction provider
7. **Node G** — Deduplication engine
8. **Node H** — Evidence claim generation
9. **Node I** — Fixtures/tests
10. **Node J** — Independent audits (provenance, hallucination, duplicates, timestamps, zero-LLM)
11. **Node K** — Integration/docs/commit

## File Structure (New)

```
src/trading_copilot/
├── providers/
│   ├── news_provider.py        # NewsProvider protocol & base
│   ├── sec_exhibit_provider.py # Reuses SEC infrastructure for exhibits
│   ├── ir_release_provider.py  # Company IR RSS ingestion
│   ├── news_rss_provider.py    # General news RSS ingestion
│   ├── management_extractor.py # Deterministic statement extraction
│   ├── llm_provider.py         # DisabledLLMProvider / LocalLLMProvider
│   └── evidence_claims.py      # Evidence claim generation
├── models/
│   └── news.py                 # NewsDocument, EvidenceClaim, etc.
└── events/
    └── store.py                # Extended with new event types
```

## Deferred to Phase 9+

- Market impact conclusions
- Bullish/bearish advice
- Company impact / stock bias
- Scenario engine
- Why It Matters synthesis
- Answer engine integration