"""
SilverTrade AI — Feature Gates
==============================
Subscription tier enforcement and feature access control.
"""

from functools import wraps
from flask import g, jsonify

PLAN_LIMITS = {
    'free': {
        'signals_per_month': 50,
        'brokers': 1,
        'chat_per_day': 20,
        'auto_execute': False,
        'signal_history_days': 7,
        'missed_opportunities_days': 7,
        'telegram_alerts': False,
        'api_access': False,
    },
    'pro': {
        'signals_per_month': -1,  # Unlimited
        'brokers': 3,
        'chat_per_day': -1,  # Unlimited
        'auto_execute': True,
        'signal_history_days': 90,
        'missed_opportunities_days': 90,
        'telegram_alerts': True,
        'api_access': True,
    },
    'enterprise': {
        'signals_per_month': -1,  # Unlimited
        'brokers': -1,  # Unlimited
        'chat_per_day': -1,  # Unlimited
        'auto_execute': True,
        'signal_history_days': 365,
        'missed_opportunities_days': 365,
        'telegram_alerts': True,
        'api_access': True,
    },
}

PLAN_RANK = {'free': 0, 'pro': 1, 'enterprise': 2}


def require_plan(min_plan: str):
    """Decorator: blocks endpoint if user's plan is below required."""
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            user_plan = getattr(g, 'user_plan', 'free')
            if PLAN_RANK.get(user_plan, 0) < PLAN_RANK[min_plan]:
                return jsonify({
                    'status': 'error',
                    'code': 'PLAN_LIMIT',
                    'message': f'This feature requires {min_plan} plan.',
                    'upgrade_url': '/pricing',
                }), 402
            return f(*args, **kwargs)
        return decorator
    return decorator


def check_signal_limit(user_signals_used: int, user_plan: str) -> tuple[bool, str]:
    """Check if user has exceeded monthly signal limit.
    
    Returns (can_proceed, error_message)
    """
    limits = PLAN_LIMITS.get(user_plan, PLAN_LIMITS['free'])
    limit = limits['signals_per_month']
    
    if limit == -1:  # Unlimited
        return True, None
    
    if user_signals_used >= limit:
        return False, f"Monthly signal limit ({limit}) reached. Upgrade to Pro for unlimited signals."
    
    return True, None


def check_feature(feature: str, user_plan: str) -> bool:
    """Check if user's plan includes a specific feature."""
    limits = PLAN_LIMITS.get(user_plan, PLAN_LIMITS['free'])
    return limits.get(feature, False)


def get_plan_limits(user_plan: str) -> dict:
    """Get limits for a specific plan."""
    return PLAN_LIMITS.get(user_plan, PLAN_LIMITS['free'])
