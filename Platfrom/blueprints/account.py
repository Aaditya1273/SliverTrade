"""
SilverTrade AI — Account Deletion Blueprint (Phase 10)
=====================================================
DPDP Act 2023 compliant account deletion and data export endpoints.
"""

import logging
from flask import Blueprint, jsonify, request, session

from limiter import limiter
from services.account_deletion_service import account_deletion_service
from utils.tenant_context import get_user_id

logger = logging.getLogger(__name__)

account_bp = Blueprint("account", __name__, url_prefix="/account")
API_RATE_LIMIT = "10 per minute"


@account_bp.route("/delete", methods=["POST"])
@limiter.limit(API_RATE_LIMIT)
def initiate_deletion():
    """Initiate account deletion with 24-hour grace period."""
    try:
        data = request.json
        password = data.get("password")

        if not password:
            return jsonify({"status": "error", "message": "Password required"}), 400

        user_id = get_user_id()

        success, message = account_deletion_service.initiate_deletion(user_id, password)

        if success:
            return jsonify({"status": "success", "message": message})
        else:
            return jsonify({"status": "error", "message": message}), 400

    except Exception as e:
        logger.exception("Deletion initiation error: %s", e)
        return jsonify({"status": "error", "message": "Failed to initiate deletion"}), 500


@account_bp.route("/cancel-deletion", methods=["POST"])
@limiter.limit(API_RATE_LIMIT)
def cancel_deletion():
    """Cancel pending account deletion."""
    try:
        data = request.json
        token = data.get("token")

        if not token:
            return jsonify({"status": "error", "message": "Token required"}), 400

        user_id = get_user_id()

        success, message = account_deletion_service.cancel_deletion(user_id, token)

        if success:
            return jsonify({"status": "success", "message": message})
        else:
            return jsonify({"status": "error", "message": message}), 400

    except Exception as e:
        logger.exception("Deletion cancellation error: %s", e)
        return jsonify({"status": "error", "message": "Failed to cancel deletion"}), 500


@account_bp.route("/export-data", methods=["GET"])
@limiter.limit(API_RATE_LIMIT)
def export_data():
    """Export all user data (DPDP compliance)."""
    try:
        user_id = get_user_id()

        success, data, message = account_deletion_service.export_user_data(user_id)

        if success:
            from flask import send_file
            from io import BytesIO

            buffer = BytesIO(data)
            filename = f"silvertrade_data_export_{user_id}_{datetime.now().strftime('%Y%m%d')}.zip"

            return send_file(
                buffer, mimetype="application/zip", as_attachment=True, download_name=filename
            )
        else:
            return jsonify({"status": "error", "message": message}), 400

    except Exception as e:
        logger.exception("Data export error: %s", e)
        return jsonify({"status": "error", "message": "Failed to export data"}), 500
