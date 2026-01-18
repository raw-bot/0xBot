"""Comprehensive test suite for bot management routes."""

import pytest
from decimal import Decimal
from fastapi.testclient import TestClient

from src.main import app


@pytest.fixture
def client():
    """Create FastAPI test client."""
    return TestClient(app)


@pytest.fixture
def auth_token(client):
    """Create authenticated user and return token."""
    response = client.post(
        "/auth/register",
        json={
            "email": "testuser@example.com",
            "password": "SecurePassword123",
        },
    )
    return response.json()["token"]


class TestCreateBot:
    """Tests for bot creation endpoint."""

    def test_create_bot_success(self, client, auth_token):
        """Test successful bot creation."""
        response = client.post(
            "/bots",
            json={
                "name": "Test Bot",
                "model_name": "trinity_confluence",
                "capital": 10000.0,
                "trading_symbols": ["BTC/USDT", "ETH/USDT"],
                "paper_trading": True,
            },
            headers={"Authorization": f"Bearer {auth_token}"},
        )

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Test Bot"
        assert data["capital"] == 10000.0
        assert data["paper_trading"] == True
        assert "id" in data
        assert "status" in data

    def test_create_bot_minimum_capital(self, client, auth_token):
        """Test bot creation with minimum capital."""
        response = client.post(
            "/bots",
            json={
                "name": "Min Capital Bot",
                "model_name": "indicator",
                "capital": 100.0,
            },
            headers={"Authorization": f"Bearer {auth_token}"},
        )

        assert response.status_code == 201
        data = response.json()
        assert data["capital"] == 100.0

    def test_create_bot_insufficient_capital(self, client, auth_token):
        """Test bot creation with insufficient capital."""
        response = client.post(
            "/bots",
            json={
                "name": "Low Capital Bot",
                "model_name": "indicator",
                "capital": 50.0,  # Below minimum of 100
            },
            headers={"Authorization": f"Bearer {auth_token}"},
        )

        assert response.status_code == 422  # Validation error

    def test_create_bot_missing_required_fields(self, client, auth_token):
        """Test bot creation without required fields."""
        response = client.post(
            "/bots",
            json={
                "model_name": "indicator",
                "capital": 10000.0,
            },
            headers={"Authorization": f"Bearer {auth_token}"},
        )

        assert response.status_code == 422

    def test_create_bot_without_auth(self, client):
        """Test bot creation without authentication."""
        response = client.post(
            "/bots",
            json={
                "name": "Test Bot",
                "model_name": "indicator",
                "capital": 10000.0,
            },
        )

        assert response.status_code == 403

    def test_create_bot_with_custom_risk_params(self, client, auth_token):
        """Test bot creation with custom risk parameters."""
        response = client.post(
            "/bots",
            json={
                "name": "Risk Bot",
                "model_name": "indicator",
                "capital": 10000.0,
                "risk_params": {
                    "max_position_pct": 0.15,
                    "max_drawdown_pct": 0.25,
                    "max_trades_per_day": 20,
                },
            },
            headers={"Authorization": f"Bearer {auth_token}"},
        )

        assert response.status_code == 201
        data = response.json()
        assert data["risk_params"]["max_position_pct"] == 0.15


