"""Alert service layer."""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional, List
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
        triggers = self.store.get_triggers(alert_id=alert_id, unacknowledged_only=True)
        count = 0
        for trigger in triggers:
            if self.store.acknowledge_trigger(trigger.id):
                count += 1
        return count

    # Alert Testing

    def test_alert(self, request: AlertTestRequest) -> AlertTestResponse:
        """Test an alert against current data (placeholder implementation)."""
        alert = self.store.get(request.alert_id)
        if not alert:
            return AlertTestResponse(
                would_trigger=False,
                symbols_checked=[],
                current_values={},
                message=f"Alert {request.alert_id} not found",
            )

        # This is a placeholder - in a real implementation, you would:
        # 1. Fetch current market data for the alert's symbols
        # 2. Evaluate the alert condition against current values
        # 3. Return whether it would trigger

        # For now, return a mock response
        symbols_checked = alert.symbols if alert.symbols else ["AAPL", "MSFT", "GOOGL"]
        return AlertTestResponse(
            would_trigger=False,
            symbols_checked=symbols_checked,
            current_values={sym: {"price": 150.0, "change_pct": 0.5} for sym in symbols_checked},
            message="Alert test completed (mock implementation)",
        )

    # Alert Evaluation (to be called by scheduler)

    def evaluate_alerts(self, current_data: dict) -> List[AlertTrigger]:
        """
        Evaluate all active alerts against current market data.
        
        Args:
            current_data: Dict with symbol -> {price, change_pct, volume, etc.}
            
        Returns:
            List of triggered alerts
        """
        active_alerts = self.store.get_all(active_only=True)
        triggered = []

        for alert in active_alerts:
            if not alert.is_active:
                continue

            # Check cooldown
            if alert.last_triggered:
                cooldown_end = alert.last_triggered + timedelta(minutes=alert.cooldown_minutes)
                if datetime.now() < cooldown_end:
                    continue

            # Evaluate for each symbol
            for symbol in alert.symbols:
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
        if threshold is None:
            return None

        triggered = False
        condition = AlertCondition(alert.condition)

        if condition == AlertCondition.ABOVE and value > threshold:
            triggered = True
        elif condition == AlertCondition.BELOW and value < threshold:
            triggered = True
        elif condition == AlertCondition.EQUALS and abs(value - threshold) < 0.001:
            triggered = True
        # For CROSSES_ABOVE/BELOW we'd need previous value

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
            metadata={"condition": alert.condition, "alert_name": alert.name},
        )

        return trigger