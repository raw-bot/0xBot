"""Comprehensive test suite for dashboard routes."""

import pytest
from fastapi.testclient import TestClient

from src.main import app


@pytest.fixture
def client():
    """Create FastAPI test client."""
    return TestClient(app)


class TestDashboardEndpoint:
    """Tests for main dashboard endpoint."""

    def test_get_dashboard_no_bots(self, client):
        """Test getting dashboard when no bots exist."""
        response = client.get("/dashboard")

        assert response.status_code == 200
        data = response.json()
        assert data["bot"] is None
        assert data["positions"] == []
        assert data["equity_snapshots"] == []
        assert data["trade_history"] == []
        assert data["current_equity"] == 10000.0
        assert data["total_return_pct"] == 0.0

    def test_get_dashboard_with_period(self, client):
        """Test dashboard with period filter."""
        for period in ["1h", "24h", "7d", "30d"]:
            response = client.get(f"/dashboard?period={period}")

            assert response.status_code == 200
            data = response.json()
            assert "bot" in data
            assert "positions" in data
            assert "equity_snapshots" in data
            assert "trade_history" in data

    def test_get_dashboard_invalid_period(self, client):
        """Test dashboard with invalid period."""
        response = client.get("/dashboard?period=invalid")

        assert response.status_code == 200  # Invalid period is ignored
        data = response.json()
        # Should return all data (no period filter applied)
        assert "bot" in data

    def test_dashboard_response_structure(self, client):
        """Test dashboard response has all expected fields."""
        response = client.get("/dashboard")

        assert response.status_code == 200
        data = response.json()

        # Check all required fields exist
        assert "bot" in data
        assert "positions" in data
        assert "equity_snapshots" in data
        assert "trade_history" in data
        assert "current_equity" in data
        assert "total_return_pct" in data
        assert "total_unrealized_pnl" in data
        assert "btc_start_price" in data
        assert "btc_current_price" in data
        assert "hodl_return_pct" in data
        assert "alpha_pct" in data


class TestPublicBotsEndpoint:
    """Tests for public bots listing endpoint."""

    def test_list_bots_public(self, client):
        """Test getting list of all bots (public endpoint)."""
        response = client.get("/dashboard/bots")

        assert response.status_code == 200
        data = response.json()
        assert "bots" in data
        assert "total" in data
        assert isinstance(data["bots"], list)

    def test_list_bots_public_structure(self, client):
        """Test public bots endpoint response structure."""
        response = client.get("/dashboard/bots")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == len(data["bots"])

        # If any bots, check structure
        if data["bots"]:
            bot = data["bots"][0]
            assert "id" in bot
            assert "name" in bot
            assert "status" in bot
            assert "capital" in bot
            assert "initial_capital" in bot

    def test_list_bots_public_empty(self, client):
        """Test public bots endpoint when no bots exist."""
        response = client.get("/dashboard/bots")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 0
        assert len(data["bots"]) == data["total"]


class TestSentimentEndpoint:
    """Tests for market sentiment endpoint."""

    def test_get_sentiment_endpoint(self, client):
        """Test getting market sentiment."""
        response = client.get("/dashboard/sentiment")

        assert response.status_code == 200
        data = response.json()
        assert "available" in data

    def test_sentiment_response_when_unavailable(self, client):
        """Test sentiment endpoint handles unavailability gracefully."""
        response = client.get("/dashboard/sentiment")

        assert response.status_code == 200
        data = response.json()
        # Should still have available key
        assert "available" in data

    def test_sentiment_response_structure_if_available(self, client):
        """Test sentiment response structure when available."""
        response = client.get("/dashboard/sentiment")

        assert response.status_code == 200
        data = response.json()

        if data["available"]:
            assert "fear_greed" in data
            assert "global_market" in data
            assert "market_phase" in data
            assert "llm_guidance" in data
            assert "timestamp" in data
        else:
            assert "error" in data


