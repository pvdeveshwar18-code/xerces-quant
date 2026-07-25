"""
XERCES Institutional Decision Engine
Synthesizes Technicals, Market Regime, Relative Strength, Volatility & Fundamentals into a unified Decision Score (0-100), Signal, Entry/Exit levels, and Trade Thesis.
"""

import numpy as np
import pandas as pd
from analytics.market_regime import MarketRegimeDetector
from analytics.relative_strength import RelativeStrengthEngine
from risk.risk_engine import InstitutionalRiskEngine

class InstitutionalDecisionEngine:
    """
    Multi-Factor Decision & Trade Generation Engine.
    """

    @staticmethod
    def evaluate_stock(df: pd.DataFrame, ticker: str = "STOCK", fundamentals: dict = None, benchmark: str = "^NSEI") -> dict:
        """
        Evaluates stock dataframe and returns institutional signal matrix.
        """
        if df is None or len(df) < 50:
            return {
                "signal": "HOLD",
                "score": 50,
                "confidence_pct": 50.0,
                "entry_price": 0.0,
                "stop_loss": 0.0,
                "target_1": 0.0,
                "target_2": 0.0,
                "risk_reward_ratio": 1.0,
                "regime_info": {},
                "rs_info": {},
                "risk_info": {},
                "thesis": "Insufficient data available for institutional signal scoring."
            }

        latest_price = float(df['Close'].iloc[-1])

        # 1. Market Regime Analysis
        regime_info = MarketRegimeDetector.analyze_regime(df)
        
        # 2. Relative Strength Analysis
        rs_info = RelativeStrengthEngine.calculate_relative_strength(df, benchmark_symbol=benchmark)

        # 3. Risk Engine Analysis
        risk_info = InstitutionalRiskEngine.calculate_risk_metrics(df)

        # 4. Technical Indicators Scoring
        close = df['Close']
        ema20 = close.ewm(span=20, adjust=False).mean().iloc[-1]
        ema50 = close.ewm(span=50, adjust=False).mean().iloc[-1]
        ema200 = close.ewm(span=200, adjust=False).mean().iloc[-1] if len(df) >= 200 else ema50

        # RSI (14)
        delta = close.diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / (loss + 1e-8)
        rsi = 100 - (100 / (1 + rs)).iloc[-1]

        # MACD
        exp1 = close.ewm(span=12, adjust=False).mean()
        exp2 = close.ewm(span=26, adjust=False).mean()
        macd = exp1 - exp2
        signal_line = macd.ewm(span=9, adjust=False).mean()
        macd_hist = (macd - signal_line).iloc[-1]

        # -------------------------------------------------------------
        # WEIGHTED FACTOR SCORING SYSTEM (0 - 100 Points)
        # -------------------------------------------------------------
        score = 50.0

        # Factor A: EMA Alignment (20 pts)
        if latest_price > ema20 > ema50 > ema200:
            score += 20.0
        elif latest_price > ema20 > ema50:
            score += 12.0
        elif latest_price < ema20 < ema50 < ema200:
            score -= 20.0
        elif latest_price < ema20 < ema50:
            score -= 12.0

        # Factor B: Momentum / RSI (15 pts)
        if 50 <= rsi <= 65:
            score += 15.0  # Sweet spot for bullish momentum
        elif 40 <= rsi < 50:
            score += 5.0
        elif rsi > 70:
            score -= 5.0   # Overbought caution
        elif rsi < 30:
            score += 5.0   # Oversold bounce potential

        # Factor C: MACD Crossover (15 pts)
        if macd_hist > 0:
            score += 15.0
        else:
            score -= 15.0

        # Factor D: Relative Strength vs Benchmark (20 pts)
        mrs = rs_info.get('mrs', 0.0)
        if mrs > 5.0:
            score += 20.0
        elif mrs > 0.0:
            score += 10.0
        elif mrs < -5.0:
            score -= 20.0
        else:
            score -= 10.0

        # Factor E: Market Regime (20 pts)
        regime_sc = regime_info.get('regime_score', 50)
        score += (regime_sc - 50) * 0.4  # Scales [-20, +20]

        # Factor F: Fundamentals (10 pts) if provided
        if fundamentals:
            pe = fundamentals.get('pe', 25)
            roe = fundamentals.get('roe', 15)
            if roe > 18 and pe < 30:
                score += 10.0
            elif roe < 10:
                score -= 10.0

        # Clamp Score between 0 and 100
        final_score = round(max(0.0, min(100.0, score)), 1)

        # -------------------------------------------------------------
        # SIGNAL CLASSIFICATION & CONFIDENCE
        # -------------------------------------------------------------
        if final_score >= 80:
            signal = "STRONG BUY"
            confidence = 88.0
        elif final_score >= 65:
            signal = "BUY"
            confidence = 75.0
        elif final_score <= 25:
            signal = "STRONG SELL"
            confidence = 85.0
        elif final_score <= 40:
            signal = "SELL"
            confidence = 70.0
        else:
            signal = "HOLD / NEUTRAL"
            confidence = 60.0

        # -------------------------------------------------------------
        # ENTRY, STOP LOSS & TARGET LEVELS
        # -------------------------------------------------------------
        atr = risk_info.get('atr_14', latest_price * 0.02)
        stop_loss = round(latest_price - (2.0 * atr), 2)
        risk_per_share = latest_price - stop_loss
        
        target_1 = round(latest_price + (2.0 * risk_per_share), 2)  # 1:2 R:R
        target_2 = round(latest_price + (3.2 * risk_per_share), 2)  # 1:3.2 R:R
        
        rr_ratio = round((target_1 - latest_price) / max(1e-4, risk_per_share), 2)

        # -------------------------------------------------------------
        # THESIS GENERATION
        # -------------------------------------------------------------
        thesis = (
            f"**{signal} Signal (Score: {final_score}/100)** for `{ticker}`. "
            f"Asset is currently operating in a **{regime_info.get('regime')}** regime "
            f"with **{rs_info.get('rs_status')}** status (Mansfield RS: {mrs:+.2f}%). "
            f"Technicals show RSI at {rsi:.1f} and MACD histogram at {macd_hist:+.2f}. "
            f"Recommended entry around ₹{latest_price:.2f} with ATR stop loss set at ₹{stop_loss:.2f} "
            f"for Target 1 of ₹{target_1:.2f} (R:R {rr_ratio}:1)."
        )

        return {
            "signal": signal,
            "score": final_score,
            "confidence_pct": confidence,
            "entry_price": latest_price,
            "stop_loss": stop_loss,
            "target_1": target_1,
            "target_2": target_2,
            "risk_per_share": round(risk_per_share, 2),
            "risk_reward_ratio": rr_ratio,
            "rsi": round(rsi, 1),
            "macd_hist": round(macd_hist, 2),
            "regime_info": regime_info,
            "rs_info": rs_info,
            "risk_info": risk_info,
            "thesis": thesis
        }
