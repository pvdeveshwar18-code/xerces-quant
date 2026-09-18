import yfinance as yf
import pandas as pd
import numpy as np

# Market Presets
INDIAN_WATCHLIST = [
    "RELIANCE.NS", "TCS.NS", "INFY.NS", "HDFCBANK.NS",
    "ICICIBANK.NS", "TATAMOTORS.NS", "BHARTIARTL.NS", "SBIN.NS"
]

US_WATCHLIST = [
    "NVDA", "AAPL", "MSFT", "AMZN", "GOOGL", "META", "TSLA", "SPY", "QQQ"
]

INDIAN_INDICES = {"NIFTY 50": "^NSEI", "BANK NIFTY": "^NSEBANK", "SENSEX": "^BSESN"}
US_INDICES = {"S&P 500": "^GSPC", "NASDAQ": "^IXIC", "DOW JONES": "^DJI"}

def get_currency_symbol(ticker_symbol: str) -> str:
    """Returns currency symbol based on exchange suffix."""
    if ticker_symbol.endswith(".NS") or ticker_symbol.endswith(".BO") or ticker_symbol in ["^NSEI", "^NSEBANK", "^BSESN"]:
        return "₹"
    return "$"

def fetch_stock_data(ticker_symbol: str, period: str = "6mo", interval: str = "1d") -> pd.DataFrame:
    """
    Fetch OHLCV historical data using yfinance.
    """
    try:
        ticker = yf.Ticker(ticker_symbol)
        df = ticker.history(period=period, interval=interval)
        if df.empty:
            return pd.DataFrame()
        
        # Standardize column names
        df = df.rename(columns={
            "Open": "open", "High": "high", "Low": "low", "Close": "close", "Volume": "volume"
        })
        return df
    except Exception as e:
        print(f"Error fetching data for {ticker_symbol}: {e}")
        return pd.DataFrame()

def calculate_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate comprehensive technical indicators for Xerces decision engine.
    """
    if df.empty or len(df) < 20:
        return df
    
    df = df.copy()
    close = df['close']
    high = df['high']
    low = df['low']
    
    # 1. Moving Averages
    df['sma_20'] = close.rolling(window=min(20, len(close))).mean()
    df['sma_50'] = close.rolling(window=min(50, len(close))).mean()
    df['sma_200'] = close.rolling(window=min(200, len(close))).mean()
    df['ema_9'] = close.ewm(span=9, adjust=False).mean()
    df['ema_21'] = close.ewm(span=21, adjust=False).mean()
    
    # 2. RSI (14)
    delta = close.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / (loss + 1e-9)
    df['rsi_14'] = 100 - (100 / (1 + rs))
    
    # 3. MACD (12, 26, 9)
    ema_12 = close.ewm(span=12, adjust=False).mean()
    ema_26 = close.ewm(span=26, adjust=False).mean()
    df['macd_line'] = ema_12 - ema_26
    df['macd_signal'] = df['macd_line'].ewm(span=9, adjust=False).mean()
    df['macd_hist'] = df['macd_line'] - df['macd_signal']
    
    # 4. Bollinger Bands (20, 2)
    bb_mid = close.rolling(window=min(20, len(close))).mean()
    bb_std = close.rolling(window=min(20, len(close))).std()
    df['bb_upper'] = bb_mid + (bb_std * 2)
    df['bb_lower'] = bb_mid - (bb_std * 2)
    df['bb_width'] = (df['bb_upper'] - df['bb_lower']) / (bb_mid + 1e-9)
    
    # 5. ATR (Average True Range 14)
    tr1 = high - low
    tr2 = (high - close.shift(1)).abs()
    tr3 = (low - close.shift(1)).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    df['atr_14'] = tr.rolling(window=min(14, len(tr))).mean()
    
    # 6. Volume Metrics
    df['vol_sma_20'] = df['volume'].rolling(window=min(20, len(df))).mean()
    df['volume_ratio'] = df['volume'] / (df['vol_sma_20'] + 1e-9)
    
    return df

def get_stock_info(ticker_symbol: str) -> dict:
    """
    Fetch company info, current price details, and currency.
    """
    currency_symbol = get_currency_symbol(ticker_symbol)
    try:
        t = yf.Ticker(ticker_symbol)
        info = t.info
        name = info.get("shortName", info.get("longName", ticker_symbol))
        price = info.get("currentPrice", info.get("regularMarketPrice", info.get("previousClose", 0.0)))
        prev_close = info.get("previousClose", price)
        change_pct = ((price - prev_close) / prev_close) * 100 if prev_close > 0 else 0.0
        
        return {
            "symbol": ticker_symbol,
            "name": name,
            "sector": info.get("sector", "N/A"),
            "industry": info.get("industry", "N/A"),
            "current_price": price,
            "prev_close": prev_close,
            "change_pct": round(change_pct, 2),
            "currency_symbol": currency_symbol,
            "fiftyTwoWeekHigh": info.get("fiftyTwoWeekHigh", 0.0),
            "fiftyTwoWeekLow": info.get("fiftyTwoWeekLow", 0.0),
            "marketCap": info.get("marketCap", 0)
        }
    except Exception as e:
        return {
            "symbol": ticker_symbol,
            "name": ticker_symbol,
            "sector": "N/A",
            "industry": "N/A",
            "current_price": 0.0,
            "prev_close": 0.0,
            "change_pct": 0.0,
            "currency_symbol": currency_symbol,
            "fiftyTwoWeekHigh": 0.0,
            "fiftyTwoWeekLow": 0.0,
            "marketCap": 0
        }