class TestListBots:
    """Tests for bot listing endpoint."""

    def test_list_bots_empty(self, client, auth_token):
        """Test listing bots when none exist."""
        response = client.get(
            "/bots",
            headers={"Authorization": f"Bearer {auth_token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert data["bots"] == []

    def test_list_bots_with_bots(self, client, auth_token):
        """Test listing bots when bots exist."""
        # Create bot first
        client.post(
            "/bots",
            json={
                "name": "Bot 1",
                "model_name": "indicator",
                "capital": 10000.0,
            },
            headers={"Authorization": f"Bearer {auth_token}"},
        )

        # List bots
        response = client.get(
            "/bots",
            headers={"Authorization": f"Bearer {auth_token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1
        assert len(data["bots"]) >= 1
        assert data["bots"][0]["name"] == "Bot 1"

    def test_list_bots_user_isolation(self, client):
        """Test that users only see their own bots."""
        # Create user 1
        user1_token = client.post(
            "/auth/register",
            json={
                "email": "user1@example.com",
                "password": "SecurePassword123",
            },
        ).json()["token"]

        # Create user 2
        user2_token = client.post(
            "/auth/register",
            json={
                "email": "user2@example.com",
                "password": "SecurePassword456",
            },
        ).json()["token"]

        # User 1 creates bot
        client.post(
            "/bots",
            json={
                "name": "User1 Bot",
                "model_name": "indicator",
                "capital": 10000.0,
            },
            headers={"Authorization": f"Bearer {user1_token}"},
        )

        # User 2 creates bot
        client.post(
            "/bots",
            json={
                "name": "User2 Bot",
                "model_name": "indicator",
                "capital": 10000.0,
            },
            headers={"Authorization": f"Bearer {user2_token}"},
        )

        # User 1 lists bots - should only see their bot
        user1_response = client.get(
            "/bots",
            headers={"Authorization": f"Bearer {user1_token}"},
        )
        user1_bots = user1_response.json()["bots"]

        # User 2 lists bots - should only see their bot
        user2_response = client.get(
            "/bots",
            headers={"Authorization": f"Bearer {user2_token}"},
        )
        user2_bots = user2_response.json()["bots"]

        # Check isolation
        user1_names = [bot["name"] for bot in user1_bots]
        user2_names = [bot["name"] for bot in user2_bots]

        assert "User1 Bot" in user1_names
        assert "User2 Bot" not in user1_names
        assert "User2 Bot" in user2_names
        assert "User1 Bot" not in user2_names

    def test_list_bots_without_auth(self, client):
        """Test listing bots without authentication."""
        response = client.get("/bots")

        assert response.status_code == 403


class TestGetBot:
    """Tests for getting specific bot endpoint."""

    def test_get_bot_success(self, client, auth_token):
        """Test successfully getting a bot."""
        # Create bot
        create_response = client.post(
            "/bots",
            json={
                "name": "Test Bot",
                "model_name": "indicator",
                "capital": 10000.0,
            },
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        bot_id = create_response.json()["id"]

        # Get bot
        response = client.get(
            f"/bots/{bot_id}",
            headers={"Authorization": f"Bearer {auth_token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == bot_id
        assert data["name"] == "Test Bot"

    def test_get_bot_not_found(self, client, auth_token):
        """Test getting non-existent bot."""
        response = client.get(
            "/bots/00000000-0000-0000-0000-000000000000",
            headers={"Authorization": f"Bearer {auth_token}"},
        )

        assert response.status_code == 404

    def test_get_bot_invalid_id(self, client, auth_token):
        """Test getting bot with invalid ID format."""
        response = client.get(
            "/bots/invalid-id",
            headers={"Authorization": f"Bearer {auth_token}"},
        )

        assert response.status_code == 400

    def test_get_bot_unauthorized(self, client):
        """Test getting bot without authentication."""
        response = client.get("/bots/00000000-0000-0000-0000-000000000000")

        assert response.status_code == 403

    def test_get_bot_other_user_forbidden(self, client):
        """Test getting other user's bot returns 403."""
        # User 1 creates bot
        user1_token = client.post(
            "/auth/register",
            json={
                "email": "user1@example.com",
                "password": "SecurePassword123",
            },
        ).json()["token"]

        create_response = client.post(
            "/bots",
            json={
                "name": "User1 Bot",
                "model_name": "indicator",
                "capital": 10000.0,
            },
            headers={"Authorization": f"Bearer {user1_token}"},
        )
        bot_id = create_response.json()["id"]

        # User 2 tries to get User 1's bot
        user2_token = client.post(
            "/auth/register",
            json={
                "email": "user2@example.com",
                "password": "SecurePassword456",
            },
        ).json()["token"]

        response = client.get(
            f"/bots/{bot_id}",
            headers={"Authorization": f"Bearer {user2_token}"},
        )

        assert response.status_code == 403


class TestUpdateBot:
    """Tests for bot update endpoint."""

    def test_update_bot_success(self, client, auth_token):
        """Test successfully updating a bot."""
        # Create bot
        create_response = client.post(
            "/bots",
            json={
                "name": "Original Bot",
                "model_name": "indicator",
                "capital": 10000.0,
            },
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        bot_id = create_response.json()["id"]

        # Update bot
        response = client.put(
            f"/bots/{bot_id}",
            json={
                "name": "Updated Bot",
                "capital": 15000.0,
            },
            headers={"Authorization": f"Bearer {auth_token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Bot"
        assert data["capital"] == 15000.0

    def test_update_bot_not_found(self, client, auth_token):
        """Test updating non-existent bot."""
        response = client.put(
            "/bots/00000000-0000-0000-0000-000000000000",
            json={"name": "Updated"},
            headers={"Authorization": f"Bearer {auth_token}"},
        )

        assert response.status_code == 404

    def test_update_bot_unauthorized(self, client):
        """Test updating bot without authentication."""
        response = client.put(
            "/bots/00000000-0000-0000-0000-000000000000",
            json={"name": "Updated"},
        )

        assert response.status_code == 403

    def test_update_bot_other_user_forbidden(self, client):
        """Test updating other user's bot returns 403."""
        # User 1 creates bot
        user1_token = client.post(
            "/auth/register",
            json={
                "email": "user1@example.com",
                "password": "SecurePassword123",
            },
        ).json()["token"]

        create_response = client.post(
            "/bots",
            json={
                "name": "User1 Bot",
                "model_name": "indicator",
                "capital": 10000.0,
            },
            headers={"Authorization": f"Bearer {user1_token}"},
        )
        bot_id = create_response.json()["id"]

        # User 2 tries to update User 1's bot
        user2_token = client.post(
            "/auth/register",
            json={
                "email": "user2@example.com",
                "password": "SecurePassword456",
            },
        ).json()["token"]

        response = client.put(
            f"/bots/{bot_id}",
            json={"name": "Hacked Bot"},
            headers={"Authorization": f"Bearer {user2_token}"},
        )

        assert response.status_code == 403


class TestDeleteBot:
    """Tests for bot deletion endpoint."""

    def test_delete_bot_success(self, client, auth_token):
        """Test successfully deleting a bot."""
        # Create bot
        create_response = client.post(
            "/bots",
            json={
                "name": "Bot to Delete",
                "model_name": "indicator",
                "capital": 10000.0,
            },
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        bot_id = create_response.json()["id"]

        # Delete bot
        response = client.delete(
            f"/bots/{bot_id}",
            headers={"Authorization": f"Bearer {auth_token}"},
        )

        assert response.status_code == 200
        assert response.json()["message"] == "Bot deleted successfully"

        # Verify bot is deleted
        get_response = client.get(
            f"/bots/{bot_id}",
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        assert get_response.status_code == 404

    def test_delete_bot_not_found(self, client, auth_token):
        """Test deleting non-existent bot."""
        response = client.delete(
            "/bots/00000000-0000-0000-0000-000000000000",
            headers={"Authorization": f"Bearer {auth_token}"},
        )

        assert response.status_code == 404

    def test_delete_bot_unauthorized(self, client):
        """Test deleting bot without authentication."""
        response = client.delete("/bots/00000000-0000-0000-0000-000000000000")

        assert response.status_code == 403

    def test_delete_bot_other_user_forbidden(self, client):
        """Test deleting other user's bot returns 403."""
        # User 1 creates bot
        user1_token = client.post(
            "/auth/register",
            json={
                "email": "user1@example.com",
                "password": "SecurePassword123",
            },
        ).json()["token"]

        create_response = client.post(
            "/bots",
            json={
                "name": "User1 Bot",
                "model_name": "indicator",
                "capital": 10000.0,
            },
            headers={"Authorization": f"Bearer {user1_token}"},
        )
        bot_id = create_response.json()["id"]

        # User 2 tries to delete User 1's bot
        user2_token = client.post(
            "/auth/register",
            json={
                "email": "user2@example.com",
                "password": "SecurePassword456",
            },
        ).json()["token"]

        response = client.delete(
            f"/bots/{bot_id}",
            headers={"Authorization": f"Bearer {user2_token}"},
        )

        assert response.status_code == 403


class TestBotStatusOperations:
    """Tests for bot status operations (start, pause, stop)."""

    def test_get_bot_positions_empty(self, client, auth_token):
        """Test getting positions for bot with no open positions."""
        # Create bot
        create_response = client.post(
            "/bots",
            json={
                "name": "Test Bot",
                "model_name": "indicator",
                "capital": 10000.0,
            },
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        bot_id = create_response.json()["id"]

        # Get positions
        response = client.get(
            f"/bots/{bot_id}/positions",
            headers={"Authorization": f"Bearer {auth_token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert data["positions"] == []

    def test_get_bot_trades_empty(self, client, auth_token):
        """Test getting trades for bot with no trades."""
        # Create bot
        create_response = client.post(
            "/bots",
            json={
                "name": "Test Bot",
                "model_name": "indicator",
                "capital": 10000.0,
            },
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        bot_id = create_response.json()["id"]

        # Get trades
        response = client.get(
            f"/bots/{bot_id}/trades",
            headers={"Authorization": f"Bearer {auth_token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert data["trades"] == []

    def test_get_bot_equity_history(self, client, auth_token):
        """Test getting equity history for bot."""
        # Create bot
        create_response = client.post(
            "/bots",
            json={
                "name": "Test Bot",
                "model_name": "indicator",
                "capital": 10000.0,
            },
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        bot_id = create_response.json()["id"]

        # Get equity history
        response = client.get(
            f"/bots/{bot_id}/equity",
            headers={"Authorization": f"Bearer {auth_token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "snapshots" in data
        assert "current_equity" in data
        assert "initial_capital" in data
        assert "total_return_pct" in data

    def test_get_bot_equity_with_period(self, client, auth_token):
        """Test getting equity history with period filter."""
        # Create bot
        create_response = client.post(
            "/bots",
            json={
                "name": "Test Bot",
                "model_name": "indicator",
                "capital": 10000.0,
            },
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        bot_id = create_response.json()["id"]

        # Get equity history with period
        for period in ["1h", "24h", "7d", "30d"]:
            response = client.get(
                f"/bots/{bot_id}/equity?period={period}",
                headers={"Authorization": f"Bearer {auth_token}"},
            )
            assert response.status_code == 200


class TestBotErrorHandling:
    """Tests for error handling in bot endpoints."""

    def test_create_bot_empty_name(self, client, auth_token):
        """Test bot creation with empty name."""
        response = client.post(
            "/bots",
            json={
                "name": "",
                "model_name": "indicator",
                "capital": 10000.0,
            },
            headers={"Authorization": f"Bearer {auth_token}"},
        )

        assert response.status_code == 422

    def test_create_bot_negative_capital(self, client, auth_token):
        """Test bot creation with negative capital."""
        response = client.post(
            "/bots",
            json={
                "name": "Test Bot",
                "model_name": "indicator",
                "capital": -1000.0,
            },
            headers={"Authorization": f"Bearer {auth_token}"},
        )

        assert response.status_code == 422

    def test_list_bots_with_invalid_token(self, client):
        """Test listing bots with invalid token."""
        response = client.get(
            "/bots",
            headers={"Authorization": "Bearer invalid_token"},
        )

        assert response.status_code == 403
