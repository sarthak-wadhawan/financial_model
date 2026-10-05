"""Research infrastructure for autonomous model discovery."""

from research.contracts import EvaluationContract, create_default_contract, CANDIDATE_RANKING_CONTRACT
from research.datasets import DatasetStore, DatasetVersion, create_dataset_from_runs, save_model_artifact
from research.evaluation import EvaluationResult, evaluate_experiment, run_baseline_predictions
from research.leaderboard import Leaderboard, LeaderboardEntry
from research.registry import ExperimentRecord, ExperimentRegistry, generate_experiment_id
from research.shepherd import ResearchQuestion, Shepherd, run_full_research_cycle

__all__ = [
    "EvaluationContract",
    "create_default_contract",
    "CANDIDATE_RANKING_CONTRACT",
    "DatasetStore",
    "DatasetVersion",
    "create_dataset_from_runs",
    "save_model_artifact",
    "EvaluationResult",
    "evaluate_experiment",
    "run_baseline_predictions",
    "Leaderboard",
    "LeaderboardEntry",
    "ExperimentRecord",
    "ExperimentRegistry",
    "generate_experiment_id",
    "ResearchQuestion",
    "Shepherd",
    "run_full_research_cycle",
]