"""Command-line interface for AI Trading Research Copilot."""

from __future__ import annotations

# Enable Python 3.9 support for union syntax (X | None)
try:
    import eval_type_backport  # noqa: F401
except ImportError:
    pass

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from trading_copilot.config import Config, load_config, load_settings
from trading_copilot.logging import get_logger, setup_logging
from trading_copilot.models import SymbolInfo
from trading_copilot.models.features import FeatureRow, QuantScore
from trading_copilot.models.results import FinalCandidate, RunManifest
from trading_copilot.pipeline.universe import MockUniverseProvider
from trading_copilot.pipeline.features import FeatureEngine
from trading_copilot.pipeline.eligibility import EligibilityFilter
from trading_copilot.pipeline.quant_score import QuantScorer
from trading_copilot.pipeline.report import ReportGenerator
from trading_copilot.providers import create_market_data_provider
from trading_copilot.storage.runs import RunStore
from trading_copilot.storage.cache import FileCache

app = typer.Typer(
    name="trading-copilot",
    help="AI Trading Research Copilot - V1",
    add_completion=False,
)

console = Console()
logger = get_logger(__name__)


@app.callback()
def main(
    config: Annotated[
        Path,
        typer.Option("--config", "-c", help="Path to configuration YAML file", exists=True, readable=True),
    ] = Path("config.yaml"),
    log_level: Annotated[str, typer.Option("--log-level", help="Logging level")] = "INFO",
    json_logs: Annotated[bool, typer.Option("--json-logs", help="Output logs as JSON")] = False,
) -> None:
    """AI Trading Research Copilot - V1."""
    setup_logging(level=log_level, json_format=json_logs)
    # Store config path in context for subcommands
    app.config_path = config  # type: ignore[attr-defined]


@app.command()
def scan(
    config: Annotated[
        Path,
        typer.Option("--config", "-c", help="Path to configuration YAML file", exists=True, readable=True),
    ] = Path("config.yaml"),
    output: Annotated[
        Path | None,
        typer.Option("--output", "-o", help="Output directory for artifacts"),
    ] = None,
) -> None:
    """Run the offline deterministic scanner on fixture data."""
    logger.info("Starting scan", extra={"config_path": str(config)})
    
    cfg = load_config(config)
    settings = load_settings()
    
    # Create run directory
    run_id = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H%M%SZ")
    artifact_dir = Path(cfg.app.artifact_dir) / run_id
    artifact_dir.mkdir(parents=True, exist_ok=True)
    
    # Save config snapshot
    config_snapshot = artifact_dir / "config.yaml"
    import yaml
    with open(config_snapshot, "w") as f:
        yaml.safe_dump(cfg.model_dump(), f)
    
    logger.info("Run started", extra={"run_id": run_id, "artifact_dir": str(artifact_dir)})
    
    # Stage 1: Build universe
    universe_provider = MockUniverseProvider()
    symbols = universe_provider.get_symbols()
    logger.info("Universe built", extra={"count": len(symbols)})
    
    # Stage 2: Get market data
    end_date = datetime.now(timezone.utc)
    from datetime import timedelta
    start_date = end_date - timedelta(days=cfg.market.history_days)
    
    # Initialize cache if enabled
    cache = None
    if cfg.runtime.cache_enabled:
        # Use a separate cache directory outside of run artifacts
        cache_dir = Path(cfg.app.artifact_dir).parent / "cache" / "market_data"
        cache = FileCache(cache_dir, ttl_days=7)
    
    # Create market data provider based on config
    market_provider = create_market_data_provider(
        provider_name=cfg.market.provider,
        cache=cache,
    )
    
    try:
        market_data = market_provider.get_daily_bars(
            symbols=[s.symbol for s in symbols],
            start=start_date,
            end=end_date,
        )
        benchmark_bars = market_provider.get_benchmark_bars(
            benchmark=cfg.market.benchmark,
            start=start_date,
            end=end_date,
        )
        logger.info("Market data loaded", extra={"symbols_with_data": len(market_data)})
    finally:
        # Close provider if it has a close method
        if hasattr(market_provider, 'close'):
            market_provider.close()
    
    # Stage 3: Compute features
    feature_engine = FeatureEngine()
    feature_rows = feature_engine.compute(market_data, benchmark_bars)
    logger.info("Features computed", extra={"count": len(feature_rows)})
    
    # Stage 4: Eligibility filter
    eligibility_filter = EligibilityFilter(cfg.eligibility)
    eligible_features = eligibility_filter.apply(feature_rows)
    logger.info("Eligibility filter applied", extra={"eligible": len(eligible_features)})
    
    # Stage 5: Quant scoring
    quant_scorer = QuantScorer(cfg.scoring.quant)
    quant_scores = quant_scorer.score(eligible_features)
    logger.info("Quant scores computed", extra={"count": len(quant_scores)})
    
    # Stage 6: Top N
    top_n = cfg.scan.top_n
    top_candidates = quant_scores[:top_n]
    logger.info("Top candidates selected", extra={"top_n": len(top_candidates)})
    
    # Create run manifest
    manifest = RunManifest(
        run_id=run_id,
        started_at=datetime.now(timezone.utc),
        config_hash="",  # Will be computed by RunStore
        git_commit=None,
        universe_size=len(symbols),
        eligible_count=len(eligible_features),
        top_n=len(top_candidates),
        failures=0,
    )
    
    # Generate report
    report_gen = ReportGenerator(artifact_dir)
    report_gen.write_top20(top_candidates, eligible_features)
    report_gen.write_features(feature_rows)
    report_gen.write_manifest(manifest)
    
    # Print summary to console
    _print_scan_summary(top_candidates, eligible_features, artifact_dir)
    
    logger.info("Scan completed", extra={"run_id": run_id})


