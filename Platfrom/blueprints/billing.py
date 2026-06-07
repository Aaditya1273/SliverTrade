"""
SilverTrade AI — Billing Blueprint
=================================
Stripe billing endpoints for subscription management.
"""

import logging
from datetime import datetime
from flask import Blueprint, jsonify, request, session

from limiter import limiter
from services.billing_service import billing_service
from utils.tenant_context import get_user_id

from database.user_db import User

logger = logging.getLogger(__name__)

billing_bp = Blueprint('billing', __name__, url_prefix='/billing')
API_RATE_LIMIT = "20 per minute"


@billing_bp.route('/checkout', methods=['POST'])
@limiter.limit(API_RATE_LIMIT)
def create_checkout():
    """Create Stripe checkout session for plan upgrade."""
    try:
        if not billing_service.is_available():
            return jsonify({
                "status": "error",
                "message": "Billing service not available"
            }), 503
        
        data = request.json
        plan = data.get('plan')
        interval = data.get('interval', 'month')
        
        if plan not in ['pro', 'enterprise']:
            return jsonify({
                "status": "error",
                "message": "Invalid plan"
            }), 400
        
        if interval not in ['month', 'year']:
            return jsonify({
                "status": "error",
                "message": "Invalid interval. Must be 'month' or 'year'."
            }), 400
        
        user_id = get_user_id()
        
        checkout_url = billing_service.create_checkout_session(user_id, plan, interval)
        
        if not checkout_url:
            return jsonify({
                "status": "error",
                "message": "Failed to create checkout session"
            }), 500
        
        return jsonify({
            "status": "success",
            "checkout_url": checkout_url
        })
        
    except Exception as e:
        logger.exception("Checkout creation error: %s", e)
        return jsonify({
            "status": "error",
            "message": "Failed to create checkout"
        }), 500


@billing_bp.route('/portal', methods=['GET'])
@limiter.limit(API_RATE_LIMIT)
def customer_portal():
    """Get Stripe Customer Portal URL for subscription management."""
    try:
        if not billing_service.is_available():
            return jsonify({
                "status": "error",
                "message": "Billing service not available"
            }), 503
        
        user_id = get_user_id()
        
        portal_url = billing_service.create_customer_portal_session(user_id)
        
        if not portal_url:
            return jsonify({
                "status": "error",
                "message": "Failed to create portal session"
            }), 500
        
        return jsonify({
            "status": "success",
            "portal_url": portal_url
        })
        
    except Exception as e:
        logger.exception("Portal creation error: %s", e)
        return jsonify({
            "status": "error",
            "message": "Failed to create portal"
        }), 500


# Plan-level feature limits — maps plan name to its caps.
# These are the server-side source of truth; the frontend PLANS array
# should match for display.
PLAN_LIMITS = {
    "free": {
        "signals_per_month": 50,
        "active_strategies": 1,
        "python_strategies": 0,
        "chartink_strategies": 1,
        "flow_workflows": 1,
        "api_rate_limit": "20 per minute",
        "has_telegram_charts": False,
        "has_option_chain": False,
        "has_python_engine": False,
        "has_flow_editor": False,
        "has_multiple_brokers": False,
        "has_advanced_analytics": False,
        "has_dedicated_support": False,
    },
    "pro": {
        "signals_per_month": 10000,
        "active_strategies": None,  # unlimited
        "python_strategies": 10,
        "chartink_strategies": None,  # unlimited
        "flow_workflows": 10,
        "api_rate_limit": "60 per minute",
        "has_telegram_charts": True,
        "has_option_chain": True,
        "has_python_engine": True,
        "has_flow_editor": True,
        "has_multiple_brokers": False,
        "has_advanced_analytics": True,
        "has_dedicated_support": False,
    },
    "enterprise": {
        "signals_per_month": None,  # unlimited
        "active_strategies": None,  # unlimited
        "python_strategies": None,  # unlimited
        "chartink_strategies": None,  # unlimited
        "flow_workflows": None,  # unlimited
        "api_rate_limit": "120 per minute",
        "has_telegram_charts": True,
        "has_option_chain": True,
        "has_python_engine": True,
        "has_flow_editor": True,
        "has_multiple_brokers": True,
        "has_advanced_analytics": True,
        "has_dedicated_support": True,
    },
}


@billing_bp.route('/subscription', methods=['GET'])
@limiter.limit(API_RATE_LIMIT)
def get_subscription():
    """Get the current user's subscription status, usage, and plan limits."""
    try:
        user_id = get_user_id()
        user = User.query.get(user_id)

        if not user:
            return jsonify({
                "status": "error",
                "message": "User not found"
            }), 404

        plan = user.plan or "free"
        is_active = plan in ("pro", "enterprise") and (
            user.plan_expires_at is None or user.plan_expires_at > datetime.utcnow()
        )
        limits = PLAN_LIMITS.get(plan, PLAN_LIMITS["free"])

        return jsonify({
            "status": "success",
            "subscription": {
                "plan": plan,
                "plan_expires_at": user.plan_expires_at.isoformat() if user.plan_expires_at else None,
                "stripe_customer_id": user.stripe_customer_id,
                "is_active": is_active,
                "usage": {
                    "signals_used_this_month": user.signals_used_this_month or 0,
                    "signals_limit": limits["signals_per_month"],
                    "signals_remaining": (
                        None if limits["signals_per_month"] is None
                        else max(0, limits["signals_per_month"] - (user.signals_used_this_month or 0))
                    ),
                },
                "limits": limits,
            }
        })

    except Exception as e:
        logger.exception("Subscription fetch error: %s", e)
        return jsonify({
            "status": "error",
            "message": "Failed to fetch subscription"
        }), 500


@billing_bp.route('/webhook', methods=['POST'])
def stripe_webhook():
    """Handle Stripe webhook events."""
    try:
        payload = request.data
        sig_header = request.headers.get('Stripe-Signature')
        
        if not payload or not sig_header:
            return jsonify({"status": "error", "message": "Missing payload or signature"}), 400
        
        success = billing_service.handle_webhook(payload, sig_header)
        
        if success:
            return jsonify({"status": "success"}), 200
        else:
            return jsonify({"status": "error", "message": "Webhook handling failed"}), 500
            
    except Exception as e:
        logger.exception("Webhook error: %s", e)
        return jsonify({"status": "error", "message": "Webhook error"}), 500
