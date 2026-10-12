"""Configuration loading and validation."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppConfig(BaseModel):
    artifact_dir: str = "artifacts/runs"
    timezone: str = "America/New_York"


class UniverseConfig(BaseModel):
    mode: str = "fixed_or_provider"
    include_etfs: bool = False
    symbols_file: str | None = None


class MarketConfig(BaseModel):
    provider: str = "alpaca"
    benchmark: str = "SPY"
    history_days: int = 300


class EligibilityConfig(BaseModel):
    min_price: float = 5.0
    min_avg_dollar_volume_20d: float = 50_000_000.0
    min_history_days: int = 220


class ScanConfig(BaseModel):
    top_n: int = 20
    final_n: int = 3

    @field_validator("final_n")
    @classmethod
    def final_n_le_top_n(cls, v: int, info: Any) -> int:
        if "top_n" in info.data and v > info.data["top_n"]:
            raise ValueError("final_n must be <= top_n")
        return v


class SourcesConfig(BaseModel):
    news_lookback_days: int = 7
    filings_lookback_days: int = 45
    max_news_per_symbol: int = 8
    max_filings_per_symbol: int = 4


class LLMConfig(BaseModel):
    enabled: bool = True
    base_url_env: str = "LLM_BASE_URL"
    api_key_env: str = "LLM_API_KEY"
    model_env: str = "LLM_MODEL"
    max_concurrency: int = 3
    timeout_seconds: int = 90
    retry_count: int = 1


class QuantWeights(BaseModel):
    momentum_weight: float = 0.40
    trend_weight: float = 0.25
    liquidity_weight: float = 0.15
    volume_weight: float = 0.10
    volatility_weight: float = 0.10

    @model_validator(mode="after")
    def weights_sum_to_one(self) -> QuantWeights:
        total = (
            self.momentum_weight
            + self.trend_weight
            + self.liquidity_weight
            + self.volume_weight
            + self.volatility_weight
        )
        if abs(total - 1.0) > 1e-6:
            raise ValueError(f"Quant weights must sum to 1.0, got {total}")
        return self


class FinalWeights(BaseModel):
    quant_weight: float = 0.80
    catalyst_weight: float = 0.20

    @model_validator(mode="after")
    def weights_sum_to_one(self) -> FinalWeights:
        total = self.quant_weight + self.catalyst_weight
        if abs(total - 1.0) > 1e-6:
            raise ValueError(f"Final weights must sum to 1.0, got {total}")
        return self


class ScoringConfig(BaseModel):
    quant: QuantWeights = Field(default_factory=QuantWeights)
    final: FinalWeights = Field(default_factory=FinalWeights)


class RiskConfig(BaseModel):
    exclude_earnings_within_days: int = 0
    fail_closed_on_invalid_market_data: bool = True
    invalid_ai_fallback_catalyst_score: float = 50.0


class OptionsConfig(BaseModel):
    enabled: bool = False


class RuntimeConfig(BaseModel):
    cache_enabled: bool = True
    provider_max_concurrency: int = 5


class EventsConfig(BaseModel):
    db_path: str = "data/events.db"


class Config(BaseModel):
    app: AppConfig = Field(default_factory=AppConfig)
    universe: UniverseConfig = Field(default_factory=UniverseConfig)
    market: MarketConfig = Field(default_factory=MarketConfig)
    eligibility: EligibilityConfig = Field(default_factory=EligibilityConfig)
    scan: ScanConfig = Field(default_factory=ScanConfig)
    sources: SourcesConfig = Field(default_factory=SourcesConfig)
    llm: LLMConfig = Field(default_factory=LLMConfig)
    scoring: ScoringConfig = Field(default_factory=ScoringConfig)
    risk: RiskConfig = Field(default_factory=RiskConfig)
    options: OptionsConfig = Field(default_factory=OptionsConfig)
    runtime: RuntimeConfig = Field(default_factory=RuntimeConfig)
    events: EventsConfig = Field(default_factory=EventsConfig)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Canonical Alpaca credential names (preferred)
    apca_api_key_id: str | None = None
    apca_api_secret_key: str | None = None
    # Legacy Alpaca credential names (deprecated, for backwards compatibility)
    alpaca_api_key: str | None = None
    alpaca_api_secret: str | None = None
    llm_base_url: str | None = None
    llm_api_key: str | None = None
    llm_model: str | None = None
    sec_user_agent: str | None = None


def load_config(config_path: str | Path) -> Config:
    """Load configuration from YAML file."""
    with open(config_path, "r") as f:
        data = yaml.safe_load(f)
    return Config(**data)


def load_settings() -> Settings:
    """Load environment-based settings."""
    return Settings()


def get_llm_config(settings: Settings, config: Config) -> dict[str, str | None]:
    """Resolve LLM configuration from environment variables."""
    return {
        "base_url": settings.llm_base_url or os.environ.get(config.llm.base_url_env),
        "api_key": settings.llm_api_key or os.environ.get(config.llm.api_key_env),
        "model": settings.llm_model or os.environ.get(config.llm.model_env),
    }


def get_alpaca_config(settings: Settings) -> dict[str, str | None]:
    """Resolve Alpaca configuration from environment variables.

    Priority order (first non-None wins):
    1. Canonical: APCA_API_KEY_ID / APCA_API_SECRET_KEY (via settings or os.environ)
    2. Legacy: ALPACA_API_KEY / ALPACA_API_SECRET (via settings or os.environ)
    """
    return {
        "api_key": (
            settings.apca_api_key_id
            or os.environ.get("APCA_API_KEY_ID")
            or settings.alpaca_api_key
            or os.environ.get("ALPACA_API_KEY")
        ),
        "api_secret": (
            settings.apca_api_secret_key
            or os.environ.get("APCA_API_SECRET_KEY")
            or settings.alpaca_api_secret
            or os.environ.get("ALPACA_API_SECRET")
        ),
    }