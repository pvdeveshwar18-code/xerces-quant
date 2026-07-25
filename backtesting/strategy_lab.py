"""
XERCES Strategy Lab Engine
Allows custom multi-indicator strategy building and instant event-driven backtesting.
"""

import numpy as np
import pandas as pd

class StrategyLabEngine:
    """
    Custom strategy builder and backtesting engine.
    """

    @staticmethod
    def backtest_custom_strategy(
        df: pd.DataFrame,
        entry_conditions: dict,
        exit_conditions: dict,
        initial_capital: float = 100000.0,
        stop_loss_pct: float = 5.0,
        take_profit_pct: float = 10.0,
        transaction_fee_pct: float = 0.1
    ) -> dict:
        """
        Executes backtest based on user-defined rules.
        """
        if df is None or len(df) < 50:
            return {
                "error": "Insufficient historical price data for backtest (minimum 50 bars required)."
            }

        data = df.copy().reset_index()
        if 'Date' not in data.columns:
            data['Date'] = data.index

        close = data['Close']
        high = data['High'] if 'High' in data.columns else close
        low = data['Low'] if 'Low' in data.columns else close
        open_p = data['Open'] if 'Open' in data.columns else close
        volume = data['Volume'] if 'Volume' in data.columns else pd.Series(1, index=data.index)

        # -------------------------------------------------------------
        # 1. CALCULATE ALL SUPPORTED INDICATORS
        # -------------------------------------------------------------
        data['SMA_20'] = close.rolling(20).mean()
        data['SMA_50'] = close.rolling(50).mean()
        data['SMA_200'] = close.rolling(200).mean().fillna(data['SMA_50'])

        data['EMA_20'] = close.ewm(span=20, adjust=False).mean()
        data['EMA_50'] = close.ewm(span=50, adjust=False).mean()

        # RSI (14)
        delta = close.diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / (loss + 1e-8)
        data['RSI_14'] = 100 - (100 / (1 + rs))

        # MACD (12, 26, 9)
        exp1 = close.ewm(span=12, adjust=False).mean()
        exp2 = close.ewm(span=26, adjust=False).mean()
        data['MACD'] = exp1 - exp2
        data['MACD_Signal'] = data['MACD'].ewm(span=9, adjust=False).mean()
        data['MACD_Hist'] = data['MACD'] - data['MACD_Signal']

        # Bollinger Bands (20, 2)
        std_20 = close.rolling(20).std()
        data['BB_Upper'] = data['SMA_20'] + (2 * std_20)
        data['BB_Lower'] = data['SMA_20'] - (2 * std_20)

        # Volume MA
        data['Vol_SMA20'] = volume.rolling(20).mean()

        # -------------------------------------------------------------
        # 2. EVALUATE ENTRY & EXIT BOOLEAN MASKS
        # -------------------------------------------------------------
        n = len(data)
        entry_mask = np.ones(n, dtype=bool)
        exit_mask = np.zeros(n, dtype=bool)

        # Entry Rules
        if entry_conditions.get('price_above_ema20'):
            entry_mask &= (data['Close'] > data['EMA_20'])
        if entry_conditions.get('ema20_above_ema50'):
            entry_mask &= (data['EMA_20'] > data['EMA_50'])
        if entry_conditions.get('rsi_under'):
            thresh = entry_conditions.get('rsi_under_val', 40)
            entry_mask &= (data['RSI_14'] < thresh)
        if entry_conditions.get('rsi_over'):
            thresh = entry_conditions.get('rsi_over_val', 50)
            entry_mask &= (data['RSI_14'] > thresh)
        if entry_conditions.get('macd_hist_positive'):
            entry_mask &= (data['MACD_Hist'] > 0)
        if entry_conditions.get('price_below_bb_lower'):
            entry_mask &= (data['Close'] < data['BB_Lower'])
        if entry_conditions.get('volume_spike'):
            mult = entry_conditions.get('volume_spike_mult', 1.5)
            entry_mask &= (data['Volume'] > (mult * data['Vol_SMA20']))

        # Exit Rules
        if exit_conditions.get('rsi_over_exit'):
            thresh = exit_conditions.get('rsi_over_exit_val', 70)
            exit_mask |= (data['RSI_14'] > thresh)
        if exit_conditions.get('price_below_ema20_exit'):
            exit_mask |= (data['Close'] < data['EMA_20'])
        if exit_conditions.get('macd_hist_negative_exit'):
            exit_mask |= (data['MACD_Hist'] < 0)
        if exit_conditions.get('price_above_bb_upper_exit'):
            exit_mask |= (data['Close'] > data['BB_Upper'])

        # -------------------------------------------------------------
        # 3. BACKTEST SIMULATION LOOP
        # -------------------------------------------------------------
        trades = []
        equity_curve = [initial_capital]
        current_cash = initial_capital
        position = 0  # 0 = Out, 1 = In
        entry_price = 0.0
        entry_date = None
        shares = 0

        fee_rate = transaction_fee_pct / 100.0
        sl_rate = stop_loss_pct / 100.0
        tp_rate = take_profit_pct / 100.0

        for i in range(1, n):
            today_date = data['Date'].iloc[i]
            today_open = data['Open'].iloc[i]
            today_high = data['High'].iloc[i]
            today_low = data['Low'].iloc[i]
            today_close = data['Close'].iloc[i]

            prev_entry_signal = entry_mask[i - 1]
            prev_exit_signal = exit_mask[i - 1]

            # In Position — Check Exit
            if position == 1:
                # Check Stop Loss / Take Profit hit during bar
                sl_price = entry_price * (1.0 - sl_rate)
                tp_price = entry_price * (1.0 + tp_rate)

                exit_triggered = False
                actual_exit_price = today_open
                exit_reason = "Signal"

                if today_low <= sl_price:
                    exit_triggered = True
                    actual_exit_price = sl_price
                    exit_reason = "Stop Loss"
                elif today_high >= tp_price:
                    exit_triggered = True
                    actual_exit_price = tp_price
                    exit_reason = "Take Profit"
                elif prev_exit_signal:
                    exit_triggered = True
                    actual_exit_price = today_open
                    exit_reason = "Indicator Exit Signal"

                if exit_triggered:
                    gross_proceeds = shares * actual_exit_price
                    net_proceeds = gross_proceeds * (1.0 - fee_rate)
                    pnl_amount = net_proceeds - (shares * entry_price * (1.0 + fee_rate))
                    pnl_pct = ((actual_exit_price / entry_price) - 1) * 100.0

                    current_cash = net_proceeds
                    position = 0

                    trades.append({
                        "Entry Date": str(entry_date)[:10],
                        "Exit Date": str(today_date)[:10],
                        "Entry Price": round(entry_price, 2),
                        "Exit Price": round(actual_exit_price, 2),
                        "Shares": shares,
                        "P&L (₹)": round(pnl_amount, 2),
                        "Return (%)": round(pnl_pct, 2),
                        "Reason": exit_reason
                    })

            # Out of Position — Check Entry Signal
            elif position == 0 and prev_entry_signal:
                entry_price = today_open
                entry_date = today_date
                cost_per_share = entry_price * (1.0 + fee_rate)
                shares = int(current_cash // cost_per_share)

                if shares > 0:
                    position = 1

            # Update Equity Curve
            if position == 1:
                current_equity = shares * today_close
            else:
                current_equity = current_cash

            equity_curve.append(current_equity)

        # Final Evaluation Metrics
        equity_series = pd.Series(equity_curve, index=data['Date'])
        final_equity = equity_series.iloc[-1]
        total_return_pct = ((final_equity / initial_capital) - 1) * 100.0

        # Benchmark (Buy & Hold)
        bh_shares = int(initial_capital // data['Open'].iloc[0])
        bh_final = bh_shares * data['Close'].iloc[-1]
        bh_return_pct = ((bh_final / initial_capital) - 1) * 100.0

        trades_df = pd.DataFrame(trades)

        if not trades_df.empty:
            win_trades = trades_df[trades_df['P&L (₹)'] > 0]
            loss_trades = trades_df[trades_df['P&L (₹)'] < 0]
            win_rate = (len(win_trades) / len(trades_df)) * 100.0
            gross_win = win_trades['P&L (₹)'].sum() if len(win_trades) > 0 else 0.0
            gross_loss = abs(loss_trades['P&L (₹)'].sum()) if len(loss_trades) > 0 else 0.0
            profit_factor = (gross_win / gross_loss) if gross_loss > 0 else (gross_win if gross_win > 0 else 1.0)
        else:
            win_rate = 0.0
            profit_factor = 0.0

        # Drawdown calculation
        rolling_max = equity_series.cummax()
        drawdowns = (equity_series - rolling_max) / rolling_max
        max_dd_pct = abs(drawdowns.min()) * 100.0

        return {
            "initial_capital": initial_capital,
            "final_equity": round(final_equity, 2),
            "total_return_pct": round(total_return_pct, 2),
            "buy_hold_return_pct": round(bh_return_pct, 2),
            "outperformance_pct": round(total_return_pct - bh_return_pct, 2),
            "total_trades": len(trades_df),
            "win_rate_pct": round(win_rate, 1),
            "profit_factor": round(profit_factor, 2),
            "max_drawdown_pct": round(max_dd_pct, 2),
            "trades_df": trades_df,
            "equity_series": equity_series
        }
