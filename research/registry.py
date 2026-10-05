"""Lightweight experiment registry for model discovery research."""

from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from trading_copilot.storage.hashes import content_hash


@dataclass
class ExperimentRecord:
    """Single experiment record for the registry."""

    experiment_id: str
    research_question: str
    hypothesis: str
    dataset_version: str
    feature_version: str
    target_version: str
    model_family: str
    parameters: dict[str, Any]
    train_period: str  # ISO format: "start_date/end_date"
    validation_period: str
    holdout_period: str
    universe: str  # e.g., "liquid_47", "sp500"
    metrics: dict[str, float] = field(default_factory=dict)
    artifact_path: str = ""
    git_commit: str = ""
    status: str = "pending"  # pending, running, completed, failed, promoted, rejected
    notes: str = ""
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    completed_at: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ExperimentRecord":
        return cls(**data)


class ExperimentRegistry:
    """SQLite-backed experiment registry."""

    def __init__(self, db_path: str | Path = "research/experiments.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self) -> None:
        with self._conn() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS experiments (
                    experiment_id TEXT PRIMARY KEY,
                    research_question TEXT NOT NULL,
                    hypothesis TEXT NOT NULL,
                    dataset_version TEXT NOT NULL,
                    feature_version TEXT NOT NULL,
                    target_version TEXT NOT NULL,
                    model_family TEXT NOT NULL,
                    parameters TEXT NOT NULL,
                    train_period TEXT NOT NULL,
                    validation_period TEXT NOT NULL,
                    holdout_period TEXT NOT NULL,
                    universe TEXT NOT NULL,
                    metrics TEXT NOT NULL DEFAULT '{}',
                    artifact_path TEXT NOT NULL DEFAULT '',
                    git_commit TEXT NOT NULL DEFAULT '',
                    status TEXT NOT NULL DEFAULT 'pending',
                    notes TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL,
                    completed_at TEXT
                );

                CREATE INDEX IF NOT EXISTS idx_experiments_question ON experiments(research_question);
                CREATE INDEX IF NOT EXISTS idx_experiments_status ON experiments(status);
                CREATE INDEX IF NOT EXISTS idx_experiments_model ON experiments(model_family);
                CREATE INDEX IF NOT EXISTS idx_experiments_created ON experiments(created_at);
                """
            )

    @contextmanager
    def _conn(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def add(self, record: ExperimentRecord) -> None:
        with self._conn() as conn:
            conn.execute(
                """
                INSERT INTO experiments (
                    experiment_id, research_question, hypothesis, dataset_version,
                    feature_version, target_version, model_family, parameters,
                    train_period, validation_period, holdout_period, universe,
                    metrics, artifact_path, git_commit, status, notes,
                    created_at, completed_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record.experiment_id,
                    record.research_question,
                    record.hypothesis,
                    record.dataset_version,
                    record.feature_version,
                    record.target_version,
                    record.model_family,
                    json.dumps(record.parameters),
                    record.train_period,
                    record.validation_period,
                    record.holdout_period,
                    record.universe,
                    json.dumps(record.metrics),
                    record.artifact_path,
                    record.git_commit,
                    record.status,
                    record.notes,
                    record.created_at,
                    record.completed_at,
                ),
            )

    def get(self, experiment_id: str) -> Optional[ExperimentRecord]:
        with self._conn() as conn:
            cursor = conn.execute("SELECT * FROM experiments WHERE experiment_id = ?", (experiment_id,))
            row = cursor.fetchone()
            if row:
                return self._row_to_record(row)
            return None

    def update(self, record: ExperimentRecord) -> None:
        with self._conn() as conn:
            conn.execute(
                """
                UPDATE experiments SET
                    research_question = ?, hypothesis = ?, dataset_version = ?,
                    feature_version = ?, target_version = ?, model_family = ?,
                    parameters = ?, train_period = ?, validation_period = ?,
                    holdout_period = ?, universe = ?, metrics = ?, artifact_path = ?,
                    git_commit = ?, status = ?, notes = ?, completed_at = ?
                WHERE experiment_id = ?
                """,
                (
                    record.research_question,
                    record.hypothesis,
                    record.dataset_version,
                    record.feature_version,
                    record.target_version,
                    record.model_family,
                    json.dumps(record.parameters),
                    record.train_period,
                    record.validation_period,
                    record.holdout_period,
                    record.universe,
                    json.dumps(record.metrics),
                    record.artifact_path,
                    record.git_commit,
                    record.status,
                    record.notes,
                    record.completed_at,
                    record.experiment_id,
                ),
            )

    def list_by_question(self, research_question: str) -> list[ExperimentRecord]:
        with self._conn() as conn:
            cursor = conn.execute(
                "SELECT * FROM experiments WHERE research_question = ? ORDER BY created_at DESC",
                (research_question,),
            )
            return [self._row_to_record(row) for row in cursor.fetchall()]

    def list_all(self, status: Optional[str] = None) -> list[ExperimentRecord]:
        with self._conn() as conn:
            if status:
                cursor = conn.execute(
                    "SELECT * FROM experiments WHERE status = ? ORDER BY created_at DESC", (status,)
                )
            else:
                cursor = conn.execute("SELECT * FROM experiments ORDER BY created_at DESC")
            return [self._row_to_record(row) for row in cursor.fetchall()]

    def _row_to_record(self, row: sqlite3.Row) -> ExperimentRecord:
        return ExperimentRecord(
            experiment_id=row["experiment_id"],
            research_question=row["research_question"],
            hypothesis=row["hypothesis"],
            dataset_version=row["dataset_version"],
            feature_version=row["feature_version"],
            target_version=row["target_version"],
            model_family=row["model_family"],
            parameters=json.loads(row["parameters"]),
            train_period=row["train_period"],
            validation_period=row["validation_period"],
            holdout_period=row["holdout_period"],
            universe=row["universe"],
            metrics=json.loads(row["metrics"]),
            artifact_path=row["artifact_path"],
            git_commit=row["git_commit"],
            status=row["status"],
            notes=row["notes"],
            created_at=row["created_at"],
            completed_at=row["completed_at"] if row["completed_at"] else None,
        )


def generate_experiment_id(research_question: str, model_family: str, params: dict[str, Any]) -> str:
    """Generate a deterministic experiment ID from key components."""
    key = f"{research_question}|{model_family}|{json.dumps(params, sort_keys=True)}"
    return content_hash(key.encode())[:16]


def get_git_commit() -> str:
    """Get current git commit hash."""
    try:
        import subprocess
        result = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, cwd="/home/bito/Desktop/financial_model")
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    return "unknown"