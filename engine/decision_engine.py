import pandas as pd
import numpy as np

def evaluate_stock(df: pd.DataFrame, timeframe: str = "Swing Trading (1-4 Weeks)") -> dict:
    """
    Core Xerces Decision Engine to calculate BUY, SELL, or HOLD decisions,
    entry/exit targets, stop-loss, and multi-factor score tailored to chosen timeframe.
    """
    if df.empty or len(df) < 25:
        return {
            "decision": "HOLD",
            "confidence": 50,
            "score_pct": 50.0,
            "timeframe": timeframe,
            "current_price": 0.0,
            "entry_min": 0.0, "entry_max": 0.0,
            "target_1": 0.0, "target_2": 0.0,
            "stop_loss": 0.0, "rr_ratio": 0.0,
            "atr": 0.0,
            "summary": "Insufficient price data to perform technical evaluation.",
            "bullish_factors": [], "bearish_factors": [], "risk_warnings": ["Data insufficient"]
        }
    
    last_row = df.iloc[-1]
    prev_row = df.iloc[-2]
    
    current_price = float(last_row['close'])
    atr = float(last_row['atr_14']) if ('atr_14' in last_row and not np.isnan(last_row['atr_14'])) else current_price * 0.02
    
    bullish_factors = []
    bearish_factors = []
    risk_warnings = []
    
    total_score = 0.0
    max_score = 0.0
    
    # -------------------------------------------------------------
    # 1. TIMEFRAME SPECIFIC EVALUATION
    # -------------------------------------------------------------
    if "Swing" in timeframe:
        # Swing Trading: Focus on EMA 9/21, RSI, MACD, Volume
        
        # Factor A: EMA 9 / 21 Trend
        max_score += 25
        if last_row.get('ema_9', 0) > last_row.get('ema_21', 0):
            total_score += 25
            bullish_factors.append("Fast EMA (9) is above Slow EMA (21) indicating short-term bullish momentum.")
            if prev_row.get('ema_9', 0) <= prev_row.get('ema_21', 0):
                total_score += 5  # Bonus for fresh crossover
                bullish_factors.append("Fresh Bullish EMA (9/21) Golden Crossover detected!")
        else:
            bearish_factors.append("EMA (9) is below EMA (21) indicating short-term bearish pressure.")
            
        # Factor B: RSI Momentum
        max_score += 25
        rsi = float(last_row.get('rsi_14', 50))
        if rsi >= 50 and rsi <= 70:
            total_score += 25
            bullish_factors.append(f"RSI ({rsi:.1f}) is in optimal bullish momentum range (50-70).")
        elif rsi < 35:
            total_score += 15
            bullish_factors.append(f"RSI ({rsi:.1f}) is oversold; potential mean-reversion bounce.")
        elif rsi > 70:
            total_score += 5
            bearish_factors.append(f"RSI ({rsi:.1f}) is overbought (>70). Watch for pullback.")
            risk_warnings.append("High RSI overbought risk.")
        else:
            total_score += 10
            
        # Factor C: MACD Signal
        max_score += 25
        if last_row.get('macd_hist', 0) > 0:
            total_score += 25
            bullish_factors.append("MACD Histogram is positive and expanding.")
        else:
            bearish_factors.append("MACD Histogram is negative, showing bearish momentum.")
            
        # Factor D: Volume Spike
        max_score += 25
        vol_ratio = float(last_row.get('volume_ratio', 1.0))
        if vol_ratio >= 1.2:
            total_score += 25
            bullish_factors.append(f"High buying volume spike ({vol_ratio:.2f}x of 20-day average).")
        elif vol_ratio < 0.8:
            total_score += 10
            bearish_factors.append("Below-average volume indicates weak momentum.")
        else:
            total_score += 15

        # Targets & Stop Loss for Swing (Multiplier based on ATR)
        stop_loss = round(current_price - (1.5 * atr), 2)
        target_1 = round(current_price + (2.0 * atr), 2)
        target_2 = round(current_price + (3.5 * atr), 2)

    elif "Short-Term" in timeframe:
        # Short Term (1-3 Months): Focus on 20/50 SMA, Bollinger Bands, MACD Line
        
        max_score += 30
        if last_row.get('close', 0) > last_row.get('sma_50', 0):
            total_score += 30
            bullish_factors.append("Price is trading above 50-day SMA, supporting medium-term uptrend.")
        else:
            bearish_factors.append("Price is below 50-day SMA, indicating medium-term weakness.")
            
        max_score += 25
        if last_row.get('sma_20', 0) > last_row.get('sma_50', 0):
            total_score += 25
            bullish_factors.append("20-day SMA is above 50-day SMA (Bullish alignment).")
        else:
            bearish_factors.append("20-day SMA is below 50-day SMA (Bearish alignment).")
            
        max_score += 25
        bb_upper = float(last_row.get('bb_upper', current_price * 1.05))
        bb_lower = float(last_row.get('bb_lower', current_price * 0.95))
        if current_price < bb_lower * 1.02:
            total_score += 20
            bullish_factors.append("Price near lower Bollinger Band; oversold opportunity.")
        elif current_price > bb_upper * 0.98:
            bearish_factors.append("Price near upper Bollinger Band; resistance test.")
        else:
            total_score += 15
            
        max_score += 20
        rsi = float(last_row.get('rsi_14', 50))
        if 45 <= rsi <= 65:
            total_score += 20
            bullish_factors.append(f"RSI ({rsi:.1f}) balanced in medium-term growth zone.")
            
        stop_loss = round(min(last_row.get('sma_50', current_price * 0.95) * 0.98, current_price - (2.0 * atr)), 2)
        target_1 = round(current_price + (3.0 * atr), 2)
        target_2 = round(current_price + (5.0 * atr), 2)

    else:
        # Long-Term (1-5 Years): Focus on 200 SMA, 52-Week Range, Structural Trend
        
        max_score += 35
        if last_row.get('close', 0) > last_row.get('sma_200', 0):
            total_score += 35
            bullish_factors.append("Price is well above the 200-day SMA, confirming long-term bull market.")
        else:
            bearish_factors.append("Price is below 200-day SMA, indicating long-term bear structure.")
            
        max_score += 35
        if last_row.get('sma_50', 0) > last_row.get('sma_200', 0):
            total_score += 35
            bullish_factors.append("Golden Cross active (50-day SMA > 200-day SMA).")
        else:
            bearish_factors.append("Death Cross structure (50-day SMA < 200-day SMA).")
            
        max_score += 30
        rsi = float(last_row.get('rsi_14', 50))
        if rsi < 45:
            total_score += 30
            bullish_factors.append(f"Long-term accumulation zone (RSI {rsi:.1f}).")
        else:
            total_score += 15
            
        stop_loss = round(min(last_row.get('sma_200', current_price * 0.90) * 0.95, current_price - (3.5 * atr)), 2)
        target_1 = round(current_price * 1.15, 2)
        target_2 = round(current_price * 1.30, 2)

    # -------------------------------------------------------------
    # 2. FINAL SCORE & DECISION COMPUTATION
    # -------------------------------------------------------------
    score_percentage = (total_score / max_score) * 100 if max_score > 0 else 50
    
    if score_percentage >= 65:
        decision = "BUY"
        confidence = min(round(score_percentage), 95)
        summary = f"Strong bullish confluence on {timeframe}. High-probability buy signal."
    elif score_percentage <= 38:
        decision = "SELL"
        confidence = min(round(100 - score_percentage), 95)
        summary = f"Bearish alignment across key technical indicators on {timeframe}. Liquidate or avoid."
    else:
        decision = "HOLD"
        confidence = round(100 - abs(score_percentage - 50) * 2)
        summary = f"Neutral market consolidation on {timeframe}. Maintain current position or await breakout confirmation."
        
    # Entry zone calculation
    entry_min = round(current_price * 0.992, 2)
    entry_max = round(current_price * 1.005, 2)
    
    # Risk-Reward Calculation
    risk = max(current_price - stop_loss, 0.01)
    reward = max(target_1 - current_price, 0.01)
    rr_ratio = round(reward / risk, 2)
    
    return {
        "decision": decision,
        "confidence": confidence,
        "score_pct": round(score_percentage, 1),
        "timeframe": timeframe,
        "current_price": round(current_price, 2),
        "entry_min": entry_min,
        "entry_max": entry_max,
        "target_1": target_1,
        "target_2": target_2,
        "stop_loss": stop_loss,
        "rr_ratio": rr_ratio,
        "atr": round(atr, 2),
        "summary": summary,
        "bullish_factors": bullish_factors,
        "bearish_factors": bearish_factors,
        "risk_warnings": risk_warnings
    }
