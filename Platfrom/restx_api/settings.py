import os

from flask import jsonify, make_response, request
from flask_restx import Namespace, Resource, fields

from database.settings_db import get_user_settings, set_user_settings
from utils.logging import get_logger
from utils.session import check_session_validity

logger = get_logger(__name__)

api = Namespace("settings", description="User Trading Settings API")

# API model for swagger docs
settings_model = api.model(
    "Settings",
    {
        "default_exchange": fields.String(description="Default exchange (NSE/BSE/CRYPTO)"),
        "default_product_type": fields.String(description="Default product type (CNC/NRML/MIS)"),
        "default_order_type": fields.String(description="Default order type (MARKET/LIMIT)"),
        "risk_per_trade_pct": fields.Integer(description="Risk per trade as % of capital (1-5)"),
        "min_signal_confidence": fields.Integer(
            description="Minimum signal confidence to execute (50-95)"
        ),
        "max_open_positions": fields.Integer(description="Maximum concurrent open positions"),
        "daily_loss_limit_pct": fields.Integer(
            description="Stop trading if daily P&L drops below -X%"
        ),
        "auto_execute": fields.Boolean(
            description="Auto-execute signals above confidence threshold"
        ),
    },
)


@api.route("/", strict_slashes=False)
class UserSettingsResource(Resource):
    @check_session_validity
    def get(self):
        """Get current user's trading settings."""
        from flask import session

        username = session["user"]

        try:
            settings = get_user_settings(username)
            return make_response(jsonify({"status": "success", "data": settings}), 200)
        except Exception as e:
            logger.exception(f"Error getting user settings: {e}")
            return make_response(
                jsonify({"status": "error", "message": "Failed to get settings"}), 500
            )

    @check_session_validity
    def post(self):
        """Save user's trading settings."""
        from flask import session

        username = session["user"]

        try:
            data = request.json
            if not data:
                return make_response(
                    jsonify({"status": "error", "message": "No settings data provided"}), 400
                )

            # Validate risk_per_trade_pct range
            risk = data.get("risk_per_trade_pct")
            if risk is not None and (risk < 0.5 or risk > 5):
                return make_response(
                    jsonify(
                        {"status": "error", "message": "Risk per trade must be between 0.5% and 5%"}
                    ),
                    400,
                )

            # Validate min_signal_confidence range
            confidence = data.get("min_signal_confidence")
            if confidence is not None and (confidence < 50 or confidence > 95):
                return make_response(
                    jsonify(
                        {
                            "status": "error",
                            "message": "Minimum signal confidence must be between 50% and 95%",
                        }
                    ),
                    400,
                )

            # Save settings
            success = set_user_settings(username, data)
            if success:
                return make_response(
                    jsonify({"status": "success", "message": "Settings saved successfully"}), 200
                )
            else:
                return make_response(
                    jsonify({"status": "error", "message": "Failed to save settings"}), 500
                )

        except Exception as e:
            logger.exception(f"Error saving user settings: {e}")
            return make_response(
                jsonify({"status": "error", "message": "Failed to save settings"}), 500
            )
