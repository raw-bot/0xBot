"""Comprehensive test suite for authentication routes."""

import pytest
from httpx import AsyncClient


class TestRegister:
    """Tests for user registration endpoint."""

    @pytest.mark.asyncio
    async def test_register_success(self, async_client: AsyncClient):
        """Test successful user registration."""
        response = await async_client.post(
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

    @pytest.mark.asyncio
    async def test_register_duplicate_email(self, async_client: AsyncClient):
        """Test registration with already registered email."""
        # First registration
        await async_client.post(
            "/auth/register",
            json={
                "email": "duplicate@example.com",
                "password": "SecurePassword123",
            },
        )

        # Try duplicate
        response = await async_client.post(
            "/auth/register",
            json={
                "email": "duplicate@example.com",
                "password": "SecurePassword456",
            },
        )

        assert response.status_code == 400
        assert "already registered" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_register_invalid_email(self, async_client: AsyncClient):
        """Test registration with invalid email."""
        response = await async_client.post(
            "/auth/register",
            json={
                "email": "not-an-email",
                "password": "SecurePassword123",
            },
        )

        assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_register_password_too_short(self, async_client: AsyncClient):
        """Test registration with short password."""
        response = await async_client.post(
            "/auth/register",
            json={
                "email": "user@example.com",
                "password": "short",
            },
        )

        assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_register_missing_email(self, async_client: AsyncClient):
        """Test registration without email."""
        response = await async_client.post(
            "/auth/register",
            json={
                "password": "SecurePassword123",
            },
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_register_missing_password(self, async_client: AsyncClient):
        """Test registration without password."""
        response = await async_client.post(
            "/auth/register",
            json={
                "email": "user@example.com",
            },
        )

        assert response.status_code == 422


class TestLogin:
    """Tests for user login endpoint."""

    @pytest.mark.asyncio
    async def test_login_success(self, async_client: AsyncClient):
        """Test successful login."""
        # Register first
        await async_client.post(
            "/auth/register",
            json={
                "email": "user@example.com",
                "password": "SecurePassword123",
            },
        )

        # Login
        response = await async_client.post(
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

    @pytest.mark.asyncio
    async def test_login_invalid_password(self, async_client: AsyncClient):
        """Test login with wrong password."""
        # Register first
        await async_client.post(
            "/auth/register",
            json={
                "email": "user@example.com",
                "password": "SecurePassword123",
            },
        )

        # Login with wrong password
        response = await async_client.post(
            "/auth/login",
            json={
                "email": "user@example.com",
                "password": "WrongPassword",
            },
        )

        assert response.status_code == 401
        assert "Invalid email or password" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_login_nonexistent_user(self, async_client: AsyncClient):
        """Test login with non-existent email."""
        response = await async_client.post(
            "/auth/login",
            json={
                "email": "nonexistent@example.com",
                "password": "SomePassword123",
            },
        )

        assert response.status_code == 401
        assert "Invalid email or password" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_login_missing_credentials(self, async_client: AsyncClient):
        """Test login without credentials."""
        response = await async_client.post("/auth/login", json={})

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_login_invalid_email_format(self, async_client: AsyncClient):
        """Test login with invalid email format."""
        response = await async_client.post(
            "/auth/login",
            json={
                "email": "not-an-email",
                "password": "SomePassword123",
            },
        )

        assert response.status_code == 422


class TestRefreshToken:
    """Tests for token refresh endpoint."""

    @pytest.mark.asyncio
    async def test_refresh_token_success(self, async_client: AsyncClient):
        """Test successful token refresh."""
        # Register and get token
        register_response = await async_client.post(
            "/auth/register",
            json={
                "email": "user@example.com",
                "password": "SecurePassword123",
            },
        )
        token = register_response.json()["token"]

        # Refresh token
        response = await async_client.post(
            "/auth/refresh",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    @pytest.mark.asyncio
    async def test_refresh_token_missing_auth(self, async_client: AsyncClient):
        """Test refresh without authentication."""
        response = await async_client.post("/auth/refresh")

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_refresh_token_invalid_token(self, async_client: AsyncClient):
        """Test refresh with invalid token."""
        response = await async_client.post(
            "/auth/refresh",
            headers={"Authorization": "Bearer invalid_token"},
        )

        assert response.status_code == 401


class TestGetCurrentUserInfo:
    """Tests for getting current user info endpoint."""

    @pytest.mark.asyncio
    async def test_get_current_user_info_success(self, async_client: AsyncClient):
        """Test successfully getting current user info."""
        # Register and get token
        register_response = await async_client.post(
            "/auth/register",
            json={
                "email": "user@example.com",
                "password": "SecurePassword123",
            },
        )
        token = register_response.json()["token"]

        # Get current user info
        response = await async_client.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "user@example.com"
        assert "id" in data
        assert "token" in data

    @pytest.mark.asyncio
    async def test_get_current_user_info_missing_auth(self, async_client: AsyncClient):
        """Test getting user info without authentication."""
        response = await async_client.get("/auth/me")

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_get_current_user_info_invalid_token(self, async_client: AsyncClient):
        """Test getting user info with invalid token."""
        response = await async_client.get(
            "/auth/me",
            headers={"Authorization": "Bearer invalid_token"},
        )

        assert response.status_code == 401


class TestAuthenticationFlow:
    """Tests for complete authentication flows."""

    @pytest.mark.asyncio
    async def test_register_login_refresh_flow(self, async_client: AsyncClient):
        """Test complete authentication flow: register -> login -> refresh."""
        # Register
        register_response = await async_client.post(
            "/auth/register",
            json={
                "email": "user@example.com",
                "password": "SecurePassword123",
            },
        )
        assert register_response.status_code == 201
        register_token = register_response.json()["token"]

        # Login
        login_response = await async_client.post(
            "/auth/login",
            json={
                "email": "user@example.com",
                "password": "SecurePassword123",
            },
        )
        assert login_response.status_code == 200
        login_token = login_response.json()["token"]

        # Refresh with login token
        refresh_response = await async_client.post(
            "/auth/refresh",
            headers={"Authorization": f"Bearer {login_token}"},
        )
        assert refresh_response.status_code == 200
        new_token = refresh_response.json()["access_token"]

        # Use new token to get user info
        user_response = await async_client.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {new_token}"},
        )
        assert user_response.status_code == 200
        assert user_response.json()["email"] == "user@example.com"

    @pytest.mark.asyncio
    async def test_multiple_users_isolated(self, async_client: AsyncClient):
        """Test that multiple users can register independently."""
        # Register user 1
        user1_response = await async_client.post(
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
        user2_response = await async_client.post(
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
        user1_info = await async_client.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {user1_token}"},
        )
        assert user1_info.json()["email"] == "user1@example.com"

        user2_info = await async_client.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {user2_token}"},
        )
        assert user2_info.json()["email"] == "user2@example.com"


class TestAuthErrorHandling:
    """Tests for error handling in auth endpoints."""

    @pytest.mark.asyncio
    async def test_register_empty_email(self, async_client: AsyncClient):
        """Test registration with empty email."""
        response = await async_client.post(
            "/auth/register",
            json={
                "email": "",
                "password": "SecurePassword123",
            },
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_register_empty_password(self, async_client: AsyncClient):
        """Test registration with empty password."""
        response = await async_client.post(
            "/auth/register",
            json={
                "email": "user@example.com",
                "password": "",
            },
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_register_very_long_password(self, async_client: AsyncClient):
        """Test registration with very long password."""
        response = await async_client.post(
            "/auth/register",
            json={
                "email": "user@example.com",
                "password": "x" * 1001,  # More than max
            },
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_login_with_get_request(self, async_client: AsyncClient):
        """Test that login endpoint doesn't accept GET."""
        response = await async_client.get("/auth/login")

        assert response.status_code == 405  # Method not allowed

    @pytest.mark.asyncio
    async def test_register_with_get_request(self, async_client: AsyncClient):
        """Test that register endpoint doesn't accept GET."""
        response = await async_client.get("/auth/register")

        assert response.status_code == 405  # Method not allowed
