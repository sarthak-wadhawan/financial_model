"""Independent evaluation module for model discovery research.

The evaluation agent must be independent - it should not blindly trust
each experiment's own reported performance. It should independently:
- load artifacts
- rerun common evaluation
- verify splits
- inspect leakage
- compare against baselines
- verify metrics
- identify suspicious results
"""

from __future__ import annotations

import json
import pickle
from dataclasses import asdict, dataclass, field
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Callable, Literal

import numpy as np
import pandas as pd
from scipy import stats

from trading_copilot.storage.hashes import content_hash


@dataclass
class EvaluationResult:
    """Result of independent evaluation."""

    experiment_id: str
    dataset_version: str
    contract_version: str

    # Core metrics
    train_metrics: dict[str, float]
    validation_metrics: dict[str, float]
    holdout_metrics: dict[str, float]

    # Baseline comparison
    baseline_name: str
    baseline_holdout_metrics: dict[str, float]
    beats_baseline: bool
    margin: float

    # Stability
    stability_metrics: dict[str, float]  # period -> metric
    stability_passed: bool

    # Leakage checks
    leakage_checks: dict[str, bool]
    leakage_passed: bool
    leakage_notes: list[str]

    # Economic metrics (if applicable)
    economic_metrics: dict[str, float] = None

    # Complexity
    model_size_mb: float = 0.0
    inference_ms_per_symbol: float = 0.0

    # Overall verdict
    verdict: Literal["promote", "reject", "investigate"] = "investigate"
    notes: str = ""

    evaluated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def compute_information_coefficient(predictions: np.ndarray, actuals: np.ndarray) -> float:
    """Compute Spearman Information Coefficient (rank correlation)."""
    if len(predictions) < 2:
        return 0.0
    rho, _ = stats.spearmanr(predictions, actuals)
    return float(rho) if not np.isnan(rho) else 0.0


def compute_hit_rate(predictions: np.ndarray, actuals: np.ndarray, threshold: float = 0.0) -> float:
    """Compute hit rate: fraction of predictions with correct sign."""
    if len(predictions) == 0:
        return 0.0
    correct = np.sum((predictions > threshold) == (actuals > threshold))
    return float(correct / len(predictions))


def compute_roc_auc(predictions: np.ndarray, actuals: np.ndarray) -> float:
    """Compute ROC AUC for binary classification (positive return)."""
    try:
        from sklearn.metrics import roc_auc_score
        binary_actuals = (actuals > 0).astype(int)
        return float(roc_auc_score(binary_actuals, predictions))
    except Exception:
        return 0.5


def compute_brier_score(predictions: np.ndarray, actuals: np.ndarray) -> float:
    """Compute Brier score for probability calibration."""
    try:
        from sklearn.metrics import brier_score_loss
        binary_actuals = (actuals > 0).astype(int)
        # Normalize predictions to [0, 1] if they're not already
        preds_norm = (predictions - predictions.min()) / (predictions.max() - predictions.min() + 1e-8)
        return float(brier_score_loss(binary_actuals, preds_norm))
    except Exception:
        return 1.0


def compute_sharpe_ratio(returns: np.ndarray, risk_free: float = 0.0) -> float:
    """Compute annualized Sharpe ratio."""
    if len(returns) < 2 or np.std(returns) == 0:
        return 0.0
    excess = returns - risk_free / 252  # Daily risk-free
    return float(np.mean(excess) / np.std(excess) * np.sqrt(252))


def compute_max_drawdown(returns: np.ndarray) -> float:
    """Compute maximum drawdown."""
    cumulative = np.cumprod(1 + returns)
    peak = np.maximum.accumulate(cumulative)
    drawdown = (cumulative - peak) / peak
    return float(np.min(drawdown))


def compute_turnover(weights: np.ndarray) -> float:
    """Compute average daily turnover."""
    if len(weights) < 2:
        return 0.0
    changes = np.abs(np.diff(weights, axis=0))
    return float(np.mean(np.sum(changes, axis=1)) / 2)


