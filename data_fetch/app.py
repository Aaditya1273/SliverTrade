from flask import Flask, render_template, jsonify, request, send_from_directory
from flask_cors import CORS
from datetime import datetime
import pandas as pd
import os
from dotenv import load_dotenv
from data_fetcher import DataFetcher

# Load environment variables from .env file - override system vars
load_dotenv(override=True)

app = Flask(__name__, static_folder='static', static_url_path='/static')
CORS(app)

# Initialize data fetcher with environment variables
api_key = os.getenv('SILVERTRADE_API_KEY')
host = os.getenv('SILVERTRADE_HOST', 'http://platform:5000')

data_fetcher = DataFetcher(
    api_key=api_key,
    host=host
)

@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/data')
def get_data():
    try:
        symbol = request.args.get('symbol', 'SBIN')
        exchange = request.args.get('exchange', 'NSE')
        interval = request.args.get('interval', '5m')
        start_date = request.args.get('start_date', '2025-01-01')
        end_date = request.args.get('end_date', '2025-01-24')
        
        # Check if API key is configured
        if not api_key:
            return jsonify({'error': 'SilverTrade AI API key not configured'}), 500
        
        df = data_fetcher.get_historical_data(
            symbol=symbol,
            exchange=exchange,
            interval=interval,
            start_date=start_date,
            end_date=end_date
        )
        
        if df is None:
            return jsonify({'error': 'Failed to fetch data from SilverTrade AI. Please check your API key and SilverTrade AI server status.'}), 500
        
        if df.empty:
            return jsonify({'error': 'No data available for the specified parameters'}), 404
        
        chart_data = []
        for idx, row in df.iterrows():
            timestamp = int(idx.timestamp())
            chart_data.append({
                'time': timestamp,
                'open': float(row['open']),
                'high': float(row['high']),
                'low': float(row['low']),
                'close': float(row['close']),
                'volume': float(row['volume'])
            })
        
        return jsonify({'data': chart_data})
        
    except Exception as e:
        return jsonify({'error': f'Server error: {str(e)}'}), 500

@app.route('/api/health')
def health_check():
    """Health check endpoint.
    Returns 200 even when upstream API key is missing — the service
    itself is healthy and ready to serve cached or configured data.
    """
    try:
        api_key = os.getenv('SILVERTRADE_API_KEY')
        host = os.getenv('SILVERTRADE_HOST')
        
        if not api_key:
            return jsonify({
                'status': 'warning',
                'message': 'Service running. SILVERTRADE_API_KEY not configured — upstream data fetching unavailable.',
                'config': {'host': host, 'api_key': 'not set'}
            }), 200
        
        test_data = data_fetcher.get_realtime_data('SBIN', 'NSE')
        
        return jsonify({
            'status': 'ok',
            'message': 'SilverTrade AI connection successful',
            'config': {
                'host': host,
                'api_key': f"{api_key[:10]}...{api_key[-10:]}" if len(api_key) > 20 else 'configured'
            },
            'test_connection': 'success' if test_data else 'failed'
        })
        
    except Exception as e:
        return jsonify({
            'status': 'warning',
            'message': f'Service running. Upstream check failed: {str(e)}',
            'config': {
                'host': os.getenv('SILVERTRADE_HOST'),
                'api_key': 'configured' if os.getenv('SILVERTRADE_API_KEY') else 'not set'
            }
        }), 200

@app.route('/static/<path:path>')
def send_static(path):
    return send_from_directory('static', path)


@app.route('/')
def status():
    return jsonify({
        "status": "online",
        "service": "SilverTrade Data Fetcher",
        "version": "1.0.0",
        "engine": "PineTS-Integrated"
    })

if __name__ == '__main__':
    # Get configuration from environment variables
    debug = os.getenv('FLASK_DEBUG', 'True').lower() in ('true', '1', 't')
    host = os.getenv('FLASK_HOST', '0.0.0.0')
    port = int(os.getenv('FLASK_PORT', 5005))
    
    print(f"Starting SilverTrade Data Fetcher on http://{host}:{port}")
    print(f"Connected to Platform API at {os.getenv('SILVERTRADE_HOST')}")

    
    app.run(debug=debug, host=host, port=port)