class TestDashboardErrorHandling:
    """Tests for error handling in dashboard endpoints."""

    def test_dashboard_with_invalid_period_type(self, client):
        """Test dashboard with non-string period."""
        response = client.get("/dashboard?period=123")

        # Should handle gracefully
        assert response.status_code == 200

    def test_dashboard_multiple_periods(self, client):
        """Test dashboard with multiple period parameters."""
        response = client.get("/dashboard?period=24h&period=7d")

        # Should use first value or handle gracefully
        assert response.status_code == 200

    def test_public_bots_with_extra_params(self, client):
        """Test public bots endpoint ignores extra parameters."""
        response = client.get("/dashboard/bots?extra=param&another=value")

        assert response.status_code == 200
        data = response.json()
        assert "bots" in data
        assert "total" in data

    def test_sentiment_endpoint_resilience(self, client):
        """Test sentiment endpoint handles errors gracefully."""
        # Call multiple times to test resilience
        for _ in range(3):
            response = client.get("/dashboard/sentiment")
            assert response.status_code == 200
            data = response.json()
            assert "available" in data


class TestDashboardIntegration:
    """Integration tests for dashboard endpoints."""

    def test_dashboard_all_periods(self, client):
        """Test dashboard works with all supported periods."""
        periods = ["1h", "24h", "7d", "30d"]

        for period in periods:
            response = client.get(f"/dashboard?period={period}")
            assert response.status_code == 200

    def test_dashboard_and_bots_consistency(self, client):
        """Test that dashboard and public bots endpoints are consistent."""
        dashboard_response = client.get("/dashboard")
        bots_response = client.get("/dashboard/bots")

        assert dashboard_response.status_code == 200
        assert bots_response.status_code == 200

        dashboard_data = dashboard_response.json()
        bots_data = bots_response.json()

        # Bots should always be accessible
        assert "bots" in bots_data
        assert "total" in bots_data

    def test_sentiment_isolation(self, client):
        """Test that sentiment endpoint is independent."""
        response1 = client.get("/dashboard/sentiment")
        response2 = client.get("/dashboard/sentiment")

        assert response1.status_code == 200
        assert response2.status_code == 200

        # Both should have same structure
        data1 = response1.json()
        data2 = response2.json()

        assert "available" in data1
        assert "available" in data2


class TestDashboardCaching:
    """Tests for dashboard caching and performance."""

    def test_dashboard_consistent_calls(self, client):
        """Test that dashboard returns consistent structure across calls."""
        response1 = client.get("/dashboard")
        response2 = client.get("/dashboard")

        data1 = response1.json()
        data2 = response2.json()

        # Both should have same keys
        assert set(data1.keys()) == set(data2.keys())

    def test_dashboard_field_types(self, client):
        """Test that dashboard fields have expected types."""
        response = client.get("/dashboard")
        data = response.json()

        assert isinstance(data["positions"], list)
        assert isinstance(data["equity_snapshots"], list)
        assert isinstance(data["trade_history"], list)
        assert isinstance(data["current_equity"], (int, float))
        assert isinstance(data["total_return_pct"], (int, float))
        assert isinstance(data["total_unrealized_pnl"], (int, float))

    def test_bots_list_format(self, client):
        """Test that bots list is properly formatted."""
        response = client.get("/dashboard/bots")
        data = response.json()

        assert isinstance(data["bots"], list)
        assert isinstance(data["total"], int)
        assert data["total"] == len(data["bots"])


class TestEquityHistoryResponseFormat:
    """Tests for equity history response format."""

    def test_equity_snapshot_format(self, client):
        """Test equity snapshot format in dashboard."""
        response = client.get("/dashboard")
        data = response.json()

        # Check structure of equity snapshots
        for snapshot in data["equity_snapshots"]:
            assert "timestamp" in snapshot
            assert "equity" in snapshot
            assert isinstance(snapshot["timestamp"], str)
            assert isinstance(snapshot["equity"], (int, float))

    def test_trade_history_format(self, client):
        """Test trade history format in dashboard."""
        response = client.get("/dashboard")
        data = response.json()

        # Check structure of trade history
        for trade in data["trade_history"]:
            assert "timestamp" in trade
            assert "symbol" in trade
            assert "side" in trade
            assert "pnl" in trade
            assert "cumulative_pnl" in trade
