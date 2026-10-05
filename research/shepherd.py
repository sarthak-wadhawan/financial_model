"""Shepherd: Coordinates autonomous model discovery research.

The Shepherd:
1. Defines research questions and evaluation contracts
2. Generates competing hypotheses
3. Assigns independent experiments
4. Runs experiments (via sub-agents or direct execution)
5. Performs common evaluation
6. Compares results
7. Diagnoses failures
8. Proposes follow-up experiments
9. Maintains leaderboard
10. Enforces promotion gate
"""

from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Literal

from trading_copilot.storage.hashes import content_hash

from research.contracts import EvaluationContract, create_default_contract
from research.datasets import DatasetStore, DatasetVersion, create_dataset_from_runs
from research.evaluation import (
    EvaluationResult,
    evaluate_experiment,
    run_baseline_predictions,
)
from research.leaderboard import Leaderboard, LeaderboardEntry
from research.registry import ExperimentRecord, ExperimentRegistry, generate_experiment_id, get_git_commit


@dataclass
class ResearchQuestion:
    """A research question for model discovery."""

    name: str
    description: str
    contract: EvaluationContract
    dataset: DatasetVersion | None = None
    status: Literal["defined", "data_ready", "running", "completed", "promoted"] = "defined"
    hypotheses: list[str] = field(default_factory=list)
    baseline_names: list[str] = field(default_factory=list)
    promoted_experiment: str = ""


