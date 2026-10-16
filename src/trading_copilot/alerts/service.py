"""Alert service layer."""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional, List
from math import isfinite
import uuid

from trading_copilot.alerts.store import AlertStore
from trading_copilot.alerts.models import (
    Alert,
    AlertCreate,
    AlertUpdate,
    AlertTrigger,
    AlertType,
    AlertSeverity,
    AlertChannel,
    AlertCondition,
    AlertTestRequest,
    AlertTestResponse,
)


class AlertService:
    """High-level alert operations."""

    def __init__(self, store: AlertStore):
        self.store = store

    # Alert CRUD

    def create_alert(self, alert: AlertCreate, user_id: Optional[str] = None) -> Alert:
        """Create a new alert."""
        return self.store.create(alert, user_id)

    def get_alert(self, alert_id: str) -> Optional[Alert]:
        """Get an alert by ID."""
        return self.store.get(alert_id)

    def get_all_alerts(self, user_id: Optional[str] = None, active_only: bool = False) -> List[Alert]:
        """Get all alerts."""
        return self.store.get_all(user_id=user_id, active_only=active_only)

    def update_alert(self, alert_id: str, update: AlertUpdate) -> Optional[Alert]:
        """Update an alert."""
        return self.store.update(alert_id, update)

    def delete_alert(self, alert_id: str) -> bool:
        """Delete an alert."""
        return self.store.delete(alert_id)

    def activate_alert(self, alert_id: str) -> Optional[Alert]:
        """Activate an alert."""
        return self.store.update(alert_id, AlertUpdate(is_active=True))

    def deactivate_alert(self, alert_id: str) -> Optional[Alert]:
        """Deactivate an alert."""
        return self.store.update(alert_id, AlertUpdate(is_active=False))

    # Alert Triggers

    def get_triggers(
        self,
        alert_id: Optional[str] = None,
        symbol: Optional[str] = None,
        limit: int = 100,
        unacknowledged_only: bool = False,
    ) -> List[AlertTrigger]:
        """Get alert triggers."""
        return self.store.get_triggers(
            alert_id=alert_id,
            symbol=symbol,
            limit=limit,
            unacknowledged_only=unacknowledged_only,
        )

    def get_recent_triggers(self, hours: int = 24, limit: int = 50) -> List[AlertTrigger]:
        """Get recent alert triggers."""
        return self.store.get_recent_triggers(hours=hours, limit=limit)

    def acknowledge_trigger(self, trigger_id: str) -> bool:
        """Acknowledge an alert trigger."""
        return self.store.acknowledge_trigger(trigger_id)

    def acknowledge_all_for_alert(self, alert_id: str) -> int:
        """Acknowledge all triggers for an alert."""
        count = 0
        while True:
            triggers = self.store.get_triggers(alert_id=alert_id, unacknowledged_only=True)
            if not triggers:
                break
            for trigger in triggers:
                if self.store.acknowledge_trigger(trigger.id):
                    count += 1
        return count

    # Alert Testing

    def test_alert(self, request: AlertTestRequest, current_data: Optional[dict] = None) -> AlertTestResponse:
        """Side-effect-free evaluation of supplied observations; never fabricate data."""
        alert = self.store.get(request.alert_id)
        if not alert:
            raise KeyError("Alert not found")
        observations = current_data or {}
        symbols = alert.symbols or list(observations)
        available = {s: observations[s] for s in symbols if s in observations and self._has_inputs(alert, observations[s])}
        missing = [s for s in symbols if s not in available]
        matches = any(self._evaluate_condition(alert, s, data) for s, data in available.items())
        complete = bool(symbols) and not missing
        return AlertTestResponse(
            would_trigger=matches if complete else (True if matches else None),
            status="evaluated" if complete else "unavailable",
            unavailable_symbols=missing,
            symbols_checked=list(available),
            current_values=available,
            message=("Dry-run only: condition evaluated; no notification sent or history changed."
                     if complete else "Evaluation unavailable or incomplete: missing observations, prior values, or unsupported alert type. No notification sent."),
        )

    @staticmethod
    def _field(alert: Alert) -> Optional[str]:
        return {AlertType.PRICE: "price", AlertType.PRICE_CHANGE_PCT: "change_pct",
                AlertType.VOLUME: "volume", AlertType.QUANT_SCORE: "quant_score"}.get(alert.alert_type)

    def _has_inputs(self, alert: Alert, data: dict) -> bool:
        field = self._field(alert)
        if not field or not isinstance(data, dict):
            return False
        def numeric(value):
            return isinstance(value, (int, float)) and not isinstance(value, bool) and isfinite(value)
        if not numeric(data.get(field)):
            return False
        if alert.condition != AlertCondition.CHANGES and not numeric(alert.threshold):
            return False
        if alert.condition in (AlertCondition.CROSSES_ABOVE, AlertCondition.CROSSES_BELOW, AlertCondition.CHANGES):
            return numeric(data.get(f"previous_{field}"))
        return True

    # Alert Evaluation (to be called by scheduler)

    def evaluate_alerts(self, current_data: dict, alert_id: Optional[str] = None) -> List[AlertTrigger]:
        """
        Evaluate all active alerts against current market data.
        
        Args:
            current_data: Dict with symbol -> {price, change_pct, volume, etc.}
            
        Returns:
            List of triggered alerts
        """
        active_alerts = ([self.store.get(alert_id)] if alert_id is not None
                         else self.store.get_all(active_only=True))
        triggered = []

        for alert in active_alerts:
            if alert is None or not alert.is_active:
                continue

            # Check cooldown
            if alert.last_triggered:
                cooldown_end = alert.last_triggered + timedelta(minutes=alert.cooldown_minutes)
                if datetime.now() < cooldown_end:
                    continue

            # Evaluate for each symbol
            for symbol in alert.symbols or list(current_data):
                if symbol not in current_data:
                    continue

                data = current_data[symbol]
                trigger = self._evaluate_condition(alert, symbol, data)
                if trigger:
                    self.store.record_trigger(trigger)
                    self.store.update_trigger_info(alert.id)
                    triggered.append(trigger)

        return triggered

    def _evaluate_condition(self, alert: Alert, symbol: str, data: dict) -> Optional[AlertTrigger]:
        """Evaluate a single alert condition against data."""
        if not self._has_inputs(alert, data):
            return None
        value = None

        # Map alert type to data field
        if alert.alert_type == AlertType.PRICE:
            value = data.get("price")
        elif alert.alert_type == AlertType.PRICE_CHANGE_PCT:
            value = data.get("change_pct")
        elif alert.alert_type == AlertType.VOLUME:
            value = data.get("volume")
        elif alert.alert_type == AlertType.QUANT_SCORE:
            value = data.get("quant_score")
        else:
            # For other types, we'd need more sophisticated evaluation
            return None

        if value is None:
            return None

        threshold = alert.threshold
        if threshold is None and alert.condition != AlertCondition.CHANGES:
            return None

        triggered = False
        condition = AlertCondition(alert.condition)

        if condition == AlertCondition.ABOVE and value > threshold:
            triggered = True
        elif condition == AlertCondition.BELOW and value < threshold:
            triggered = True
        elif condition == AlertCondition.EQUALS and abs(value - threshold) < 0.001:
            triggered = True
        elif condition == AlertCondition.CROSSES_ABOVE:
            triggered = data[f"previous_{self._field(alert)}"] <= threshold < value
        elif condition == AlertCondition.CROSSES_BELOW:
            triggered = data[f"previous_{self._field(alert)}"] >= threshold > value
        elif condition == AlertCondition.CHANGES:
            triggered = data[f"previous_{self._field(alert)}"] != value

        if not triggered:
            return None

        # Create trigger
        severity = AlertSeverity(alert.severity)
        trigger = AlertTrigger(
            id=str(uuid.uuid4()),
            alert_id=alert.id,
            symbol=symbol,
            alert_type=alert.alert_type.value,
            message=f"{symbol} {alert.name}: {value:.2f} {condition.value} threshold {threshold}",
            value=value,
            threshold=threshold,
            severity=severity.value,
            triggered_at=datetime.now(),
            metadata={"condition": alert.condition, "alert_name": alert.name,
                      "observation": data, "delivery": "in_app_history_only"},
        )

        return trigger
