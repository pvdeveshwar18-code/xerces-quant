"""
Automated Strategy Runner & Live Signal Evaluator.
Evaluates strategy conditions on the latest available market data,
calculates dynamic bracket orders (Entry, Stop Loss, Take Profit),
and routes automated paper/live orders to connected brokers.
"""

from typing import Dict, Any, Optional
import time
import numpy as np
import pandas as pd
from brokers.executor import execute_order

def evaluate_live_strategy_signal(
    df: pd.DataFrame,
    strategy_name: str = "Pullback EMA",
    atr_multiple_sl: float = 1.5,
    risk_reward: float = 2.0,
) -> Dict[str, Any]:
    """
    Evaluates current bar strategy signals and generates execution parameters.
    """
    if df is None or len(df) < 20:
        return {
            "status": "INSUFFICIENT_DATA",
            "action": "HOLD",
            "strength": 0,
            "rationale": "Insufficient historical candles to evaluate strategy.",
            "entry_price": 0.0,
            "stop_loss": 0.0,
            "take_profit": 0.0,
            "risk_reward": risk_reward,
        }

    last = df.iloc[-1]
    prev = df.iloc[-2]
    close = float(last["Close"])
    atr = float(last["ATR_14"]) if "ATR_14" in last and pd.notna(last["ATR_14"]) else (close * 0.02)
    rsi = float(last["RSI_14"]) if "RSI_14" in last and pd.notna(last["RSI_14"]) else 50.0

    action = "HOLD"
    strength = 50
    rationale = "No strong trigger on current bar. Monitoring price action."

    strat_lower = strategy_name.lower()

    if "pullback" in strat_lower or "ema" in strat_lower:
        # Pullback EMA Strategy
        sma20 = float(last.get("SMA_20", close))
        sma50 = float(last.get("SMA_50", close))
        
        # Bullish pullback: Trend is up (SMA20 > SMA50), price touches/tests SMA20 or bounces
        if close >= sma20 and sma20 > sma50 and rsi < 65 and rsi > 40:
            action = "BUY"
            strength = int(min(95, 60 + (65 - rsi) * 1.2))
            rationale = f"Bullish EMA pullback confirmed: Price (₹{close:,.2f}) holding above SMA20 with RSI at {rsi:.1f}."
        elif close < sma20 and sma20 < sma50 and rsi > 35 and rsi < 60:
            action = "SELL"
            strength = int(min(95, 60 + (rsi - 35) * 1.2))
            rationale = f"Bearish EMA rejection: Price below SMA20 in downward trend alignment with RSI at {rsi:.1f}."

    elif "whale" in strat_lower or "flow" in strat_lower or "inflow" in strat_lower:
        # Whale Order Flow Breakout
        from analytics.capital_flow import compute_capital_flow
        c_res = compute_capital_flow(df)
        if c_res:
            c_sum = c_res.get("summary", {})
            c_div = c_res.get("divergence", {})
            if c_sum.get("smart_money_net", 0) > 0 and "BULLISH" in c_div.get("type", ""):
                action = "BUY"
                strength = 85
                rationale = f"Whale Accumulation Breakout: Strong institutional net inflow with {c_div.get('type')} detected."
            elif c_sum.get("smart_money_net", 0) < 0 and "BEARISH" in c_div.get("type", ""):
                action = "SELL"
                strength = 80
                rationale = f"Whale Distribution Breakdown: Institutional selling into highs ({c_div.get('type')})."

    else:
        # General Momentum / Breakout
        macd = float(last.get("MACD", 0))
        macd_sig = float(last.get("MACD_Signal", 0))
        if macd > macd_sig and rsi > 50:
            action = "BUY"
            strength = 70
            rationale = f"MACD Bullish Crossover (MACD: {macd:.2f} > Signal: {macd_sig:.2f}) with RSI > 50."
        elif macd < macd_sig and rsi < 50:
            action = "SELL"
            strength = 68
            rationale = f"MACD Bearish Crossover (MACD: {macd:.2f} < Signal: {macd_sig:.2f}) with RSI < 50."

    # Bracket Order Calculation
    is_buy = action == "BUY"
    sl_dist = atr * atr_multiple_sl
    tp_dist = sl_dist * risk_reward

    stop_loss = round(close - sl_dist if is_buy else close + sl_dist, 2)
    take_profit = round(close + tp_dist if is_buy else close - tp_dist, 2)
    risk_per_share = max(round(abs(close - stop_loss), 2), 0.1)

    return {
        "status": "EVALUATED",
        "action": action,
        "strength": strength,
        "rationale": rationale,
        "entry_price": round(close, 2),
        "stop_loss": stop_loss,
        "take_profit": take_profit,
        "risk_per_share": risk_per_share,
        "risk_reward": risk_reward,
        "atr": round(atr, 2),
        "rsi": round(rsi, 1),
    }

def deploy_strategy_signal(
    broker_name: str,
    symbol: str,
    action: str,
    quantity: int,
    price: float,
    stop_loss: Optional[float] = None,
    take_profit: Optional[float] = None,
    paper_mode: bool = True,
) -> Dict[str, Any]:
    """
    Executes a strategy signal order via broker adapters with bracket metadata.
    """
    res = execute_order(
        broker_name=broker_name,
        symbol=symbol,
        transaction_type=action,
        quantity=quantity,
        price=price,
    )
    
    # Enrich response with strategy bracket metadata
    res["stop_loss"] = stop_loss
    res["take_profit"] = take_profit
    res["paper_mode"] = paper_mode
    return res
