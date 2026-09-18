import numpy as np
import pandas as pd

def add_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Calculate core technical indicators on the close price series."""
    out = df.copy()
    if len(out) < 20:
        return out
    
    c = out["Close"].astype(float)
    out["Return"]        = c.pct_change()
    out["SMA_20"]        = c.rolling(20).mean()
    out["SMA_50"]        = c.rolling(50).mean()
    out["SMA_200"]       = c.rolling(200).mean()
    out["EMA_12"]        = c.ewm(span=12, adjust=False).mean()
    out["EMA_26"]        = c.ewm(span=26, adjust=False).mean()
    out["MACD"]          = out["EMA_12"] - out["EMA_26"]
    out["MACD_Signal"]   = out["MACD"].ewm(span=9, adjust=False).mean()
    out["MACD_Hist"]     = out["MACD"] - out["MACD_Signal"]
    out["BB_Mid"]        = c.rolling(20).mean()
    out["BB_Std"]        = c.rolling(20).std()
    out["BB_Upper"]      = out["BB_Mid"] + 2 * out["BB_Std"]
    out["BB_Lower"]      = out["BB_Mid"] - 2 * out["BB_Std"]
    out["Volatility_20"] = out["Return"].rolling(20).std() * np.sqrt(252)
    
    delta = c.diff()
    gain  = delta.clip(lower=0).rolling(14).mean()
    loss  = (-delta.clip(upper=0)).rolling(14).mean()
    out["RSI_14"] = 100 - (100 / (1 + gain / (loss + 1e-9)))
    
    if "High" in out.columns and "Low" in out.columns:
        hi = out["High"].astype(float)
        lo = out["Low"].astype(float)
        hl = hi - lo
        hc = (hi - c.shift()).abs()
        lc = (lo - c.shift()).abs()
        out["ATR_14"] = pd.concat([hl, hc, lc], axis=1).max(axis=1).rolling(14).mean()
    else:
        out["ATR_14"] = c.rolling(14).std()
        
    low14  = out["Low"].astype(float).rolling(14).min() if "Low" in out.columns else c.rolling(14).min()
    high14 = out["High"].astype(float).rolling(14).max() if "High" in out.columns else c.rolling(14).max()
    out["Stoch_K"] = (c - low14) / (high14 - low14 + 1e-9) * 100
    out["Stoch_D"] = out["Stoch_K"].rolling(3).mean()
    
    if "Volume" in out.columns:
        vol = out["Volume"].astype(float)
        obv = [0.0]
        for i in range(1, len(out)):
            if out["Close"].iloc[i] > out["Close"].iloc[i-1]:
                obv.append(obv[-1] + vol.iloc[i])
            elif out["Close"].iloc[i] < out["Close"].iloc[i-1]:
                obv.append(obv[-1] - vol.iloc[i])
            else:
                obv.append(obv[-1])
        out["OBV"] = obv
        
    return out

def get_signal(df: pd.DataFrame) -> str:
    """Determine single technical rule signal (BUY/SELL/HOLD)."""
    if len(df) < 52:
        return "HOLD"
    last = df.iloc[-1]
    prev = df.iloc[-2]
    needed = ["SMA_20","SMA_50","RSI_14","MACD","MACD_Signal"]
    if any(pd.isna(last.get(x, np.nan)) for x in needed):
        return "HOLD"
    
    macd_cross_up   = float(last["MACD"]) > float(last["MACD_Signal"]) and float(prev["MACD"]) <= float(prev["MACD_Signal"])
    macd_cross_down = float(last["MACD"]) < float(last["MACD_Signal"]) and float(prev["MACD"]) >= float(prev["MACD_Signal"])
    trend_up   = float(last["SMA_20"]) > float(last["SMA_50"])
    trend_down = float(last["SMA_20"]) < float(last["SMA_50"])
    above_200  = pd.notna(last.get("SMA_200")) and float(last["Close"]) > float(last["SMA_200"])
    rsi = float(last["RSI_14"])
    
    if trend_up and above_200 and rsi < 70 and (macd_cross_up or rsi < 45):
        return "BUY"
    if trend_down and (rsi > 70 or macd_cross_down):
        return "SELL"
    return "HOLD"

def get_signal_strength(df: pd.DataFrame) -> int:
    """Score the tech strength on a scale from 0 to 100."""
    if len(df) < 52:
        return 50
    last = df.iloc[-1]
    score = 50
    try:
        rsi = float(last.get("RSI_14", 50) or 50)
        if rsi < 30:   score += 20
        elif rsi < 45: score += 10
        elif rsi > 70: score -= 20
        elif rsi > 60: score -= 10
        
        sma20 = float(last.get("SMA_20", 0) or 0)
        sma50 = float(last.get("SMA_50", 0) or 0)
        sma200= float(last.get("SMA_200", 0) or 0)
        cl    = float(last.get("Close", 0) or 0)
        
        if sma20 > sma50:  score += 10
        else:              score -= 10
        if cl > sma200:    score += 10
        else:              score -= 10
        
        macd  = float(last.get("MACD", 0) or 0)
        macds = float(last.get("MACD_Signal", 0) or 0)
        if macd > macds:   score += 10
        else:              score -= 10
    except Exception:
        pass
    return max(0, min(100, score))

def detect_market_regime(df: pd.DataFrame) -> dict:
    """
    Identify current market regime:
    - Trending Bull: SMAs stacked, ADX/trend-strength high
    - Trending Bear: SMAs inverted, ADX/trend-strength high
    - Range-bound Volatile: high volatility, SMAs flat/crossing
    - Range-bound Squeeze: low volatility, Bollinger Bands narrowing
    """
    if len(df) < 50:
        return {"regime": "Undetermined", "strength": 50, "volatility": "Medium"}
    
    last = df.iloc[-1]
    close = float(last["Close"])
    
    # Calculate simple moving average slope / alignment
    sma20 = float(last["SMA_20"]) if pd.notna(last.get("SMA_20")) else close
    sma50 = float(last["SMA_50"]) if pd.notna(last.get("SMA_50")) else close
    sma200 = float(last["SMA_200"]) if pd.notna(last.get("SMA_200")) else close
    
    # Standard deviation / BB Width
    bb_upper = float(last["BB_Upper"]) if pd.notna(last.get("BB_Upper")) else close
    bb_lower = float(last["BB_Lower"]) if pd.notna(last.get("BB_Lower")) else close
    bb_width = (bb_upper - bb_lower) / (sma20 + 1e-9)
    
    # Historical bb_width values to check for squeeze
    historical_bb_widths = (df["BB_Upper"] - df["BB_Lower"]) / (df["BB_Mid"] + 1e-9)
    bb_width_percentile = float(historical_bb_widths.rolling(100).rank(pct=True).iloc[-1]) if len(historical_bb_widths) >= 100 else 0.5
    
    vol = float(last.get("Volatility_20", 0.2))
    
    # Trend Strength (Slope of 20 SMA vs 50 SMA)
    prev_10 = df.iloc[-10] if len(df) >= 10 else df.iloc[0]
    sma20_prev = float(prev_10["SMA_20"]) if pd.notna(prev_10.get("SMA_20")) else close
    trend_slope = (sma20 - sma20_prev) / (sma20_prev + 1e-9)
    
    trend_aligned_bull = (close > sma20 > sma50 > sma200)
    trend_aligned_bear = (close < sma20 < sma50 < sma200)
    
    if trend_aligned_bull and trend_slope > 0.005:
        regime = "Trending Bull"
        strength = int(min(100, 70 + trend_slope * 2000))
    elif trend_aligned_bear and trend_slope < -0.005:
        regime = "Trending Bear"
        strength = int(min(100, 70 + abs(trend_slope) * 2000))
    else:
        # Range-bound
        if bb_width_percentile < 0.25:
            regime = "Range-bound Squeeze"
            strength = int(40 - (0.25 - bb_width_percentile) * 100)
        else:
            regime = "Range-bound Volatile"
            strength = int(min(70, max(30, vol * 150)))
            
    vol_label = "High" if vol > 0.35 else "Low" if vol < 0.15 else "Medium"
    
    return {
        "regime": regime,
        "strength": strength,
        "volatility": vol_label,
        "bb_width": round(bb_width, 4),
        "bb_width_percentile": round(bb_width_percentile * 100, 1),
        "volatility_val": round(vol, 4)
    }

def confirm_multi_timeframe(df: pd.DataFrame) -> dict:
    """
    Check confirmation of trend across Daily, Weekly, and Monthly charts.
    Returns confirmations and aggregate confidence score (%).
    """
    if len(df) < 100:
        return {"confirmed": False, "confidence": 50, "daily": "Neutral", "weekly": "Neutral", "monthly": "Neutral"}
    
    # 1. Daily
    last = df.iloc[-1]
    c_d = float(last["Close"])
    sma20_d = float(last["SMA_20"])
    sma50_d = float(last["SMA_50"])
    daily_trend = "Bullish" if c_d > sma20_d > sma50_d else ("Bearish" if c_d < sma20_d < sma50_d else "Neutral")
    
    # 2. Weekly (Aggregate every 5 rows)
    weekly_close = df["Close"].iloc[::5].astype(float)
    if len(weekly_close) >= 20:
        w_last = weekly_close.iloc[-1]
        w_sma5 = weekly_close.rolling(5).mean().iloc[-1]
        w_sma10 = weekly_close.rolling(10).mean().iloc[-1]
        weekly_trend = "Bullish" if w_last > w_sma5 > w_sma10 else ("Bearish" if w_last < w_sma5 < w_sma10 else "Neutral")
    else:
        weekly_trend = "Neutral"
        
    # 3. Monthly (Aggregate every 20 rows)
    monthly_close = df["Close"].iloc[::20].astype(float)
    if len(monthly_close) >= 10:
        m_last = monthly_close.iloc[-1]
        m_sma3 = monthly_close.rolling(3).mean().iloc[-1]
        m_sma5 = monthly_close.rolling(5).mean().iloc[-1]
        monthly_trend = "Bullish" if m_last > m_sma3 > m_sma5 else ("Bearish" if m_last < m_sma3 < m_sma5 else "Neutral")
    else:
        monthly_trend = "Neutral"
        
    # Calculate confidence based on alignment
    alignment = [daily_trend, weekly_trend, monthly_trend]
    bull_count = alignment.count("Bullish")
    bear_count = alignment.count("Bearish")
    
    if daily_trend == "Bullish":
        confidence = 60 + bull_count * 15 - bear_count * 10
    elif daily_trend == "Bearish":
        confidence = 60 + bear_count * 15 - bull_count * 10
    else:
        confidence = 50 + (bull_count - bear_count) * 10
        
    confidence = max(10, min(95, confidence))
    confirmed = (bull_count == 3) or (bear_count == 3)
    
    return {
        "confirmed": confirmed,
        "confidence": confidence,
        "daily": daily_trend,
        "weekly": weekly_trend,
        "monthly": monthly_trend,
        "alignment_summary": f"D: {daily_trend} | W: {weekly_trend} | M: {monthly_trend}"
    }

def compute_relative_strength(stock_df: pd.DataFrame, benchmark_df: pd.DataFrame) -> dict:
    """
    Compare stock returns to benchmark (e.g. NIFTY 50) returns.
    Returns beta, alpha, and Mansfield Relative Strength (MRS).
    """
    if len(stock_df) < 60 or benchmark_df is None or len(benchmark_df) < 60:
        return {"alpha": 0.0, "beta": 1.0, "rs_ratio": 1.0, "mansfield_rs": 0.0}
    
    # Align dates
    stock_df = stock_df.copy()
    benchmark_df = benchmark_df.copy()
    
    merged = pd.merge(
        stock_df[["Date", "Close"]], 
        benchmark_df[["Date", "Close"]], 
        on="Date", 
        suffixes=("_stock", "_bench")
    ).sort_values("Date")
    
    if len(merged) < 20:
        return {"alpha": 0.0, "beta": 1.0, "rs_ratio": 1.0, "mansfield_rs": 0.0}
        
    merged["ret_stock"] = merged["Close_stock"].pct_change()
    merged["ret_bench"] = merged["Close_bench"].pct_change()
    merged = merged.dropna()
    
    # Calculate Beta
    cov = merged["ret_stock"].cov(merged["ret_bench"])
    var = merged["ret_bench"].var()
    beta = cov / (var + 1e-9)
    
    # Calculate Alpha (annualized, assuming 252 trading days)
    alpha = (merged["ret_stock"].mean() - beta * merged["ret_bench"].mean()) * 252
    
    # Calculate Mansfield Relative Strength
    # RS Ratio = Stock Close / Benchmark Close
    merged["RS_Ratio"] = merged["Close_stock"] / merged["Close_bench"]
    # 50-day average of RS Ratio
    merged["RS_Ratio_SMA50"] = merged["RS_Ratio"].rolling(50).mean()
    # Mansfield RS = ((RS_Ratio / RS_Ratio_SMA50) - 1) * 10
    last_row = merged.iloc[-1]
    mrs = float(((last_row["RS_Ratio"] / (last_row["RS_Ratio_SMA50"] + 1e-9)) - 1) * 10)
    
    return {
        "alpha": round(alpha * 100, 2), # percentage
        "beta": round(beta, 2),
        "rs_ratio": round(float(last_row["RS_Ratio"]), 4),
        "mansfield_rs": round(mrs, 3),
        "performance_vs_benchmark_1m": round(float((merged["ret_stock"].iloc[-20:].sum() - merged["ret_bench"].iloc[-20:].sum()) * 100), 2)
    }
