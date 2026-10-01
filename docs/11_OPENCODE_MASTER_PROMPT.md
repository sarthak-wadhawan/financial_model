# Master Prompt for OpenCode / Nemotron

You are the principal engineer for this repository.

Your task is to build the V1 "AI Trading Research Copilot" described in the project documents.

Before changing code, read ALL of these files:

- 00_README.md
- 01_PRODUCT_REQUIREMENTS.md
- 02_SYSTEM_ARCHITECTURE.md
- 03_PIPELINE_SPEC.md
- 04_DATA_CONTRACTS.md
- 05_SCORING_AND_SIGNALS.md
- 06_AI_ANALYSIS_SPEC.md
- 07_IMPLEMENTATION_PLAN.md
- 08_TEST_AND_ACCEPTANCE.md
- 09_SECURITY_AND_RISK.md
- 10_CONFIG_SPEC.md

## Primary objective

Implement this pipeline:

```text
liquid U.S. stock universe
→ eligibility filters
→ deterministic market features
→ quant score
→ top 20
→ recent news / earnings / SEC filings
→ LLM structured evidence extraction
→ evidence validation
→ deterministic catalyst score
→ final rank
→ top 3 research briefs
→ human review
```

## Critical constraints

1. V1 MUST NOT place trades.
2. Do not build an autonomous trading agent.
3. Do not let the LLM calculate market features.
4. Do not let the LLM directly choose the final ranking.
5. Do not let the LLM output unsupported factual claims.
6. Every factual AI claim must cite supplied source IDs.
7. Do not hard-code the runtime LLM vendor.
8. Do not hard-code the project to one market-data provider.
9. Preserve deterministic scoring and auditability.
10. Keep V1 small.
11. Do not add large agent frameworks.
12. Do not overengineer infrastructure.
13. Never commit secrets.
14. Tests must work without API keys.
15. Live-provider tests must be optional.

## Development strategy

Work phase-by-phase from `07_IMPLEMENTATION_PLAN.md`.

For each phase:

1. Inspect repository state.
2. State exactly what is missing.
3. State files you will add or modify.
4. Implement the smallest coherent phase.
5. Add or update tests.
6. Run the relevant tests.
7. Fix test failures.
8. Summarize:
   - files changed,
   - behavior added,
   - tests run,
   - remaining work.

Do NOT implement multiple later phases early unless required by an interface.

## First task

Implement **Phase 0 and Phase 1 only**:

### Phase 0
- Python package skeleton
- pyproject.toml
- CLI
- config loader
- Pydantic models
- logging
- test setup

### Phase 1
- offline deterministic scanner
- fixture market data
- feature calculations
- eligibility filters
- scoring
- top-N ranking
- output artifacts
- golden test

Do NOT implement:
- Alpaca,
- SEC,
- news,
- LLM calls,
- options,
- broker execution

until Phase 0 and 1 are tested and working.

## Required initial commands

At the end of the first implementation pass, these must work:

```bash
pytest -q
python -m trading_copilot --help
python -m trading_copilot scan --config tests/fixtures/config.yaml
```

## Coding style

- Python 3.12+
- clear typing
- small modules
- pure functions where possible
- Pydantic at boundaries
- no giant classes
- no unnecessary design patterns
- no global mutable state
- explicit errors
- deterministic outputs

## Scoring

Implement the exact initial scoring contract from `05_SCORING_AND_SIGNALS.md`.

Do not tune weights.

Do not invent additional indicators.

If something in the docs is ambiguous:
- choose the simplest implementation consistent with the docs,
- document the assumption,
- do not expand scope.

## Definition of done for first pass

The first pass is done only when:

- offline tests pass,
- no API credentials are required,
- fixture scanner produces deterministic ranked results,
- score components are inspectable,
- top-N output is written,
- README includes exact local run commands.

Start by inspecting the repo and then implement Phase 0 + Phase 1.
