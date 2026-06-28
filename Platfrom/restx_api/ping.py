import os

from flask import jsonify, make_response, request
from flask_restx import Namespace, Resource
from marshmallow import ValidationError

from limiter import limiter
from services.ping_service import get_ping
from utils.logging import get_logger

from .account_schema import PingSchema

API_RATE_LIMIT = os.getenv("API_RATE_LIMIT", "10 per second")
api = Namespace("ping", description="Ping API to check connectivity and authentication")

# Initialize logger
logger = get_logger(__name__)

# Initialize schema
ping_schema = PingSchema()


@api.route("/", strict_slashes=False)
class Ping(Resource):
    @limiter.limit(API_RATE_LIMIT)
    def get(self):
        """Check API connectivity and authentication (via GET)"""
        try:
            # For GET requests, parameters are in request.args
            api_key = request.args.get("apikey")
            if not api_key:
                return make_response(
                    jsonify(
                        {
                            "status": "error",
                            "message": {"apikey": ["Missing data for required field."]},
                        }
                    ),
                    400,
                )

            # Call the service function to get ping response with API key
            success, response_data, status_code = get_ping(api_key=api_key)
            return make_response(jsonify(response_data), status_code)

        except Exception as e:
            logger.exception(f"Unexpected error in ping GET endpoint: {e}")
            return make_response(
                jsonify({"status": "error", "message": "An unexpected error occurred"}), 500
            )

    @limiter.limit(API_RATE_LIMIT)
    def post(self):
        """Check API connectivity and authentication (via POST)"""
        try:
            # Validate request data
            ping_data = ping_schema.load(request.json)

            api_key = ping_data["apikey"]

            # Call the service function to get ping response with API key
            success, response_data, status_code = get_ping(api_key=api_key)
            return make_response(jsonify(response_data), status_code)

        except ValidationError as err:
            return make_response(jsonify({"status": "error", "message": err.messages}), 400)
        except Exception as e:
            logger.exception(f"Unexpected error in ping POST endpoint: {e}")
            return make_response(
                jsonify({"status": "error", "message": "An unexpected error occurred"}), 500
            )
