/**
 * Williams VIX Fix Indicator Module
 * A modular implementation of the Williams VIX Fix indicator
 * 
 * The Williams VIX Fix is a technical indicator that measures market fear
 * and identifies potential market bottoms when fear is high.
 */

class WilliamsVixFixIndicator {
    constructor() {
        this.name = "Williams VIX Fix";
        this.version = "1.0.0";
    }

    /**
     * Calculate Williams VIX Fix indicator
     * @param {Array} marketData - Array of OHLCV data
     * @param {Object} params - Indicator parameters
     * @returns {Object} - Calculated indicator plots
     */
    calculate(marketData, params = {}) {
        const {
            pdLength = 22,      // LookBack Period Standard Deviation High
            bblLength = 20,     // Bollinger Band Length
            mult = 2.0,         // Bollinger Band Standard Deviation Up
            lb = 50,            // Look Back Period Percentile High
            ph = 0.85,          // Highest Percentile
            pl = 1.01,          // Lowest Percentile
            hp = true,          // Show High Range
            sd = true           // Show Standard Deviation Line
        } = params;

        const pineTS = new MockPineTS(marketData);

        const { result, plots } = pineTS.run((context) => {
            const { close, high, low } = context.data;
            const ta = context.ta;
            const { plot, color } = context.core;

            // Calculate Williams VIX Fix
            const highestClose = ta.highest(close, pdLength);
            const wvf = highestClose.map((hc, i) => ((hc - low[i]) / hc) * 100);

            const sDev = ta.stdev(wvf, bblLength).map(sd => mult * sd);
            const midLine = ta.sma(wvf, bblLength);
            const upperBand = midLine.map((ml, i) => ml + sDev[i]);

            const rangeHigh = ta.highest(wvf, lb).map(rh => rh * ph);
            const rangeLow = ta.lowest(wvf, lb).map(rl => rl * pl);

            // Color logic for histogram
            const col = wvf.map((w, i) => (w >= upperBand[i] || w >= rangeHigh[i]) ? color.lime : color.gray);

            // Conditional lines based on parameters
            const RangeHigh = rangeHigh.map(rh => hp && !isNaN(rh) ? rh : NaN);
            const RangeLow = rangeLow.map(rl => hp && !isNaN(rl) ? rl : NaN);
            const UpperBand = upperBand.map(ub => sd && !isNaN(ub) ? ub : NaN);

            // Plot all series
            plot(RangeHigh, 'RangeHigh', { 
                style: 'line', 
                linewidth: 1, 
                color: 'lime',
                title: 'Range High'
            });
            
            plot(RangeLow, 'RangeLow', { 
                style: 'line', 
                linewidth: 1, 
                color: 'orange',
                title: 'Range Low'
            });
            
            plot(UpperBand, 'UpperBand', { 
                style: 'line', 
                linewidth: 2, 
                color: 'aqua',
                title: 'Upper Band'
            });
            
            plot(wvf, 'WilliamsVixFix', { 
                style: 'histogram', 
                linewidth: 4, 
                color: col,
                title: 'Williams VIX Fix'
            });
        });

        return plots;
    }

    /**
     * Get default parameters for the indicator
     * @returns {Object} - Default parameter values
     */
    getDefaultParams() {
        return {
            pdLength: 22,
            bblLength: 20,
            mult: 2.0,
            lb: 50,
            ph: 0.85,
            pl: 1.01,
            hp: true,
            sd: true
        };
    }

    /**
     * Get parameter definitions for UI generation
     * @returns {Array} - Parameter definitions
     */
    getParamDefinitions() {
        return [
            {
                name: 'pdLength',
                label: 'Period Length',
                type: 'number',
                min: 1,
                max: 100,
                default: 22,
                description: 'LookBack Period Standard Deviation High'
            },
            {
                name: 'bblLength',
                label: 'BBL Length',
                type: 'number',
                min: 1,
                max: 100,
                default: 20,
                description: 'Bollinger Band Length'
            },
            {
                name: 'mult',
                label: 'Multiplier',
                type: 'number',
                min: 0.1,
                max: 10.0,
                step: 0.1,
                default: 2.0,
                description: 'Bollinger Band Standard Deviation Multiplier'
            },
            {
                name: 'lb',
                label: 'Lookback Period',
                type: 'number',
                min: 10,
                max: 200,
                default: 50,
                description: 'Look Back Period Percentile High'
            },
            {
                name: 'ph',
                label: 'Highest Percentile',
                type: 'number',
                min: 0.1,
                max: 1.0,
                step: 0.01,
                default: 0.85,
                description: 'Highest Percentile - 0.85=85%, 0.95=95%'
            },
            {
                name: 'pl',
                label: 'Lowest Percentile',
                type: 'number',
                min: 1.0,
                max: 2.0,
                step: 0.01,
                default: 1.01,
                description: 'Lowest Percentile - 1.01=99%, 1.05=95%'
            },
            {
                name: 'hp',
                label: 'Show High Range',
                type: 'boolean',
                default: true,
                description: 'Show High Range based on Percentile and LookBack Period'
            },
            {
                name: 'sd',
                label: 'Show Standard Deviation',
                type: 'boolean',
                default: true,
                description: 'Show Standard Deviation Line'
            }
        ];
    }

