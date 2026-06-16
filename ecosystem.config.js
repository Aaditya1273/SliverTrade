module.exports = {
  apps: [
    {
      name: 'SilverTrade-Platform',
      script: 'uv',
      args: 'run python app.py',
      cwd: './Platfrom',
      interpreter: 'none',
      env: {
        PORT: 5000,
        FLASK_ENV: 'production',
        // Strategy Engine internal URL — required for execute_signal staleness check
        // and chat context fetching
        STRATEGY_HOST: 'http://127.0.0.1:5007',
      }
    },
    {
      name: 'SilverTrade-Data',
      script: 'uv',
      args: 'run python app.py',
      cwd: './data_fetch',
      interpreter: 'none',
      env: {
        PORT: 5005,
      }
    },
    {
      name: 'SilverTrade-AI-Engine',
      script: 'uv',
      args: 'run python strategies_app.py',
      cwd: './Trade_Strategies',
      interpreter: 'none',
      env: {
        PORT: 5007,
        STRATEGY_PORT: 5007,
        // Platform URL — required so Strategy Engine can fetch OHLCV data
        SILVERTRADE_HOST: 'http://127.0.0.1:5000',
        // SILVERTRADE_API_KEY is read from .env file — set it there
        // Run: cd Platfrom && uv run python -c "from database.auth_db import get_api_key_for_tradingview; print(get_api_key_for_tradingview('admin'))"
        // Then add SILVERTRADE_API_KEY to Trade_Strategies/.env
      }
    },
    {
      name: 'SilverTrade-UI',
      script: 'npm',
      args: 'start',
      cwd: './ui',
      env: {
        PORT: 3000,
        NODE_ENV: 'production',
      }
    }
  ]
};