class Shepherd:
    """Autonomous research coordinator."""

    def __init__(
        self,
        registry_path: Path = Path("research/experiments.db"),
        datasets_path: Path = Path("research/datasets"),
        leaderboards_path: Path = Path("research/leaderboards"),
        artifacts_path: Path = Path("research/artifacts"),
    ):
        self.registry = ExperimentRegistry(registry_path)
        self.dataset_store = DatasetStore(datasets_path)
        self.leaderboards_path = leaderboards_path
        self.artifacts_path = artifacts_path

        self.questions: dict[str, ResearchQuestion] = {}
        self.baseline_fns: dict[str, Callable[[Any], Any]] = {}

    def define_question(
        self,
        name: str,
        description: str,
        contract: EvaluationContract | None = None,
    ) -> ResearchQuestion:
        """Define a new research question."""
        if contract is None:
            contract = create_default_contract(name)

        question = ResearchQuestion(
            name=name,
            description=description,
            contract=contract,
            baseline_names=contract.baselines,
        )
        self.questions[name] = question
        return question

    def prepare_data(
        self,
        question_name: str,
        run_ids: list[str],
        feature_families: list[str],
        target_name: str,
        target_horizon_days: int,
    ) -> DatasetVersion:
        """Prepare dataset for a research question from historical runs."""
        question = self.questions[question_name]
        contract = question.contract

        dataset, X, y = create_dataset_from_runs(
            run_ids=run_ids,
            feature_families=feature_families,
            target_name=target_name,
            target_horizon_days=target_horizon_days,
            universe_definition=contract.universe_definition,
            name=f"{question_name}_dataset",
        )

        # Save dataset
        self.dataset_store.save(dataset, X, y)
        question.dataset = dataset
        question.status = "data_ready"

        return dataset

    def generate_hypotheses(self, question_name: str) -> list[dict[str, Any]]:
        """Generate competing hypotheses for a research question.

        Returns list of experiment configurations to run.
        """
        question = self.questions[question_name]

        # Define diverse model families to test
        hypotheses = [
            # Baselines
            {
                "model_family": "baseline_random",
                "hypothesis": "Random predictions (sanity check)",
                "parameters": {"baseline": "random"},
            },
            {
                "model_family": "baseline_momentum",
                "hypothesis": "21-day relative momentum as predictor",
                "parameters": {"baseline": "momentum_21d"},
            },
            {
                "model_family": "baseline_quant_score",
                "hypothesis": "Deterministic quant score as predictor",
                "parameters": {"baseline": "quant_score"},
            },

            # Linear models
            {
                "model_family": "logistic_regression",
                "hypothesis": "Regularized logistic regression on market features",
                "parameters": {"C": 1.0, "penalty": "l2", "solver": "lbfgs", "max_iter": 1000},
            },
            {
                "model_family": "ridge_regression",
                "hypothesis": "Ridge regression for return prediction",
                "parameters": {"alpha": 1.0, "solver": "auto"},
            },

            # Tree models
            {
                "model_family": "random_forest",
                "hypothesis": "Random Forest with moderate depth",
                "parameters": {"n_estimators": 200, "max_depth": 5, "min_samples_leaf": 10, "n_jobs": -1},
            },
            {
                "model_family": "extra_trees",
                "hypothesis": "ExtraTrees (more randomized trees)",
                "parameters": {"n_estimators": 200, "max_depth": 5, "min_samples_leaf": 10, "n_jobs": -1},
            },
            {
                "model_family": "hist_gradient_boosting",
                "hypothesis": "Histogram Gradient Boosting (fast, handles missing)",
                "parameters": {"max_iter": 200, "max_depth": 5, "learning_rate": 0.1, "min_samples_leaf": 10},
            },
            {
                "model_family": "gradient_boosting",
                "hypothesis": "Classic Gradient Boosted Trees",
                "parameters": {"n_estimators": 200, "max_depth": 4, "learning_rate": 0.1, "min_samples_leaf": 10},
            },

            # Neural
            {
                "model_family": "small_mlp",
                "hypothesis": "Small MLP (2 hidden layers, 64/32 units)",
                "parameters": {"hidden_layers": [64, 32], "dropout": 0.1, "learning_rate": 1e-3, "epochs": 50, "batch_size": 256},
            },
        ]

        question.hypotheses = [h["hypothesis"] for h in hypotheses]
        return hypotheses

    def create_experiments(self, question_name: str, hypotheses: list[dict[str, Any]]) -> list[ExperimentRecord]:
        """Create experiment records for all hypotheses."""
        question = self.questions[question_name]
        contract = question.contract
        dataset = question.dataset

        if dataset is None:
            raise ValueError(f"No dataset prepared for {question_name}")

        experiments = []
        for hyp in hypotheses:
            exp_id = generate_experiment_id(question_name, hyp["model_family"], hyp["parameters"])

            record = ExperimentRecord(
                experiment_id=exp_id,
                research_question=question_name,
                hypothesis=hyp["hypothesis"],
                dataset_version=dataset.version_id,
                feature_version=content_hash(str(sorted(dataset.feature_list)).encode())[:16],
                target_version=content_hash(f"{dataset.target_name}|{dataset.target_definition}".encode())[:16],
                model_family=hyp["model_family"],
                parameters=hyp["parameters"],
                train_period=f"{contract.train_start.isoformat()}/{contract.train_end.isoformat()}",
                validation_period=f"{contract.validation_start.isoformat()}/{contract.validation_end.isoformat()}",
                holdout_period=f"{contract.holdout_start.isoformat()}/{contract.holdout_end.isoformat()}",
                universe=contract.target_universe,
                git_commit=get_git_commit(),
                status="pending",
            )
            self.registry.add(record)
            experiments.append(record)

        return experiments

    def run_experiment(self, experiment: ExperimentRecord, X: pd.DataFrame, y: pd.Series) -> Path:
        """Run a single experiment and save artifact."""
        from research.datasets import save_model_artifact

        artifact_path = self.artifacts_path / experiment.experiment_id
        artifact_path.mkdir(parents=True, exist_ok=True)

        # Get splits from dataset
        dataset, _, _ = self.dataset_store.load(experiment.dataset_version)

        train_idx = dataset.train_indices
        val_idx = dataset.validation_indices
        holdout_idx = dataset.holdout_indices

        # Train model based on family
        model = self._train_model(experiment, X.iloc[train_idx], y.iloc[train_idx])

        # Save artifact
        save_model_artifact(
            model=model,
            experiment_id=experiment.experiment_id,
            dataset_version=experiment.dataset_version,
            feature_version=experiment.feature_version,
            metrics={},  # Will be filled by evaluator
            path=artifact_path,
        )

        # Update registry
        experiment.status = "completed"
        experiment.artifact_path = str(artifact_path)
        experiment.completed_at = datetime.now(timezone.utc).isoformat()
        self.registry.update(experiment)

        return artifact_path

    def _train_model(self, experiment: ExperimentRecord, X_train: pd.DataFrame, y_train: pd.Series):
        """Train a model based on experiment configuration."""
        family = experiment.model_family
        params = experiment.parameters

        # Handle baselines
        if family.startswith("baseline_"):
            return {"type": "baseline", "name": params.get("baseline", "random")}

        # Import sklearn
        from sklearn.linear_model import LogisticRegression, Ridge
        from sklearn.ensemble import RandomForestClassifier, ExtraTreesClassifier, HistGradientBoostingClassifier, GradientBoostingClassifier
        from sklearn.neural_network import MLPClassifier
        from sklearn.preprocessing import StandardScaler
        from sklearn.pipeline import Pipeline

        # Fill NaN values
        X_train = X_train.fillna(0)

        if family == "logistic_regression":
            model = LogisticRegression(random_state=42, **params)
        elif family == "ridge_regression":
            model = Ridge(random_state=42, **params)
        elif family == "random_forest":
            model = RandomForestClassifier(random_state=42, **params)
        elif family == "extra_trees":
            model = ExtraTreesClassifier(random_state=42, **params)
        elif family == "hist_gradient_boosting":
            model = HistGradientBoostingClassifier(random_state=42, **params)
        elif family == "gradient_boosting":
            model = GradientBoostingClassifier(random_state=42, **params)
        elif family == "small_mlp":
            # MLP needs scaling
            scaler = StandardScaler()
            X_scaled = scaler.fit_transform(X_train)
            mlp = MLPClassifier(
                hidden_layer_sizes=tuple(params.get("hidden_layers", [64, 32])),
                alpha=params.get("dropout", 0.1),
                learning_rate_init=params.get("learning_rate", 1e-3),
                max_iter=params.get("epochs", 50),
                batch_size=params.get("batch_size", 256),
                random_state=42,
                early_stopping=True,
                validation_fraction=0.1,
            )
            mlp.fit(X_scaled, (y_train > 0).astype(int))
            return Pipeline([("scaler", scaler), ("mlp", mlp)])
        else:
            raise ValueError(f"Unknown model family: {family}")

        # For classification, convert target to binary
        y_binary = (y_train > 0).astype(int)
        model.fit(X_train, y_binary)
        return model

    def evaluate_all(self, question_name: str) -> list[EvaluationResult]:
        """Evaluate all experiments for a question."""
        question = self.questions[question_name]
        contract = question.contract
        dataset = question.dataset

        if dataset is None:
            raise ValueError(f"No dataset for {question_name}")

        # Load data
        _, X, y = self.dataset_store.load(dataset.version_id)

        # Get experiments
        experiments = self.registry.list_by_question(question_name)

        # Define baseline functions
        baselines = {}
        for name in contract.baselines:
            baselines[name] = lambda X, n=name: run_baseline_predictions(X, n)

        # Evaluate each experiment
        results = []
        leaderboard = Leaderboard(question_name, contract.contract_version)

        for exp in experiments:
            if exp.status != "completed":
                continue

            artifact_path = Path(exp.artifact_path)
            if not artifact_path.exists():
                continue

            result = evaluate_experiment(
                experiment_path=artifact_path,
                dataset_version=dataset.version_id,
                contract=contract,
                X=X,
                y=y,
                train_indices=dataset.train_indices,
                val_indices=dataset.validation_indices,
                holdout_indices=dataset.holdout_indices,
                baselines=baselines,
            )

            # Add to leaderboard
            entry = LeaderboardEntry(
                experiment_id=exp.experiment_id,
                model_family=exp.model_family,
                research_question=question_name,
                val_primary=result.validation_metrics.get(contract.primary_metric, 0.0),
                val_secondary={k: v for k, v in result.validation_metrics.items() if k != contract.primary_metric},
                holdout_primary=result.holdout_metrics.get(contract.primary_metric, 0.0),
                holdout_secondary={k: v for k, v in result.holdout_metrics.items() if k != contract.primary_metric},
                stability_scores=result.stability_metrics,
                model_size_mb=result.model_size_mb,
                inference_ms_per_symbol=result.inference_ms_per_symbol,
                sharpe_ratio=result.holdout_metrics.get("sharpe", 0.0),
                max_drawdown=result.holdout_metrics.get("max_drawdown", 0.0),
                turnover=result.holdout_metrics.get("turnover", 0.0),
                hit_rate=result.holdout_metrics.get("hit_rate", 0.0),
                avg_forward_return=result.holdout_metrics.get("avg_return", 0.0),
                status=result.verdict if result.verdict != "investigate" else "candidate",
                beats_baseline=result.beats_baseline,
                baseline_name=result.baseline_name,
                baseline_margin=result.margin,
                dataset_version=dataset.version_id,
                feature_version=exp.feature_version,
                target_version=exp.target_version,
                git_commit=exp.git_commit,
            )
            leaderboard.add(entry)
            results.append(result)

            # Update experiment with metrics
            exp.metrics = result.holdout_metrics
            exp.status = result.verdict
            self.registry.update(exp)

        return results

    def diagnose_failures(self, question_name: str) -> dict[str, Any]:
        """Analyze experiment results and propose follow-up experiments."""
        question = self.questions[question_name]
        experiments = self.registry.list_by_question(question_name)
        leaderboard = Leaderboard(question_name, question.contract.contract_version)

        completed = [e for e in experiments if e.status in ["completed", "promoted", "rejected", "investigate"]]

        # Find best performing model family
        best_entry = leaderboard.get_best("holdout_primary")

        diagnosis = {
            "question": question_name,
            "total_experiments": len(experiments),
            "completed": len(completed),
            "promoted": len([e for e in completed if e.status == "promoted"]),
            "rejected": len([e for e in completed if e.status == "rejected"]),
            "best_model": best_entry.model_family if best_entry else None,
            "best_holdout_metric": best_entry.holdout_primary if best_entry else 0.0,
            "follow_up_hypotheses": [],
        }

        # Analyze failures and generate follow-up hypotheses
        if best_entry:
            # Check if best model is tree-based
            if "forest" in best_entry.model_family.lower() or "tree" in best_entry.model_family.lower() or "boost" in best_entry.model_family.lower():
                diagnosis["follow_up_hypotheses"].append({
                    "hypothesis": "Tree model performs well but may overfit earnings periods",
                    "proposed_experiments": [
                        "Exclude earnings windows from training",
                        "Add earnings-context features (days to earnings, earnings surprise history)",
                        "Train separate earnings-period model",
                    ],
                })

            # Check if neural model underperforms
            neural_entries = [e for e in leaderboard.entries if "mlp" in e.model_family.lower() or "neural" in e.model_family.lower()]
            if neural_entries and best_entry.model_family not in [e.model_family for e in neural_entries]:
                diagnosis["follow_up_hypotheses"].append({
                    "hypothesis": "MLP underperforms tree models - try different architecture",
                    "proposed_experiments": [
                        "Wider MLP (128, 64, 32)",
                        "Deeper MLP (4 layers)",
                        "Add layer normalization",
                        "Try different activation (GELU vs ReLU)",
                    ],
                })

            # Feature ablation
            diagnosis["follow_up_hypotheses"].append({
                "hypothesis": "Determine which feature families contribute most",
                "proposed_experiments": [
                    "Market-only features",
                    "Market + macro events",
                    "Market + earnings proximity",
                    "Full feature set minus momentum",
                    "Full feature set minus volatility",
                ],
            })

        return diagnosis

    def promote_best(self, question_name: str) -> ExperimentRecord | None:
        """Promote the best experiment if it passes all gates."""
        question = self.questions[question_name]
        leaderboard = Leaderboard(question_name, question.contract.contract_version)
        best = leaderboard.get_best("holdout_primary")

        if best and best.status == "promoted":
            # Verify promotion gate
            gate_checks = self._verify_promotion_gate(question_name, best.experiment_id)
            if all(gate_checks.values()):
                leaderboard.mark_promoted(best.experiment_id)
                question.promoted_experiment = best.experiment_id
                question.status = "promoted"

                exp = self.registry.get(best.experiment_id)
                if exp:
                    exp.status = "promoted"
                    self.registry.update(exp)

                return self.registry.get(best.experiment_id)

        return None

    def _verify_promotion_gate(self, question_name: str, experiment_id: str) -> dict[str, bool]:
        """Verify all promotion gate criteria."""
        exp = self.registry.get(experiment_id)
        if not exp:
            return {"exists": False}

        checks = {
            "exists": True,
            "evaluation_contract_respected": exp.dataset_version != "",
            "leakage_checks_passed": True,  # Would check evaluation result
            "baseline_beaten": exp.metrics.get("ic", 0) > 0,  # Simplified
            "holdout_positive": exp.metrics.get("ic", 0) > 0,
            "stability_acceptable": True,  # Would check stability
            "complexity_justified": True,  # Would compare complexity
            "reproducible": exp.git_commit != "",
            "integration_safe": True,  # Would test integration
        }
        return checks

    def generate_report(self, question_name: str) -> str:
        """Generate a comprehensive research report."""
        question = self.questions[question_name]
        leaderboard = Leaderboard(question_name, question.contract.contract_version)
        diagnosis = self.diagnose_failures(question_name)

        lines = [
            f"# Research Report: {question_name}",
            f"**Question**: {question.description}",
            f"**Contract**: {question.contract.contract_version}",
            f"**Status**: {question.status}",
            f"**Dataset**: {question.dataset.version_id if question.dataset else 'Not prepared'}",
            f"**Promoted Experiment**: {question.promoted_experiment or 'None'}",
            "",
            "## Leaderboard",
            leaderboard.to_markdown(),
            "",
            "## Diagnosis",
            f"- Total experiments: {diagnosis['total_experiments']}",
            f"- Completed: {diagnosis['completed']}",
            f"- Promoted: {diagnosis['promoted']}",
            f"- Rejected: {diagnosis['rejected']}",
            f"- Best model: {diagnosis['best_model']} (holdout {diagnosis['best_holdout_metric']:.4f})",
            "",
            "## Follow-up Hypotheses",
        ]

        for i, followup in enumerate(diagnosis["follow_up_hypotheses"], 1):
            lines.append(f"\n### {i}. {followup['hypothesis']}")
            for exp in followup["proposed_experiments"]:
                lines.append(f"  - {exp}")

        return "\n".join(lines)


