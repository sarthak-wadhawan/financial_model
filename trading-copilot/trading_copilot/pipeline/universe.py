"""Universe provider implementations."""

from __future__ import annotations

from typing import Protocol

from trading_copilot.models import SymbolInfo


class UniverseProvider(Protocol):
    """Protocol for universe providers."""

    def get_symbols(self) -> list[SymbolInfo]:
        ...


class MockUniverseProvider:
    """Mock universe provider for offline testing with a fixed symbol list."""

    # A diverse set of liquid US stocks for testing
    DEFAULT_SYMBOLS = [
        "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA", "AVGO",
        "JPM", "V", "WMT", "MA", "UNH", "HD", "PG", "LLY", "MRK", "ABBV",
        "PEP", "KO", "COST", "ADBE", "CRM", "NFLX", "AMD", "INTC", "CSCO",
        "PFE", "TMO", "ACN", "DHR", "VZ", "TXN", "QCOM", "HON", "UPS", "LOW",
        "SPY", "QQQ", "IWM", "DIA", "XLF", "XLK", "XLE", "XLV", "XLI", "XLP",
    ]

    def __init__(self, symbols: list[str] | None = None):
        self.symbols = symbols or self.DEFAULT_SYMBOLS

    def get_symbols(self) -> list[SymbolInfo]:
        """Return a fixed list of symbols for testing."""
        return [
            SymbolInfo(
                symbol=sym,
                name=f"{sym} Inc.",
                exchange="NASDAQ" if sym not in ["SPY", "QQQ", "IWM", "DIA", "XLF", "XLK", "XLE", "XLV", "XLI", "XLP"] else "ARCA",
                asset_type="equity",
                active=True,
            )
            for sym in self.symbols
        ]


class FileUniverseProvider:
    """Universe provider that reads symbols from a file."""

    def __init__(self, symbols_file: str):
        self.symbols_file = symbols_file

    def get_symbols(self) -> list[SymbolInfo]:
        """Read symbols from a file (one per line)."""
        with open(self.symbols_file) as f:
            symbols = [line.strip().upper() for line in f if line.strip() and not line.startswith("#")]
        
        return [
            SymbolInfo(
                symbol=sym,
                name=f"{sym} Inc.",
                exchange="NASDAQ",
                asset_type="equity",
                active=True,
            )
            for sym in symbols
        ]