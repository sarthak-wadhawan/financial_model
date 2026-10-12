"""Alert models."""
from __future__ import annotations

from datetime import datetime
from typing import Optional, List, Any
from pydantic import BaseModel, Field
from enum import Enum


class AlertType(str, Enum):
    """Types of alerts."""
    PRICE = "price"
    PRICE_CHANGE_PCT = "price_change_pct"
    VOLUME = "volume"
    EARNINGS = "earnings"
    EARNINGS_SURPRISE = "earnings_surprise"
    GUIDANCE_CHANGE = "guidance_change"
    FILING = "filing"
    INSIDER = "insider"
    LEADERSHIP = "leadership"
    NEWS = "news"
    MACRO_EVENT = "macro_event"
    QUANT_SCORE = "quant_score"
    CUSTOM = "custom"


class AlertCondition(str, Enum):
    """Alert condition operators."""
    ABOVE = "above"
    BELOW = "below"
    EQUALS = "equals"
    CROSSES_ABOVE = "crosses_above"
    CROSSES_BELOW = "crosses_below"
    CHANGES = "changes"


class AlertSeverity(str, Enum):
    """Alert severity levels."""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class AlertChannel(str, Enum):
    """Alert delivery channels."""
    IN_APP = "in_app"
    EMAIL = "email"
    WEBHOOK = "webhook"


class AlertBase(BaseModel):
    """Base alert configuration."""
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    alert_type: AlertType
    symbols: List[str] = Field(default_factory=list)
    condition: AlertCondition
    threshold: Optional[float] = None
    threshold_secondary: Optional[float] = None
    severity: AlertSeverity = AlertSeverity.INFO
    channels: List[AlertChannel] = Field(default_factory=lambda: [AlertChannel.IN_APP])
    is_active: bool = True
    cooldown_minutes: int = Field(default=60, ge=1)
    metadata: dict = Field(default_factory=dict)


class AlertCreate(AlertBase):
    """Alert creation model."""
    pass


class AlertUpdate(BaseModel):
    """Alert update model."""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    symbols: Optional[List[str]] = None
    condition: Optional[str] = None
    threshold: Optional[float] = None
    threshold_secondary: Optional[float] = None
    severity: Optional[str] = None
    channels: Optional[List[str]] = None
    is_active: Optional[bool] = None
    cooldown_minutes: Optional[int] = Field(None, ge=1)
    metadata: Optional[dict] = None


class Alert(AlertBase):
    """Complete alert model."""
    id: str
    user_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    last_triggered: Optional[datetime] = None
    trigger_count: int = 0


class AlertTrigger(BaseModel):
    """Alert trigger event."""
    id: str
    alert_id: str
    symbol: str
    alert_type: str
    message: str
    value: Optional[float] = None
    threshold: Optional[float] = None
    severity: str
    triggered_at: datetime
    acknowledged: bool = False
    acknowledged_at: Optional[datetime] = None
    metadata: dict = Field(default_factory=dict)


class AlertTestRequest(BaseModel):
    """Request to test an alert against current data."""
    alert_id: str


class AlertTestResponse(BaseModel):
    """Response from alert test."""
    would_trigger: bool
    symbols_checked: List[str]
    current_values: dict
    message: Optional[str] = None