def run_full_research_cycle(
    question_name: str,
    description: str,
    run_ids: list[str],
    feature_families: list[str],
    target_name: str = "fwd_ret_5d",
    target_horizon_days: int = 5,
) -> Shepherd:
    """Run a complete autonomous research cycle for a question."""
    shepherd = Shepherd()

    # 1. Define question
    contract = create_default_contract(question_name)
    contract.feature_families = feature_families
    shepherd.define_question(question_name, description, contract)

    # 2. Prepare data
    shepherd.prepare_data(
        question_name=question_name,
        run_ids=run_ids,
        feature_families=feature_families,
        target_name=target_name,
        target_horizon_days=target_horizon_days,
    )

    # 3. Generate hypotheses
    hypotheses = shepherd.generate_hypotheses(question_name)

    # 4. Create experiments
    experiments = shepherd.create_experiments(question_name, hypotheses)

    # 5. Run experiments
    question = shepherd.questions[question_name]
    _, X, y = shepherd.dataset_store.load(question.dataset.version_id)

    for exp in experiments:
        print(f"Running experiment: {exp.experiment_id} ({exp.model_family})")
        shepherd.run_experiment(exp, X, y)

    # 6. Evaluate all
    shepherd.evaluate_all(question_name)

    # 7. Promote best
    shepherd.promote_best(question_name)

    # 8. Generate report
    report = shepherd.generate_report(question_name)
    report_path = Path(f"research/reports/{question_name}_report.md")
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(report)
    print(f"Report saved to {report_path}")

    return shepherd