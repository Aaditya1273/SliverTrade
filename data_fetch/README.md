# SilverTrade AI-PineTS

A professional charting application that displays the **Williams VIX Fix** indicator using **SilverTrade AI** for market data and **TradingView Lightweight Charts** for visualization.

![SilverTrade AI-PineTS Williams VIX Fix](static/images/pinets.png)

*Real-time Williams VIX Fix indicator with SBIN data showing price chart and volatility analysis*

## 🚀 Features

- **Williams VIX Fix Indicator**: Complete implementation with customizable parameters
- **SilverTrade AI Integration**: Real-time and historical market data from your SilverTrade AI instance
- **PineTS Framework**: Powered by [PineTS](https://alaa-eddine.github.io/PineTS/) - Pine Script in TypeScript
- **TradingView Lightweight Charts v5.0.8**: Professional-grade charting library (locally hosted)
- **Interactive Controls**: Customize symbol, timeframe, and indicator parameters
- **Responsive Design**: Modern UI with DaisyUI components
- **Real-time Status**: Connection status and error handling
- **Modular Architecture**: Clean, extensible codebase for easy indicator development

## 📋 Prerequisites

- **Python 3.7+** (with pip)
- **SilverTrade AI server** running on `http://127.0.0.1:5000`
- Valid SilverTrade AI API key

## 🔗 Related Projects

- **[PineTS](https://alaa-eddine.github.io/PineTS/)** - Pine Script in TypeScript framework
- **[PineTS GitHub](https://github.com/alaa-eddine/PineTS)** - Source code and documentation
- **[SilverTrade AI](https://github.com/marketcalls/silvertrade)** - Open source trading platform

## 🛠️ Installation

### Step 1: Navigate to Project Directory
```bash
cd silvertrade-pinets
```

### Step 2: Create Virtual Environment
```bash
python -m venv venv
```

### Step 3: Activate Virtual Environment

#### Windows:
```bash
venv\Scripts\activate
```

#### Linux/Mac:
```bash
source venv/bin/activate
```

### Step 4: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 5: Configure Environment Variables
Copy the sample environment file and update it with your settings:
```bash
cp .env.sample .env
```

Edit `.env` and update your SilverTrade AI API key:
```bash
SILVERTRADE_API_KEY=your_silvertrade_api_key_here
SILVERTRADE_HOST=http://127.0.0.1:5000
```

## 🏃 Running the Application

### Step 1: Start SilverTrade AI
Ensure your SilverTrade AI server is running on `http://127.0.0.1:5000`

### Step 2: Start the Flask Application
```bash
python app.py
```

### Step 3: Open Your Browser
Navigate to `http://127.0.0.1:5005`

## 📁 Project Structure

```
silvertrade-pinets/
├── venv/                   # Python virtual environment
├── app.py                  # Main Flask application
├── data_fetcher.py         # SilverTrade AI data fetcher module
├── templates/
│   └── index.html         # Main UI template
├── static/
│   ├── js/
│   │   ├── silvertrade-provider.js        # SilverTrade AI data provider module
│   │   └── williams-vix-fix-indicator.js # Williams VIX Fix indicator module
│   ├── lib/
│   │   └── lightweight-charts-5.0.8.js # TradingView Lightweight Charts (local)
│   └── images/
│       └── pinets.png      # Application screenshot
├── requirements.txt       # Python dependencies
└── README.md             # This file
```

## 🔧 Configuration

### Environment Variables
The application uses environment variables for configuration. Copy `.env.sample` to `.env` and update the values:

```bash
# SilverTrade AI Configuration
SILVERTRADE_API_KEY=your_silvertrade_api_key_here
SILVERTRADE_HOST=http://127.0.0.1:5000

# Flask Configuration
FLASK_ENV=development
FLASK_DEBUG=True
FLASK_HOST=127.0.0.1
FLASK_PORT=5005
```

### Security Note
- **Never commit your `.env` file** - it contains sensitive API keys
- The `.env` file is already in `.gitignore` for security
- Always use `.env.sample` for documentation and examples

### Williams VIX Fix Parameters

The indicator supports the following customizable parameters:

- **Period Length (pd)**: Default 22 - Lookback period for standard deviation high
- **BBL Length (bbl)**: Default 20 - Bollinger Band length
- **Multiplier (mult)**: Default 2.0 - Bollinger Band standard deviation multiplier
- **Lookback Period (lb)**: Default 50 - Lookback period for percentile high
- **Highest Percentile (ph)**: Default 0.85 - Highest percentile threshold
- **Lowest Percentile (pl)**: Default 1.01 - Lowest percentile threshold

## 📊 Available Chart Settings

### Symbol & Exchange
- **Symbol**: Stock symbol (default: SBIN)
- **Exchange**: NSE or BSE (default: NSE)

### Timeframes
- 1 minute (1m)
- 5 minutes (5m) - **Default**
- 15 minutes (15m)
- 30 minutes (30m)
- 1 hour (1h)
- 1 day (D)

### Date Range
- **Start Date**: Beginning of data range
- **End Date**: End of data range

## 🔍 API Endpoints

### Flask Application (Port 8080)
- `GET /` - Main Williams VIX Fix UI
- `GET /api/data` - Fetch OHLCV data from SilverTrade AI

#### `/api/data` Parameters:
- `symbol` - Stock symbol (e.g., "SBIN")
- `exchange` - Exchange name (e.g., "NSE")
- `interval` - Timeframe (e.g., "5m")
- `start_date` - Start date (YYYY-MM-DD)
- `end_date` - End date (YYYY-MM-DD)

## 📦 Dependencies

### Python
- **Flask** - Web framework
- **flask-cors** - CORS support  
- **pandas** - Data manipulation
- **silvertrade** - SilverTrade AI API client
- **requests** - HTTP client

### JavaScript Modules
- **silvertrade-provider.js** - Handles data fetching from SilverTrade AI API
- **williams-vix-fix-indicator.js** - Modular Williams VIX Fix indicator implementation

## 🧩 Modular Architecture

### SilverTrade AI Provider Module
The `SilverTrade AIProvider` class handles all data communication with your SilverTrade AI instance:

```javascript
const provider = new SilverTrade AIProvider();
const data = await provider.getMarketData('SBIN', 'NSE', '5m', '2025-01-01', '2025-01-24');
```

### Williams VIX Fix Indicator Module
The `WilliamsVixFixIndicator` class provides a complete, reusable implementation:

```javascript
const indicator = new WilliamsVixFixIndicator();
const params = { pdLength: 22, bblLength: 20, mult: 2.0 };
const plots = indicator.calculate(marketData, params);
```

#### Features:
- ✅ **Parameter validation** - Ensures valid inputs
- ✅ **Default parameters** - Sensible defaults for all settings  
- ✅ **Metadata support** - Get parameter definitions and descriptions
- ✅ **Extensible** - Easy to modify or extend functionality

### PineTS Integration
This project demonstrates how to integrate [PineTS](https://alaa-eddine.github.io/PineTS/) indicators with web applications:

```javascript
// PineTS-style indicator development
const context = {
    data: { open, high, low, close, volume },
    ta: { sma, ema, highest, lowest, stdev },
    core: { plot, color }
};

// Calculate Williams VIX Fix using PineTS methodology
const wvf = ta.highest(close, pd).map((hc, i) => ((hc - low[i]) / hc) * 100);
plot(wvf, 'WilliamsVixFix', { style: 'histogram', color: col });
```

For more indicators and advanced usage, visit the [PineTS documentation](https://alaa-eddine.github.io/PineTS/).

## 🐛 Troubleshooting

### Virtual Environment Issues
```bash
# If virtual environment fails to create
python -m pip install --upgrade pip
python -m pip install virtualenv

# Recreate virtual environment
rm -rf venv  # or rmdir /s venv on Windows
python -m venv venv
```

### SilverTrade AI Connection Issues
1. **Verify SilverTrade AI is running**: Check `http://127.0.0.1:5000` in your browser
2. **Check API key**: Ensure your API key is valid and has proper permissions
3. **Firewall**: Make sure ports 5000 and 8080 are not blocked

### Chart Not Loading
1. **Check browser console** for JavaScript errors
2. **Verify data response** - Check network tab in browser dev tools
3. **Clear browser cache** and refresh the page

### Port Already in Use
If port 5005 is already in use, change it in your `.env` file:
```bash
FLASK_PORT=5006  # Or any available port
```

## 🎯 Usage

1. **Start the application** following the installation steps
2. **Adjust chart settings** using the form controls:
   - Select your desired symbol and exchange
   - Choose timeframe (5m recommended for intraday analysis)
   - Set appropriate date range
3. **Customize Williams VIX Fix parameters** based on your analysis needs
4. **Click "Load Data"** to fetch new data
5. **Click "Apply Indicator"** to recalculate with new parameters

## 📈 Understanding Williams VIX Fix

The Williams VIX Fix is a technical indicator that:

- **Measures market fear** similar to the VIX volatility index
- **Identifies potential market bottoms** when fear is high
- **Uses price action** instead of options data (unlike traditional VIX)
- **Generates signals** when the indicator reaches extreme levels

### Interpretation:
- **High values** (green histogram bars) suggest potential buying opportunities
- **Range lines** (orange/lime) show historical percentile levels  
- **Upper band** (aqua line) indicates overbought fear levels

### Screenshot Analysis:
The included screenshot shows SBIN stock data with:
- **Price Chart**: Candlestick chart showing price movement over time
- **Williams VIX Fix**: Lower panel showing volatility spikes (green bars) during market stress periods
- **Signal Lines**: Range high (lime), range low (orange), and upper band (aqua) providing context levels
- **Fear Spikes**: Notable green peaks in December 2024 and March 2025 indicating potential buying opportunities

## 📄 License

This project is licensed under the **GNU Affero General Public License v3.0** (AGPL-3.0).

See the [LICENSE](License.md) file for details.

### Key Points:
- ✅ **Free to use** - Use the software for any purpose
- ✅ **Open source** - Access to source code is guaranteed  
- ✅ **Copyleft** - Modifications must also be open source
- ⚠️ **Network use** - If you run this on a server, users must have access to the source code
- 📋 **Attribution required** - You must include the license and copyright notice

For more information about AGPL-3.0, visit: https://www.gnu.org/licenses/agpl-3.0.html

## 🤝 Contributing

Contributions are welcome! Please feel free to submit pull requests or open issues.

## 📞 Support

For issues or questions:
1. Check the troubleshooting section above
2. Verify your SilverTrade AI setup is working correctly
3. Check browser console for JavaScript errors
4. Open an issue on GitHub with detailed error information