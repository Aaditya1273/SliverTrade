/**
 * SilverTradeAI Data Provider Module
 * Handles data fetching from SilverTradeAI Flask API
 */

class SilverTradeAIProvider {
    constructor(apiUrl = window.location.origin) {
        this.apiUrl = apiUrl;
        this.name = "SilverTradeAI Provider";
        this.version = "1.0.0";
    }

    /**
     * Fetch market data from SilverTradeAI
     * @param {string} symbol - Stock symbol
     * @param {string} exchange - Exchange name
     * @param {string} interval - Time interval
     * @param {string} startDate - Start date (YYYY-MM-DD)
     * @param {string} endDate - End date (YYYY-MM-DD)
     * @returns {Promise<Array>} - Market data array
     */
    async getMarketData(symbol, exchange, interval, startDate, endDate) {
        try {
            const params = new URLSearchParams({
                symbol: symbol,
                exchange: exchange,
                interval: interval,
                start_date: startDate,
                end_date: endDate
            });

            const response = await fetch(`${this.apiUrl}/api/data?${params}`);
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const result = await response.json();
            
            if (result.error) {
                throw new Error(result.error);
            }

            return result.data.map(candle => ({
                time: candle.time,
                open: parseFloat(candle.open),
                high: parseFloat(candle.high),
                low: parseFloat(candle.low),
                close: parseFloat(candle.close),
                volume: parseFloat(candle.volume || 0)
            }));
        } catch (error) {
            console.error('Error fetching data from SilverTradeAI:', error);
            throw error;
        }
    }

    /**
     * Test connection to SilverTradeAI
     * @returns {Promise<boolean>} - Connection status
     */
    async testConnection() {
        try {
            const response = await fetch(`${this.apiUrl}/api/data?symbol=SBIN&exchange=NSE&interval=5m&start_date=2025-01-20&end_date=2025-01-21`);
            return response.ok;
        } catch (error) {
            console.error('Connection test failed:', error);
            return false;
        }
    }

    /**
     * Get provider information
     * @returns {Object} - Provider metadata
     */
    getInfo() {
        return {
            name: this.name,
            version: this.version,
            description: "Data provider for SilverTradeAI market data API",
            apiUrl: this.apiUrl
        };
    }
}

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = SilverTradeAIProvider;
} else {
    // Make available globally for browser use
    window.SilverTradeAIProvider = SilverTradeAIProvider;
}