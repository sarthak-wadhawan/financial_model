"""Unit tests for IRReleaseProvider."""

from __future__ import annotations

import tempfile
from datetime import date
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from trading_copilot.providers.ir_release_provider import IRReleaseProvider
from trading_copilot.models.news import NewsSourceType


class TestIRReleaseProvider:
    """Tests for IRReleaseProvider."""

    @pytest.fixture
    def provider(self):
        """Create an IR release provider."""
        with tempfile.TemporaryDirectory() as tmpdir:
            provider = IRReleaseProvider(cache_dir=tmpdir)
            yield provider
            provider.close()

    def test_provider_initialization(self, provider):
        """Test provider initializes correctly."""
        assert provider is not None
        assert "AAPL" in provider.feeds
        assert "MSFT" in provider.feeds
        assert len(provider.feeds) >= 50

    def test_clean_html(self, provider):
        """Test HTML cleaning."""
        html = "<p>Hello <b>World</b></p><script>alert('xss')</script>"
        clean = provider._clean_html(html)
        assert "Hello World" in clean
        assert "script" not in clean.lower()
        assert "alert" not in clean.lower()

    def test_clean_html_entities(self, provider):
        """Test HTML entity decoding."""
        html = "AAPL & MSFT < 100 > 50 &nbsp; test"
        clean = provider._clean_html(html)
        assert "AAPL & MSFT < 100 > 50 test" in clean

    def test_extract_symbol(self, provider):
        """Test symbol extraction from text."""
        known = {"AAPL", "MSFT", "GOOGL"}
        
        # Test $AAPL pattern
        assert provider._extract_symbol("$AAPL beats estimates", known) == "AAPL"
        
        # Test NASDAQ: AAPL pattern
        assert provider._extract_symbol("NASDAQ: AAPL reports earnings", known) == "AAPL"
        
        # Test AAPL stock pattern
        assert provider._extract_symbol("AAPL stock rises", known) == "AAPL"
        
        # Test AAPL (NASDAQ) pattern
        assert provider._extract_symbol("AAPL (NASDAQ) beats", known) == "AAPL"
        
        # Test unknown symbol returns None
        assert provider._extract_symbol("Unknown company reports", known) is None

    def test_custom_feeds(self, provider):
        """Test adding custom feeds."""
        custom = {"TEST": "https://test.com/feed.xml"}
        provider2 = IRReleaseProvider(custom_feeds=custom)
        assert "TEST" in provider2.feeds
        assert provider2.feeds["TEST"] == "https://test.com/feed.xml"


class TestIRReleaseProviderIntegration:
    """Integration tests using synthetic IR RSS fixtures."""

    @pytest.fixture
    def synthetic_ir_feed(self):
        return Path(__file__).parents[1] / "fixtures" / "ir" / "syn_rss.xml"

    def test_ir_fixture_loads(self, synthetic_ir_feed):
        """Test that IR RSS fixture loads correctly."""
        import feedparser
        feed = feedparser.parse(synthetic_ir_feed.read_text())
        assert len(feed.entries) == 3
        assert "Synthetic Corp Reports" in feed.entries[0].title
        assert "Alice Example" in feed.entries[0].summary
        assert "Bob Sample" in feed.entries[0].summary
        assert "1.55" in feed.entries[0].summary


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
