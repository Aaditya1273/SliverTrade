"""
SilverTrade AI — Tenant Context
===============================
Multi-tenancy utilities for ensuring user data isolation.
"""

from functools import wraps
from flask import g, request


class AuthorizationError(Exception):
    """Raised when user_id context is not set."""
    pass


def require_user_id(f):
    """Decorator that ensures user_id is in Flask g before any DB operation."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not hasattr(g, 'user_id') or not g.user_id:
            raise AuthorizationError("user_id context not set")
        return f(*args, **kwargs)
    return decorated


def get_user_id() -> int:
    """Get current user_id from Flask g or session."""
    if hasattr(g, 'user_id') and g.user_id:
        return g.user_id
    
    # Fallback to session
    from flask import session
    user_id = session.get('user_id')
    if user_id:
        return user_id
    
    raise AuthorizationError("No user context available")


def set_user_id(user_id: int):
    """Set user_id in Flask g for the current request."""
    g.user_id = user_id