def evaluate_predictions(
    predictions: np.ndarray,
    actuals: np.ndarray,
    weights: np.ndarray | None = None,
    metric_name: str = "ic",
) -> dict[str, float]:
    """Compute standard evaluation metrics."""
    metrics = {}

    # Information Coefficient (Spearman rank correlation)
    metrics["ic"] = compute_information_coefficient(predictions, actuals)
    metrics["ic_pearson"] = float(np.corrcoef(predictions, actuals)[0, 1]) if len(predictions) > 1 else 0.0

    # Hit rate
    metrics["hit_rate"] = compute_hit_rate(predictions, actuals)
    metrics["hit_rate_positive"] = compute_hit_rate(predictions, actuals, 0.0)

    # Classification metrics
    metrics["roc_auc"] = compute_roc_auc(predictions, actuals)
    metrics["brier"] = compute_brier_score(predictions, actuals)

    # Economic metrics if weights provided
    if weights is not None:
        portfolio_returns = np.sum(weights * actuals.reshape(-1, 1), axis=1) if weights.ndim > 1 else weights * actuals
        metrics["sharpe"] = compute_sharpe_ratio(portfolio_returns)
        metrics["max_drawdown"] = compute_max_drawdown(portfolio_returns)
        metrics["avg_return"] = float(np.mean(portfolio_returns))
        metrics["turnover"] = compute_turnover(weights)
        metrics["cumulative_return"] = float(np.prod(1 + portfolio_returns) - 1)

    return metrics


def verify_splits(
    X: pd.DataFrame,
    y: pd.Series,
    train_indices: list[int],
    val_indices: list[int],
    holdout_indices: list[int],
) -> tuple[bool, list[str]]:
    """Verify that data splits are valid and non-overlapping."""
    violations = []

    all_indices = set(train_indices) | set(val_indices) | set(holdout_indices)
    if len(all_indices) != len(train_indices) + len(val_indices) + len(holdout_indices):
        violations.append("Splits have overlapping indices")

    if max(all_indices) >= len(X):
        violations.append("Split indices exceed data length")

    # Check chronological order (assuming data is sorted by date)
    if train_indices and val_indices:
        if max(train_indices) >= min(val_indices):
            violations.append("Train indices not strictly before validation indices")

    if val_indices and holdout_indices:
        if max(val_indices) >= min(holdout_indices):
            violations.append("Validation indices not strictly before holdout indices")

    return len(violations) == 0, violations


def check_leakage(
    X: pd.DataFrame,
    y: pd.Series,
    feature_metadata: dict[str, Any] | None = None,
) -> tuple[bool, list[str]]:
    """
    Check for common leakage patterns.

    Returns (passed, notes).
    """
    notes = []

    # Check for future data in features
    # This would need feature metadata about when each feature is available
    # For now, basic checks

    # Check for constant/near-constant features (potential leakage)
    for col in X.columns:
        if X[col].nunique() <= 1:
            notes.append(f"Feature {col} is constant (possible leakage or bug)")

    # Check for perfect correlation with target (possible leakage)
    if len(y) > 10:
        for col in X.columns:
            try:
                corr = np.abs(np.corrcoef(X[col].fillna(0), y.fillna(0))[0, 1])
                if corr > 0.99:
                    notes.append(f"Feature {col} has suspiciously high correlation with target ({corr:.4f})")
            except Exception:
                pass

    # Check for target in features
    target_name = y.name if y.name else "target"
    if target_name in X.columns:
        notes.append(f"Target column '{target_name}' found in features (LEAKAGE)")

    passed = len([n for n in notes if "LEAKAGE" in n]) == 0
    return passed, notes