    /**
     * Validate parameters
     * @param {Object} params - Parameters to validate
     * @returns {Object} - Validation result
     */
    validateParams(params) {
        const errors = [];
        const paramDefs = this.getParamDefinitions();
        
        paramDefs.forEach(def => {
            const value = params[def.name];
            
            if (value === undefined || value === null) {
                errors.push(`${def.label} is required`);
                return;
            }
            
            if (def.type === 'number') {
                if (isNaN(value)) {
                    errors.push(`${def.label} must be a number`);
                    return;
                }
                
                if (def.min !== undefined && value < def.min) {
                    errors.push(`${def.label} must be >= ${def.min}`);
                }
                
                if (def.max !== undefined && value > def.max) {
                    errors.push(`${def.label} must be <= ${def.max}`);
                }
            }
        });
        
        return {
            isValid: errors.length === 0,
            errors: errors
        };
    }

    /**
     * Get indicator information
     * @returns {Object} - Indicator metadata
     */
    getInfo() {
        return {
            name: this.name,
            version: this.version,
            description: "The Williams VIX Fix is a technical indicator that measures market fear and identifies potential market bottoms.",
            author: "Larry Williams",
            category: "Volatility",
            interpretation: {
                highValues: "High values (green histogram bars) suggest potential buying opportunities",
                rangeLines: "Range lines (orange/lime) show historical percentile levels",
                upperBand: "Upper band (aqua line) indicates overbought fear levels"
            }
        };
    }
}

/**
 * Mock PineTS implementation for technical analysis calculations
 */
class MockPineTS {
    constructor(marketData) {
        this.marketData = marketData;
    }

    run(indicatorFunction) {
        const context = this.createContext(this.marketData);
        const result = indicatorFunction(context);
        return {
            result: result,
            plots: context._plots
        };
    }

    createContext(marketData) {
        const data = {
            open: marketData.map(d => d.open),
            high: marketData.map(d => d.high),
            low: marketData.map(d => d.low),
            close: marketData.map(d => d.close),
            volume: marketData.map(d => d.volume),
            time: marketData.map(d => d.time)
        };

        const plots = {};

        const context = {
            data: data,
            _plots: plots,
            
            ta: {
                highest: (series, length) => {
                    const result = [];
                    for (let i = 0; i < series.length; i++) {
                        const start = Math.max(0, i - length + 1);
                        const slice = series.slice(start, i + 1);
                        result.push(Math.max(...slice));
                    }
                    return result;
                },
                
                lowest: (series, length) => {
                    const result = [];
                    for (let i = 0; i < series.length; i++) {
                        const start = Math.max(0, i - length + 1);
                        const slice = series.slice(start, i + 1);
                        result.push(Math.min(...slice));
                    }
                    return result;
                },
                
                sma: (series, length) => {
                    const result = [];
                    for (let i = 0; i < series.length; i++) {
                        if (i < length - 1) {
                            result.push(NaN);
                        } else {
                            const slice = series.slice(i - length + 1, i + 1);
                            const sum = slice.reduce((a, b) => a + b, 0);
                            result.push(sum / length);
                        }
                    }
                    return result;
                },
                
                stdev: (series, length) => {
                    const sma = context.ta.sma(series, length);
                    const result = [];
                    for (let i = 0; i < series.length; i++) {
                        if (i < length - 1) {
                            result.push(NaN);
                        } else {
                            const slice = series.slice(i - length + 1, i + 1);
                            const mean = sma[i];
                            const variance = slice.reduce((sum, val) => sum + Math.pow(val - mean, 2), 0) / length;
                            result.push(Math.sqrt(variance));
                        }
                    }
                    return result;
                }
            },
            
            math: Math,
            
            input: {
                int: (defaultValue, title) => defaultValue,
                float: (defaultValue, title) => defaultValue,
                bool: (defaultValue, title) => defaultValue
            },
            
            core: {
                plot: (series, name, options) => {
                    const plotData = series.map((value, index) => ({
                        time: data.time[index],
                        value: isNaN(value) ? null : value,
                        options: {
                            color: Array.isArray(options.color) ? options.color[index] : options.color
                        }
                    })).filter(point => point.value !== null);
                    
                    plots[name] = {
                        name: name,
                        data: plotData,
                        options: options
                    };
                },
                
                color: {
                    lime: '#00ff00',
                    gray: '#808080',
                    orange: '#ffa500',
                    aqua: '#00ffff'
                }
            }
        };

        return context;
    }
}

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = WilliamsVixFixIndicator;
} else {
    // Make available globally for browser use
    window.WilliamsVixFixIndicator = WilliamsVixFixIndicator;
}