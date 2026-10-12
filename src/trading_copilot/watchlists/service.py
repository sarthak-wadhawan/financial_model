"""Watchlist service layer."""
from __future__ import annotations

from typing import Optional, List

from trading_copilot.watchlists.store import WatchlistStore
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


class WatchlistService:
    """High-level watchlist operations."""

    def __init__(self, store: WatchlistStore):
        self.store = store

    # Watchlist CRUD

    def create_watchlist(self, watchlist: WatchlistCreate) -> Watchlist:
        """Create a new watchlist."""
        return self.store.create(watchlist)

    def get_watchlist(self, watchlist_id: str) -> Optional[Watchlist]:
        """Get a watchlist by ID."""
        return self.store.get(watchlist_id)

    def get_watchlist_with_items(self, watchlist_id: str) -> Optional[WatchlistWithItems]:
        """Get a watchlist with all its items."""
        return self.store.get_watchlist_with_items(watchlist_id)

    def get_all_watchlists(self) -> List[Watchlist]:
        """Get all watchlists."""
        return self.store.get_all()

    def get_default_watchlist(self) -> Optional[Watchlist]:
        """Get the default watchlist."""
        return self.store.get_default()

    def update_watchlist(self, watchlist_id: str, update: WatchlistUpdate) -> Optional[Watchlist]:
        """Update a watchlist."""
        return self.store.update(watchlist_id, update)

    def delete_watchlist(self, watchlist_id: str) -> bool:
        """Delete a watchlist."""
        return self.store.delete(watchlist_id)

    def set_default_watchlist(self, watchlist_id: str) -> Optional[Watchlist]:
        """Set a watchlist as the default."""
        return self.store.update(watchlist_id, WatchlistUpdate(is_default=True))

    # Watchlist Items

    def get_items(self, watchlist_id: str) -> List[WatchlistItem]:
        """Get all items in a watchlist."""
        return self.store.get_items(watchlist_id)

    def add_item(self, watchlist_id: str, item: WatchlistItemCreate) -> WatchlistItem:
        """Add a symbol to a watchlist."""
        # Normalize symbol
        item.symbol = item.symbol.upper().strip()
        return self.store.add_item(watchlist_id, item)

    def update_item(self, watchlist_id: str, symbol: str, update: WatchlistItemUpdate) -> Optional[WatchlistItem]:
        """Update a watchlist item."""
        return self.store.update_item(watchlist_id, symbol.upper(), update)

    def get_item(self, watchlist_id: str, symbol: str) -> Optional[WatchlistItem]:
        """Get a specific watchlist item."""
        return self.store.get_item(watchlist_id, symbol.upper())

    def remove_item(self, watchlist_id: str, symbol: str) -> bool:
        """Remove a symbol from a watchlist."""
        return self.store.remove_item(watchlist_id, symbol.upper())

    def reorder_items(self, watchlist_id: str, symbols: List[str]) -> None:
        """Reorder watchlist items."""
        normalized = [s.upper().strip() for s in symbols]
        self.store.reorder_items(watchlist_id, normalized)

    def get_symbols(self, watchlist_id: str) -> List[str]:
        """Get just the symbols in a watchlist."""
        return [item.symbol for item in self.store.get_items(watchlist_id)]

    def has_symbol(self, watchlist_id: str, symbol: str) -> bool:
        """Check if a symbol is in a watchlist."""
        return self.store.get_item(watchlist_id, symbol.upper()) is not None

    def get_watchlists_for_symbol(self, symbol: str) -> List[Watchlist]:
        """Get all watchlists containing a symbol."""
        all_watchlists = self.store.get_all()
        result = []
        for wl in all_watchlists:
            if self.has_symbol(wl.id, symbol):
                result.append(wl)
        return result