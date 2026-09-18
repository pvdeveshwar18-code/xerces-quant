"""
PB EMA (Pullback EMA) Strategy Engine for XERCES.
Highly effective for Equities and Commodities (Gold, Silver, Crude Oil).
Strategy Mechanics:
1. Trend Qualification: Price > 50 SMA and 20 EMA > 50 SMA with positive slope.
2. Pullback Qualification: Price retraces into the 9/21 EMA value zone (testing 20 EMA).
3. Rejection Confirmation: Bullish rejection wick/candle off the 20 EMA with positive volume.
4. Risk Management: Micro-stop just below 20 EMA / swing low, targeting 1:2.5 to 1:3 R:R with Breakeven trailing.
"""

import numpy as np
import pandas as pd
from analytics.friction import calculate_indian_equity_friction

def run_pullback_ema_backtest(
    df: pd.DataFrame,
    capital: float = 100000.0,
    risk_pct_per_trade: float = 1.5,
    rr_ratio: float = 2.5,
    ema_fast: int = 9,
    ema_mid: int = 21,
    friction_enabled: bool = True,
    trade_type: str = "delivery"
) -> tuple[pd.DataFrame, list[dict], dict]:
    """
    Backtest PB EMA (Pullback to 20/21 EMA) with tight risk controls and friction modeling.
    """
    bt = df.copy().reset_index(drop=True)
    n = len(bt)
    if n < 50:
        return bt, [], {}

    close = bt["Close"].astype(float)
    high = bt["High"].astype(float) if "High" in bt.columns else close
    low = bt["Low"].astype(float) if "Low" in bt.columns else close
    open_p = bt["Open"].astype(float) if "Open" in bt.columns else close

    ema9 = close.ewm(span=ema_fast, adjust=False).mean()
    ema21 = close.ewm(span=ema_mid, adjust=False).mean()
    sma50 = close.rolling(50).mean().bfill()
    atr = (high - low).rolling(14).mean().bfill()

    # Trend filter: Bullish regime
    trend_bull = (close > sma50) & (ema21 > sma50) & (ema21.diff(3) > 0)

    # Pullback condition: Low dips into or slightly below 21 EMA while Close remains resilient
    pullback_touch = (low <= (ema21 * 1.008)) & (close >= (ema21 * 0.985))

    # Rejection candle: Green candle or hammer wick
    body = (close - open_p).abs()
    lower_wick = np.minimum(open_p, close) - low
    bullish_rejection = (close > open_p) | (lower_wick >= (body * 1.2))

    raw_signal = trend_bull & pullback_touch & bullish_rejection

    trades = []
    in_trade = False
    entry_idx = 0
    entry_price = 0.0
    entry_date = None
    stop_loss = 0.0
    target_price = 0.0
    shares = 0
    highest_price = 0.0

    equity = capital
    signal_bt = [0] * n

    for i in range(25, n - 1):
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
                highest_price = entry_price

                # Stop loss placed just below the pullback low or 1.2 ATR
                c_atr = float(atr.iloc[i]) if pd.notna(atr.iloc[i]) and float(atr.iloc[i]) > 0 else (entry_price * 0.02)
                swing_low_dist = entry_price - float(low.iloc[i])
                stop_dist = max(entry_price * 0.008, min(swing_low_dist + (c_atr * 0.2), c_atr * 1.5))
                stop_loss = entry_price - stop_dist
                target_price = entry_price + (stop_dist * rr_ratio)

                risk_capital = equity * (risk_pct_per_trade / 100.0)
                shares = max(1, int(risk_capital / (stop_dist + 1e-9)))
                max_shares = max(1, int((equity * 0.30) / entry_price))
                shares = min(shares, max_shares)

                signal_bt[i + 1] = 1
        else:
            signal_bt[i] = 1
            highest_price = max(highest_price, curr_hi)
            initial_risk = entry_price - stop_loss

            # Move stop to Breakeven once 1.2R reached
            if (highest_price - entry_price) >= (initial_risk * 1.2):
                stop_loss = max(stop_loss, entry_price)

            # Trail stop along 21 EMA once 2R reached
            if (highest_price - entry_price) >= (initial_risk * 2.0):
                stop_loss = max(stop_loss, float(ema21.iloc[i]))

            exit_triggered = False
            exit_reason = ""
            exit_price = 0.0

            if curr_lo <= stop_loss:
                exit_triggered = True
                exit_price = min(stop_loss, curr_p)
                exit_reason = "Trailing Stop (PB EMA Hit)" if exit_price >= entry_price else "Stop Loss Hit"
            elif curr_hi >= target_price:
                exit_triggered = True
                exit_price = target_price
                exit_reason = f"Take Profit Target (1:{rr_ratio} R:R)"
            elif curr_p < float(sma50.iloc[i]):
                exit_triggered = True
                exit_price = curr_p
                exit_reason = "50 SMA Breakdown Exit"

            if exit_triggered or (i == n - 2):
                if not exit_triggered:
                    exit_price = float(close.iloc[-1])
                    exit_reason = "End of Period"

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
                    "Gross P&L %": friction["gross_pnl_pct"],
                    "Friction & Tax ₹": friction["total_friction"],
                    "Net P&L %": friction["net_pnl_pct"],
                    "P&L %": friction["net_pnl_pct"],
                    "Reason": exit_reason,
                    "Result": "✅ WIN" if net_gain > 0 else "❌ LOSS"
                })

    bt["Signal_BT"] = signal_bt
    bt["Strat_Ret"] = bt["Signal_BT"].shift(1) * close.pct_change()
    bt["Equity"] = (1 + bt["Strat_Ret"].fillna(0)).cumprod()

    total_trades = len(trades)
    wins = sum(1 for t in trades if t["Net P&L %"] > 0)
    win_rate = (wins / total_trades * 100.0) if total_trades > 0 else 0.0
    gross_pnl_total = sum(t.get("Gross P&L ₹", 0.0) for t in trades)
    net_pnl_total = sum(t.get("Net P&L ₹", 0.0) for t in trades)
    friction_total = sum(t["Friction & Tax ₹"] for t in trades)

    gp = sum(t["Net P&L %"] for t in trades if t["Net P&L %"] > 0)
    gl = abs(sum(t["Net P&L %"] for t in trades if t["Net P&L %"] < 0))
    profit_factor = (gp / gl) if gl > 0 else (999.0 if gp > 0 else 0.0)

    summary = {
        "total_trades": total_trades,
        "win_rate": round(win_rate, 1),
        "friction_total": round(friction_total, 2),
        "profit_factor": round(profit_factor, 2),
        "final_equity": round(equity, 2),
    }

    return bt, trades, summary
