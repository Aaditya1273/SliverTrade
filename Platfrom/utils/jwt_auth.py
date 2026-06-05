"""JWT-based authentication for SilverTrade AI.

Provides access tokens (short-lived, 15 min) and refresh tokens (long-lived, 7 days)
for stateless API authentication. Compatible with existing session-based auth for
legacy API consumers during the migration period.

Usage:
    from utils.jwt_auth import (
        create_access_token, create_refresh_token,
        decode_token, jwt_required, get_current_user
    )

    # Flask route
    @app.route('/api/v1/secure-endpoint')
    @jwt_required
    def secure_route():
        user = get_current_user()
        return jsonify({"user_id": user["sub"], "org_id": user["org"]})
"""

import os
import datetime
from typing import Any, Dict, Optional, Tuple
from functools import wraps

import jwt as pyjwt
from flask import request, jsonify, g, current_app

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

# Use APP_KEY as the JWT secret by default, or a dedicated JWT_SECRET
JWT_SECRET = os.getenv("JWT_SECRET") or os.getenv("APP_KEY", "")
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRY_MINUTES = int(os.getenv("JWT_ACCESS_EXPIRY", "15"))
REFRESH_TOKEN_EXPIRY_DAYS = int(os.getenv("JWT_REFRESH_EXPIRY", "7"))


# ---------------------------------------------------------------------------
# Token Creation
# ---------------------------------------------------------------------------

def create_access_token(
    user_id: str,
    organization_id: Optional[str] = None,
    role: str = "member",
    username: Optional[str] = None,
) -> str:
    """Create a short-lived JWT access token.

    Args:
        user_id: Unique identifier for the user.
        organization_id: Organization the user belongs to.
        role: User role (admin, trader, viewer, member).
        username: Display name for the user.

    Returns:
        Encoded JWT string.
    """
    now = datetime.datetime.now(datetime.timezone.utc)
    payload = {
        "sub": user_id,
        "org": organization_id,
        "role": role,
        "type": "access",
        "iat": now,
        "exp": now + datetime.timedelta(minutes=ACCESS_TOKEN_EXPIRY_MINUTES),
    }
    if username:
        payload["name"] = username

    return pyjwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def create_refresh_token(user_id: str) -> Tuple[str, datetime.datetime]:
    """Create a long-lived refresh token.

    Args:
        user_id: Unique identifier for the user.

    Returns:
        Tuple of (encoded JWT string, expiration datetime).
    """
    now = datetime.datetime.now(datetime.timezone.utc)
    expiry = now + datetime.timedelta(days=REFRESH_TOKEN_EXPIRY_DAYS)
    payload = {
        "sub": user_id,
        "type": "refresh",
        "jti": _generate_token_id(),
        "iat": now,
        "exp": expiry,
    }
    return pyjwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM), expiry


# ---------------------------------------------------------------------------
# Token Verification
# ---------------------------------------------------------------------------

def decode_token(token: str) -> Optional[Dict[str, Any]]:
    """Decode and verify a JWT token.

    Args:
        token: The JWT string to decode.

    Returns:
        Decoded payload dict, or None if the token is invalid/expired.
    """
    try:
        payload = pyjwt.decode(
            token,
            JWT_SECRET,
            algorithms=[JWT_ALGORITHM],
            options={"verify_exp": True},
        )
        return payload
    except pyjwt.ExpiredSignatureError:
        return None
    except pyjwt.InvalidTokenError:
        return None


def refresh_access_token(refresh_token: str) -> Optional[Dict[str, str]]:
    """Exchange a refresh token for a new access token.

    Args:
        refresh_token: Valid refresh token string.

    Returns:
        Dict with new access_token and expires_in, or None if invalid.
    """
    payload = decode_token(refresh_token)
    if not payload or payload.get("type") != "refresh":
        return None

    user_id = payload.get("sub")
    if not user_id:
        return None

    # Check blacklist (requires Redis)
    token_jti = payload.get("jti")
    if token_jti and _is_token_blacklisted(token_jti):
        return None

    new_token = create_access_token(user_id)
    return {
        "access_token": new_token,
        "token_type": "Bearer",
        "expires_in": ACCESS_TOKEN_EXPIRY_MINUTES * 60,
    }


# ---------------------------------------------------------------------------
# Flask Middleware
# ---------------------------------------------------------------------------

