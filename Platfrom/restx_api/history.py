import os

from flask import jsonify, make_response, request
from flask_restx import Namespace, Resource
from marshmallow import ValidationError

from limiter import limiter
from services.history_service import get_history
from utils.logging import get_logger

from .data_schemas import HistorySchema

API_RATE_LIMIT = os.getenv("API_RATE_LIMIT", "10 per second")
api = Namespace("history", description="Historical Data API")

# Initialize logger
logger = get_logger(__name__)

# Initialize schema
history_schema = HistorySchema()


@api.route("/", strict_slashes=False)
class History(Resource):
    @limiter.limit(API_RATE_LIMIT)
    def get(self):
        """Get historical data for given symbol (via GET)"""
        try:
            # For GET requests, parameters are in request.args
            # We convert to a dict for schema validation
            data = request.args.to_dict()
            history_data = history_schema.load(data)

            return self._handle_history_request(history_data)

        except ValidationError as err:
            return make_response(jsonify({"status": "error", "message": err.messages}), 400)
        except Exception as e:
            logger.exception(f"Unexpected error in history GET endpoint: {e}")
            return make_response(
                jsonify({"status": "error", "message": "An unexpected error occurred"}), 500
            )

    @limiter.limit(API_RATE_LIMIT)
    def post(self):
        """Get historical data for given symbol (via POST)"""
        try:
            # Validate request data
            history_data = history_schema.load(request.json)
            return self._handle_history_request(history_data)

        except ValidationError as err:
            return make_response(jsonify({"status": "error", "message": err.messages}), 400)
        except Exception as e:
            logger.exception(f"Unexpected error in history POST endpoint: {e}")
            return make_response(
                jsonify({"status": "error", "message": "An unexpected error occurred"}), 500
            )

    def _handle_history_request(self, history_data):
        """Common logic for handling history requests"""
        try:
            api_key = history_data["apikey"]
            symbol = history_data["symbol"]
            exchange = history_data["exchange"]
            interval = history_data["interval"]
            start_date = history_data["start_date"]
            end_date = history_data["end_date"]
            source = history_data.get("source", "api")

            # Call the service function to get historical data with API key
            success, response_data, status_code = get_history(
                symbol=symbol,
                exchange=exchange,
                interval=interval,
                start_date=start_date,
                end_date=end_date,
                api_key=api_key,
                source=source,
            )

            return make_response(jsonify(response_data), status_code)
        except Exception as e:
            logger.exception(f"Unexpected error in _handle_history_request: {e}")
            raise e
