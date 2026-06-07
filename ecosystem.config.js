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
