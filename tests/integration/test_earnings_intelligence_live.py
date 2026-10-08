"""Live integration tests for EarningsIntelligenceProvider (SEC EDGAR).

Gated by RUN_LIVE_TESTS=1 environment variable.
These tests hit the real SEC EDGAR API and require a valid SEC_USER_AGENT.
"""

import os
import tempfile
from datetime import date

import pytest

from trading_copilot.events.store import EventStore
from trading_copilot.providers.earnings_intelligence import EarningsIntelligenceProvider
from trading_copilot.providers.sec_http import SECTransport


pytestmark = pytest.mark.skipif(
    not os.environ.get("RUN_LIVE_TESTS"),
    reason="Live tests require RUN_LIVE_TESTS=1 and SEC_USER_AGENT",
)


def test_earnings_intelligence_live_aapl():
    """Test live earnings intelligence extraction for AAPL (known to have 8-K earnings)."""
    if not os.environ.get("SEC_USER_AGENT"):
        pytest.skip("SEC_USER_AGENT required for live SEC tests")

    with tempfile.TemporaryDirectory() as tmpdir:
        store = EventStore(tmpdir + "/events.db")
        transport = SECTransport()
        
        provider = EarningsIntelligenceProvider(
            event_store=store,
            cache_dir=tmpdir + "/earnings_intelligence",
            transport=transport,
        )
        
        try:
            # Fetch recent earnings for AAPL (last 90 days)
            counts = provider.refresh(
                symbols=["AAPL"],
                lookback_days=90,
            )
            
            # Should have at least some results (AAPL reports quarterly)
            # Note: may be 0 if no earnings in lookback window
            print(f"Earnings intelligence counts: {counts}")
            assert counts["ERROR"] == 0
            
            # Query stored events
            events = store.events_by_type("earnings_result", limit=10)
            for event in events:
                if event.symbol == "AAPL":
                    # Verify required fields
                    assert event.event_type.value == "earnings_result"
                    assert event.metadata.get("fiscal_quarter")
                    assert event.metadata.get("fiscal_year")
                    assert event.source == "sec_edgar"
                    assert event.source_url
                    assert event.source_id
                    assert "filing_accepted_at" in event.metadata
                    assert "announcement_released_at" in event.metadata
                    assert "release_time_source" in event.metadata
                    assert "release_time_precision" in event.metadata
                    # Actual EPS/revenue should be present for earnings results
                    assert event.metadata.get("eps_actual") is not None
                    assert event.metadata.get("revenue_actual") is not None
                    
        finally:
            provider.close()
            store.close()


def test_earnings_intelligence_live_multiple_symbols():
    """Test earnings intelligence for multiple symbols."""
    if not os.environ.get("SEC_USER_AGENT"):
        pytest.skip("SEC_USER_AGENT required for live SEC tests")

    with tempfile.TemporaryDirectory() as tmpdir:
        store = EventStore(tmpdir + "/events.db")
        transport = SECTransport()
        
        provider = EarningsIntelligenceProvider(
            event_store=store,
            cache_dir=tmpdir + "/earnings_intelligence",
            transport=transport,
        )
        
        try:
            counts = provider.refresh(
                symbols=["AAPL", "MSFT"],
                lookback_days=180,
            )
            
            assert counts["ERROR"] == 0
            
            # Check both symbols have events
            for symbol in ["AAPL", "MSFT"]:
                events = store.events_for_symbol(
                    symbol=symbol,
                    event_types=["earnings_result", "earnings_guidance"],
                    limit=20,
                )
                # At least some events expected for large caps
                if events:
                    for event in events:
                        assert event.symbol == symbol
                        assert event.metadata.get("source_document_id", "").startswith("sec_edgar:")
                        
        finally:
            provider.close()
            store.close()


def test_earnings_guidance_live():
    """Test that guidance events are extracted when present."""
    if not os.environ.get("SEC_USER_AGENT"):
        pytest.skip("SEC_USER_AGENT required for live SEC tests")

    with tempfile.TemporaryDirectory() as tmpdir:
        store = EventStore(tmpdir + "/events.db")
        transport = SECTransport()
        
        provider = EarningsIntelligenceProvider(
            event_store=store,
            cache_dir=tmpdir + "/earnings_intelligence",
            transport=transport,
        )
        
        try:
            # Use a longer lookback to catch guidance
            counts = provider.refresh(
                symbols=["AAPL"],
                lookback_days=365,
            )
            
            assert counts["ERROR"] == 0
            
            # Check for guidance events
            guidance_events = store.events_for_symbol(
                symbol="AAPL",
                event_types=["earnings_guidance"],
                limit=20,
            )
            
            # Guidance may or may not be present depending on filings
            for event in guidance_events:
                assert event.event_type.value == "earnings_guidance"
                assert event.metadata.get("period")
                assert event.metadata.get("guidance_change") in ["raised", "lowered", "maintained", "new"]
                assert event.source == "sec_edgar"
                
        finally:
            provider.close()
            store.close()


def test_earnings_intelligence_idempotency():
    """Test that refresh is idempotent (second run produces UNCHANGED)."""
    if not os.environ.get("SEC_USER_AGENT"):
        pytest.skip("SEC_USER_AGENT required for live SEC tests")

    with tempfile.TemporaryDirectory() as tmpdir:
        store = EventStore(tmpdir + "/events.db")
        transport = SECTransport()
        
        provider = EarningsIntelligenceProvider(
            event_store=store,
            cache_dir=tmpdir + "/earnings_intelligence",
            transport=transport,
        )
        
        try:
            counts1 = provider.refresh(symbols=["AAPL"], lookback_days=90)
            counts2 = provider.refresh(symbols=["AAPL"], lookback_days=90)
            
            assert counts1["ERROR"] == 0
            assert counts2["ERROR"] == 0
            # Second run should be mostly UNCHANGED
            assert counts2["UNCHANGED"] >= counts1["NEW"]
            assert counts2["NEW"] == 0
            
        finally:
            provider.close()
            store.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])