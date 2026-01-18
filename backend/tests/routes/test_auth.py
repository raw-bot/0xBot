"""Comprehensive test suite for authentication routes."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.main import app


@pytest.fixture
def client():
    """Create FastAPI test client."""
    return TestClient(app)


class TestRegister:
    """Tests for user registration endpoint."""

    def test_register_success(self, client):
        """Test successful user registration."""
        response = client.post(
            "/auth/register",
            json={
                "email": "newuser@example.com",
                "password": "SecurePassword123",
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["email"] == "newuser@example.com"
        assert "token" in data
        assert "id" in data

    def test_register_duplicate_email(self, client):
        """Test registration with already registered email."""
        # First registration
        client.post(
            "/auth/register",
            json={
                "email": "duplicate@example.com",
                "password": "SecurePassword123",
            },
        )

        # Try duplicate
        response = client.post(
            "/auth/register",
            json={
                "email": "duplicate@example.com",
                "password": "SecurePassword456",
            },
        )

        assert response.status_code == 400
        assert "already registered" in response.json()["detail"]

    def test_register_invalid_email(self, client):
        """Test registration with invalid email."""
        response = client.post(
            "/auth/register",
            json={
                "email": "not-an-email",
                "password": "SecurePassword123",
            },
        )

        assert response.status_code == 422  # Validation error

    def test_register_password_too_short(self, client):
        """Test registration with short password."""
        response = client.post(
            "/auth/register",
            json={
                "email": "user@example.com",
                "password": "short",
            },
        )

        assert response.status_code == 422  # Validation error

    def test_register_missing_email(self, client):
        """Test registration without email."""
        response = client.post(
            "/auth/register",
            json={
                "password": "SecurePassword123",
            },
        )

        assert response.status_code == 422

    def test_register_missing_password(self, client):
        """Test registration without password."""
        response = client.post(
            "/auth/register",
            json={
                "email": "user@example.com",
            },
        )

        assert response.status_code == 422


class TestLogin:
    """Tests for user login endpoint."""

    def test_login_success(self, client):
        """Test successful login."""
        # Register first
        client.post(
            "/auth/register",
            json={
                "email": "user@example.com",
                "password": "SecurePassword123",
            },
        )

        # Login
        response = client.post(
            "/auth/login",
            json={
                "email": "user@example.com",
                "password": "SecurePassword123",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "user@example.com"
        assert "token" in data

    def test_login_invalid_password(self, client):
        """Test login with wrong password."""
        # Register first
        client.post(
            "/auth/register",
            json={
                "email": "user@example.com",
                "password": "SecurePassword123",
            },
        )

        # Login with wrong password
        response = client.post(
            "/auth/login",
            json={
                "email": "user@example.com",
                "password": "WrongPassword",
            },
        )

        assert response.status_code == 401
        assert "Invalid email or password" in response.json()["detail"]

    def test_login_nonexistent_user(self, client):
        """Test login with non-existent email."""
        response = client.post(
            "/auth/login",
            json={
                "email": "nonexistent@example.com",
                "password": "SomePassword123",
            },
        )

        assert response.status_code == 401
        assert "Invalid email or password" in response.json()["detail"]

    def test_login_missing_credentials(self, client):
        """Test login without credentials."""
        response = client.post("/auth/login", json={})

        assert response.status_code == 422

    def test_login_invalid_email_format(self, client):
        """Test login with invalid email format."""
        response = client.post(
            "/auth/login",
            json={
                "email": "not-an-email",
                "password": "SomePassword123",
            },
        )

        assert response.status_code == 422


class TestRefreshToken:
    """Tests for token refresh endpoint."""

    def test_refresh_token_success(self, client):
        """Test successful token refresh."""
        # Register and get token
        register_response = client.post(
            "/auth/register",
            json={
                "email": "user@example.com",
                "password": "SecurePassword123",
            },
        )
        token = register_response.json()["token"]

        # Refresh token
        response = client.post(
            "/auth/refresh",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    def test_refresh_token_missing_auth(self, client):
        """Test refresh without authentication."""
        response = client.post("/auth/refresh")

        assert response.status_code == 403

    def test_refresh_token_invalid_token(self, client):
        """Test refresh with invalid token."""
        response = client.post(
            "/auth/refresh",
            headers={"Authorization": "Bearer invalid_token"},
        )

        assert response.status_code == 403


class TestGetCurrentUserInfo:
    """Tests for getting current user info endpoint."""

    def test_get_current_user_info_success(self, client):
        """Test successfully getting current user info."""
        # Register and get token
        register_response = client.post(
            "/auth/register",
            json={
                "email": "user@example.com",
                "password": "SecurePassword123",
            },
        )
        token = register_response.json()["token"]

        # Get current user info
        response = client.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "user@example.com"
        assert "id" in data
        assert "token" in data

    def test_get_current_user_info_missing_auth(self, client):
        """Test getting user info without authentication."""
        response = client.get("/auth/me")

        assert response.status_code == 403

    def test_get_current_user_info_invalid_token(self, client):
        """Test getting user info with invalid token."""
        response = client.get(
            "/auth/me",
            headers={"Authorization": "Bearer invalid_token"},
        )

        assert response.status_code == 403


class TestAuthenticationFlow:
    """Tests for complete authentication flows."""

    def test_register_login_refresh_flow(self, client):
        """Test complete authentication flow: register -> login -> refresh."""
        # Register
        register_response = client.post(
            "/auth/register",
            json={
                "email": "user@example.com",
                "password": "SecurePassword123",
            },
        )
        assert register_response.status_code == 201
        register_token = register_response.json()["token"]

        # Login
        login_response = client.post(
            "/auth/login",
            json={
                "email": "user@example.com",
                "password": "SecurePassword123",
            },
        )
        assert login_response.status_code == 200
        login_token = login_response.json()["token"]

        # Refresh with login token
        refresh_response = client.post(
            "/auth/refresh",
            headers={"Authorization": f"Bearer {login_token}"},
        )
        assert refresh_response.status_code == 200
        new_token = refresh_response.json()["access_token"]

        # Use new token to get user info
        user_response = client.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {new_token}"},
        )
        assert user_response.status_code == 200
        assert user_response.json()["email"] == "user@example.com"

    def test_multiple_users_isolated(self, client):
        """Test that multiple users can register independently."""
        # Register user 1
        user1_response = client.post(
            "/auth/register",
            json={
                "email": "user1@example.com",
                "password": "SecurePassword123",
            },
        )
        assert user1_response.status_code == 201
        user1_token = user1_response.json()["token"]
        user1_id = user1_response.json()["id"]

        # Register user 2
        user2_response = client.post(
            "/auth/register",
            json={
                "email": "user2@example.com",
                "password": "SecurePassword456",
            },
        )
        assert user2_response.status_code == 201
        user2_token = user2_response.json()["token"]
        user2_id = user2_response.json()["id"]

        # Verify users are different
        assert user1_id != user2_id

        # Verify each token works for its own user
        user1_info = client.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {user1_token}"},
        )
        assert user1_info.json()["email"] == "user1@example.com"

        user2_info = client.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {user2_token}"},
        )
        assert user2_info.json()["email"] == "user2@example.com"


class TestAuthErrorHandling:
    """Tests for error handling in auth endpoints."""

    def test_register_empty_email(self, client):
        """Test registration with empty email."""
        response = client.post(
            "/auth/register",
            json={
                "email": "",
                "password": "SecurePassword123",
            },
        )

        assert response.status_code == 422

    def test_register_empty_password(self, client):
        """Test registration with empty password."""
        response = client.post(
            "/auth/register",
            json={
                "email": "user@example.com",
                "password": "",
            },
        )

        assert response.status_code == 422

    def test_register_very_long_password(self, client):
        """Test registration with very long password."""
        response = client.post(
            "/auth/register",
            json={
                "email": "user@example.com",
                "password": "x" * 1001,  # More than max
            },
        )

        assert response.status_code == 422

    def test_login_with_get_request(self, client):
        """Test that login endpoint doesn't accept GET."""
        response = client.get("/auth/login")

        assert response.status_code == 405  # Method not allowed

    def test_register_with_get_request(self, client):
        """Test that register endpoint doesn't accept GET."""
        response = client.get("/auth/register")

        assert response.status_code == 405  # Method not allowed
