"""Leaderboard for model discovery research."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from trading_copilot.storage.hashes import content_hash


@dataclass
class LeaderboardEntry:
    """Single entry in the research leaderboard."""

    experiment_id: str = ""
    model_family: str = ""
    research_question: str = ""

    # Validation metrics
    val_primary: float = 0.0
    val_secondary: dict[str, float] = field(default_factory=dict)

    # Holdout metrics (the real test)
    holdout_primary: float = 0.0
    holdout_secondary: dict[str, float] = field(default_factory=dict)

    # Stability metrics
    stability_scores: dict[str, float] = field(default_factory=dict)  # period -> metric

    # Complexity metrics
    model_size_mb: float = 0.0
    inference_ms_per_symbol: float = 0.0
    n_parameters: int = 0
    training_time_seconds: float = 0.0

    # Economic metrics (if applicable)
    sharpe_ratio: float = 0.0
    max_drawdown: float = 0.0
    turnover: float = 0.0
    hit_rate: float = 0.0
    avg_forward_return: float = 0.0

    # Status
    status: Literal["candidate", "promoted", "rejected", "baseline"] = "candidate"
    beats_baseline: bool = False
    baseline_name: str = ""
    baseline_margin: float = 0.0

    # Provenance
    dataset_version: str = ""
    feature_version: str = ""
    target_version: str = ""
    git_commit: str = ""
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "LeaderboardEntry":
        return cls(**data)


class Leaderboard:
    """Leaderboard for a research question."""

    def __init__(self, research_question: str, contract_version: str, path: Path | None = None):
        self.research_question = research_question
        self.contract_version = contract_version
        self.path = path or Path(f"research/leaderboards/{research_question}.json")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.entries: list[LeaderboardEntry] = []
        self._load()

    def _load(self) -> None:
        if self.path.exists():
            data = json.loads(self.path.read_text())
            self.entries = [LeaderboardEntry.from_dict(e) for e in data.get("entries", [])]

    def _save(self) -> None:
        data = {
            "research_question": self.research_question,
            "contract_version": self.contract_version,
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "entries": [e.to_dict() for e in self.entries],
        }
        self.path.write_text(json.dumps(data, indent=2))

    def add(self, entry: LeaderboardEntry) -> None:
        # Remove existing entry with same experiment_id
        self.entries = [e for e in self.entries if e.experiment_id != entry.experiment_id]
        self.entries.append(entry)
        self._save()

    def get_sorted(self, metric: str = "holdout_primary", ascending: bool = False) -> list[LeaderboardEntry]:
        """Get entries sorted by a metric."""
        def get_val(e: LeaderboardEntry) -> float:
            if metric == "holdout_primary":
                return e.holdout_primary
            elif metric == "val_primary":
                return e.val_primary
            elif metric == "sharpe_ratio":
                return e.sharpe_ratio
            elif metric == "hit_rate":
                return e.hit_rate
            elif metric == "avg_forward_return":
                return e.avg_forward_return
            elif metric == "max_drawdown":
                return -e.max_drawdown  # Lower is better
            elif metric == "turnover":
                return -e.turnover  # Lower is better
            elif metric == "model_size_mb":
                return -e.model_size_mb  # Smaller is better
            elif metric == "inference_ms_per_symbol":
                return -e.inference_ms_per_symbol  # Faster is better
            return 0.0

        return sorted(self.entries, key=get_val, reverse=not ascending)

    def get_best(self, metric: str = "holdout_primary") -> LeaderboardEntry | None:
        sorted_entries = self.get_sorted(metric)
        return sorted_entries[0] if sorted_entries else None

    def get_promoted(self) -> list[LeaderboardEntry]:
        return [e for e in self.entries if e.status == "promoted"]

    def get_baselines(self) -> list[LeaderboardEntry]:
        return [e for e in self.entries if e.status == "baseline"]

    def mark_promoted(self, experiment_id: str) -> None:
        for e in self.entries:
            if e.experiment_id == experiment_id:
                e.status = "promoted"
        self._save()

    def mark_rejected(self, experiment_id: str, reason: str = "") -> None:
        for e in self.entries:
            if e.experiment_id == experiment_id:
                e.status = "rejected"
                e.notes = reason
        self._save()

    def to_markdown(self) -> str:
        """Generate markdown leaderboard table."""
        lines = [
            f"# Leaderboard: {self.research_question}",
            f"Contract: {self.contract_version}",
            f"Updated: {datetime.now(timezone.utc).isoformat()}",
            "",
            "| Rank | Model | Val Primary | Holdout Primary | Hit Rate | Sharpe | Max DD | Turnover | Size (MB) | Inference (ms) | Status |",
            "|------|-------|-------------|-----------------|----------|--------|--------|----------|-----------|----------------|--------|",
        ]

        for i, entry in enumerate(self.get_sorted("holdout_primary"), 1):
            status_icon = "✅" if entry.status == "promoted" else "❌" if entry.status == "rejected" else "🔬" if entry.status == "baseline" else "⏳"
            lines.append(
                f"| {i} | {entry.model_family} | {entry.val_primary:.4f} | "
                f"{entry.holdout_primary:.4f} | {entry.hit_rate:.2%} | "
                f"{entry.sharpe_ratio:.2f} | {entry.max_drawdown:.2%} | "
                f"{entry.turnover:.2f} | {entry.model_size_mb:.1f} | "
                f"{entry.inference_ms_per_symbol:.1f} | {status_icon} {entry.status} |"
            )

        return "\n".join(lines)

    def to_csv(self) -> str:
        """Generate CSV leaderboard."""
        if not self.entries:
            return ""

        headers = [
            "rank", "experiment_id", "model_family", "val_primary", "holdout_primary",
            "hit_rate", "sharpe_ratio", "max_drawdown", "turnover",
            "model_size_mb", "inference_ms_per_symbol", "status", "beats_baseline",
            "baseline_name", "baseline_margin", "dataset_version", "feature_version",
            "git_commit", "created_at"
        ]

        rows = [",".join(headers)]
        for i, entry in enumerate(self.get_sorted("holdout_primary"), 1):
            rows.append(",".join([
                str(i), entry.experiment_id, entry.model_family,
                f"{entry.val_primary:.6f}", f"{entry.holdout_primary:.6f}",
                f"{entry.hit_rate:.6f}", f"{entry.sharpe_ratio:.6f}",
                f"{entry.max_drawdown:.6f}", f"{entry.turnover:.6f}",
                f"{entry.model_size_mb:.3f}", f"{entry.inference_ms_per_symbol:.3f}",
                entry.status, str(entry.beats_baseline), entry.baseline_name,
                f"{entry.baseline_margin:.6f}", entry.dataset_version, entry.feature_version,
                entry.git_commit, entry.created_at
            ]))
        return "\n".join(rows)


def compute_stability_scores(
    predictions: dict[str, dict[datetime, float]],  # symbol -> {date: prediction}
    actuals: dict[str, dict[datetime, float]],       # symbol -> {date: actual}
    periods: list[tuple[datetime, datetime]],        # list of (start, end) periods
    metric_fn,                                       # function(preds, actuals) -> float
) -> dict[str, float]:
    """
    Compute metric for each period to assess stability.

    Returns dict of period_name -> metric_value.
    """
    scores = {}
    for i, (start, end) in enumerate(periods):
        period_preds = []
        period_actuals = []
        for symbol, pred_dict in predictions.items():
            for date_val, pred in pred_dict.items():
                if start <= date_val <= end and symbol in actuals and date_val in actuals[symbol]:
                    period_preds.append(pred)
                    period_actuals.append(actuals[symbol][date_val])
        if period_preds:
            scores[f"period_{i}_{start.date()}_{end.date()}"] = metric_fn(period_preds, period_actuals)
    return scores