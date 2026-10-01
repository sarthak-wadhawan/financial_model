"""Integration test for the full offline scan pipeline."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def test_cli_help():
    """Test that CLI help works."""
    result = subprocess.run(
        [sys.executable, "-m", "trading_copilot", "--help"],
        capture_output=True,
        text=True,
        cwd=Path(__file__).parent.parent.parent,
    )
    assert result.returncode == 0
    assert "AI Trading Research Copilot" in result.stdout
    assert "scan" in result.stdout
    assert "explain" in result.stdout
    assert "validate-run" in result.stdout


def test_scan_command():
    """Test the scan command with fixture config."""
    config_path = Path(__file__).parent.parent / "fixtures" / "config.yaml"
    
    result = subprocess.run(
        [sys.executable, "-m", "trading_copilot", "scan", "--config", str(config_path)],
        capture_output=True,
        text=True,
        cwd=Path(__file__).parent.parent.parent,
    )
    
    print("STDOUT:", result.stdout)
    print("STDERR:", result.stderr)
    print("Return code:", result.returncode)
    
    assert result.returncode == 0, f"Scan failed: {result.stderr}"
    
    # Check that artifacts were created
    # Find the latest run directory
    artifacts_dir = Path(__file__).parent.parent.parent / "artifacts" / "runs"
    run_dirs = sorted(artifacts_dir.glob("*"), reverse=True)
    assert len(run_dirs) > 0, "No run directory created"
    
    latest_run = run_dirs[0]
    assert (latest_run / "top20.csv").exists(), "top20.csv not created"
    assert (latest_run / "all_features.csv").exists(), "all_features.csv not created"
    assert (latest_run / "run_manifest.json").exists(), "run_manifest.json not created"
    
    # Verify top20.csv has 20 rows (plus header)
    import pandas as pd
    df = pd.read_csv(latest_run / "top20.csv")
    assert len(df) == 20, f"Expected 20 rows, got {len(df)}"
    
    # Verify required columns
    required_cols = ["rank", "symbol", "quant_score", "momentum_score", "trend_score", 
                     "liquidity_score", "volume_score", "volatility_quality_score"]
    for col in required_cols:
        assert col in df.columns, f"Missing column: {col}"
    
    # Verify scores are in bounds
    assert (df["quant_score"] >= 0).all() and (df["quant_score"] <= 100).all()
    
    # Verify ranking is correct
    assert (df["quant_score"].diff().dropna() <= 0).all(), "Scores not in descending order"
    
    print(f"Test passed! Run artifacts in: {latest_run}")


def test_validate_run():
    """Test validate-run command."""
    config_path = Path(__file__).parent.parent / "fixtures" / "config.yaml"
    
    # First run scan
    subprocess.run(
        [sys.executable, "-m", "trading_copilot", "scan", "--config", str(config_path)],
        capture_output=True,
        cwd=Path(__file__).parent.parent.parent,
    )
    
    # Find latest run
    artifacts_dir = Path(__file__).parent.parent.parent / "artifacts" / "runs"
    run_dirs = sorted(artifacts_dir.glob("*"), reverse=True)
    run_id = run_dirs[0].name
    
    # Test validate-run (run_id is now a positional argument)
    result = subprocess.run(
        [sys.executable, "-m", "trading_copilot", "validate-run", run_id, "--config", str(config_path)],
        capture_output=True,
        text=True,
        cwd=Path(__file__).parent.parent.parent,
    )
    
    assert result.returncode == 0, f"validate-run failed: {result.stderr}"
    assert "Run Validation" in result.stdout
    assert run_id in result.stdout


def test_explain_command():
    """Test explain command."""
    config_path = Path(__file__).parent.parent / "fixtures" / "config.yaml"
    
    # First run scan
    subprocess.run(
        [sys.executable, "-m", "trading_copilot", "scan", "--config", str(config_path)],
        capture_output=True,
        cwd=Path(__file__).parent.parent.parent,
    )
    
    # Find latest run
    artifacts_dir = Path(__file__).parent.parent.parent / "artifacts" / "runs"
    run_dirs = sorted(artifacts_dir.glob("*"), reverse=True)
    run_id = run_dirs[0].name
    
    # Get a symbol from top20
    import pandas as pd
    df = pd.read_csv(run_dirs[0] / "top20.csv")
    symbol = df.iloc[0]["symbol"]
    
    # Test explain (run_id is now a positional argument)
    result = subprocess.run(
        [sys.executable, "-m", "trading_copilot", "explain", symbol, run_id, "--config", str(config_path)],
        capture_output=True,
        text=True,
        cwd=Path(__file__).parent.parent.parent,
    )
    
    assert result.returncode == 0, f"explain failed: {result.stderr}"
    assert symbol in result.stdout
    assert "Feature breakdown" in result.stdout


if __name__ == "__main__":
    test_cli_help()
    print("test_cli_help passed")
    
    test_scan_command()
    print("test_scan_command passed")
    
    test_validate_run()
    print("test_validate_run passed")
    
    test_explain_command()
    print("test_explain_command passed")
    
    print("\nAll integration tests passed!")