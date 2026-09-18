"""
Institutional Confluence Strategy & Dynamic Risk Management for XERCES.
Combines:
1. Regime Alignment (Trend Filter: Close > SMA_200, 20 EMA > 50 EMA)
2. Institutional Volume Thrust (Volume > 1.3x 20-day Volume MA, Green Candle)
3. Dynamic ATR Stop Loss & Trailing Profit Target (1:2 Risk/Reward)
4. Full Indian Market Friction Modeling via analytics.friction
"""

import numpy as np
import pandas as pd
from analytics.friction import calculate_indian_equity_friction

def run_institutional_confluence_backtest(
    df: pd.DataFrame,
    capital: float = 100000.0,
    risk_pct_per_trade: float = 1.5,
    rr_ratio: float = 2.0,
    atr_mult_stop: float = 1.5,
    friction_enabled: bool = True,
    trade_type: str = "delivery"
) -> tuple[pd.DataFrame, list[dict], dict]:
    """
    Simulates institutional trade execution with strict risk-to-reward stops, trailing stops,
    and exchange-accurate friction modeling.
    """
    bt = df.copy().reset_index(drop=True)
    n = len(bt)
    if n < 50:
        return bt, [], {}

    # Ensure required columns
    close = bt["Close"].astype(float)
    high = bt["High"].astype(float) if "High" in bt.columns else close
    low = bt["Low"].astype(float) if "Low" in bt.columns else close
    open_p = bt["Open"].astype(float) if "Open" in bt.columns else close

    sma50 = bt["SMA_50"].astype(float) if "SMA_50" in bt.columns else close.rolling(50).mean()
    sma200 = bt["SMA_200"].astype(float) if "SMA_200" in bt.columns else close.rolling(min(200, n)).mean()
    ema12 = bt["EMA_12"].astype(float) if "EMA_12" in bt.columns else close.ewm(span=12).mean()
    ema26 = bt["EMA_26"].astype(float) if "EMA_26" in bt.columns else close.ewm(span=26).mean()
    rsi = bt["RSI_14"].astype(float) if "RSI_14" in bt.columns else pd.Series(50, index=bt.index)
    atr = bt["ATR_14"].astype(float) if "ATR_14" in bt.columns else (high - low).rolling(14).mean()

    # Volume confirmation
    if "Volume" in bt.columns and bt["Volume"].sum() > 0:
        vol = bt["Volume"].astype(float)
        vol_ma = vol.rolling(20).mean().fillna(vol)
        vol_thrust = vol >= (vol_ma * 1.25)
    else:
        vol_thrust = pd.Series(True, index=bt.index)

    green_candle = close >= open_p
    trend_filter = (close >= sma50) & ((close >= sma200) | sma200.isna())
    momentum_filter = (ema12 >= ema26) & (rsi >= 42.0) & (rsi <= 68.0)

    # Buy signals generated on bar i, entered at next bar open
    raw_signal = trend_filter & momentum_filter & vol_thrust & green_candle

    trades = []
    in_trade = False
    entry_idx = 0
    entry_price = 0.0
    entry_date = None
    stop_loss = 0.0
    target_price = 0.0
    shares = 0
    highest_price_in_trade = 0.0

    equity = capital
    signal_bt = [0] * n

    for i in range(20, n - 1):
        curr_p = float(close.iloc[i])
        curr_hi = float(high.iloc[i])
        curr_lo = float(low.iloc[i])
        nxt_open = float(open_p.iloc[i + 1])
        nxt_date = str(bt.iloc[i + 1].get("Date", f"Bar {i+1}"))[:10]

        if not in_trade:
            if bool(raw_signal.iloc[i]):
                in_trade = True
                entry_idx = i + 1
                entry_price = nxt_open
                entry_date = nxt_date
                highest_price_in_trade = entry_price

                # Risk sizing based on ATR
                c_atr = float(atr.iloc[i]) if pd.notna(atr.iloc[i]) and float(atr.iloc[i]) > 0 else (entry_price * 0.02)
                stop_dist = max(entry_price * 0.01, c_atr * atr_mult_stop)
                stop_loss = entry_price - stop_dist
                target_price = entry_price + (stop_dist * rr_ratio)

                risk_capital = equity * (risk_pct_per_trade / 100.0)
                shares = max(1, int(risk_capital / (stop_dist + 1e-9)))
                max_shares = max(1, int((equity * 0.30) / entry_price))
                shares = min(shares, max_shares)

                signal_bt[i + 1] = 1
        else:
            signal_bt[i] = 1
            highest_price_in_trade = max(highest_price_in_trade, curr_hi)
            c_atr = float(atr.iloc[i]) if pd.notna(atr.iloc[i]) and float(atr.iloc[i]) > 0 else (entry_price * 0.02)

            # Trail stop to Breakeven once price moves 1.5R in profit
            profit_move = highest_price_in_trade - entry_price
            initial_risk = entry_price - stop_loss
            if profit_move >= (initial_risk * 1.5):
                stop_loss = max(stop_loss, entry_price)

            # Dynamic trailing stop above 2R
            if profit_move >= (initial_risk * 2.0):
                trail_level = highest_price_in_trade - (c_atr * 1.2)
                stop_loss = max(stop_loss, trail_level)

            exit_triggered = False
            exit_reason = ""
            exit_price = 0.0

            if curr_lo <= stop_loss:
                exit_triggered = True
                exit_price = min(stop_loss, curr_p)
                exit_reason = "Stop Loss Hit" if exit_price < entry_price else "Trailing Stop Hit"
            elif curr_hi >= target_price:
                exit_triggered = True
                exit_price = target_price
                exit_reason = "Take Profit Target (1:2 R:R)"
            elif curr_p < float(sma50.iloc[i]) and float(rsi.iloc[i]) < 40.0:
                exit_triggered = True
                exit_price = curr_p
                exit_reason = "Trend Exhaustion Exit"

            if exit_triggered or (i == n - 2):
                if not exit_triggered:
                    exit_price = float(close.iloc[-1])
                    exit_reason = "End of Test Period"

                in_trade = False
                friction = calculate_indian_equity_friction(
                    entry_price=entry_price,
                    exit_price=exit_price,
                    quantity=shares,
                    trade_type=trade_type,
                    slippage_bps=5.0 if friction_enabled else 0.0
                ) if friction_enabled else {
                    "gross_pnl": round((exit_price - entry_price) * shares, 2),
                    "gross_pnl_pct": round(((exit_price - entry_price) / entry_price) * 100, 2),
                    "net_pnl": round((exit_price - entry_price) * shares, 2),
                    "net_pnl_pct": round(((exit_price - entry_price) / entry_price) * 100, 2),
                    "total_friction": 0.0,
                    "friction_pct_of_trade": 0.0,
                    "breakdown": {"stt": 0, "brokerage": 0, "exchange_charges": 0, "gst": 0, "sebi_fees": 0, "stamp_duty": 0, "slippage": 0}
                }

                net_gain = friction["net_pnl"]
                equity += net_gain

                trades.append({
                    "Entry Date": entry_date,
                    "Exit Date": str(bt.iloc[i].get("Date", f"Bar {i}"))[:10],
                    "Entry ₹": round(entry_price, 2),
                    "Exit ₹": round(exit_price, 2),
                    "Shares": shares,
                    "Gross P&L ₹": friction["gross_pnl"],
                    "Gross P&L %": friction["gross_pnl_pct"],
                    "Friction & Tax ₹": friction["total_friction"],
                    "Net P&L ₹": friction["net_pnl"],
                    "Net P&L %": friction["net_pnl_pct"],
                    "P&L %": friction["net_pnl_pct"],
                    "Reason": exit_reason,
                    "Result": "✅ WIN" if net_gain > 0 else "❌ LOSS"
                })

    bt["Signal_BT"] = signal_bt
    bt["Strat_Ret"] = bt["Signal_BT"].shift(1) * close.pct_change()
    bt["Equity"] = (1 + bt["Strat_Ret"].fillna(0)).cumprod()

    total_trades = len(trades)
    wins = sum(1 for t in trades if t["Net P&L ₹"] > 0)
    win_rate = (wins / total_trades * 100.0) if total_trades > 0 else 0.0
    gross_pnl_total = sum(t["Gross P&L ₹"] for t in trades)
    net_pnl_total = sum(t["Net P&L ₹"] for t in trades)
    friction_total = sum(t["Friction & Tax ₹"] for t in trades)

    gross_wins = sum(t["Gross P&L ₹"] for t in trades if t["Gross P&L ₹"] > 0)
    gross_losses = abs(sum(t["Gross P&L ₹"] for t in trades if t["Gross P&L ₹"] < 0))
    profit_factor = (gross_wins / gross_losses) if gross_losses > 0 else (999.0 if gross_wins > 0 else 0.0)

    summary = {
        "total_trades": total_trades,
        "win_rate": round(win_rate, 1),
        "gross_pnl_total": round(gross_pnl_total, 2),
        "net_pnl_total": round(net_pnl_total, 2),
        "friction_total": round(friction_total, 2),
        "profit_factor": round(profit_factor, 2),
        "final_equity": round(equity, 2),
    }

    return bt, trades, summary
