"""
XERCES Institutional Analytics — Relative Strength Engine
Calculates Mansfield Relative Strength (MRS) and Relative Momentum against benchmark (NIFTY 50 / ^NSEI).
"""

import numpy as np
import pandas as pd
import yfinance as yf

class RelativeStrengthEngine:
    """
    Computes Mansfield Relative Strength and comparative performance.
    """

    @staticmethod
    def calculate_relative_strength(stock_df: pd.DataFrame, benchmark_symbol: str = "^NSEI", lookback_days: int = 252) -> dict:
        """
        Calculates Mansfield Relative Strength (MRS) and percentage outperformance.
        """
        if stock_df is None or len(stock_df) < 50:
            return {
                "mrs": 0.0,
                "outperformance_pct": 0.0,
                "rs_status": "NEUTRAL",
                "rs_trend": "FLAT",
                "stock_return_pct": 0.0,
                "benchmark_return_pct": 0.0,
                "benchmark": benchmark_symbol
            }

        try:
            # Download benchmark data for same date range
            start_date = stock_df.index.min()
            end_date = stock_df.index.max()
            bm = yf.download(benchmark_symbol, start=start_date, end=end_date, progress=False)

            if isinstance(bm.columns, pd.MultiIndex):
                bm_close = bm['Close'][benchmark_symbol]
            else:
                bm_close = bm['Close']

            stock_close = stock_df['Close']

            # Align timestamps
            combined = pd.DataFrame({'Stock': stock_close, 'Benchmark': bm_close}).dropna()

            if len(combined) < 20:
                return {
                    "mrs": 0.0,
                    "outperformance_pct": 0.0,
                    "rs_status": "NEUTRAL",
                    "rs_trend": "FLAT",
                    "stock_return_pct": 0.0,
                    "benchmark_return_pct": 0.0,
                    "benchmark": benchmark_symbol
                }

            # 1. Base Ratio
            ratio = combined['Stock'] / combined['Benchmark']

            # 2. Mansfield Relative Strength (MRS)
            # MRS = ((Ratio / SMA(Ratio, 52 weeks)) - 1) * 100
            sma_len = min(len(ratio), lookback_days)
            ratio_sma = ratio.rolling(window=sma_len).mean()
            mrs_series = ((ratio / ratio_sma) - 1) * 100
            latest_mrs = mrs_series.iloc[-1]

            if pd.isna(latest_mrs):
                latest_mrs = 0.0

            # 3. Period Return Comparison
            stock_ret = ((combined['Stock'].iloc[-1] / combined['Stock'].iloc[0]) - 1) * 100
            bm_ret = ((combined['Benchmark'].iloc[-1] / combined['Benchmark'].iloc[0]) - 1) * 100
            outperf = stock_ret - bm_ret

            # RS Status
            if latest_mrs > 5:
                rs_status = "SUPERIOR OUTPERFORMER"
            elif latest_mrs > 0:
                rs_status = "OUTPERFORMING"
            elif latest_mrs > -5:
                rs_status = "UNDERPERFORMING"
            else:
                rs_status = "SEVERE UNDERPERFORMER"

            # Trend of MRS (last 10 days)
            if len(mrs_series) >= 10:
                mrs_delta = mrs_series.iloc[-1] - mrs_series.iloc[-10]
                if mrs_delta > 1.5:
                    rs_trend = "RISING / GAINING LEADER STATUS"
                elif mrs_delta < -1.5:
                    rs_trend = "WEAKENING / LOSING MOMENTUM"
                else:
                    rs_trend = "STABLE"
            else:
                rs_trend = "FLAT"

            return {
                "mrs": round(float(latest_mrs), 2),
                "outperformance_pct": round(float(outperf), 2),
                "rs_status": rs_status,
                "rs_trend": rs_trend,
                "stock_return_pct": round(float(stock_ret), 2),
                "benchmark_return_pct": round(float(bm_ret), 2),
                "benchmark": benchmark_symbol
            }

        except Exception as e:
            return {
                "mrs": 0.0,
                "outperformance_pct": 0.0,
                "rs_status": "NEUTRAL",
                "rs_trend": f"ERROR: {str(e)}",
                "stock_return_pct": 0.0,
                "benchmark_return_pct": 0.0,
                "benchmark": benchmark_symbol
            }
