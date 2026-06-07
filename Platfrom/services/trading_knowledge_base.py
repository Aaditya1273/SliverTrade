"""
SilverTrade AI — Trading Knowledge Base
========================================
Contains ~50 knowledge chunks about trading, markets, and technical analysis.

Each chunk has:
  - text: str   (the knowledge content, ~100-300 words)
  - category: str  (general, candlestick, india_market, options_greeks,
                    strategy, technical_analysis, risk_management, broker)
  - tags: list[str]  (keywords for matching)

Used by: rag_service.py to seed the ChromaDB vector store.
"""

KnowledgeChunk = dict  # {text: str, category: str, tags: list[str]}

KNOWLEDGE_CHUNKS: list[KnowledgeChunk] = [
    # ── Candlestick Patterns ───────────────────────────────────────────

    {
        "text": (
            "Bullish Engulfing Pattern: A two-candle reversal pattern that appears "
            "during a downtrend. The first candle is a small bearish (red) candle. "
            "The second candle is a larger bullish (green) candle that completely "
            "engulfs the body of the first candle. This indicates strong buying "
            "pressure and a potential trend reversal to the upside. For higher "
            "reliability, look for the pattern at a support level or oversold "
            "condition. Volume confirmation (higher volume on the engulfing day) "
            "significantly increases the probability of a successful reversal."
        ),
        "category": "candlestick",
        "tags": ["bullish engulfing", "reversal", "candlestick", "bullish", "buy"],
    },
    {
        "text": (
            "Bearish Engulfing Pattern: A two-candle reversal pattern that appears "
            "during an uptrend. The first candle is a small bullish (green) candle. "
            "The second candle is a larger bearish (red) candle that completely "
            "engulfs the body of the first candle. This indicates strong selling "
            "pressure and a potential trend reversal to the downside. The pattern "
            "is more reliable when it occurs at a resistance level or overbought "
            "condition. Higher volume on the engulfing day adds conviction to the signal."
        ),
        "category": "candlestick",
        "tags": ["bearish engulfing", "reversal", "candlestick", "bearish", "sell"],
    },
    {
        "text": (
            "Doji: A single-candle pattern where the opening and closing prices "
            "are virtually equal, forming a cross or plus sign shape. The doji "
            "represents indecision in the market — neither buyers nor sellers "
            "gained control. A doji after a strong uptrend can signal a potential "
            "top (bearish reversal). A doji after a strong downtrend can signal "
            "a potential bottom (bullish reversal). The longer the shadows (wicks), "
            "the more significant the indecision. Dragonfly doji (long lower shadow) "
            "and gravestone doji (long upper shadow) have stronger reversal implications."
        ),
        "category": "candlestick",
        "tags": ["doji", "indecision", "reversal", "candlestick"],
    },
    {
        "text": (
            "Hammer and Hanging Man: Both have the same shape — a small real body "
            "at the upper end with a long lower shadow (at least 2x the body length) "
            "and little to no upper shadow. The Hammer appears during a downtrend "
            "and signals a bullish reversal. The Hanging Man appears during an "
            "uptrend and signals a bearish reversal. The colour of the body is not "
            "critical, but a white (green) hammer is more bullish. Confirmation "
            "with the next candle's close above/below the hammer's close increases "
            "reliability. Volume on the hammer day should ideally be higher than "
            "the previous session."
        ),
        "category": "candlestick",
        "tags": ["hammer", "hanging man", "candlestick", "reversal", "support"],
    },
    {
        "text": (
            "Morning Star and Evening Star: Three-candle reversal patterns. Morning "
            "Star (bullish) appears in a downtrend: 1) Long bearish candle, 2) Small "
            "candle (doji or spinning top) that gaps down, 3) Long bullish candle "
            "that closes at least halfway up the first candle's body. This shows "
            "selling exhausted then buyers took over. Evening Star (bearish) is the "
            "opposite in an uptrend. The middle candle can be a doji (preferred) or "
            "a small-bodied candle. The gap between consecutive candles increases "
            "the pattern's significance. These are among the most reliable reversal "
            "patterns in technical analysis."
        ),
        "category": "candlestick",
        "tags": ["morning star", "evening star", "reversal", "candlestick", "three candle"],
    },
    {
        "text": (
            "Piercing Pattern and Dark Cloud Cover: Two-candle reversal patterns. "
            "Piercing Pattern (bullish): occurs in downtrend. Day 1 is bearish, "
            "Day 2 opens lower but closes above the midpoint of Day 1's body. "
            "This shows buyers stepping in at lower levels. Dark Cloud Cover "
            "(bearish): occurs in uptrend. Day 1 is bullish, Day 2 opens higher "
            "but closes below the midpoint of Day 1's body. Shows sellers "
            "entering at higher levels. Stronger than engulfing when confirmed "
            "by volume. Best used at established support/resistance levels."
        ),
        "category": "candlestick",
        "tags": ["piercing pattern", "dark cloud cover", "reversal", "candlestick"],
    },
    {
        "text": (
            "Shooting Star and Inverted Hammer: Both have small lower bodies with "
            "long upper shadows (at least 2x body length). Shooting Star appears "
            "in an uptrend — the long upper wick shows buying was rejected at "
            "higher prices, signalling a bearish reversal. Inverted Hammer appears "
            "in a downtrend — the upper wick shows buyers attempted to push price "
            "higher, suggesting a potential bullish reversal. Confirmation is "
            "essential: a lower close for shooting star confirmation, or a higher "
            "close for inverted hammer confirmation on the following candle."
        ),
        "category": "candlestick",
        "tags": ["shooting star", "inverted hammer", "reversal", "candlestick"],
    },
    {
        "text": (
            "Harami Pattern: A two-candle pattern where the second candle's body "
            "is completely inside the first candle's body (pregnant-like shape). "
            "Bullish Harami occurs in a downtrend — small bullish body inside the "
            "previous bearish body, indicating selling exhaustion. Bearish Harami "
            "occurs in an uptrend — small bearish body inside the previous bullish "
            "body, suggesting buying exhaustion. Harami Cross (second candle is a "
            "doji) is a stronger reversal signal. Harami is a weaker pattern than "
            "Engulfing but still useful, especially at key support/resistance levels."
        ),
        "category": "candlestick",
        "tags": ["harami", "candlestick", "reversal", "inside candle"],
    },

    # ── Indian Market Rules ────────────────────────────────────────────

    {
        "text": (
            "SEBI (Securities and Exchange Board of India) is the regulatory body "
            "for Indian securities markets. Key rules: 1) T+1 settlement for equity "
            "delivery — funds and securities are settled the next working day. "
            "2) Circuit filters (price bands) are applied to individual stocks to "
            "prevent excessive volatility — typically 10% or 20% depending on the "
            "stock. 3) FII (Foreign Institutional Investor) positions are monitored "
            "and reported daily. 4) Insider trading is strictly prohibited with "
            "penalties including imprisonment. 5) All trades must go through SEBI-"
            "registered brokers. 6) Position limits apply for derivatives (futures "
            "and options) based on market capitalisation."
        ),
        "category": "india_market",
        "tags": ["sebi", "regulation", "india", "t+1", "settlement", "circuit"],
    },
    {
        "text": (
            "Circuit Filters in Indian Markets: SEBI mandates price bands (circuit "
            "filters) for equities to prevent excessive volatility. Most stocks have "
            "a 10% or 20% daily price band. When a stock hits the upper circuit, "
            "only sell orders are executed — buyers cannot enter at that price. "
            "When a stock hits the lower circuit, only buy orders execute. Indices "
            "like NIFTY 50 and SENSEX do not have circuit filters. F&O (Futures "
            "and Options) stocks typically have wider bands (10-20%). If a stock "
            "is locked in circuit for multiple days, SEBI may suspend trading."
        ),
        "category": "india_market",
        "tags": ["circuit", "price band", "upper circuit", "lower circuit", "sebi", "india"],
    },
    {
        "text": (
            "Trading Hours in India: Equity cash market (NSE, BSE) operates Monday "
            "to Friday, 9:15 AM to 3:30 PM IST. Pre-market session: 9:00-9:15 AM. "
            "Derivatives (F&O) trade 9:15 AM to 3:30 PM. Commodity market (MCX) "
            "trades split into morning (9:00 AM-5:00 PM) and evening (5:00 PM-11:30 PM) "
            "sessions. Currency derivatives trade 9:00 AM to 5:00 PM. Markets are "
            "closed on Saturday, Sunday, and declared holidays. The last 30 minutes "
            "(3:00-3:30 PM) are often volatile as traders square off positions."
        ),
        "category": "india_market",
        "tags": ["trading hours", "nse", "bse", "market timings", "india", "ist"],
    },
    {
        "text": (
            "NSE (National Stock Exchange) and BSE (Bombay Stock Exchange) are "
            "India's two primary stock exchanges. NSE (founded 1992) is the larger "
            "by trading volume and handles most derivatives trading through its "
            "NFO (NSE Futures and Options) segment. BSE (founded 1875) is Asia's "
            "oldest exchange. Key indices: NIFTY 50 (NSE's benchmark of 50 large "
            "companies), SENSEX (BSE's 30-stock benchmark), Bank Nifty (banking "
            "sector), and sectoral indices. Most retail traders use NSE due to "
            "higher liquidity in F&O. All brokers registered with both exchanges."
        ),
        "category": "india_market",
        "tags": ["nse", "bse", "nifty", "sensex", "exchange", "india"],
    },
    {
        "text": (
            "F&O (Futures and Options) in India: Monthly expiry contracts for "
            "indices (NIFTY, BANKNIFTY, FINNIFTY) and select stocks. Weekly "
            "expiries also exist for NIFTY (Thursday), BANKNIFTY (Wednesday), "
            "FINNIFTY (Tuesday), and MIDCPNIFTY (Monday). Option contracts settle "
            "in cash — no delivery of underlying. Physical settlement was being "
            "considered but postponed. Premium received from option selling is "
            "collected upfront. Margin requirements are calculated using SPAN "
            "and Exposure margin systems. F&O trading requires a separate risk "
            "disclosure and a higher account balance."
        ),
        "category": "india_market",
        "tags": ["fno", "futures", "options", "expiry", "nfo", "india", "derivatives"],
    },
    {
        "text": (
            "Taxation of Trading in India: 1) Intraday equity trading profits are "
            "treated as Business Income and taxed at your slab rate. The transaction "
            "is classified as 'speculative business'. 2) F&O (Futures & Options) "
            "trading is considered 'non-speculative business' — losses can be set "
            "off against other business income. 3) STT (Securities Transaction Tax) "
            "is 0.1% on delivery selling and 0.025% on F&O sell side. 4) Long-term "
            "capital gains (LTCG) on equity exceeding Rs 1 lakh per year is taxed "
            "at 10%. 5) Short-term capital gains (STCG) on equity delivery held "
            "less than 12 months is 15%. 6) GST is 18% on brokerage and other "
            "charges. Consult a CA for your specific situation."
        ),
        "category": "india_market",
        "tags": ["tax", "stt", "capital gains", "intraday", "fno taxation", "india"],
    },
    {
        "text": (
            "Margin Trading in India: 1) MIS (Intraday Square-off) margin: 5-20% "
            "of contract value for equities. Positions must be squared off by "
            "3:15 PM IST or auto-squared-off. 2) NRML (Normal/Overnight) margin: "
            "full delivery or SPAN+Exposure margin for F&O. Can hold overnight. "
            "3) CO (Cover Order): predefined stop loss, margin ~50% of contract "
            "value. 4) BO (Bracket Order): predefined target and stop loss, margin "
            "~50%. Peak margin rules (SEBI) require 100% margin upfront by 11:00 AM "
            "trade day. You cannot trade with unsettled funds across brokers."
        ),
        "category": "india_market",
        "tags": ["margin", "mis", "nrml", "intraday", "delivery", "peak margin", "sebi"],
    },
    {
        "text": (
            "T2T (Trade-to-Trade) Segment in India: SEBI identifies certain stocks "
            "that must be traded in the T2T segment due to high volatility or "
            "suspicious trading activity. In T2T stocks: 1) Intraday trading is "
            "NOT allowed — every buy must result in delivery. 2) You must have "
            "sufficient funds to pay for the full purchase amount. 3) You cannot "
            "sell shares unless you already hold them in your demat account. "
            "4) T2T stocks typically have narrower circuit limits. Brokers display "
            "a T2T tag next to these symbols. Check SEBI's list regularly as it "
            "updates monthly."
        ),
        "category": "india_market",
        "tags": ["t2t", "trade to trade", "delivery", "sebi", "restricted", "india"],
    },
    {
        "text": (
            "ASBA (Application Supported by Blocked Amount) is the default method "
            "for IPO applications in India. When you apply for an IPO, the amount "
            "is blocked in your bank account (not debited) until allotment. If not "
            "allotted, the amount is unblocked. UPI-based IPO applications via "
            "stock brokers are now common — use your UPI ID to apply directly. "
            "SEBI mandates 75% minimum subscription for retail IPOs. The listing "
            "day typically sees high volatility. Apply for IPOs through your "
            "trading account or directly via the exchange's platform."
        ),
        "category": "india_market",
        "tags": ["ipo", "asba", "up", "listing", "sebi", "allotment", "india"],
    },
    {
        "text": (
            "Portfolio Management Services (PMS) and Alternative Investment Funds "
            "(AIF) in India: PMS requires a minimum investment of Rs 50 lakh. "
            "AIFs require Rs 1 crore minimum. Both are SEBI-regulated. PMS gives "
            "direct ownership of stocks in your demat account. AIFs pool investor "
            "money into a trust structure. PMS fees typically include a fixed "
            "management fee (1.5-2.5% p.a.) and profit sharing (10-20% above a "
            "hurdle rate). AIF fees vary by category. These are for high-net-worth "
            "individuals (HNIs). Most retail traders are better served by mutual "
            "funds or direct stock trading."
        ),
        "category": "india_market",
        "tags": ["pms", "aif", "portfolio", "hni", "sebi", "investment management"],
    },

    # ── Options Greeks ─────────────────────────────────────────────────

    {
        "text": (
            "Delta (Δ) measures the rate of change of an option's price relative "
            "to a Rs 1 change in the underlying asset. Call options have positive "
            "delta (0 to 1). Put options have negative delta (0 to -1). At-the-money "
            "(ATM) options have delta around 0.5 (calls) or -0.5 (puts). Deep in-the-"
            "money (ITM) calls have delta near 1, deep OTM calls have delta near 0. "
            "Delta also represents the approximate probability of the option expiring "
            "in-the-money. For NIFTY options: a delta of 0.6 means the option price "
            "moves ~Rs 0.6 for every 1-point NIFTY move. Delta changes with time "
            "and volatility."
        ),
        "category": "options_greeks",
        "tags": ["delta", "greeks", "options", "probability", "itm", "otm", "atm"],
    },
    {
        "text": (
            "Gamma (Γ) measures the rate of change of delta for a Rs 1 change in "
            "the underlying. High gamma means delta changes rapidly, making the "
            "option sensitive to large price moves. ATM options have the highest "
            "gamma. Gamma is highest near expiry (gamma risk). A long gamma position "
            "(buying options) benefits from large price moves. Short gamma (selling "
            "options) is dangerous near expiry because a sudden move causes delta "
            "to flip dramatically. Gamma scalping is a strategy where delta-neutral "
            "traders buy/sell the underlying to profit from gamma. Always check "
            "gamma before holding options into expiry."
        ),
        "category": "options_greeks",
        "tags": ["gamma", "greeks", "options", "gamma risk", "expiry", "gamma scalping"],
    },
    {
        "text": (
            "Theta (Θ) measures time decay — how much an option's price decreases "
            "per day as expiration approaches, assuming all other factors constant. "
            "Theta is always negative for long option positions (you lose money "
            "each day). ATM options have the highest theta. Theta accelerates "
            "in the last 30 days before expiry — the decay curve is exponential, "
            "not linear. Short options strategies (credit spreads, iron condors) "
            "aim to profit from theta decay. Long options need large directional "
            "moves to overcome theta. A rule of thumb: an ATM option with 30 days "
            "to expiry loses roughly 1/N of its value each day where N = days to expiry."
        ),
        "category": "options_greeks",
        "tags": ["theta", "time decay", "greeks", "options", "expiry", "short options"],
    },
    {
        "text": (
            "Vega (ν) measures sensitivity to implied volatility (IV). Specifically, "
            "how much an option's price changes for a 1% change in IV. Vega is "
            "highest for ATM options with longer time to expiry. When IV is high, "
            "options are expensive (good to sell). When IV is low, options are "
            "cheap (good to buy). IV typically rises during market uncertainty, "
            "earnings announcements, and before major events. After events, IV "
            "drops sharply (volatility crush). Option sellers profit from both "
            "theta decay and declining IV. Vega is not linear — it changes with "
            "moneyness and time. Long vega benefits from rising IV."
        ),
        "category": "options_greeks",
        "tags": ["vega", "iv", "implied volatility", "greeks", "options", "volatility crush"],
    },
    {
        "text": (
            "Rho (ρ) measures sensitivity to changes in interest rates. For most "
            "short-dated options, rho is negligible. For long-dated options (LEAPS) "
            "or in high-interest-rate environments, rho matters more. Call options "
            "have positive rho (higher rates = higher call prices). Put options "
            "have negative rho (higher rates = lower put prices). In India's "
            "current interest rate environment, rho is typically ignored for "
            "positions under 60 days. LEAPS and deep ITM options are most "
            "affected by rho changes."
        ),
        "category": "options_greeks",
        "tags": ["rho", "interest rates", "greeks", "options", "leaps"],
    },
    {
        "text": (
            "Implied Volatility (IV) vs Historical Volatility (HV): IV is the "
            "market's forecast of future volatility, derived from option prices. "
            "HV (or realised volatility) measures actual past price movements. "
            "When IV > HV, options are overpriced (consider selling). When IV < HV, "
            "options are underpriced (consider buying). The IV-HV spread is a "
            "common mean-reversion signal. IV Rank (percentile over last year) and "
            "IV Percentile help determine if current IV is high or low. IV Rank > 50% "
            "means current IV is above its 1-year median. IV is typically highest "
            "during market crashes and lowest during steady trends."
        ),
        "category": "options_greeks",
        "tags": ["iv", "implied volatility", "historical volatility", "iv rank", "options"],
    },
    {
        "text": (
            "Volatility Smile and Skew: In equity options, implied volatility varies "
            "by strike price, creating a 'smile' or 'skew' pattern. OTM puts "
            "typically have higher IV than OTM calls (skew), reflecting market's "
            "fear of downside crashes. This is the 'volatility skew' or 'risk "
            "reversal'. A steeper skew indicates more fear. During normal markets, "
            "OTM puts trade at a premium to OTM calls. During euphoria, the skew "
            "flattens. In F&O markets, the skew for NIFTY and BANKNIFTY can help "
            "identify market sentiment. A flattening or inverted skew can signal "
            "a potential market top."
        ),
        "category": "options_greeks",
        "tags": ["volatility skew", "smile", "risk reversal", "options", "sentiment"],
    },
    {
        "text": (
            "Expected Move and Option Pricing: The ATM straddle (ATM call + ATM put) "
            "price approximates the market's expected 1-standard-deviation move "
            "until expiry. For NIFTY: if the ATM straddle costs Rs 500, the market "
            "expects approximately a +/-1% move by expiry. The expected move = "
            "0.85 * (ATM straddle price). Options traders use this to set profit "
            "targets and stop losses. If an option strategy costs more than the "
            "expected move, it may be overpriced. Expected move expands during "
            "high-volatility events (budget day, Fed meetings, elections)."
        ),
        "category": "options_greeks",
        "tags": ["expected move", "straddle", "option pricing", "volatility"],
    },

    # ── Trading Strategies ─────────────────────────────────────────────

    {
        "text": (
            "Iron Condor: A four-leg options strategy designed to profit from "
            "low volatility. Sell an OTM put spread (sell put + buy lower strike "
            "put) AND sell an OTM call spread (sell call + buy higher strike call). "
            "All legs have the same expiry. Max profit = net credit received. "
            "Max loss = width of one wing - credit. Best used when IV is high and "
            "you expect the underlying to stay within a range. For NIFTY: typical "
            "width is 500-1000 points (5-10 strikes). Enter when IV Rank > 50%. "
            "Manage at 50% of max profit. This is an advanced strategy suitable "
            "for experienced options traders with adequate margin."
        ),
        "category": "strategy",
        "tags": ["iron condor", "credit spread", "non-directional", "volatility", "options"],
    },
    {
        "text": (
            "Straddle: Buy both an ATM call and ATM put with the same strike and "
            "expiry. Profit when the underlying moves significantly in either "
            "direction (beyond the combined premium paid). Best used before major "
            "events (budget, RBI policy, earnings) where a large move is expected "
            "but direction is uncertain. Max loss = premium paid. Breakeven points: "
            "strike +/- total premium. Strangle: similar but uses OTM call and "
            "OTM put — cheaper but requires a larger move to profit. After the "
            "event, close before IV collapses. Long straddles suffer from theta "
            "decay, so timing is critical."
        ),
        "category": "strategy",
        "tags": ["straddle", "strangle", "volatility", "events", "earnings", "non-directional"],
    },
    {
        "text": (
            "Covered Call: Own 100 shares (or the equivalent lot size in NIFTY/BANKNIFTY) "
            "and sell an OTM call against it. This generates income (premium) but "
            "caps upside. Best used in a mildly bullish or neutral market where "
            "you expect the stock to trade sideways or slightly up. The sold call's "
            "strike should be above your entry price. If assigned, you sell shares "
            "at the strike price (still a profit if above cost basis). Max loss = "
            "unlimited (stock can fall). This is a conservative strategy suitable "
            "for long-term holders of index ETFs or large-cap stocks. For NIFTY, "
            "1 lot = 50 units."
        ),
        "category": "strategy",
        "tags": ["covered call", "income", "buy write", "options", "conservative"],
    },
    {
        "text": (
            "Credit Spread (Bull Put / Bear Call): Bull Put Spread: sell an OTM "
            "put and buy a further OTM put (same expiry). Collect premium. Profit "
            "if underlying stays above short strike. Bear Call Spread: sell an OTM "
            "call and buy a further OTM call. Collect premium. Profit if underlying "
            "stays below short strike. Max profit = net credit. Max loss = width - "
            "credit. Manage at 50% profit or if underlying breaches short strike. "
            "These are defined-risk, high-probability strategies. For NIFTY: 1:2 "
            "risk-to-reward is typical. Use when IV is elevated to capture "
            "volatility premium."
        ),
        "category": "strategy",
        "tags": ["credit spread", "bull put", "bear call", "defined risk", "options"],
    },
    {
        "text": (
            "Option Buying (Long Call / Long Put): Buy an ATM or slightly OTM "
            "option for directional exposure. Long Call: bullish. Long Put: "
            "bearish. Advantages: defined risk (premium only), unlimited upside "
            "(calls), no margin required. Disadvantages: theta decay works against "
            "you, need directional move significantly before expiry to profit. "
            "Best used when: 1) Strong directional conviction, 2) Low IV (options "
            "are cheap), 3) Adequate time to expiry (30-60 days). Avoid buying "
            "options with less than 7 DTE unless earnings/event play. Position "
            "sizing: risk no more than 2-5% of capital per trade. Options expire "
            "worthless ~80% of the time."
        ),
        "category": "strategy",
        "tags": ["long call", "long put", "directional", "options buying", "theta"],
    },
    {
        "text": (
            "Iron Butterfly: A four-leg strategy that profits from low volatility "
            "at a specific price point. Sell an ATM straddle + buy an OTM put "
            "spread (for protection) + buy an OTM call spread (for protection). "
            "Max profit at the short strike (the meat of the butterfly). Max loss "
            "limited to the width of one wing minus credit received. Higher premium "
            "capture than Iron Condor, but narrower profit zone. Best when you "
            "expect the underlying to settle very close to a specific price at expiry "
            "(e.g., NIFTY close at 18000 on expiry day). Requires precise timing. "
            "High commissions due to 4 legs."
        ),
        "category": "strategy",
        "tags": ["iron butterfly", "straddle", "options", "non-directional", "volatility"],
    },
    {
        "text": (
            "Calendar (Time) Spread: Simultaneously buy a longer-dated option and "
            "sell a shorter-dated option at the same strike. Profit from accelerated "
            "time decay of the short option vs slow decay of the long option. The "
            "short option decays faster (especially in last 30 days), while the "
            "long option maintains more value. Neutral outlook — profit if underlying "
            "stays near the strike. Best entered when term structure (IV of back "
            "month > front month) is favourable. For NIFTY: sell weekly expiry, "
            "buy monthly expiry at same strike. Manage when short option expires "
            "or reaches 50% profit."
        ),
        "category": "strategy",
        "tags": ["calendar spread", "time spread", "theta", "options", "neutral"],
    },
    {
        "text": (
            "Delta Hedging: A technique to neutralise directional risk in options "
            "positions. If you have a long call with delta 0.6, you short 60 shares "
            "(or equivalent futures) per lot to make the position delta-neutral. "
            "This isolates gamma and theta — you profit from time decay and "
            "volatility changes without caring about direction. Requires continuous "
            "rebalancing as delta changes. Gamma scalping: profit from small price "
            "oscillations by rehedging. Most suitable for institutional traders due "
            "to transaction costs. Common in market making and volatility arbitrage."
        ),
        "category": "strategy",
        "tags": ["delta hedging", "gamma scalping", "neutral", "options", "advanced"],
    },

    # ── Technical Analysis ────────────────────────────────────────────

    {
        "text": (
            "Support and Resistance: Support is a price level where buying is "
            "strong enough to prevent further decline. Resistance is a level where "
            "selling prevents further advance. Key concepts: 1) Role reversal — "
            "resistance becomes support after being broken, and vice versa. "
            "2) Round numbers (18000 for NIFTY) act as psychological S/R. 3) The "
            "more times a level is tested, the stronger it becomes (unless it "
            "breaks). 4) Volume confirms breaks — a resistance break on low volume "
            "is suspect. 5) Prior highs/lows are natural S/R. 6) Moving averages "
            "act as dynamic S/R (20, 50, 200 EMA especially for NIFTY/BANKNIFTY)."
        ),
        "category": "technical_analysis",
        "tags": ["support", "resistance", "s/r", "levels", "technical analysis"],
    },
    {
        "text": (
            "Trend Analysis: Uptrend = higher highs + higher lows. Downtrend = "
            "lower highs + lower lows. Sideways/Range = roughly equal highs and "
            "lows. Trendlines: drawn connecting at least 2 reaction highs/lows "
            "(3 touches make it significant). The steeper the trendline, the less "
            "reliable. Pullbacks to trendlines in a strong trend are entry "
            "opportunities. Trend is your friend — trade in the direction of the "
            "larger timeframe trend. Use multiple timeframes to confirm: daily "
            "for primary trend, 1-hour for secondary trend, 15-min for entry. "
            "A reversal requires a break of trendline AND a break of the previous "
            "swing high/low."
        ),
        "category": "technical_analysis",
        "tags": ["trend", "uptrend", "downtrend", "trendline", "pullback", "technical analysis"],
    },
    {
        "text": (
            "Moving Averages: SMA (Simple) = average of N closing prices. EMA "
            "(Exponential) = gives more weight to recent prices, reacts faster. "
            "Common periods: 9 and 21 EMA (short-term), 50 EMA (medium-term), "
            "200 EMA (long-term). Golden Cross: 50 EMA crosses above 200 EMA "
            "(bullish). Death Cross: 50 EMA crosses below 200 EMA (bearish). "
            "In trending markets, price tends to respect EMAs as support/resistance. "
            "In ranging markets, EMAs give false signals. The 20 EMA on NIFTY "
            "daily is a strong support in uptrends. Moving average convergence/divergence "
            "with price is a common entry signal."
        ),
        "category": "technical_analysis",
        "tags": ["moving average", "ema", "sma", "golden cross", "death cross", "technical analysis"],
    },
    {
        "text": (
            "RSI (Relative Strength Index): A momentum oscillator measuring the "
            "speed and change of price movements on a scale of 0-100. RSI > 70 = "
            "overbought (potential sell/reversal). RSI < 30 = oversold (potential "
            "buy/reversal). In strong trends, RSI can stay overbought/oversold for "
            "extended periods. Divergence: when price makes a new high but RSI "
            "makes a lower high (bearish divergence — weakening momentum). Similarly "
            "for bullish divergence at lows. RSI 14 is the default period. RSI 7-9 "
            "is more sensitive. RSI 21-28 is smoother. Failed swings (RSI crosses "
            "above 30 then back below) can signal entry points."
        ),
        "category": "technical_analysis",
        "tags": ["rsi", "relative strength index", "momentum", "overbought", "oversold", "divergence"],
    },
    {
        "text": (
            "MACD (Moving Average Convergence Divergence): A trend-following "
            "momentum indicator with three components: 1) MACD line = 12 EMA - "
            "26 EMA, 2) Signal line = 9 EMA of MACD line, 3) Histogram = MACD "
            "line - Signal line. Bullish: MACD crosses above signal line (buy). "
            "Bearish: MACD crosses below signal line (sell). Zero line crossover: "
            "MACD above zero = bullish momentum, below zero = bearish. Divergence: "
            "price makes higher high but MACD makes lower high (bearish divergence — "
            "trend weakening). MACD works best in trending markets, gives false "
            "signals in ranges. Default settings: 12, 26, 9 for daily charts."
        ),
        "category": "technical_analysis",
        "tags": ["macd", "moving average convergence divergence", "momentum", "trend"],
    },
    {
        "text": (
            "Bollinger Bands: A volatility indicator with three lines: 20-period "
            "SMA (middle), upper band = SMA + 2*SD, lower band = SMA - 2*SD "
            "(SD = standard deviation). When bands widen, volatility is increasing. "
            "When bands contract (squeeze), a big move is imminent. Price touching "
            "the upper band = overextended (but not necessarily a sell — strong "
            "trends can walk the band). Price touching lower band = oversold. "
            "Band walk: price hugging the upper band in a strong uptrend. Squeeze "
            "followed by expansion is the most reliable signal. For NIFTY/BANKNIFTY, "
            "the 2.0 SD setting works well. Adjust to 2.5 SD for crypto."
        ),
        "category": "technical_analysis",
        "tags": ["bollinger bands", "volatility", "squeeze", "bands", "standard deviation"],
    },
    {
        "text": (
            "Fibonacci Retracement: Key ratios (23.6%, 38.2%, 50%, 61.8%, 78.6%) "
            "used to identify potential support/resistance levels after a price "
            "move. Draw from swing low to swing high (downtrend retracement) or "
            "vice versa. The 61.8% level (golden ratio) is the most significant. "
            "In a strong trend, retracements typically stop at 38.2% or 50%. "
            "In weaker trends, deeper retracements to 61.8% are common. Confluence "
            "with moving averages or prior S/R increases significance. Extension "
            "levels (127.2%, 161.8%) project price targets. For NIFTY: 50% and "
            "61.8% retracements of major moves are closely watched by institutional "
            "traders."
        ),
        "category": "technical_analysis",
        "tags": ["fibonacci", "retracement", "golden ratio", "technical analysis", "levels"],
    },
    {
        "text": (
            "Volume Analysis: Volume confirms price action. Rising price + rising "
            "volume = strong trend (healthy). Rising price + falling volume = "
            "weakening trend (potential reversal). Volume spikes at support/"
            "resistance confirm breaks. Volume Profile: displays volume at specific "
            "price levels, identifying high-volume nodes (support/resistance) and "
            "low-volume nodes (where price moves quickly). On-balance Volume (OBV) "
            "cumulates volume on up/down days. OBV leading price = smart money "
            "accumulating/distributing. In Indian markets, delivery percentage "
            "(% of delivery in total volume) helps identify genuine accumulation "
            "vs speculative activity."
        ),
        "category": "technical_analysis",
        "tags": ["volume", "obv", "volume profile", "delivery", "technical analysis"],
    },
    {
        "text": (
            "Chart Patterns (Continuation): Flags, Pennants, and Wedges are short-term "
            "continuation patterns. Bull Flag: sharp upward move (flagpole) followed "
            "by a downward-sloping consolidation (flag) — break above flag = "
            "continuation higher. Bear Flag: opposite for downtrends. Pennants: "
            "small symmetrical triangles after a sharp move. Rising Wedge (bearish): "
            "price making higher highs within converging trendlines. Falling Wedge "
            "(bullish): lower lows within converging trendlines. Measured move "
            "target: add the flagpole height to the breakout point. Volume should "
            "decline during consolidation and expand on breakout."
        ),
        "category": "technical_analysis",
        "tags": ["flag", "pennant", "wedge", "chart pattern", "continuation", "breakout"],
    },
    {
        "text": (
            "Chart Patterns (Reversal): Head and Shoulders (H&S) — three peaks "
            "with the middle (head) higher than the two shoulders. Neckline breaks "
            "to confirm. Target = distance from head to neckline projected downward. "
            "Inverse H&S is the bullish version. Double Top: two roughly equal "
            "peaks with a valley between. Neckline break confirms. Double Bottom: "
            "opposite. Triple Top/Bottom: stronger version. Rounding Bottom (saucer): "
            "long-term reversal pattern. These patterns are more reliable on higher "
            "timeframes (daily, weekly). Volume confirmation is critical — declining "
            "volume during formation, expanding on breakout. False breakouts above "
            "neckline are common — wait for a daily close to confirm."
        ),
        "category": "technical_analysis",
        "tags": ["head and shoulders", "double top", "double bottom", "reversal", "chart pattern"],
    },

    # ── Risk Management ────────────────────────────────────────────────

    {
        "text": (
            "Position Sizing (Kelly Criterion and Fixed %): Never risk more than "
            "1-2% of your trading capital on any single trade. For a Rs 5,00,000 "
            "account: max risk per trade = Rs 5,000-10,000. Position size = (account "
            "* risk_percent) / (entry_price - stop_loss_price). For F&O: calculate "
            "based on premium at risk, not notional value. Half-Kelly (1/2 of Kelly %) "
            "is recommended for retail traders. If win rate = 60% and avg win/avg loss "
            "= 2:1, Kelly suggests risking ~33% — but in practice limit to 1-2%. "
            "The goal is to survive losing streaks (typical max consecutive losses "
            "= 5-10 for active traders)."
        ),
        "category": "risk_management",
        "tags": ["position sizing", "kelly", "risk management", "capital management"],
    },
    {
        "text": (
            "Stop Loss Strategies: 1) Fixed % stop: 5-10% below entry for stocks, "
            "30-50% for options premium (options can lose 100%). 2) ATR-based stop: "
            "1.5-2x ATR(14) below entry. Adjusts for volatility. 3) Support-based "
            "stop: place just below the nearest support level. 4) Moving average "
            "stop: below 20 EMA for trend trades. 5) Trail stop: raise stop as "
            "price moves in your favour (trailing % or ATR). For NIFTY futures: "
            "ATR of ~200-250 points → 400-point stop is reasonable. Always use "
            "electronic stops (broker-side) not mental stops — mental stops are "
            "not enforced and lead to larger losses."
        ),
        "category": "risk_management",
        "tags": ["stop loss", "trailing stop", "atr stop", "risk management"],
    },
    {
        "text": (
            "Risk-Reward Ratio (R:R): Every trade should have a clear risk-reward "
            "ratio before entry. Minimum 1:2 is recommended — risk Rs 100 to make "
            "Rs 200. R:R = (target_price - entry_price) / (entry_price - stop_price) "
            "for longs. Even with only 40% win rate, a 1:3 R:R strategy is profitable "
            "(+20% expected return per trade). Win rate alone is misleading — a 90% "
            "win rate strategy can lose money if losses are 10x larger than wins. "
            "Track both metrics. For options: adjust R:R to account for theta decay "
            "— options need more favourable R:R due to time drag."
        ),
        "category": "risk_management",
        "tags": ["risk reward", "r:r", "ratio", "win rate", "risk management"],
    },
    {
        "text": (
            "Correlation and Diversification: NIFTY 50, BANKNIFTY, and FINNIFTY are "
            "highly correlated (0.7-0.9). Holding positions in all three is NOT "
            "diversification — they tend to move together. True diversification: "
            "add asset classes (gold, commodities, international equities). For "
            "intraday: limit to 3-5 uncorrelated positions. The maximum drawdown "
            "of a portfolio = sum of individual risks if perfectly correlated. "
            "With uncorrelated assets, portfolio risk = sqrt(sum of squared risks). "
            "During market crashes, correlations converge to 1 (all assets fall "
            "together), so diversification provides less protection than expected."
        ),
        "category": "risk_management",
        "tags": ["correlation", "diversification", "portfolio", "risk management", "drawdown"],
    },
    {
        "text": (
            "The 1% Rule for Day Trading: Risk no more than 1% of capital per day. "
            "If you lose 1% in a day, stop trading. This prevents a single bad day "
            "from becoming a catastrophic week. Example: Rs 5,00,000 account → max "
            "daily loss = Rs 5,000. If you lose that, walk away. Most traders blow "
            "up because they try to 'make back' losses by taking oversized risks. "
            "Similarly, after 2-3 consecutive losses, take a break (step away from "
            "the screen for at least 30 minutes). Keep a trading journal — review "
            "every trade to identify patterns in your losing streaks."
        ),
        "category": "risk_management",
        "tags": ["1% rule", "daily loss limit", "trading psychology", "risk management"],
    },

    # ── Broker-Specific ────────────────────────────────────────────────

    {
        "text": (
            "Zerodha (largest Indian broker): Kite platform. API access available "
            "for algorithmic trading. 3-in-1: trading + demat + bank account. "
            "Account opening: free. Brokerage: Rs 20 per executed order (intraday "
            "and F&O), 0% for delivery (but 0.1% STT applies). MIS margin: 5-20%. "
            "NRML margin: SPAN + Exposure. Supports GTT (Good Till Triggered) for "
            "up to 1 year. Login via Kite Connect API for algorithmic trading. "
            "Kite app available for mobile. Coin platform for direct mutual funds. "
            "Zerodha charges account maintenance fee of Rs 300/year (waived for "
            "first year)."
        ),
        "category": "broker",
        "tags": ["zerodha", "kite", "broker", "api", "margin"],
    },
    {
        "text": (
            "Angel One: Full-service and discount broker. Angel Speed platform. "
            "API available via SmartAPI for algorithmic trading. Brokerage: Rs 20 "
            "per order (intraday/F&O), 0% equity delivery. Angel also offers "
            "margin trading facility (MTF) for delivery at 4x leverage. Has research "
            "reports and advisory services. ARQ (AI-based stock recommendation) "
            "engine integrated. Account opening: free. Angel One charges annual "
            "maintenance fees. Supports GTT orders. Margin: MIS 5-20%, NRML Full. "
            "SmartAPI supports WebSocket for real-time data."
        ),
        "category": "broker",
        "tags": ["angel one", "smartapi", "broker", "api", "margin"],
    },
    {
        "text": (
            "Upstox (formerly RKSV): Discount broker backed by Ratan Tata and Tiger "
            "Global. Upstox Pro platform. API available via Upstox API for algo "
            "trading. Brokerage: Rs 20 per order (intraday/F&O), delivery free. "
            "Account opening: free. Upstox offers competitive margin and a clean "
            "mobile app. Supports GTT orders. Auto square-off at 3:15 PM for "
            "intraday positions. Upstox API supports WebSocket streaming. Margin "
            "rates: MIS 5-20% for equities, SPAN for F&O. Charges AMC after the "
            "first year. Good for active traders due to low brokerage."
        ),
        "category": "broker",
        "tags": ["upstox", "broker", "api", "margin", "discount broker"],
    },
    {
        "text": (
            "API Trading and Smart Order Routing: SilverTrade AI supports algorithmic "
            "trading via broker APIs. For supporting an API: 1) The order goes through "
            "pre-trade risk validation (Phase 7 checks). 2) Smart order routing "
            "chooses the best broker (when multiple configured) based on margin and "
            "liquidity. 3) Order types: MARKET, LIMIT, SL (Stop Loss), SL-M. "
            "4) Product types: MIS (intraday, auto-square-off), NRML (overnight). "
            "5) Orders are placed via the broker's REST API with fallback to backup "
            "broker if primary fails (broker failover). 6) Order status is tracked "
            "and logged. All brokers have rate limits — exceeding them may temporarily "
            "block API access."
        ),
        "category": "broker",
        "tags": ["api trading", "smart order", "order routing", "broker", "algo trading"],
    },
    {
        "text": (
            "MCX (Multi Commodity Exchange) Trading: India's leading commodity "
            "derivatives exchange. Products: Gold, Silver, Crude Oil, Natural Gas, "
            "Copper, Zinc, Lead, Aluminium. Trading sessions: Morning 9:00 AM - "
            "5:00 PM, Evening 5:00 PM - 11:30 PM (winter) / 11:55 PM (summer). "
            "International commodity prices (COMEX, NYMEX, LME) influence domestic "
            "prices. Commodity options introduced in recent years (Gold, Silver, "
            "Crude Oil). Contract units: Gold 1kg, Silver 30kg, Crude Oil 100 barrels. "
            "Margin: SPAN % VAR (Value at Risk) + ELM (Extreme Loss Margin). "
            "Physical delivery available for some contracts."
        ),
        "category": "broker",
        "tags": ["mcx", "commodity", "gold", "silver", "crude oil", "broker"],
    },
]
