from flask import Blueprint, jsonify, request
from utils.logging import get_logger
import datetime
import random

logger = get_logger(__name__)

signals_bp = Blueprint("signals_bp", __name__, url_prefix="/api/v1/signals")

# In-memory storage for signals (production would use a DB)
signals_history = []

@signals_bp.route("/", methods=["GET"])
def get_signals():
    """Get all signals with filtering"""
    symbol = request.args.get("symbol")
    limit = int(request.args.get("limit", 20))
    
    filtered = signals_history
    if symbol:
        filtered = [s for s in signals_history if s["symbol"] == symbol]
        
    return jsonify({
        "status": "success",
        "count": len(filtered[:limit]),
        "signals": filtered[:limit]
    })

@signals_bp.route("/latest", methods=["GET"])
def get_latest_signal():
    """Get the most recent signal"""
    if not signals_history:
        return jsonify({"status": "error", "message": "No signals available"}), 404
        
    return jsonify({
        "status": "success",
        "signal": signals_history[0]
    })

@signals_bp.route("/generate-mock", methods=["POST"])
def generate_mock_signal():
    """Force generate a signal for testing the frontend pipe"""
    symbols = ["BTC/USDT", "ETH/USDT", "SOL/USDT", "BNB/USDT"]
    decisions = ["BUY", "SELL", "HOLD"]
    
    symbol = random.choice(symbols)
    decision = random.choice(decisions)
    confidence = round(random.uniform(70, 98), 2)
    
    new_signal = {
        "id": str(len(signals_history) + 1),
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "symbol": symbol,
        "decision": decision,
        "confidence": confidence,
        "reasoning": f"Pattern detection on {symbol} indicates a strong {decision} trend based on volume surge and RSI divergence.",
        "price": round(random.uniform(100, 60000), 2),
        "urgency": "HIGH" if confidence > 90 else "MEDIUM"
    }
    
    signals_history.insert(0, new_signal)
    
    return jsonify({
        "status": "success",
        "signal": new_signal
    })
