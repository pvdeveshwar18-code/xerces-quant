"""
XERCES Institutional Journal Intelligence Engine
Analyzes historical trade journal for win rates, profit factor, optimal holding periods, strategy performance, and behavioral mistakes.
"""

import pandas as pd
import numpy as np

class JournalIntelligenceEngine:
    """
    Analyzes trade logs and provides performance diagnostics.
    """

    @staticmethod
    def analyze_journal(df: pd.DataFrame) -> dict:
        """
        Calculates diagnostic statistics from trade journal DataFrame.
        Expects columns like: 'Ticker', 'Entry_Price', 'Exit_Price', 'Qty', 'P&L', 'Strategy', 'Date'
        """
        if df is None or df.empty or len(df) == 0:
            return {
                "total_trades": 0,
                "win_rate_pct": 0.0,
                "profit_factor": 0.0,
                "total_pnl": 0.0,
                "best_trade": 0.0,
                "worst_trade": 0.0,
                "strategy_breakdown": {},
                "insights": ["No trades recorded in journal yet. Start adding trades to activate AI Journal Intelligence."]
            }

        # Ensure P&L exists
        pnl_col = 'P&L' if 'P&L' in df.columns else ('pnl' if 'pnl' in df.columns else None)
        
        if not pnl_col:
            if 'Entry_Price' in df.columns and 'Exit_Price' in df.columns and 'Qty' in df.columns:
                df['P&L'] = (df['Exit_Price'] - df['Entry_Price']) * df['Qty']
                pnl_col = 'P&L'
            else:
                return {
                    "total_trades": len(df),
                    "win_rate_pct": 0.0,
                    "profit_factor": 0.0,
                    "total_pnl": 0.0,
                    "best_trade": 0.0,
                    "worst_trade": 0.0,
                    "strategy_breakdown": {},
                    "insights": ["Could not calculate P&L. Ensure Entry, Exit, and Qty columns are present."]
                }

        pnl = df[pnl_col].astype(float)
        wins = pnl[pnl > 0]
        losses = pnl[pnl < 0]

        total_trades = len(df)
        win_count = len(wins)
        loss_count = len(losses)

        win_rate = (win_count / total_trades) * 100.0 if total_trades > 0 else 0.0
        
        gross_profit = wins.sum() if len(wins) > 0 else 0.0
        gross_loss = abs(losses.sum()) if len(losses) > 0 else 0.0

        profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else (gross_profit if gross_profit > 0 else 1.0)

        total_pnl = pnl.sum()
        avg_win = wins.mean() if len(wins) > 0 else 0.0
        avg_loss = abs(losses.mean()) if len(losses) > 0 else 0.0

        payoff_ratio = (avg_win / avg_loss) if avg_loss > 0 else 1.0

        # Strategy Breakdown
        strat_dict = {}
        if 'Strategy' in df.columns:
            for strat, group in df.groupby('Strategy'):
                g_pnl = group[pnl_col].astype(float)
                g_wins = g_pnl[g_pnl > 0]
                g_wr = (len(g_wins) / len(group)) * 100.0
                strat_dict[str(strat)] = {
                    "trades": len(group),
                    "win_rate": round(g_wr, 1),
                    "pnl": round(g_pnl.sum(), 2)
                }

        # Generating AI Insights
        insights = []

        if win_rate > 55 and profit_factor > 1.5:
            insights.append(f"🟢 **Excellent Trading Edge**: Win rate is high ({win_rate:.1f}%) with strong Profit Factor ({profit_factor:.2f}).")
        elif win_rate < 40 and payoff_ratio < 1.2:
            insights.append(f"🔴 **Risk Alert**: Low win rate ({win_rate:.1f}%) combined with low payoff ratio ({payoff_ratio:.2f}). Focus on tightening stop losses.")

        if payoff_ratio < 1.0 and win_rate > 50:
            insights.append("⚠️ **Cutting Winners Early**: Your win rate is good, but average loss exceeds average win. Let winning trades run to targets.")

        if gross_loss > gross_profit * 1.5:
            insights.append("🚨 **Outlier Loss Risk**: A small number of large losses is eroding account profits. Always enforce ATR stop losses.")

        if strat_dict:
            best_strat = max(strat_dict.items(), key=lambda x: x[1]['pnl'])
            insights.append(f"💡 **Top Strategy**: `{best_strat[0]}` generated the highest net P&L (₹{best_strat[1]['pnl']:,.2f}).")

        return {
            "total_trades": total_trades,
            "win_rate_pct": round(win_rate, 1),
            "profit_factor": round(profit_factor, 2),
            "total_pnl": round(total_pnl, 2),
            "win_count": win_count,
            "loss_count": loss_count,
            "avg_win": round(avg_win, 2),
            "avg_loss": round(avg_loss, 2),
            "payoff_ratio": round(payoff_ratio, 2),
            "best_trade": round(pnl.max(), 2),
            "worst_trade": round(pnl.min(), 2),
            "strategy_breakdown": strat_dict,
            "insights": insights
        }
