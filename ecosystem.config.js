module.exports = {
  apps: [
    {
      name: 'SilverTrade-Platform',
      script: 'venv/bin/python3',
      args: 'app.py',
      cwd: './Platfrom',
      interpreter: 'none',
      env: {
        PORT: 5000,
      }
    },
    {
      name: 'SilverTrade-Data',
      script: 'venv/bin/python3',
      args: 'app.py',
      cwd: './data_fetch',
      interpreter: 'none',
      env: {
        PORT: 5005,
      }
    },
    {
      name: 'SilverTrade-Financial',
      script: 'venv/bin/python3',
      args: 'financial_app.py',
      cwd: './Financial_Layer',
      interpreter: 'none',
      env: {
        PORT: 5006,
      }
    },
    {
      name: 'SilverTrade-AI-Engine',
      script: 'venv/bin/python3',
      args: 'strategies_app.py',
      cwd: './Trade_Strategies',
      interpreter: 'none',
      env: {
        PORT: 5007,
      }
    },
    {
      name: 'SilverTrade-UI',
      script: 'npm',
      args: 'run dev',
      cwd: './ui',
      env: {
        PORT: 3000,
      }
    }
  ]
};
