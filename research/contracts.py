"""Evaluation contracts for leakage-free walk-forward research."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Literal

from trading_copilot.storage.hashes import content_hash


@dataclass(frozen=True)
class EvaluationContract:
    """
    Frozen evaluation contract for a research question.

    All competing experiments MUST use the same contract.
    No experiment may redefine the test to make its approach look better.
    """

    # Identification
    research_question: str
    contract_version: str  # Hash of the contract content for immutability

    # Target definition
    target_name: str  # e.g., "fwd_ret_5d", "fwd_ret_21d", "event_reaction_1d"
    target_definition: str  # Human-readable formula
    target_horizon_days: int
    target_universe: str  # e.g., "eligible_symbols", "top20", "all_liquid"

    # Feature availability (critical for leakage prevention)
    feature_as_of: str  # e.g., "market_close_t", "market_open_t+1"
    feature_lookback_days: int  # Maximum lookback for any feature
    feature_families: list[str]  # e.g., ["market", "macro_events", "earnings", "filings"]

    # Data splits (chronological, no random shuffle)
    train_start: date
    train_end: date
    validation_start: date
    validation_end: date
    holdout_start: date
    holdout_end: date

    # Universe definition (no survivorship bias)
    universe_definition: str  # e.g., "symbols with >=220 sessions in train period"
    min_history_days: int
    min_price: float
    min_avg_dollar_volume_20d: float

    # Metrics (primary first)
    primary_metric: str  # e.g., "ic_5d", "hit_rate_21d", "roc_auc", "brier"
    secondary_metrics: list[str] = field(default_factory=list)
    metric_direction: Literal["higher_better", "lower_better"] = "higher_better"

    # Transaction cost assumptions
    transaction_cost_bps: float = 10.0  # Round-trip cost in basis points
    slippage_bps: float = 5.0

    # Missing data rules
    missing_feature_rule: Literal["drop_row", "impute_median", "impute_zero", "forward_fill"] = "drop_row"
    missing_target_rule: Literal["drop_row", "exclude_symbol"] = "drop_row"

    # Baselines (must be beaten)
    baselines: list[str] = field(default_factory=lambda: ["random", "momentum_only", "quant_score"])

    # Stability requirements
    min_stability_periods: int = 3  # e.g., bull/bear/high-vol/low-vol
    stability_metric: str = "ic_5d"

    # Random seeds for reproducibility
    random_seed: int = 42
    numpy_seed: int = 42
    sklearn_seed: int = 42

    # Provenance
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    created_by: str = "shepherd"
    notes: str = ""

    def __post_init__(self) -> None:
        # Compute contract version hash
        if not self.contract_version:
            # Create a dict without the version field for hashing
            data = {k: v for k, v in asdict(self).items() if k != "contract_version"}
            object.__setattr__(self, "contract_version", content_hash(str(sorted(data.items())).encode())[:16])

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        # Convert dates to ISO strings
        for key in ["train_start", "train_end", "validation_start", "validation_end", "holdout_start", "holdout_end"]:
            if isinstance(data[key], date):
                data[key] = data[key].isoformat()
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "EvaluationContract":
        # Convert date strings back to date objects
        for key in ["train_start", "train_end", "validation_start", "validation_end", "holdout_start", "holdout_end"]:
            if isinstance(data[key], str):
                data[key] = date.fromisoformat(data[key])
        return cls(**data)

    def save(self, path: Path) -> None:
        path.write_text(json.dumps(self.to_dict(), indent=2))

    @classmethod
    def load(cls, path: Path) -> "EvaluationContract":
        return cls.from_dict(json.loads(path.read_text()))

    def verify_no_leakage(self, feature_matrix_path: Path) -> tuple[bool, list[str]]:
        """
        Verify that a feature matrix respects this contract's leakage rules.

        Returns (passed, violations).
        """
        violations = []

        # Check feature_as_of is not in the future relative to target
        # This would need actual data inspection
        # Placeholder for now - would load feature matrix and check timestamps
        pass

        return len(violations) == 0, violations


def create_default_contract(research_question: str) -> EvaluationContract:
    """Create a default evaluation contract for a research question."""
    # These are placeholders - the Shepherd should customize per question
    today = date.today()
    # Use ~2 years train, 6 months validation, 6 months holdout
    holdout_end = today
    holdout_start = date(holdout_end.year - 1, holdout_end.month, holdout_end.day)
    validation_end = date(holdout_start.year, holdout_start.month - 6, holdout_start.day) if holdout_start.month > 6 else date(holdout_start.year - 1, holdout_start.month + 6, holdout_start.day)
    validation_start = date(validation_end.year - 1, validation_end.month, validation_end.day) if validation_end.month > 6 else date(validation_end.year - 1, validation_end.month + 6, validation_end.day)
    train_end = date(validation_start.year, validation_start.month - 6, validation_start.day) if validation_start.month > 6 else date(validation_start.year - 1, validation_start.month + 6, validation_start.day)
    train_start = date(train_end.year - 2, train_end.month, train_end.day)

    return EvaluationContract(
        research_question=research_question,
        contract_version="",  # Will be computed in __post_init__
        target_name="fwd_ret_5d",
        target_definition="close_{t+5} / close_t - 1",
        target_horizon_days=5,
        target_universe="eligible_symbols",
        feature_as_of="market_close_t",
        feature_lookback_days=252,
        feature_families=["market"],
        train_start=train_start,
        train_end=train_end,
        validation_start=validation_start,
        validation_end=validation_end,
        holdout_start=holdout_start,
        holdout_end=holdout_end,
        universe_definition="symbols with >=220 sessions in train period, price >= $5, avg dollar volume 20d >= $50M",
        min_history_days=220,
        min_price=5.0,
        min_avg_dollar_volume_20d=50_000_000,
        primary_metric="ic_5d",
        secondary_metrics=["hit_rate_5d", "roc_auc_5d", "brier_5d", "turnover"],
        metric_direction="higher_better",
        transaction_cost_bps=10.0,
        slippage_bps=5.0,
        missing_feature_rule="drop_row",
        missing_target_rule="drop_row",
        baselines=["random", "momentum_21d", "quant_score", "equal_weight"],
        min_stability_periods=4,
        stability_metric="ic_5d",
        random_seed=42,
        numpy_seed=42,
        sklearn_seed=42,
    )


# Example contracts for different research questions
CANDIDATE_RANKING_CONTRACT = EvaluationContract(
    research_question="candidate_ranking_5d",
    contract_version="",
    target_name="fwd_ret_5d",
    target_definition="close_{t+5} / close_t - 1 (5-day forward return)",
    target_horizon_days=5,
    target_universe="eligible_symbols",
    feature_as_of="market_close_t",
    feature_lookback_days=252,
    feature_families=["market"],
    train_start=date(2022, 1, 1),
    train_end=date(2023, 12, 31),
    validation_start=date(2024, 1, 1),
    validation_end=date(2024, 6, 30),
    holdout_start=date(2024, 7, 1),
    holdout_end=date(2024, 12, 31),
    universe_definition="symbols with >=220 sessions in train period, price >= $5, avg dollar volume 20d >= $50M",
    min_history_days=220,
    min_price=5.0,
    min_avg_dollar_volume_20d=50_000_000,
    primary_metric="ic_5d",
    secondary_metrics=["hit_rate_5d", "roc_auc_5d", "brier_5d", "turnover", "max_drawdown"],
    metric_direction="higher_better",
    transaction_cost_bps=10.0,
    slippage_bps=5.0,
    missing_feature_rule="drop_row",
    missing_target_rule="drop_row",
    baselines=["random", "momentum_21d", "quant_score", "equal_weight", "market_cap_weight"],
    min_stability_periods=4,
    stability_metric="ic_5d",
    random_seed=42,
    numpy_seed=42,
    sklearn_seed=42,
    notes="Primary task: rank eligible symbols by expected 5-day forward return. Market-only features initially.",
)