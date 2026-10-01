# Data Contracts

Use Pydantic models for external and internal boundaries.

## SymbolInfo

```python
class SymbolInfo(BaseModel):
    symbol: str
    name: str | None = None
    exchange: str | None = None
    asset_type: str = "equity"
    active: bool = True
```

## DailyBar

```python
class DailyBar(BaseModel):
    symbol: str
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float
```

Validation:
- prices > 0,
- high >= low,
- volume >= 0,
- timestamp timezone-aware.

## FeatureRow

```python
class FeatureRow(BaseModel):
    symbol: str
    as_of: datetime
    price: float

    ret_21d: float
    ret_63d: float
    ret_126d: float

    rel_ret_21d: float
    rel_ret_63d: float
    rel_ret_126d: float

    sma_20: float
    sma_50: float
    sma_200: float

    dist_sma_20_pct: float
    dist_sma_50_pct: float
    dist_sma_200_pct: float

    realized_vol_20d: float
    avg_dollar_volume_20d: float
    relative_volume_1d: float
    drawdown_from_63d_high: float
```

## QuantScore

```python
class QuantScore(BaseModel):
    symbol: str
    momentum_score: float
    trend_score: float
    liquidity_score: float
    volatility_score: float
    quant_score: float
    components: dict[str, float]
```

All scores must be [0, 100].

## SourceDocument

```python
class SourceDocument(BaseModel):
    source_id: str
    symbol: str
    source_type: Literal[
        "news",
        "8-k",
        "10-q",
        "10-k",
        "earnings_release",
        "other_filing",
        "other"
    ]
    title: str
    published_at: datetime | None
    url: str | None
    provider: str
    text: str
    retrieval_time: datetime
    content_hash: str
```

## EvidenceClaim

```python
class EvidenceClaim(BaseModel):
    claim: str
    source_ids: list[str]
```

Rule:
`source_ids` cannot be empty.

## CatalystAnalysis

```python
class CatalystAnalysis(BaseModel):
    symbol: str

    catalyst_type: Literal[
        "earnings",
        "guidance",
        "product",
        "regulatory",
        "corporate_action",
        "analyst_revision",
        "macro_sensitive",
        "other",
        "none"
    ]

    catalyst_direction: Literal[
        "positive",
        "negative",
        "mixed",
        "neutral"
    ]

    catalyst_strength: Literal[
        "high",
        "medium",
        "low",
        "none"
    ]

    summary: str

    guidance_change: Literal[
        "raised",
        "lowered",
        "reaffirmed",
        "not_found"
    ]

    key_positive_claims: list[EvidenceClaim]
    key_negative_claims: list[EvidenceClaim]
    risks: list[EvidenceClaim]

    upcoming_events: list[EvidenceClaim]

    extraction_confidence: float
```

`extraction_confidence` describes confidence that the documents were interpreted correctly.

It is **not** a probability that the stock will rise.

## FinalCandidate

```python
class FinalCandidate(BaseModel):
    symbol: str
    quant_score: float
    catalyst_score: float
    final_score: float
    status: Literal[
        "candidate",
        "review_required",
        "excluded"
    ]
    exclusion_reasons: list[str]
    analysis: CatalystAnalysis | None
```

## ResearchBrief

```python
class ResearchBrief(BaseModel):
    symbol: str
    as_of: datetime
    price: float
    quant_score: float
    catalyst_score: float
    final_score: float

    thesis_facts: list[str]
    risks: list[str]
    upcoming_events: list[str]
    invalidation_conditions: list[str]

    sources: list[dict]
```

## RunManifest

```python
class RunManifest(BaseModel):
    run_id: str
    started_at: datetime
    completed_at: datetime | None
    config_hash: str
    git_commit: str | None
    universe_size: int
    eligible_count: int
    top_n: int
    failures: int
```
