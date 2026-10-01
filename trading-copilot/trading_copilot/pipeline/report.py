"""Report generation for scan results."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import pandas as pd

from trading_copilot.models import FeatureRow, QuantScore, RunManifest


class ReportGenerator:
    """Generate output artifacts from scan results."""

    def __init__(self, artifact_dir: Path):
        self.artifact_dir = artifact_dir
        self.artifact_dir.mkdir(parents=True, exist_ok=True)

    def write_top20(
        self,
        top_candidates: list[QuantScore],
        all_features: list[FeatureRow],
    ) -> None:
        """Write top 20 candidates to CSV."""
        feature_lookup = {f.symbol: f for f in all_features}
        
        rows = []
        for i, qs in enumerate(top_candidates, 1):
            feat = feature_lookup.get(qs.symbol)
            row = {
                "rank": i,
                "symbol": qs.symbol,
                "quant_score": round(qs.quant_score, 2),
                "momentum_score": round(qs.momentum_score, 2),
                "trend_score": round(qs.trend_score, 2),
                "liquidity_score": round(qs.liquidity_score, 2),
                "volume_score": round(qs.volume_score, 2),
                "volatility_quality_score": round(qs.volatility_score, 2),
                "price": round(feat.price, 2) if feat else None,
                "ret_21d": round(feat.ret_21d, 4) if feat else None,
                "ret_63d": round(feat.ret_63d, 4) if feat else None,
                "ret_126d": round(feat.ret_126d, 4) if feat else None,
                "rel_ret_21d": round(feat.rel_ret_21d, 4) if feat else None,
                "rel_ret_63d": round(feat.rel_ret_63d, 4) if feat else None,
                "rel_ret_126d": round(feat.rel_ret_126d, 4) if feat else None,
                "avg_dollar_volume_20d": round(feat.avg_dollar_volume_20d, 0) if feat else None,
                "realized_vol_20d": round(feat.realized_vol_20d, 4) if feat else None,
                "relative_volume_1d": round(feat.relative_volume_1d, 2) if feat else None,
                "as_of": feat.as_of.isoformat() if feat else None,
            }
            rows.append(row)
        
        df = pd.DataFrame(rows)
        df.to_csv(self.artifact_dir / "top20.csv", index=False)

    def write_features(self, feature_rows: list[FeatureRow]) -> None:
        """Write all computed features to CSV."""
        rows = []
        for feat in feature_rows:
            rows.append({
                "symbol": feat.symbol,
                "as_of": feat.as_of.isoformat(),
                "price": feat.price,
                "ret_21d": feat.ret_21d,
                "ret_63d": feat.ret_63d,
                "ret_126d": feat.ret_126d,
                "rel_ret_21d": feat.rel_ret_21d,
                "rel_ret_63d": feat.rel_ret_63d,
                "rel_ret_126d": feat.rel_ret_126d,
                "sma_20": feat.sma_20,
                "sma_50": feat.sma_50,
                "sma_200": feat.sma_200,
                "dist_sma_20_pct": feat.dist_sma_20_pct,
                "dist_sma_50_pct": feat.dist_sma_50_pct,
                "dist_sma_200_pct": feat.dist_sma_200_pct,
                "realized_vol_20d": feat.realized_vol_20d,
                "avg_dollar_volume_20d": feat.avg_dollar_volume_20d,
                "relative_volume_1d": feat.relative_volume_1d,
                "drawdown_from_63d_high": feat.drawdown_from_63d_high,
            })
        
        df = pd.DataFrame(rows)
        df.to_csv(self.artifact_dir / "all_features.csv", index=False)

    def write_manifest(self, manifest: RunManifest) -> None:
        """Write run manifest to JSON."""
        manifest.completed_at = datetime.now(manifest.started_at.tzinfo) if manifest.started_at.tzinfo else datetime.now()
        data = manifest.model_dump(mode="json")
        with open(self.artifact_dir / "run_manifest.json", "w") as f:
            json.dump(data, f, indent=2, default=str)

    def write_errors(self, errors: list[dict]) -> None:
        """Write error log to JSONL."""
        with open(self.artifact_dir / "errors.jsonl", "w") as f:
            for err in errors:
                f.write(json.dumps(err) + "\n")