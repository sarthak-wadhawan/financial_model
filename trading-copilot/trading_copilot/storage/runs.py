"""Run storage and manifest management."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from trading_copilot.config import Config
from trading_copilot.models import RunManifest


class RunStore:
    """Manage run artifacts and manifests."""

    def __init__(self, base_dir: Path):
        self.base_dir = base_dir
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def create_run(self, config: Config) -> tuple[str, Path]:
        """Create a new run directory and return run_id and path."""
        run_id = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H%M%SZ")
        run_dir = self.base_dir / run_id
        run_dir.mkdir(parents=True, exist_ok=True)
        
        # Save config snapshot
        config_snapshot = run_dir / "config.yaml"
        import yaml
        with open(config_snapshot, "w") as f:
            yaml.safe_dump(config.model_dump(), f)
        
        return run_id, run_dir

    def save_manifest(self, run_dir: Path, manifest: RunManifest) -> None:
        """Save run manifest with config hash."""
        # Compute config hash
        config_file = run_dir / "config.yaml"
        if config_file.exists():
            with open(config_file, "rb") as f:
                config_hash = hashlib.sha256(f.read()).hexdigest()[:16]
            manifest.config_hash = config_hash
        
        manifest.completed_at = datetime.now(timezone.utc)
        
        manifest_file = run_dir / "run_manifest.json"
        with open(manifest_file, "w") as f:
            json.dump(manifest.model_dump(mode="json"), f, indent=2, default=str)

    def load_manifest(self, run_dir: Path) -> RunManifest | None:
        """Load run manifest."""
        manifest_file = run_dir / "run_manifest.json"
        if not manifest_file.exists():
            return None
        
        with open(manifest_file) as f:
            data = json.load(f)
        
        return RunManifest(**data)

    def list_runs(self) -> list[dict[str, Any]]:
        """List all runs with basic info."""
        runs = []
        for run_dir in sorted(self.base_dir.iterdir(), reverse=True):
            if not run_dir.is_dir():
                continue
            
            manifest = self.load_manifest(run_dir)
            if manifest:
                runs.append({
                    "run_id": manifest.run_id,
                    "started_at": manifest.started_at.isoformat() if manifest.started_at else None,
                    "completed_at": manifest.completed_at.isoformat() if manifest.completed_at else None,
                    "universe_size": manifest.universe_size,
                    "eligible_count": manifest.eligible_count,
                    "top_n": manifest.top_n,
                    "failures": manifest.failures,
                })
        
        return runs

    def get_run_dir(self, run_id: str) -> Path | None:
        """Get run directory path by run_id."""
        run_dir = self.base_dir / run_id
        if run_dir.exists():
            return run_dir
        return None