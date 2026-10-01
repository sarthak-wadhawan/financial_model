# Test and Acceptance Plan

## Unit tests

### Feature calculations
Test exact values for:
- returns,
- relative returns,
- moving averages,
- realized volatility,
- average dollar volume,
- relative volume.

### Eligibility
Test:
- low price rejection,
- low liquidity rejection,
- insufficient history rejection,
- valid symbol acceptance.

### Scoring
Test:
- score bounds [0, 100],
- deterministic output,
- monotonic behavior where expected,
- volatility mapping,
- tie-breaking.

### Source normalization
Test:
- stable source IDs,
- content hashes,
- publication timestamps,
- missing URL handling.

### AI parsing
Test:
- valid JSON,
- malformed JSON,
- unknown source IDs,
- missing required fields,
- invalid enum value.

### Evidence validation
Test:
- valid evidence kept,
- unsupported claim dropped,
- cross-symbol source reference rejected.

### Final ranking
Test:
- hard exclusions,
- correct weighting,
- deterministic top 3.

## Integration tests

### Offline end-to-end
Use only fixtures.

Command:
```bash
python -m trading_copilot run --config tests/fixtures/config.yaml
```

Verify expected artifact files.

### Provider contract tests
Use mock provider implementations to ensure the pipeline works regardless of vendor.

### Optional live smoke tests
Require environment flag:

```text
RUN_LIVE_TESTS=1
```

Never run live tests by default.

## Golden test

Create a fixed mini-universe, for example 10 symbols with frozen bars and frozen source documents.

Expected:
- exact top-N order,
- exact score components,
- exact validated evidence,
- exact final ranking.

This protects against accidental strategy changes.

## Property checks

Examples:
- every final candidate appears in top-20 quant candidates,
- every evidence source ID exists,
- every score is between 0 and 100,
- excluded candidates cannot enter top 3,
- top 3 length <= 3,
- no order-placement function exists in V1 runtime path.

## Failure tests

Simulate:
- market API timeout,
- one bad symbol,
- EDGAR 429 response,
- malformed news record,
- empty source bundle,
- LLM timeout,
- invalid LLM JSON,
- prompt-injection text inside a news article.

Pipeline should degrade gracefully.

## Acceptance checklist

V1 can be accepted only if:

- [ ] package installs cleanly
- [ ] all offline tests pass
- [ ] CLI help works
- [ ] config is documented
- [ ] no secrets are committed
- [ ] deterministic scanner works
- [ ] top 20 created
- [ ] source bundle stored
- [ ] LLM output schema validated
- [ ] evidence references validated
- [ ] top 3 report produced
- [ ] failures logged
- [ ] run manifest saved
- [ ] no automatic order placement
