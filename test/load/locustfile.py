"""
SilverTrade AI — Load Testing Script (Phase 11)
=============================================
Locust load testing for 500 concurrent users
"""

from locust import HttpUser, task, between, constant_pacing
import random


class TradingUser(HttpUser):
    """Simulates a real trader using the platform."""
    
    wait_time = between(1, 3)
    
    def on_start(self):
        """Login and store session/API key."""
        # In production, this would use real credentials
        # For testing, we assume test users are pre-created
        self.user_id = self.environment.runner.user_count
        self.api_key = f"test_api_key_{self.user_id}"
        
    @task(5)  # Most common: checking signals
    def get_signals(self):
        """Fetch signals - most frequent operation."""
        self.client.get(
            '/api/v1/signals?limit=20',
            headers={'X-API-KEY': self.api_key},
            name='/api/v1/signals'
        )
    
    @task(3)  # Common: portfolio check
    def get_funds(self):
        """Check portfolio/funds."""
        self.client.post(
            '/api/v1/funds',
            json={'apikey': self.api_key},
            name='/api/v1/funds'
        )
    
    @task(3)  # Common: positions
    def get_positions(self):
        """Check positions."""
        self.client.post(
            '/api/v1/positions',
            json={'apikey': self.api_key},
            name='/api/v1/positions'
        )
    
    @task(2)  # Less common: generate signal
    def generate_signal(self):
        """Generate a new signal."""
        symbols = ['BTC/USDT', 'ETH/USDT', 'NIFTY', 'BANKNIFTY', 'SBIN']
        symbol = random.choice(symbols)
        self.client.post(
            '/api/v1/signal',
            json={'apikey': self.api_key, 'symbol': symbol, 'exchange': 'CRYPTO'},
            name='/api/v1/signal'
        )
    
    @task(1)  # Rare: chat message
    def send_chat(self):
        """Send a chat message."""
        questions = [
            'What is the current RSI for BTC?',
            'Should I buy or sell now?',
            'What are the key levels?',
        ]
        message = random.choice(questions)
        self.client.post(
            '/api/v1/chat',
            json={'apikey': self.api_key, 'message': message},
            name='/api/v1/chat'
        )
    
    @task(1)  # Rare: place order (would be rate limited)
    def place_order(self):
        """Place an order (simulated)."""
        # In real load test, this would use test broker
        # For now, just test the endpoint exists
        self.client.post(
            '/api/v1/placeorder',
            json={
                'apikey': self.api_key,
                'symbol': 'SBIN',
                'exchange': 'NSE',
                'action': 'BUY',
                'product_type': 'MIS',
                'pricetype': 'MARKET',
                'quantity': '10',
                'price': '0',
            },
            name='/api/v1/placeorder'
        )
