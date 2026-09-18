import numpy as np
import pandas as pd
from analytics.indicators import detect_market_regime, confirm_multi_timeframe

def compute_decision(
    df: pd.DataFrame, 
    forecast_bundle: dict = None, 
    sentiment_val: float = 0.0,
    risk_reward: float = 2.0
) -> dict:
    """
    XERCES Decision Engine.
    Combines Technical indicators, Forecast direction, Market regime, Multi-timeframe confirmation,
    and News sentiment into a single actionable Decision Score, Confidence, and Trade Plan.
    """
    if len(df) < 50:
        return {
            "score": 50, "recommendation": "Hold", "confidence": 50,
            "reason": "Insufficient historical data", "entry": 0.0, "stop": 0.0,
            "targets": [0.0, 0.0]
        }
        
    last = df.iloc[-1]
    close = float(last["Close"])
    
    # 1. Trend Subscore (30 points)
    trend_score = 0
    sma20 = float(last["SMA_20"]) if pd.notna(last.get("SMA_20")) else close
    sma50 = float(last["SMA_50"]) if pd.notna(last.get("SMA_50")) else close
    sma200 = float(last["SMA_200"]) if pd.notna(last.get("SMA_200")) else close
    
    if close > sma20: trend_score += 10
    if sma20 > sma50: trend_score += 10
    if close > sma200: trend_score += 10
    
    # 2. Momentum Subscore (25 points)
    mom_score = 0
    rsi = float(last["RSI_14"]) if pd.notna(last.get("RSI_14")) else 50.0
    if 30 <= rsi <= 60: 
        mom_score += 10 # healthy accumulation
    elif rsi < 30: 
        mom_score += 15 # oversold/value buy
    elif rsi > 70:
        mom_score += 0  # overbought risk
        
    macd = float(last.get("MACD", 0))
    macds = float(last.get("MACD_Signal", 0))
    if macd > macds:
        mom_score += 10
        
    # 3. Forecast Subscore (20 points)
    fc_score = 10 # default neutral
    if forecast_bundle is not None:
        ens_fc = forecast_bundle.get("fc_ensemble")
        if ens_fc is not None and len(ens_fc) > 0:
            start_val = close
            end_val = float(ens_fc.iloc[-1])
            fc_return = (end_val - start_val) / (start_val + 1e-9)
            if fc_return > 0.05: 
                fc_score = 20 # strong bullish forecast
            elif fc_return > 0:
                fc_score = 15 # mildly bullish forecast
            elif fc_return < -0.05:
                fc_score = 0  # strong bearish forecast
            else:
                fc_score = 5  # mildly bearish forecast

    # 4. Multi-Timeframe Confirmation (15 points)
    mtf = confirm_multi_timeframe(df)
    mtf_score = 0
    if mtf["daily"] == "Bullish": mtf_score += 5
    if mtf["weekly"] == "Bullish": mtf_score += 5
    if mtf["monthly"] == "Bullish": mtf_score += 5
    # If aligned in same direction, give a bonus
    if mtf["confirmed"]:
        mtf_score = 15 if mtf["daily"] == "Bullish" else 0

    # 5. Sentiment Subscore (10 points)
    sent_score = 5 # default neutral
    if sentiment_val > 0.2:
        sent_score = 10
    elif sentiment_val < -0.2:
        sent_score = 0
        
    # Total Score
    total_score = trend_score + mom_score + fc_score + mtf_score + sent_score
    total_score = max(0, min(100, total_score))
    
    # Recommendation Mapping
    if total_score >= 88:
        reco = "★★★★★ Strong Buy"
    elif total_score >= 70:
        reco = "★★★★☆ Buy"
    elif total_score >= 40:
        reco = "★★★☆☆ Hold"
    elif total_score >= 20:
        reco = "★★☆☆☆ Sell"
    else:
        reco = "★☆☆☆☆ Strong Sell"
        
    # Confidence calculation
    conf = int(mtf["confidence"])
    if forecast_bundle is not None:
        # Boost confidence if the forecast accuracy (100 - MAPE) is high
        best_mape = forecast_bundle.get("ensemble_mape") or 5.0
        acc_mult = max(0.5, min(1.0, 1 - (best_mape / 100.0)))
        conf = int(conf * acc_mult + (100 - best_mape) * (1 - acc_mult))
    conf = max(10, min(95, conf))
    
    # Reason Summary
    reasons = []
    if trend_score >= 20: reasons.append("Trend alignment is positive")
    if trend_score <= 10: reasons.append("Price under pressure below SMAs")
    if macd > macds and 30 <= rsi <= 65: reasons.append("Momentum is in a healthy buy zone")
    if rsi > 70: reasons.append("Momentum is overbought")
    if fc_score >= 15: reasons.append("Forecast consensus is upward trending")
    if fc_score <= 5: reasons.append("Forecast signals correction")
    if mtf["confirmed"]:
        reasons.append("Multi-timeframe trend is fully confirmed")
    if sentiment_val > 0.2:
        reasons.append("Sentiment is highly supportive")
        
    reason_str = " + ".join(reasons) if reasons else "Indicators are showing mixed signals"
    
    # Trade Plan Formulation
    atr = float(last["ATR_14"]) if pd.notna(last.get("ATR_14")) else close * 0.02
    
    # Defensive Entry: close or slightly lower on a pullback
    entry_p = close
    
    # Stop Loss based on ATR
    if "Strong Buy" in reco or "Buy" in reco:
        stop_p = close - atr * 1.5
        t1 = close + atr * 1.5 * risk_reward
        t2 = close + atr * 2.5 * risk_reward
    else:
        # For shorts/holds
        stop_p = close + atr * 1.5
        t1 = close - atr * 1.5 * risk_reward
        t2 = close - atr * 2.5 * risk_reward
        
    return {
        "score": total_score,
        "recommendation": reco,
        "confidence": conf,
        "reason": reason_str,
        "entry": round(entry_p, 2),
        "stop": round(stop_p, 2),
        "targets": [round(t1, 2), round(t2, 2)],
        "breakdown": {
            "trend": trend_score,
            "momentum": mom_score,
            "forecast": fc_score,
            "mtf": mtf_score,
            "sentiment": sent_score
        }
    }