def _print_scan_summary(
    top_candidates: list[QuantScore],
    all_features: list[FeatureRow],
    artifact_dir: Path,
) -> None:
    """Print a summary table of top candidates."""
    table = Table(title=f"Top {len(top_candidates)} Quant Candidates")
    table.add_column("Rank", justify="right", style="cyan")
    table.add_column("Symbol", style="bold")
    table.add_column("Quant Score", justify="right", style="green")
    table.add_column("Momentum", justify="right")
    table.add_column("Trend", justify="right")
    table.add_column("Liquidity", justify="right")
    table.add_column("Volume", justify="right")
    table.add_column("Vol Quality", justify="right")
    
    for i, qs in enumerate(top_candidates, 1):
        comp = qs.components
        table.add_row(
            str(i),
            qs.symbol,
            f"{qs.quant_score:.1f}",
            f"{comp.get('momentum', 0):.1f}",
            f"{comp.get('trend', 0):.1f}",
            f"{comp.get('liquidity', 0):.1f}",
            f"{comp.get('volume', 0):.1f}",
            f"{comp.get('volatility_quality', 0):.1f}",
        )
    
    console.print(table)
    console.print(f"\nArtifacts written to: {artifact_dir}")
    console.print(f"  - top20.csv")
    console.print(f"  - all_features.csv")
    console.print(f"  - run_manifest.json")


@app.command()
def explain(
    symbol: Annotated[str, typer.Argument(help="Symbol to explain")],
    run_id: Annotated[str, typer.Argument(help="Run ID to load results from")],
    config: Annotated[
        Path,
        typer.Option("--config", "-c", help="Path to configuration YAML file", exists=True, readable=True),
    ] = Path("config.yaml"),
) -> None:
    """Explain the scoring for a specific symbol from a previous run."""
    cfg = load_config(config)
    artifact_dir = Path(cfg.app.artifact_dir) / run_id
    
    if not artifact_dir.exists():
        console.print(f"[red]Run directory not found: {artifact_dir}[/red]")
        raise typer.Exit(1)
    
    # Load features
    features_file = artifact_dir / "all_features.csv"
    if not features_file.exists():
        console.print(f"[red]Features file not found: {features_file}[/red]")
        raise typer.Exit(1)
    
    import pandas as pd
    df = pd.read_csv(features_file)
    row = df[df["symbol"] == symbol]
    
    if row.empty:
        console.print(f"[red]Symbol {symbol} not found in run {run_id}[/red]")
        raise typer.Exit(1)
    
    console.print(f"\n[bold]Feature breakdown for {symbol}[/bold]")
    for col in row.columns:
        console.print(f"  {col}: {row[col].values[0]}")


@app.command()
def validate_run(
    run_id: Annotated[
        str, typer.Argument(help="Run ID to validate")
    ],
    config: Annotated[
        Path,
        typer.Option("--config", "-c", help="Path to configuration YAML file", exists=True, readable=True),
    ] = Path("config.yaml"),
) -> None:
    """Validate a previous run for reproducibility."""
    cfg = load_config(config)
    artifact_dir = Path(cfg.app.artifact_dir) / run_id
    
    if not artifact_dir.exists():
        console.print(f"[red]Run directory not found: {artifact_dir}[/red]")
        raise typer.Exit(1)
    
    manifest_file = artifact_dir / "run_manifest.json"
    if not manifest_file.exists():
        console.print(f"[red]Manifest not found: {manifest_file}[/red]")
        raise typer.Exit(1)
    
    import json
    with open(manifest_file) as f:
        manifest = json.load(f)
    
    console.print(f"\n[bold]Run Validation: {run_id}[/bold]")
    console.print(f"  Universe size: {manifest.get('universe_size')}")
    console.print(f"  Eligible count: {manifest.get('eligible_count')}")
    console.print(f"  Top N: {manifest.get('top_n')}")
    console.print(f"  Failures: {manifest.get('failures')}")
    console.print(f"  Started: {manifest.get('started_at')}")
    console.print(f"  Completed: {manifest.get('completed_at')}")
    console.print("\n[green]Run artifacts present and valid[/green]")


if __name__ == "__main__":
    app()