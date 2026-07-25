"""
XERCES Institutional Analytics — Market Regime Detector
Identifies market regimes: Bull Trend, Bear Trend, Sideways/Consolidation, and High Volatility Breakout.
"""

import numpy as np
import pandas as pd

class MarketRegimeDetector:
    """
    Detects market regimes using EMA trends, ADX (Trend Strength), ATR % (Volatility), and RSI.
    """
    
    @staticmethod
    def analyze_regime(df: pd.DataFrame) -> dict:
        """
        Calculates market regime metrics for a given stock/index price dataframe.
        Expects df with columns: 'Close', 'High', 'Low', 'Volume'
        """
        if df is None or len(df) < 50:
            return {
                "regime": "NEUTRAL / INSUFFICIENT DATA",
                "trend_bias": "NEUTRAL",
                "volatility_regime": "NORMAL",
                "trend_strength_adx": 0.0,
                "adx_signal": "Weak / Non-Trending",
                "ema_alignment": "Mixed",
                "regime_score": 50,
                "recommendation": "Maintain standard risk controls."
            }

        close = df['Close']
        high = df['High']
        low = df['Low']
        
        # 1. EMAs
        ema_20 = close.ewm(span=20, adjust=False).mean()
        ema_50 = close.ewm(span=50, adjust=False).mean()
        ema_200 = close.ewm(span=200, adjust=False).mean() if len(df) >= 200 else close.ewm(span=len(df), adjust=False).mean()

        latest_close = close.iloc[-1]
        latest_ema20 = ema_20.iloc[-1]
        latest_ema50 = ema_50.iloc[-1]
        latest_ema200 = ema_200.iloc[-1]

        # 2. ATR & Volatility
        tr1 = high - low
        tr2 = (high - close.shift(1)).abs()
        tr3 = (low - close.shift(1)).abs()
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr_14 = tr.rolling(14).mean().iloc[-1]
        atr_pct = (atr_14 / latest_close) * 100

        vol_20 = close.pct_change().std() * np.sqrt(252) * 100

        if atr_pct > 3.5 or vol_20 > 35:
            vol_regime = "HIGH VOLATILITY"
        elif atr_pct < 1.5 and vol_20 < 15:
            vol_regime = "LOW VOLATILITY / COMPRESSION"
        else:
            vol_regime = "MODERATE VOLATILITY"

        # 3. ADX Calculation
        up_move = high - high.shift(1)
        down_move = low.shift(1) - low
        plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0.0)
        minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0.0)

        tr_smooth = tr.rolling(14).sum()
        plus_di = 100 * (pd.Series(plus_dm, index=df.index).rolling(14).sum() / tr_smooth)
        minus_di = 100 * (pd.Series(minus_dm, index=df.index).rolling(14).sum() / tr_smooth)
        
        dx = 100 * ((plus_di - minus_di).abs() / (plus_di + minus_di + 1e-8))
        adx = dx.rolling(14).mean().iloc[-1]

        if pd.isna(adx):
            adx = 20.0

        if adx > 30:
            adx_signal = "Strong Trend"
        elif adx > 20:
            adx_signal = "Developing Trend"
        else:
            adx_signal = "Ranging / Choppy"

        # 4. Regime Classification
        bull_stack = (latest_close > latest_ema20) and (latest_ema20 > latest_ema50) and (latest_ema50 > latest_ema200)
        bear_stack = (latest_close < latest_ema20) and (latest_ema20 < latest_ema50) and (latest_ema50 < latest_ema200)

        if bull_stack and adx > 25:
            regime = "STRONG BULL TREND"
            trend_bias = "BULLISH"
            regime_score = 90
            rec = "Favorable for trend-following momentum buys and breakout trades."
        elif bull_stack:
            regime = "EARLY / MILD BULL TREND"
            trend_bias = "BULLISH"
            regime_score = 75
            rec = "Look for pullbacks to 20 EMA for buy entries."
        elif bear_stack and adx > 25:
            regime = "STRONG BEAR TREND"
            trend_bias = "BEARISH"
            regime_score = 10
            rec = "High risk environment. Hold cash or hedge positions."
        elif bear_stack:
            regime = "MILD BEAR TREND / DOWNWARD DRIFT"
            trend_bias = "BEARISH"
            regime_score = 30
            rec = "Avoid aggressive buying. Wait for base formation."
        elif adx < 20 and vol_regime == "LOW VOLATILITY / COMPRESSION":
            regime = "SIDEWAYS CONSOLIDATION (SQEEZE)"
            trend_bias = "NEUTRAL"
            regime_score = 50
            rec = "Prepare for potential breakout. Use tight stop losses."
        else:
            regime = "CHOPPY / MIXED REGIME"
            trend_bias = "NEUTRAL"
            regime_score = 50
            rec = "Reduce position size. Trade range extremes."

        return {
            "regime": regime,
            "trend_bias": trend_bias,
            "volatility_regime": vol_regime,
            "trend_strength_adx": round(float(adx), 2),
            "adx_signal": adx_signal,
            "atr_percent": round(float(atr_pct), 2),
            "annualized_volatility": round(float(vol_20), 2),
            "ema_alignment": "Bullish Stack" if bull_stack else ("Bearish Stack" if bear_stack else "Mixed Alignment"),
            "regime_score": regime_score,
            "recommendation": rec
        }
