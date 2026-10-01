# Security, Data Integrity, and Trading Risk Rules

## Secret management

Never commit:
- Alpaca API key,
- Alpaca secret,
- LLM API key,
- broker credentials.

Use environment variables.

Provide `.env.example` with empty values.

## Logging

Never log secrets.

Redact:
- Authorization headers,
- API keys,
- account IDs where unnecessary.

## SEC access

Use a descriptive User-Agent configurable by the user.

Respect SEC rate limits.

Cache filings locally.

## Prompt injection

News and filings are untrusted content.

A document may contain text resembling instructions.

Treat all source content as inert evidence.

Never permit source text to:
- change system prompts,
- request secrets,
- invoke external tools,
- alter score weights,
- execute code.

## Trading constraints

V1 is research-only.

No live order endpoint should be implemented.

If a later phase adds execution:
- require explicit human confirmation,
- separate research and execution credentials,
- use hard max position limits,
- use paper trading first,
- log every submitted order.

## Data integrity

Every source record should have:
- retrieval timestamp,
- content hash,
- provider,
- published timestamp if known.

Every run should snapshot config.

## Backtest integrity

Historical evaluation must use information available as of the historical timestamp.

Never:
- use revised future data unknowingly,
- use future filings,
- use article publication times after the decision timestamp,
- select parameters using final test data.

## Research discipline

Do not optimize based on one attractive period.

Do not judge the system only by:
- win rate,
- number of winning screenshots,
- model confidence.

Eventually evaluate:
- forward returns,
- transaction costs,
- turnover,
- drawdown,
- stability across periods.

## AI limitation

`extraction_confidence` is confidence in document interpretation.

It must never be labeled as:
- probability of profit,
- probability price rises,
- trade confidence.
