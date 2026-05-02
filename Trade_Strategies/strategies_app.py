from flask import Flask, jsonify, request
from flask_cors import CORS
import os
import random

app = Flask(__name__)
CORS(app)

# Mock model prediction logic (in production, this would call FinGPT)
def predict_decision(indicator_data):
    rsi = indicator_data.get('rsi', 50)
    ema_fast = indicator_data.get('ema_9', 0)
    ema_slow = indicator_data.get('ema_21', 0)
    
    confidence = 50
    decision = "HOLD"
    reasoning = "Neutral market conditions."
    
    if rsi < 30 and ema_fast > ema_slow:
        decision = "BUY"
        confidence = 85 + random.uniform(0, 10)
        reasoning = "RSI oversold combined with bullish EMA cross. High probability of reversal."
    elif rsi > 70 and ema_fast < ema_slow:
        decision = "SELL"
        confidence = 88 + random.uniform(0, 10)
        reasoning = "RSI overbought and bearish trend confirmation. Profit taking recommended."
    elif ema_fast > ema_slow:
        decision = "BUY"
        confidence = 65 + random.uniform(0, 10)
        reasoning = "Trend is bullish but momentum is moderate."
        
    return {
        "decision": decision,
        "confidence": round(confidence, 2),
        "reasoning": reasoning,
        "timestamp": indicator_data.get('timestamp')
    }

@app.route('/api/v1/decision', methods=['POST'])
def get_decision():
    """Consume financial indicators and return a trading decision"""
    data = request.json
    if not data:
        return jsonify({"error": "No data provided"}), 400
        
    symbol = data.get('symbol', 'BTC/USDT')
    indicators = data.get('indicators', {})
    
    decision_payload = predict_decision(indicators)
    decision_payload['symbol'] = symbol
    
    return jsonify({
        "status": "success",
        "data": decision_payload
    })

if __name__ == '__main__':
    port = int(os.getenv('STRATEGY_PORT', 5007))
    print(f"Trade Strategies (AI Engine) starting on port {port}")
    app.run(host='0.0.0.0', port=port)
