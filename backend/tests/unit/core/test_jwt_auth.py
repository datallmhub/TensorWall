"""Unit tests for JWT authentication module."""

import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, AsyncMock
from fastapi import HTTPException

from backend.core.jwt_auth import (
    TokenPayload,
    AuthenticatedUser,
    verify_password,
    hash_password,
    create_access_token,
    create_refresh_token,
    decode_token,
    set_auth_cookies,
    clear_auth_cookies,
    get_role_permissions,
    get_current_user,
    get_current_user_optional,
)
from backend.db.models import User, UserRole


class TestPasswordHashing:
    """Tests for password hashing functions."""

    def test_hash_password(self):
        """Test password hashing produces different hash."""
        password = "mysecretpassword"
        hashed = hash_password(password)

        assert hashed != password
        assert len(hashed) > 20  # bcrypt hashes are long

    def test_hash_password_unique(self):
        """Test same password produces different hashes (salt)."""
        password = "mysecretpassword"
        hash1 = hash_password(password)
        hash2 = hash_password(password)

        assert hash1 != hash2  # Different salts

    def test_verify_password_correct(self):
        """Test verifying correct password."""
        password = "mysecretpassword"
        hashed = hash_password(password)

        assert verify_password(password, hashed) is True

    def test_verify_password_incorrect(self):
        """Test verifying incorrect password."""
        password = "mysecretpassword"
        hashed = hash_password(password)

        assert verify_password("wrongpassword", hashed) is False


class TestTokenPayload:
    """Tests for TokenPayload model."""

    def test_creation(self):
        """Test TokenPayload creation."""
        payload = TokenPayload(
            sub="user@example.com",
            user_id=1,
            role="admin",
            exp=datetime.now(timezone.utc) + timedelta(hours=1),
            type="access",
        )

        assert payload.sub == "user@example.com"
        assert payload.user_id == 1
        assert payload.role == "admin"
        assert payload.type == "access"


class TestAuthenticatedUser:
    """Tests for AuthenticatedUser model."""

    def test_creation(self):
        """Test AuthenticatedUser creation."""
        user = AuthenticatedUser(
            id=1,
            email="user@example.com",
            name="Test User",
            role="admin",
            permissions=["read", "write"],
        )

        assert user.id == 1
        assert user.email == "user@example.com"
        assert "read" in user.permissions


class TestTokenCreation:
    """Tests for token creation functions."""

    def test_create_access_token(self):
        """Test creating access token."""
        user = MagicMock(spec=User)
        user.id = 1
        user.email = "user@example.com"
        user.role = UserRole.ADMIN

        token = create_access_token(user)

        assert isinstance(token, str)
        assert len(token) > 50  # JWT tokens are long

    def test_create_refresh_token(self):
        """Test creating refresh token."""
        user = MagicMock(spec=User)
        user.id = 1
        user.email = "user@example.com"
        user.role = UserRole.VIEWER

        token = create_refresh_token(user)

        assert isinstance(token, str)
        assert len(token) > 50

    def test_access_token_is_decodable(self):
        """Test access token can be decoded."""
        user = MagicMock(spec=User)
        user.id = 42
        user.email = "test@example.com"
        user.role = UserRole.DEVELOPER

        token = create_access_token(user)
        payload = decode_token(token)

        assert payload is not None
        assert payload.sub == "test@example.com"
        assert payload.user_id == 42
        assert payload.role == "developer"
        assert payload.type == "access"

    def test_refresh_token_is_decodable(self):
        """Test refresh token can be decoded."""
        user = MagicMock(spec=User)
        user.id = 42
        user.email = "test@example.com"
        user.role = UserRole.ADMIN

        token = create_refresh_token(user)
        payload = decode_token(token)

        assert payload is not None
        assert payload.type == "refresh"


class TestTokenDecoding:
    """Tests for token decoding."""

    def test_decode_valid_token(self):
        """Test decoding valid token."""
        user = MagicMock(spec=User)
        user.id = 1
        user.email = "user@example.com"
        user.role = UserRole.ADMIN

        token = create_access_token(user)
        payload = decode_token(token)

        assert payload is not None
        assert payload.sub == "user@example.com"

    def test_decode_invalid_token(self):
        """Test decoding invalid token returns None."""
        payload = decode_token("invalid.token.here")
        assert payload is None

    def test_decode_malformed_token(self):
        """Test decoding malformed token returns None."""
        payload = decode_token("not-a-jwt")
        assert payload is None


