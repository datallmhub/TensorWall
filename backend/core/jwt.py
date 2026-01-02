"""
JWT token handling for user authentication.

Provides functions to:
- Decode JWT tokens
- Extract user information
- Validate token signatures
"""

import logging
from typing import Optional
from fastapi import Header, HTTPException, status
from jose import JWTError, jwt
from datetime import datetime

from backend.core.config import settings

logger = logging.getLogger(__name__)

# JWT Configuration
ALGORITHM = "HS256"
SECRET_KEY = getattr(settings, "jwt_secret_key", "dev-secret-key-change-in-production")


class TokenPayload:
    """JWT Token payload"""

    def __init__(self, user_id: int, email: str, exp: Optional[datetime] = None):
        self.user_id = user_id
        self.email = email
        self.exp = exp


def decode_jwt_token(token: str) -> Optional[TokenPayload]:
    """
    Decode a JWT token and extract user information.

    Args:
        token: JWT token string

    Returns:
        TokenPayload if valid, None otherwise
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: int = payload.get("sub")
        email: str = payload.get("email")

        if user_id is None:
            return None

        return TokenPayload(user_id=int(user_id), email=email)

    except JWTError as e:
        logger.warning(f"JWT decode error: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error decoding JWT: {e}")
        return None


async def get_current_user_id(
    authorization: Optional[str] = Header(None, alias="Authorization"),
) -> int:
    """
    Extract user_id from JWT token in Authorization header.

    Falls back to user_id=1 for development if no token provided.

    Args:
        authorization: Authorization header with Bearer token

    Returns:
        user_id extracted from token

    Raises:
        HTTPException: If token is invalid or missing in production
    """
    # Development fallback
    if not authorization:
        logger.warning(
            "No Authorization header, using default user_id=1 for development"
        )
        return 1

    # Extract token from "Bearer <token>"
    if not authorization.startswith("Bearer "):
        logger.warning("Invalid Authorization header format, using default user_id=1")
        return 1

    token = authorization.replace("Bearer ", "")

    # Decode token
    payload = decode_jwt_token(token)

    if not payload:
        logger.warning("Invalid JWT token, using default user_id=1 for development")
        return 1

    logger.debug(f"Extracted user_id={payload.user_id} from JWT token")
    return payload.user_id


async def require_user_id(
    authorization: Optional[str] = Header(None, alias="Authorization"),
) -> int:
    """
    Extract user_id from JWT token - strict mode (no fallback).

    Args:
        authorization: Authorization header with Bearer token

    Returns:
        user_id extracted from token

    Raises:
        HTTPException: If token is invalid or missing
    """
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization header",
        )

    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Authorization header format",
        )

    token = authorization.replace("Bearer ", "")
    payload = decode_jwt_token(token)

    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token"
        )

    return payload.user_id


# Optional: For compatibility with existing code
async def get_current_user_id_optional(
    authorization: Optional[str] = Header(None, alias="Authorization"),
) -> Optional[int]:
    """
    Extract user_id from JWT token - returns None if not found.

    Args:
        authorization: Authorization header with Bearer token

    Returns:
        user_id if token is valid, None otherwise
    """
    if not authorization or not authorization.startswith("Bearer "):
        return None

    token = authorization.replace("Bearer ", "")
    payload = decode_jwt_token(token)

    return payload.user_id if payload else None
