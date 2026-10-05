"""Dataset and feature versioning for reproducible research."""

from __future__ import annotations

import json
import pickle
from dataclasses import asdict, dataclass, field
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Literal

import numpy as np
import pandas as pd

from trading_copilot.storage.hashes import content_hash


@dataclass
class DatasetVersion:
    """Immutable dataset version for research."""

    version_id: str = ""
    name: str = ""  # e.g., "market_features_v1", "macro_events_v1", "combined_v1"
    description: str = ""

    # Source data
    market_data_version: str = ""  # Hash of market data used
    event_data_version: str = ""  # Hash of event data used (if applicable)
    filing_data_version: str = ""  # Hash of filing data used (if applicable)

    # Feature specification
    feature_families: list[str] = field(default_factory=list)  # e.g., ["market", "macro", "earnings", "filings"]
    feature_list: list[str] = field(default_factory=list)  # Exact feature names in order
    feature_definitions: dict[str, str] = field(default_factory=dict)  # feature_name -> definition

    # Target specification
    target_name: str = ""
    target_definition: str = ""
    target_horizon_days: int = 0

    # Universe
    universe_definition: str = ""
    symbols: list[str] = field(default_factory=list)
    start_date: date = field(default_factory=lambda: date.today())
    end_date: date = field(default_factory=lambda: date.today())

    # Preprocessing
    missing_data_rule: Literal["drop_row", "impute_median", "impute_zero", "forward_fill"] = "drop_row"
    winsorize_lower: float = 0.01
    winsorize_upper: float = 0.99
    scaling: Literal["none", "standard", "robust", "percentile"] = "percentile"

    # Splits (indices, not dates, for exact reproducibility)
    train_indices: list[int] = field(default_factory=list)
    validation_indices: list[int] = field(default_factory=list)
    holdout_indices: list[int] = field(default_factory=list)

    # Provenance
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    created_by: str = "shepherd"
    git_commit: str = ""
    source_run_ids: list[str] = field(default_factory=list)  # Pipeline run IDs that produced this

    def __post_init__(self) -> None:
        if not self.version_id:
            # Compute from all fields except version_id
            data = {k: v for k, v in asdict(self).items() if k != "version_id"}
            object.__setattr__(self, "version_id", content_hash(json.dumps(data, sort_keys=True, default=str).encode())[:16])

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        # Convert dates to ISO strings
        data["start_date"] = self.start_date.isoformat()
        data["end_date"] = self.end_date.isoformat()
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "DatasetVersion":
        data["start_date"] = date.fromisoformat(data["start_date"])
        data["end_date"] = date.fromisoformat(data["end_date"])
        return cls(**data)


class DatasetStore:
    """Store for versioned datasets."""

    def __init__(self, base_path: str | Path = "research/datasets"):
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)
        self.index_path = self.base_path / "index.json"
        self._load_index()

    def _load_index(self) -> None:
        if self.index_path.exists():
            self.index = json.loads(self.index_path.read_text())
        else:
            self.index = {}

    def _save_index(self) -> None:
        self.index_path.write_text(json.dumps(self.index, indent=2))

    def save(self, dataset: DatasetVersion, X: pd.DataFrame, y: pd.Series | None = None) -> Path:
        """Save dataset version and data."""
        version_dir = self.base_path / dataset.version_id
        version_dir.mkdir(parents=True, exist_ok=True)

        # Save metadata
        (version_dir / "metadata.json").write_text(json.dumps(dataset.to_dict(), indent=2))

        # Save feature matrix
        X.to_parquet(version_dir / "X.parquet")

        # Save target if provided
        if y is not None:
            y.to_frame(name=dataset.target_name).to_parquet(version_dir / "y.parquet")

        # Save splits
        splits = {
            "train": dataset.train_indices,
            "validation": dataset.validation_indices,
            "holdout": dataset.holdout_indices,
        }
        (version_dir / "splits.json").write_text(json.dumps(splits, indent=2))

        # Update index
        self.index[dataset.version_id] = {
            "name": dataset.name,
            "version_id": dataset.version_id,
            "created_at": dataset.created_at,
            "feature_families": dataset.feature_families,
            "n_features": len(dataset.feature_list),
            "n_samples": len(X),
            "symbols": len(dataset.symbols),
            "date_range": f"{dataset.start_date} to {dataset.end_date}",
        }
        self._save_index()

        return version_dir

    def load(self, version_id: str) -> tuple[DatasetVersion, pd.DataFrame, pd.Series | None]:
        """Load dataset version and data."""
        version_dir = self.base_path / version_id
        if not version_dir.exists():
            raise FileNotFoundError(f"Dataset version {version_id} not found")

        dataset = DatasetVersion.from_dict(json.loads((version_dir / "metadata.json").read_text()))
        X = pd.read_parquet(version_dir / "X.parquet")
        y = None
        if (version_dir / "y.parquet").exists():
            y = pd.read_parquet(version_dir / "y.parquet").squeeze()

        return dataset, X, y

    def list_versions(self) -> list[dict[str, Any]]:
        return list(self.index.values())

    def get_latest(self, name_prefix: str = "") -> str | None:
        """Get latest version ID matching prefix."""
        matches = [v for v in self.index.values() if v["name"].startswith(name_prefix)]
        if not matches:
            return None
        return max(matches, key=lambda v: v["created_at"])["version_id"]