class TestCookieFunctions:
    """Tests for cookie management functions."""

    def test_set_auth_cookies(self):
        """Test setting authentication cookies."""
        response = MagicMock()

        set_auth_cookies(response, "access_token_value", "refresh_token_value")

        assert response.set_cookie.call_count == 2

        # Check access token cookie
        calls = response.set_cookie.call_args_list
        access_call = [c for c in calls if c.kwargs.get("key") == "access_token"][0]
        assert access_call.kwargs["value"] == "access_token_value"
        assert access_call.kwargs["httponly"] is True

        # Check refresh token cookie
        refresh_call = [c for c in calls if c.kwargs.get("key") == "refresh_token"][0]
        assert refresh_call.kwargs["value"] == "refresh_token_value"

    def test_clear_auth_cookies(self):
        """Test clearing authentication cookies."""
        response = MagicMock()

        clear_auth_cookies(response)

        assert response.delete_cookie.call_count == 2
        calls = response.delete_cookie.call_args_list
        cookie_names = [c[0][0] for c in calls]
        assert "access_token" in cookie_names
        assert "refresh_token" in cookie_names


class TestGetRolePermissions:
    """Tests for role permissions lookup."""

    def test_admin_permissions(self):
        """Test admin role has permissions."""
        permissions = get_role_permissions("admin")
        assert len(permissions) > 0

    def test_viewer_permissions(self):
        """Test viewer role has limited permissions."""
        permissions = get_role_permissions("viewer")
        assert isinstance(permissions, list)

    def test_invalid_role_returns_empty(self):
        """Test invalid role returns empty list."""
        permissions = get_role_permissions("invalid_role")
        assert permissions == []


class TestGetCurrentUser:
    """Tests for get_current_user dependency."""

    @pytest.mark.asyncio
    async def test_no_token_raises_401(self):
        """Test missing token raises 401."""
        request = MagicMock()
        request.cookies.get.return_value = None
        db = AsyncMock()

        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(request, db)

        assert exc_info.value.status_code == 401
        assert "Not authenticated" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_invalid_token_raises_401(self):
        """Test invalid token raises 401."""
        request = MagicMock()
        request.cookies.get.return_value = "invalid.token"
        db = AsyncMock()

        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(request, db)

        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_refresh_token_not_accepted(self):
        """Test refresh token is not accepted as access token."""
        user = MagicMock(spec=User)
        user.id = 1
        user.email = "user@example.com"
        user.role = UserRole.ADMIN

        refresh_token = create_refresh_token(user)

        request = MagicMock()
        request.cookies.get.return_value = refresh_token
        db = AsyncMock()

        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(request, db)

        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_valid_token_returns_user(self):
        """Test valid token returns authenticated user."""
        # Create a real user mock
        db_user = MagicMock(spec=User)
        db_user.id = 1
        db_user.email = "user@example.com"
        db_user.name = "Test User"
        db_user.role = UserRole.ADMIN
        db_user.is_active = True

        # Create token
        access_token = create_access_token(db_user)

        request = MagicMock()
        request.cookies.get.return_value = access_token

        # Mock database
        db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = db_user
        db.execute.return_value = mock_result

        result = await get_current_user(request, db)

        assert result.id == 1
        assert result.email == "user@example.com"
        assert result.role == "admin"

    @pytest.mark.asyncio
    async def test_user_not_found_raises_401(self):
        """Test deactivated user raises 401."""
        db_user = MagicMock(spec=User)
        db_user.id = 1
        db_user.email = "user@example.com"
        db_user.role = UserRole.ADMIN

        access_token = create_access_token(db_user)

        request = MagicMock()
        request.cookies.get.return_value = access_token

        # Mock database returning None (user not found)
        db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        db.execute.return_value = mock_result

        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(request, db)

        assert exc_info.value.status_code == 401
        assert "not found" in exc_info.value.detail.lower()


class TestGetCurrentUserOptional:
    """Tests for get_current_user_optional dependency."""

    @pytest.mark.asyncio
    async def test_no_token_returns_none(self):
        """Test missing token returns None."""
        request = MagicMock()
        request.cookies.get.return_value = None
        db = AsyncMock()

        result = await get_current_user_optional(request, db)

        assert result is None

    @pytest.mark.asyncio
    async def test_invalid_token_returns_none(self):
        """Test invalid token returns None."""
        request = MagicMock()
        request.cookies.get.return_value = "invalid.token"
        db = AsyncMock()

        result = await get_current_user_optional(request, db)

        assert result is None

    @pytest.mark.asyncio
    async def test_valid_token_returns_user(self):
        """Test valid token returns authenticated user."""
        db_user = MagicMock(spec=User)
        db_user.id = 1
        db_user.email = "user@example.com"
        db_user.name = "Test User"
        db_user.role = UserRole.DEVELOPER

        access_token = create_access_token(db_user)

        request = MagicMock()
        request.cookies.get.return_value = access_token

        db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = db_user
        db.execute.return_value = mock_result

        result = await get_current_user_optional(request, db)

        assert result is not None
        assert result.email == "user@example.com"
