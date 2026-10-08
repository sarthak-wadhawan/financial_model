"""Unit tests for SECExhibitProvider."""

from __future__ import annotations

import tempfile
from datetime import date
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from trading_copilot.providers.sec_exhibit_provider import SECExhibitProvider
from trading_copilot.providers.sec_http import SECTransport
from trading_copilot.providers.sec_cik_map import SECCIKMap


class TestSECExhibitProvider:
    """Tests for SECExhibitProvider."""

    @pytest.fixture
    def mock_transport(self):
        """Create a mock SEC transport."""
        transport = Mock(spec=SECTransport)
        transport.get = Mock()
        transport.close = Mock()
        return transport

    @pytest.fixture
    def mock_cik_map(self):
        """Create a mock CIK map."""
        cik_map = Mock(spec=SECCIKMap)
        cik_map.get_cik = Mock(return_value="0000123456")
        return cik_map

    @pytest.fixture
    def provider(self, mock_transport, mock_cik_map):
        """Create a SEC exhibit provider with mocked dependencies."""
        with tempfile.TemporaryDirectory() as tmpdir:
            provider = SECExhibitProvider(
                cache_dir=tmpdir,
                transport=mock_transport,
                cik_map=mock_cik_map,
            )
            yield provider
            provider.close()

    def test_provider_initialization(self, provider):
        """Test provider initializes correctly."""
        assert provider is not None
        assert provider.transport is not None
        assert provider.cik_map is not None
        assert provider.errors == []

    def test_find_exhibit_references(self, provider):
        """Test finding exhibit references in 8-K HTML."""
        html = """
        <html>
        <body>
        <a href="/Archives/edgar/data/123456/0000123456-26-000001/ex99_1.htm">EX-99.1</a>
        <a href="/Archives/edgar/data/123456/0000123456-26-000001/ex99_2.htm">EX-99.2</a>
        </body>
        </html>
        """
        refs = provider._find_exhibit_references(html)
        assert len(refs) >= 2
        exhibit_nums = [r[0] for r in refs]
        assert "99.1" in exhibit_nums
        assert "99.2" in exhibit_nums

    def test_extract_headline(self, provider):
        """Test headline extraction from press release."""
        text = "Synthetic Corp Reports Q3 Results\n\nCEO said we had a great quarter."
        headline = provider._extract_headline(text, "SYN")
        assert "Synthetic Corp" in headline
        assert "Q3" in headline

    def test_extract_headline_fallback(self, provider):
        """Test headline fallback when no good line found."""
        text = "Short"
        headline = provider._extract_headline(text, "SYN")
        assert "SYN Press Release" in headline


class TestSECExhibitProviderIntegration:
    """Integration tests using synthetic SEC fixtures."""

    @pytest.fixture
    def synthetic_8k(self):
        return Path(__file__).parents[1] / "fixtures" / "sec" / "synthetic_8k_with_exhibit.htm"

    @pytest.fixture
    def synthetic_exhibit(self):
        return Path(__file__).parents[1] / "fixtures" / "sec" / "synthetic_exhibit_991.htm"

    def test_exhibit_fixture_loads(self, synthetic_exhibit):
        """Test that exhibit fixture loads correctly."""
        text = synthetic_exhibit.read_text()
        assert "Synthetic Corp Reports" in text
        assert "Alice Example" in text
        assert "Bob Sample" in text
        assert "1.55" in text
        assert "$1.60 to $1.70" in text


if __name__ == "__main__":
    pytest.main([__file__, "-v"])