def evaluate_experiment(
    experiment_path: Path,
    dataset_version: str,
    contract: Any,  # EvaluationContract
    X: pd.DataFrame,
    y: pd.Series,
    train_indices: list[int],
    val_indices: list[int],
    holdout_indices: list[int],
    baselines: dict[str, Callable[[pd.DataFrame], np.ndarray]],
) -> EvaluationResult:
    """
    Independently evaluate an experiment.

    Loads the model artifact, runs predictions on all splits,
    computes metrics, checks leakage, compares to baselines.
    """
    # Load model artifact
    model_path = experiment_path / "model.pkl"
    if not model_path.exists():
        return EvaluationResult(
            experiment_id=experiment_path.name,
            dataset_version=dataset_version,
            contract_version=getattr(contract, "contract_version", "unknown"),
            train_metrics={}, validation_metrics={}, holdout_metrics={},
            baseline_name="", baseline_holdout_metrics={}, beats_baseline=False, margin=0.0,
            stability_metrics={}, stability_passed=False,
            leakage_checks={}, leakage_passed=False, leakage_notes=["Model artifact not found"],
            verdict="reject",
            notes="Model artifact not found",
        )

    with open(model_path, "rb") as f:
        model = pickle.load(f)

    # Load metadata
    metadata_path = experiment_path / "metadata.json"
    metadata = json.loads(metadata_path.read_text()) if metadata_path.exists() else {}

    # Verify splits
    splits_ok, split_violations = verify_splits(X, y, train_indices, val_indices, holdout_indices)

    # Check leakage
    leakage_ok, leakage_notes = check_leakage(X, y)

    # Make predictions on all splits
    def get_preds(indices):
        X_split = X.iloc[indices]
        y_split = y.iloc[indices]
        try:
            if hasattr(model, "predict_proba"):
                preds = model.predict_proba(X_split)[:, 1]
            elif hasattr(model, "predict"):
                preds = model.predict(X_split)
            else:
                preds = np.zeros(len(X_split))
            return preds, y_split.values
        except Exception as e:
            return np.zeros(len(X_split)), y_split.values

    train_preds, train_actuals = get_preds(train_indices)
    val_preds, val_actuals = get_preds(val_indices)
    holdout_preds, holdout_actuals = get_preds(holdout_indices)

    # Compute metrics
    train_metrics = evaluate_predictions(train_preds, train_actuals)
    val_metrics = evaluate_predictions(val_preds, val_actuals)
    holdout_metrics = evaluate_predictions(holdout_preds, holdout_actuals)

    # Compare to baselines
    baseline_results = {}
    for name, baseline_fn in baselines.items():
        try:
            base_preds = baseline_fn(X.iloc[holdout_indices])
            base_metrics = evaluate_predictions(base_preds, holdout_actuals)
            baseline_results[name] = base_metrics
        except Exception:
            baseline_results[name] = {}

    # Use primary metric from contract
    primary_metric = getattr(contract, "primary_metric", "ic")
    baseline_name = getattr(contract, "baselines", ["random"])[0]
    baseline_holdout = baseline_results.get(baseline_name, {}).get(primary_metric, 0.0)
    holdout_primary = holdout_metrics.get(primary_metric, 0.0)

    beats_baseline = holdout_primary > baseline_holdout
    margin = holdout_primary - baseline_holdout

    # Stability check (if multiple periods available)
    stability_metrics = {}
    stability_passed = True
    # Would implement period-based stability here

    # Determine verdict
    if not splits_ok:
        verdict = "reject"
        notes = f"Split violations: {split_violations}"
    elif not leakage_ok:
        verdict = "investigate"
        notes = f"Leakage concerns: {leakage_notes}"
    elif not beats_baseline:
        verdict = "reject"
        notes = f"Does not beat baseline {baseline_name} (margin: {margin:.4f})"
    elif margin < 0.01:  # Less than 1% improvement
        verdict = "investigate"
        notes = f"Marginal improvement over baseline ({margin:.4f})"
    else:
        verdict = "promote"
        notes = f"Beats baseline {baseline_name} by {margin:.4f} on {primary_metric}"

    return EvaluationResult(
        experiment_id=experiment_path.name,
        dataset_version=dataset_version,
        contract_version=getattr(contract, "contract_version", "unknown"),
        train_metrics=train_metrics,
        validation_metrics=val_metrics,
        holdout_metrics=holdout_metrics,
        baseline_name=baseline_name,
        baseline_holdout_metrics=baseline_results.get(baseline_name, {}),
        beats_baseline=beats_baseline,
        margin=margin,
        stability_metrics=stability_metrics,
        stability_passed=stability_passed,
        leakage_checks={"splits": splits_ok, "features": leakage_ok},
        leakage_passed=leakage_ok,
        leakage_notes=leakage_notes,
        verdict=verdict,
        notes=notes,
    )


def run_baseline_predictions(X: pd.DataFrame, baseline_name: str) -> np.ndarray:
    """Generate baseline predictions."""
    if baseline_name == "random":
        return np.random.RandomState(42).randn(len(X))
    elif baseline_name == "momentum_21d":
        # Use 21-day return as prediction
        if "rel_ret_21d" in X.columns:
            return X["rel_ret_21d"].values
        elif "ret_21d" in X.columns:
            return X["ret_21d"].values
        return np.zeros(len(X))
    elif baseline_name == "quant_score":
        # Would need quant score - placeholder
        return np.zeros(len(X))
    elif baseline_name == "equal_weight":
        return np.ones(len(X))
    else:
        return np.zeros(len(X))