# Implementation Plan

The coding model should build this in small verified phases.

Do not attempt the entire application in one uncontrolled patch.

## Phase 0 — Bootstrap

Create:
- pyproject.toml
- package structure
- config loader
- logging
- core Pydantic models
- CLI skeleton
- test framework

Acceptance:
```bash
pytest -q
python -m trading_copilot --help
```

must work.

## Phase 1 — Offline deterministic scanner

Build using fixture CSV data first.

Implement:
- FeatureEngine
- EligibilityFilter
- QuantScorer
- Top-N ranking
- CSV/JSON output

Acceptance:
- no API keys required,
- deterministic golden test,
- top-20 output generated from fixtures.

## Phase 2 — Alpaca market-data provider

Implement:
- authenticated provider,
- batching,
- retries,
- normalized daily bars,
- caching.

Acceptance:
- provider integration test can be skipped if no credentials,
- fixture tests remain fully offline.

## Phase 3 — SEC EDGAR provider

Implement:
- SEC-compliant user agent configuration,
- filing metadata retrieval,
- filing text retrieval,
- source normalization,
- rate-limit handling.

Acceptance:
- can retrieve/parse a known fixture,
- live test optional.

## Phase 4 — News provider

Implement provider interface.

Initial adapter:
- Alpaca News when credentials/entitlement allow.

Do not make the whole application fail if news is unavailable.

## Phase 5 — LLM abstraction

Implement:
- LLMClient protocol,
- OpenAI-compatible HTTP adapter,
- strict JSON parsing,
- schema validation,
- one retry,
- caching.

Use mocked LLM responses for unit tests.

## Phase 6 — Evidence validation

Implement:
- source-ID validation,
- symbol/source consistency,
- invalid claim removal,
- warning generation.

## Phase 7 — Catalyst scoring

Implement deterministic mapping from structured analysis.

No direct LLM numeric score.

## Phase 8 — Final ranking

Combine:
- quant score,
- catalyst score,
- risk gates.

Generate:
- top20.csv
- top3.json
- top3.md

## Phase 9 — Optional options module

Only after the above works.

Add:
- OptionsProvider interface,
- basic liquidity metrics,
- IV/delta if provider supplies them.

Do not build a pricing engine.

## Phase 10 — Production hardening

Add:
- run manifests,
- content hashes,
- structured error logs,
- retries,
- concurrency caps,
- reproducible run folders,
- config validation.

## Phase 11 — Historical evaluation harness

Before trusting the strategy:
- run scanner historically using only data known at each date,
- record forward returns separately,
- never leak future news or filings,
- evaluate turnover and simple execution assumptions.

This evaluation is separate from the daily research pipeline.

## Development rules

For every phase:
1. inspect existing code first,
2. state files to change,
3. implement smallest coherent change,
4. run tests,
5. fix failures,
6. summarize what changed,
7. do not silently refactor unrelated modules.

## Dependency rule

Prefer standard library and small stable packages.

Do not add:
- LangChain,
- CrewAI,
- AutoGen,
- Ray,
- Kafka,
- Redis,
- Celery,

unless a later requirement genuinely justifies them.

V1 does not need them.
