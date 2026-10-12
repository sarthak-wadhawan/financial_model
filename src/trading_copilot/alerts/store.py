"""Alert storage using SQLite."""
from __future__ import annotations

import json
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Any

from trading_copilot.alerts.models import (
    Alert,
    AlertCreate,
    AlertUpdate,
    AlertTrigger,
    AlertType,
    AlertSeverity,
    AlertChannel,
    AlertCondition,
)


class AlertStore:
    """SQLite-backed alert store."""

    def __init__(self, db_path: str | Path):
        self.db_path = str(db_path)
        self._init_db()

    def _init_db(self) -> None:
        """Initialize database tables."""
        with self._conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS alerts (
                    id TEXT PRIMARY KEY,
                    user_id TEXT,
                    name TEXT NOT NULL,
                    description TEXT,
                    alert_type TEXT NOT NULL,
                    symbols TEXT NOT NULL DEFAULT '[]',
                    condition TEXT NOT NULL,
                    threshold REAL,
                    threshold_secondary REAL,
                    severity TEXT NOT NULL DEFAULT 'info',
                    channels TEXT NOT NULL DEFAULT '["in_app"]',
                    is_active INTEGER NOT NULL DEFAULT 1,
                    cooldown_minutes INTEGER NOT NULL DEFAULT 60,
                    metadata TEXT NOT NULL DEFAULT '{}',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    last_triggered TEXT,
                    trigger_count INTEGER NOT NULL DEFAULT 0
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS alert_triggers (
                    id TEXT PRIMARY KEY,
                    alert_id TEXT NOT NULL,
                    symbol TEXT NOT NULL,
                    alert_type TEXT NOT NULL,
                    message TEXT NOT NULL,
                    value REAL,
                    threshold REAL,
                    severity TEXT NOT NULL,
                    triggered_at TEXT NOT NULL,
                    acknowledged INTEGER NOT NULL DEFAULT 0,
                    acknowledged_at TEXT,
                    metadata TEXT NOT NULL DEFAULT '{}',
                    FOREIGN KEY (alert_id) REFERENCES alerts (id) ON DELETE CASCADE
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_alert_triggers_alert_id 
                ON alert_triggers (alert_id)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_alert_triggers_triggered_at 
                ON alert_triggers (triggered_at)
            """)
            conn.commit()

    @contextmanager
    def _conn(self):
        """Get database connection."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    def _row_to_alert(self, row: sqlite3.Row) -> Alert:
        """Convert database row to Alert model."""
        return Alert(
            id=row["id"],
            user_id=row["user_id"],
            name=row["name"],
            description=row["description"],
            alert_type=row["alert_type"],
            symbols=json.loads(row["symbols"]) if row["symbols"] else [],
            condition=row["condition"],
            threshold=row["threshold"],
            threshold_secondary=row["threshold_secondary"],
            severity=row["severity"],
            channels=json.loads(row["channels"]) if row["channels"] else ["in_app"],
            is_active=bool(row["is_active"]),
            cooldown_minutes=row["cooldown_minutes"],
            metadata=json.loads(row["metadata"]) if row["metadata"] else {},
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
            last_triggered=datetime.fromisoformat(row["last_triggered"]) if row["last_triggered"] else None,
            trigger_count=row["trigger_count"],
        )

    def _row_to_trigger(self, row: sqlite3.Row) -> AlertTrigger:
        """Convert database row to AlertTrigger model."""
        return AlertTrigger(
            id=row["id"],
            alert_id=row["alert_id"],
            symbol=row["symbol"],
            alert_type=row["alert_type"],
            message=row["message"],
            value=row["value"],
            threshold=row["threshold"],
            severity=row["severity"],
            triggered_at=datetime.fromisoformat(row["triggered_at"]),
            acknowledged=bool(row["acknowledged"]),
            acknowledged_at=datetime.fromisoformat(row["acknowledged_at"]) if row["acknowledged_at"] else None,
            metadata=json.loads(row["metadata"]) if row["metadata"] else {},
        )

    def create(self, alert: AlertCreate, user_id: Optional[str] = None) -> Alert:
        """Create a new alert."""
        alert_id = str(uuid.uuid4())
        now = datetime.now().isoformat()

        with self._conn() as conn:
            conn.execute("""
                INSERT INTO alerts (
                    id, user_id, name, description, alert_type, symbols, condition,
                    threshold, threshold_secondary, severity, channels, is_active,
                    cooldown_minutes, metadata, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                alert_id,
                user_id,
                alert.name,
                alert.description,
                alert.alert_type.value,
                json.dumps([s.upper() for s in alert.symbols]),
                alert.condition.value,
                alert.threshold,
                alert.threshold_secondary,
                alert.severity.value,
                json.dumps([c.value for c in alert.channels]),
                1 if alert.is_active else 0,
                alert.cooldown_minutes,
                json.dumps(alert.metadata),
                now,
                now,
            ))
            conn.commit()

        return self.get(alert_id) or Alert(
            id=alert_id,
            user_id=user_id,
            **alert.model_dump(),
            created_at=datetime.fromisoformat(now),
            updated_at=datetime.fromisoformat(now),
        )

    def get(self, alert_id: str) -> Optional[Alert]:
        """Get an alert by ID."""
        with self._conn() as conn:
            row = conn.execute("SELECT * FROM alerts WHERE id = ?", (alert_id,)).fetchone()
            if not row:
                return None
            return self._row_to_alert(row)

    def get_all(self, user_id: Optional[str] = None, active_only: bool = False) -> List[Alert]:
        """Get all alerts."""
        with self._conn() as conn:
            query = "SELECT * FROM alerts WHERE 1=1"
            params = []

            if user_id:
                query += " AND user_id = ?"
                params.append(user_id)
            if active_only:
                query += " AND is_active = 1"

            query += " ORDER BY created_at DESC"

            rows = conn.execute(query, params).fetchall()
            return [self._row_to_alert(row) for row in rows]

    def update(self, alert_id: str, update: AlertUpdate) -> Optional[Alert]:
        """Update an alert."""
        fields = []
        values = []

        field_mapping = {
            "name": "name",
            "description": "description",
            "symbols": "symbols",
            "condition": "condition",
            "threshold": "threshold",
            "threshold_secondary": "threshold_secondary",
            "severity": "severity",
            "channels": "channels",
            "is_active": "is_active",
            "cooldown_minutes": "cooldown_minutes",
            "metadata": "metadata",
        }

        for key, db_field in field_mapping.items():
            val = getattr(update, key, None)
            if val is not None:
                if db_field in ["symbols", "channels"]:
                    val = json.dumps([v.upper() for v in val]) if isinstance(val, list) else json.dumps(val)
                elif db_field == "metadata":
                    val = json.dumps(val)
                fields.append(f"{db_field} = ?")
                values.append(val)

        if not fields:
            return self.get(alert_id)

        fields.append("updated_at = ?")
        values.append(datetime.now().isoformat())
        values.append(alert_id)

        with self._conn() as conn:
            conn.execute(f"UPDATE alerts SET {', '.join(fields)} WHERE id = ?", values)
            conn.commit()

        return self.get(alert_id)

    def delete(self, alert_id: str) -> bool:
        """Delete an alert."""
        with self._conn() as conn:
            cursor = conn.execute("DELETE FROM alerts WHERE id = ?", (alert_id,))
            conn.commit()
            return cursor.rowcount > 0

    def update_trigger_info(self, alert_id: str) -> None:
        """Update last triggered time and count."""
        now = datetime.now().isoformat()
        with self._conn() as conn:
            conn.execute("""
                UPDATE alerts 
                SET last_triggered = ?, trigger_count = trigger_count + 1, updated_at = ?
                WHERE id = ?
            """, (now, now, alert_id))
            conn.commit()

    # Alert Triggers

    def record_trigger(self, trigger: AlertTrigger) -> AlertTrigger:
        """Record an alert trigger."""
        with self._conn() as conn:
            conn.execute("""
                INSERT INTO alert_triggers (
                    id, alert_id, symbol, alert_type, message, value, threshold,
                    severity, triggered_at, acknowledged, acknowledged_at, metadata
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                trigger.id,
                trigger.alert_id,
                trigger.symbol,
                trigger.alert_type,
                trigger.message,
                trigger.value,
                trigger.threshold,
                trigger.severity,
                trigger.triggered_at.isoformat(),
                1 if trigger.acknowledged else 0,
                trigger.acknowledged_at.isoformat() if trigger.acknowledged_at else None,
                json.dumps(trigger.metadata),
            ))
            conn.commit()

        return trigger

    def get_triggers(
        self,
        alert_id: Optional[str] = None,
        symbol: Optional[str] = None,
        limit: int = 100,
        unacknowledged_only: bool = False,
    ) -> List[AlertTrigger]:
        """Get alert triggers."""
        with self._conn() as conn:
            query = "SELECT * FROM alert_triggers WHERE 1=1"
            params = []

            if alert_id:
                query += " AND alert_id = ?"
                params.append(alert_id)
            if symbol:
                query += " AND symbol = ?"
                params.append(symbol.upper())
            if unacknowledged_only:
                query += " AND acknowledged = 0"

            query += " ORDER BY triggered_at DESC LIMIT ?"
            params.append(limit)

            rows = conn.execute(query, params).fetchall()
            return [self._row_to_trigger(row) for row in rows]

    def acknowledge_trigger(self, trigger_id: str) -> bool:
        """Acknowledge an alert trigger."""
        now = datetime.now().isoformat()
        with self._conn() as conn:
            cursor = conn.execute("""
                UPDATE alert_triggers 
                SET acknowledged = 1, acknowledged_at = ?
                WHERE id = ?
            """, (now, trigger_id))
            conn.commit()
            return cursor.rowcount > 0

    def get_recent_triggers(
        self,
        hours: int = 24,
        limit: int = 50,
    ) -> List[AlertTrigger]:
        """Get recent alert triggers."""
        cutoff = datetime.now() - timedelta(hours=hours)
        with self._conn() as conn:
            rows = conn.execute("""
                SELECT * FROM alert_triggers 
                WHERE triggered_at >= ?
                ORDER BY triggered_at DESC
                LIMIT ?
            """, (cutoff.isoformat(), limit)).fetchall()
            return [self._row_to_trigger(row) for row in rows]