def jwt_required(f):
    """Decorator to require a valid JWT access token.

    Extracts the token from the Authorization header (Bearer scheme),
    verifies it, and populates g.user_id, g.organization_id, and g.user_role.

    Usage:
        @app.route('/api/protected')
        @jwt_required
        def protected_route():
            return jsonify({"user_id": g.user_id})
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        token = _extract_token()
        if not token:
            return jsonify({
                "status": "error",
                "message": "Authentication required. Provide a Bearer token in the Authorization header.",
                "error_code": "AUTH_REQUIRED",
            }), 401

        payload = decode_token(token)
        if not payload:
            return jsonify({
                "status": "error",
                "message": "Invalid or expired token. Use /api/v1/auth/refresh to obtain a new token.",
                "error_code": "TOKEN_INVALID",
            }), 401

        if payload.get("type") != "access":
            return jsonify({
                "status": "error",
                "message": "Invalid token type. Use an access token, not a refresh token.",
                "error_code": "TOKEN_TYPE_INVALID",
            }), 401

        # Populate Flask g object for downstream use
        g.user_id = payload.get("sub")
        g.organization_id = payload.get("org")
        g.user_role = payload.get("role", "member")
        g.jwt_payload = payload

        return f(*args, **kwargs)

    return decorated


def optional_jwt(f):
    """Decorator that optionally extracts JWT info without requiring it.

    If a valid token is present, populates g.user_id etc.
    If not, leaves them as None and continues execution.
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        token = _extract_token()
        if token:
            payload = decode_token(token)
            if payload and payload.get("type") == "access":
                g.user_id = payload.get("sub")
                g.organization_id = payload.get("org")
                g.user_role = payload.get("role", "member")

        return f(*args, **kwargs)

    return decorated


# ---------------------------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------------------------

def get_current_user() -> Optional[Dict[str, Any]]:
    """Get the currently authenticated user from g.

    Returns:
        Dict with user info, or None if no user is authenticated.
    """
    user_id = getattr(g, "user_id", None)
    if not user_id:
        return None
    return {
        "sub": user_id,
        "org": getattr(g, "organization_id", None),
        "role": getattr(g, "user_role", "member"),
    }


def _extract_token() -> Optional[str]:
    """Extract Bearer token from the Authorization header.

    Checks the Authorization header first, then falls back to
    the access_token cookie (for browser-based auth).

    Returns:
        The token string, or None if not found.
    """
    # Check Authorization header first
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        return auth_header[7:]

    # Fall back to cookie (for browser-based clients)
    token = request.cookies.get("access_token")
    if token:
        return token

    return None


def _generate_token_id() -> str:
    """Generate a unique token ID for refresh token tracking."""
    import secrets
    return secrets.token_hex(16)


# ---------------------------------------------------------------------------
# Token Blacklisting (Redis-backed)
# ---------------------------------------------------------------------------

def _is_token_blacklisted(token_jti: str) -> bool:
    """Check if a token has been blacklisted.

    Requires Redis to be configured. Falls back to False if Redis is unavailable.

    Args:
        token_jti: The unique identifier of the token.

    Returns:
        True if the token is blacklisted, False otherwise.
    """
    from extensions import redis_client
    if redis_client is None:
        return False
    try:
        return redis_client.exists(f"token_blacklist:{token_jti}") > 0
    except Exception:
        return False


def blacklist_token(token_jti: str, expires_at: Optional[datetime.datetime] = None) -> None:
    """Blacklist a refresh token so it cannot be used again.

    Args:
        token_jti: The unique identifier of the token to blacklist.
        expires_at: When the token naturally expires (used for TTL).
    """
    from extensions import redis_client
    if redis_client is None:
        return

    try:
        # Calculate TTL: how long until the token would expire naturally
        if expires_at:
            now = datetime.datetime.now(datetime.timezone.utc)
            ttl = int((expires_at - now).total_seconds())
            if ttl > 0:
                redis_client.setex(f"token_blacklist:{token_jti}", ttl, "1")
            else:
                # Token already expired, no need to blacklist
                pass
        else:
            # Default TTL: 7 days
            redis_client.setex(f"token_blacklist:{token_jti}", 604800, "1")
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Legacy Session Compatibility
# ---------------------------------------------------------------------------

def add_deprecation_header(response):
    """Add a deprecation warning header to session-based auth responses.

    Usage:
        from utils.jwt_auth import add_deprecation_header
        response = jsonify(...)
        add_deprecation_header(response)
        return response
    """
    response.headers["X-Auth-Deprecation"] = (
        "Session-based auth is deprecated. "
        "Use /api/v1/auth/login with Authorization: Bearer <token> for JWT auth."
    )
    return response
