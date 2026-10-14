"""Watchlist storage using SQLite."""
from __future__ import annotations

import json
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Any

from trading_copilot.watchlists.models import (
    Watchlist,
    WatchlistCreate,
    WatchlistUpdate,
    WatchlistItem,
    WatchlistItemCreate,
    WatchlistItemUpdate,
    WatchlistWithItems,
    WatchlistSortOrder,
)


class WatchlistStore:
    """SQLite-backed watchlist store."""

    def __init__(self, db_path: str | Path):
        self.db_path = str(db_path)
        self._init_db()

    def _init_db(self) -> None:
        """Initialize database tables."""
        with self._conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS watchlists (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    description TEXT,
                    sort_order TEXT NOT NULL DEFAULT 'manual',
                    is_default INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS watchlist_items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    watchlist_id TEXT NOT NULL,
                    symbol TEXT NOT NULL,
                    notes TEXT,
                    sort_index INTEGER NOT NULL DEFAULT 0,
                    added_at TEXT NOT NULL,
                    FOREIGN KEY (watchlist_id) REFERENCES watchlists (id) ON DELETE CASCADE,
                    UNIQUE (watchlist_id, symbol)
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_watchlist_items_watchlist_id 
                ON watchlist_items (watchlist_id)
            """)
            conn.commit()

    @contextmanager
    def _conn(self):
        """Get database connection."""
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA foreign_keys = ON")
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    def _row_to_watchlist(self, row: sqlite3.Row, include_items: bool = False) -> Watchlist | WatchlistWithItems:
        """Convert database row to Watchlist model."""
        symbols = [item.symbol for item in self.get_items(row["id"])]

        watchlist = Watchlist(
            id=row["id"],
            name=row["name"],
            description=row["description"],
            sort_order=WatchlistSortOrder(row["sort_order"]),
            is_default=bool(row["is_default"]),
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
            item_count=row["item_count"] if "item_count" in row.keys() else 0,
            symbols=symbols,
        )

        if include_items:
            items = self.get_items(watchlist.id)
            return WatchlistWithItems(
                **watchlist.model_dump(),
                items=items,
            )

        return watchlist

    def create(self, watchlist: WatchlistCreate) -> Watchlist:
        """Create a new watchlist."""
        watchlist_id = str(uuid.uuid4())
        now = datetime.now().isoformat()

        # If this is set as default, unset other defaults
        with self._conn() as conn:
            if watchlist.is_default:
                conn.execute("UPDATE watchlists SET is_default = 0 WHERE is_default = 1")
            conn.execute("""
                INSERT INTO watchlists (id, name, description, sort_order, is_default, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                watchlist_id,
                watchlist.name,
                watchlist.description,
                watchlist.sort_order.value,
                1 if watchlist.is_default else 0,
                now,
                now,
            ))
            conn.commit()

        return self.get(watchlist_id) or Watchlist(
            id=watchlist_id,
            name=watchlist.name,
            description=watchlist.description,
            sort_order=watchlist.sort_order,
            is_default=watchlist.is_default,
            created_at=datetime.fromisoformat(now),
            updated_at=datetime.fromisoformat(now),
            item_count=0,
            symbols=[],
        )

    def get(self, watchlist_id: str) -> Optional[Watchlist]:
        """Get a watchlist by ID."""
        with self._conn() as conn:
            row = conn.execute("""
                SELECT w.*, 
                    (SELECT COUNT(*) FROM watchlist_items wi WHERE wi.watchlist_id = w.id) as item_count,
                    (SELECT GROUP_CONCAT(wi.symbol) FROM watchlist_items wi WHERE wi.watchlist_id = w.id) as symbols
                FROM watchlists w
                WHERE w.id = ?
            """, (watchlist_id,)).fetchone()

            if not row:
                return None

            return self._row_to_watchlist(row)

    def get_all(self) -> List[Watchlist]:
        """Get all watchlists."""
        with self._conn() as conn:
            rows = conn.execute("""
                SELECT w.*, 
                    (SELECT COUNT(*) FROM watchlist_items wi WHERE wi.watchlist_id = w.id) as item_count,
                    (SELECT GROUP_CONCAT(wi.symbol) FROM watchlist_items wi WHERE wi.watchlist_id = w.id) as symbols
                FROM watchlists w
                ORDER BY w.created_at DESC
            """).fetchall()

            return [self._row_to_watchlist(row) for row in rows]

    def get_default(self) -> Optional[Watchlist]:
        """Get the default watchlist."""
        with self._conn() as conn:
            row = conn.execute("""
                SELECT w.*, 
                    (SELECT COUNT(*) FROM watchlist_items wi WHERE wi.watchlist_id = w.id) as item_count,
                    (SELECT GROUP_CONCAT(wi.symbol) FROM watchlist_items wi WHERE wi.watchlist_id = w.id) as symbols
                FROM watchlists w
                WHERE w.is_default = 1
                LIMIT 1
            """).fetchone()

            if not row:
                return None

            return self._row_to_watchlist(row)

    def update(self, watchlist_id: str, update: WatchlistUpdate) -> Optional[Watchlist]:
        """Update a watchlist."""
        # If setting as default, unset other defaults
        fields = []
        values = []

        if update.name is not None:
            fields.append("name = ?")
            values.append(update.name)
        if "description" in update.model_fields_set:
            fields.append("description = ?")
            values.append(update.description)
        if update.sort_order is not None:
            fields.append("sort_order = ?")
            values.append(update.sort_order.value)
        if update.is_default is not None:
            fields.append("is_default = ?")
            values.append(1 if update.is_default else 0)

        if not fields:
            return self.get(watchlist_id)

        fields.append("updated_at = ?")
        values.append(datetime.now().isoformat())
        values.append(watchlist_id)

        with self._conn() as conn:
            if not conn.execute("SELECT 1 FROM watchlists WHERE id = ?", (watchlist_id,)).fetchone():
                return None
            if update.is_default is True:
                conn.execute("UPDATE watchlists SET is_default = 0 WHERE is_default = 1 AND id != ?", (watchlist_id,))
            conn.execute(f"UPDATE watchlists SET {', '.join(fields)} WHERE id = ?", values)
            conn.commit()

        return self.get(watchlist_id)

    def delete(self, watchlist_id: str) -> bool:
        """Delete a watchlist."""
        with self._conn() as conn:
            cursor = conn.execute("DELETE FROM watchlists WHERE id = ?", (watchlist_id,))
            conn.commit()
            return cursor.rowcount > 0

    # Watchlist Items

    def get_items(self, watchlist_id: str) -> List[WatchlistItem]:
        """Get all items in a watchlist."""
        with self._conn() as conn:
            rows = conn.execute("""
                SELECT symbol, notes, sort_index, added_at
                FROM watchlist_items
                WHERE watchlist_id = ?
                ORDER BY sort_index, added_at
            """, (watchlist_id,)).fetchall()

            return [
                WatchlistItem(
                    symbol=row["symbol"],
                    notes=row["notes"],
                    sort_index=row["sort_index"],
                    added_at=datetime.fromisoformat(row["added_at"]),
                )
                for row in rows
            ]

    def add_item(self, watchlist_id: str, item: WatchlistItemCreate) -> WatchlistItem:
        """Add an item to a watchlist."""
        now = datetime.now().isoformat()

        # Get next sort index
        with self._conn() as conn:
            if not conn.execute("SELECT 1 FROM watchlists WHERE id = ?", (watchlist_id,)).fetchone():
                raise KeyError("Watchlist not found")
            if conn.execute("SELECT 1 FROM watchlist_items WHERE watchlist_id = ? AND symbol = ?", (watchlist_id, item.symbol)).fetchone():
                raise ValueError("Symbol already in watchlist")
            max_index = conn.execute("""
                SELECT COALESCE(MAX(sort_index), -1) + 1 FROM watchlist_items WHERE watchlist_id = ?
            """, (watchlist_id,)).fetchone()[0]

            conn.execute("""
                INSERT INTO watchlist_items (watchlist_id, symbol, notes, sort_index, added_at)
                VALUES (?, ?, ?, ?, ?)
            """, (watchlist_id, item.symbol.upper(), item.notes, max_index, now))
            conn.execute("UPDATE watchlists SET updated_at = ? WHERE id = ?", (now, watchlist_id))
            conn.commit()

        return WatchlistItem(
            symbol=item.symbol.upper(),
            notes=item.notes,
            sort_index=max_index,
            added_at=datetime.fromisoformat(now),
        )

    def update_item(self, watchlist_id: str, symbol: str, update: WatchlistItemUpdate) -> Optional[WatchlistItem]:
        """Update a watchlist item."""
        fields = []
        values = []

        if "notes" in update.model_fields_set:
            fields.append("notes = ?")
            values.append(update.notes)
        if update.sort_index is not None:
            fields.append("sort_index = ?")
            values.append(update.sort_index)

        if not fields:
            return self.get_item(watchlist_id, symbol)

        values.extend([watchlist_id, symbol.upper()])

        with self._conn() as conn:
            conn.execute(f"UPDATE watchlist_items SET {', '.join(fields)} WHERE watchlist_id = ? AND symbol = ?", values)
            conn.execute("UPDATE watchlists SET updated_at = ? WHERE id = ?", (datetime.now().isoformat(), watchlist_id))
            conn.commit()

        return self.get_item(watchlist_id, symbol)

    def get_item(self, watchlist_id: str, symbol: str) -> Optional[WatchlistItem]:
        """Get a specific watchlist item."""
        with self._conn() as conn:
            row = conn.execute("""
                SELECT symbol, notes, sort_index, added_at
                FROM watchlist_items
                WHERE watchlist_id = ? AND symbol = ?
            """, (watchlist_id, symbol.upper())).fetchone()

            if not row:
                return None

            return WatchlistItem(
                symbol=row["symbol"],
                notes=row["notes"],
                sort_index=row["sort_index"],
                added_at=datetime.fromisoformat(row["added_at"]),
            )

    def remove_item(self, watchlist_id: str, symbol: str) -> bool:
        """Remove an item from a watchlist."""
        with self._conn() as conn:
            cursor = conn.execute("""
                DELETE FROM watchlist_items WHERE watchlist_id = ? AND symbol = ?
            """, (watchlist_id, symbol.upper()))
            conn.execute("UPDATE watchlists SET updated_at = ? WHERE id = ?", (datetime.now().isoformat(), watchlist_id))
            conn.commit()
            return cursor.rowcount > 0

    def reorder_items(self, watchlist_id: str, symbols: List[str]) -> None:
        """Reorder watchlist items."""
        with self._conn() as conn:
            if not conn.execute("SELECT 1 FROM watchlists WHERE id = ?", (watchlist_id,)).fetchone():
                raise KeyError("Watchlist not found")
            existing = {row[0] for row in conn.execute("SELECT symbol FROM watchlist_items WHERE watchlist_id = ?", (watchlist_id,))}
            if len(symbols) != len(set(symbols)) or set(symbols) != existing:
                raise ValueError("Reorder must contain every watchlist symbol exactly once")
            for index, symbol in enumerate(symbols):
                conn.execute("""
                    UPDATE watchlist_items SET sort_index = ? WHERE watchlist_id = ? AND symbol = ?
                """, (index, watchlist_id, symbol.upper()))
            conn.execute("UPDATE watchlists SET updated_at = ? WHERE id = ?", (datetime.now().isoformat(), watchlist_id))
            conn.commit()

    def get_watchlist_with_items(self, watchlist_id: str) -> Optional[WatchlistWithItems]:
        """Get a watchlist with all its items."""
        watchlist = self.get(watchlist_id)
        if not watchlist:
            return None

        items = self.get_items(watchlist_id)
        return WatchlistWithItems(
            **watchlist.model_dump(),
            items=items,
        )