def create_dataset_from_runs(
    run_ids: list[str],
    feature_families: list[str],
    target_name: str,
    target_horizon_days: int,
    universe_definition: str,
    name: str,
) -> tuple[DatasetVersion, pd.DataFrame, pd.Series]:
    """
    Create a dataset version from historical pipeline runs.

    This is the primary way to construct research datasets - from
    preserved pipeline run artifacts (all_features.csv files).
    """
    runs_dir = Path("artifacts/runs")

    all_features = []
    all_targets = []
    symbols_set = set()

    for run_id in run_ids:
        run_dir = runs_dir / run_id
        features_path = run_dir / "all_features.csv"
        if not features_path.exists():
            continue

        df = pd.read_csv(features_path)
        df["run_id"] = run_id
        all_features.append(df)
        symbols_set.update(df["symbol"].tolist())

    if not all_features:
        raise ValueError("No valid run data found")

    X = pd.concat(all_features, ignore_index=True)
    X = X.sort_values(["run_id", "symbol"]).reset_index(drop=True)

    # Extract target from features (for now, we compute forward returns from price)
    # In practice, target would be computed from future market data
    # For now, create placeholder target
    y = pd.Series([0.0] * len(X), name=target_name, index=X.index)

    # Determine feature list from feature_families
    market_features = [
        "ret_21d", "ret_63d", "ret_126d",
        "rel_ret_21d", "rel_ret_63d", "rel_ret_126d",
        "sma_20", "sma_50", "sma_200",
        "dist_sma_20_pct", "dist_sma_50_pct", "dist_sma_200_pct",
        "realized_vol_20d", "avg_dollar_volume_20d", "relative_volume_1d", "drawdown_from_63d_high"
    ]

    feature_list = []
    feature_definitions = {}
    if "market" in feature_families:
        feature_list.extend(market_features)
        for f in market_features:
            feature_definitions[f] = f"Market feature: {f}"

    # Create dataset version
    dataset = DatasetVersion(
        version_id="",  # Will be auto-computed
        name=name,
        description=f"Dataset created from runs: {', '.join(run_ids)}",
        market_data_version=content_hash(str(sorted(run_ids)).encode())[:16],
        feature_families=feature_families,
        feature_list=feature_list,
        feature_definitions=feature_definitions,
        target_name=target_name,
        target_definition=f"Forward {target_horizon_days}-day return",
        target_horizon_days=target_horizon_days,
        universe_definition=universe_definition,
        symbols=sorted(symbols_set),
        start_date=pd.to_datetime(X["as_of"]).min().date(),
        end_date=pd.to_datetime(X["as_of"]).max().date(),
        git_commit=get_git_commit(),
        source_run_ids=run_ids,
    )

    # Create chronological splits (70/15/15)
    n = len(X)
    train_end = int(n * 0.7)
    val_end = int(n * 0.85)
    dataset.train_indices = list(range(train_end))
    dataset.validation_indices = list(range(train_end, val_end))
    dataset.holdout_indices = list(range(val_end, n))

    return dataset, X[feature_list], y


def get_git_commit() -> str:
    try:
        import subprocess
        result = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, cwd="/home/bito/Desktop/financial_model")
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    return "unknown"


def save_model_artifact(
    model: Any,
    experiment_id: str,
    dataset_version: str,
    feature_version: str,
    metrics: dict[str, float],
    path: Path | None = None,
) -> Path:
    """Save trained model artifact with metadata."""
    if path is None:
        path = Path(f"research/artifacts/{experiment_id}")
    path.mkdir(parents=True, exist_ok=True)

    # Save model
    with open(path / "model.pkl", "wb") as f:
        pickle.dump(model, f)

    # Save metadata
    metadata = {
        "experiment_id": experiment_id,
        "dataset_version": dataset_version,
        "feature_version": feature_version,
        "metrics": metrics,
        "saved_at": datetime.now(timezone.utc).isoformat(),
        "git_commit": get_git_commit(),
    }
    (path / "metadata.json").write_text(json.dumps(metadata, indent=2))

    return path