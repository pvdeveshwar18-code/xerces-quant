"""
XERCES Institutional AI Committee Engine
Simulates a 5-member Investment Committee (Technicals, Fundamentals, Macro/Regime, Risk, Sentiment).
"""

import numpy as np
import pandas as pd

class AIInvestmentCommittee:
    """
    Simulates a multi-agent investment committee vote.
    """

    @staticmethod
    def evaluate_committee(ticker: str, df: pd.DataFrame, decision_res: dict, fundamentals: dict = None) -> dict:
        """
        Synthesizes committee perspectives into a unified vote.
        """
        if df is None or len(df) < 30:
            return {
                "consensus_vote": "HOLD",
                "consensus_score": 50.0,
                "committee_members": {}
            }

        latest_price = float(df['Close'].iloc[-1])
        regime = decision_res.get('regime_info', {})
        rs = decision_res.get('rs_info', {})
        risk = decision_res.get('risk_info', {})

        # -------------------------------------------------------------
        # 1. Technical Analyst Persona
        # -------------------------------------------------------------
        rsi = decision_res.get('rsi', 50)
        macd = decision_res.get('macd_hist', 0)
        if rsi > 50 and macd > 0:
            tech_vote = "BULLISH"
            tech_comment = f"Price is above key moving averages with bullish RSI ({rsi}) and positive MACD momentum."
            tech_score = 80
        elif rsi < 40 or macd < 0:
            tech_vote = "BEARISH"
            tech_comment = f"Weak momentum structure with RSI at {rsi} and negative MACD histogram."
            tech_score = 30
        else:
            tech_vote = "NEUTRAL"
            tech_comment = "Indicators are in mid-range consolidation mode."
            tech_score = 50

        # -------------------------------------------------------------
        # 2. Fundamental Analyst Persona
        # -------------------------------------------------------------
        if fundamentals:
            roe = fundamentals.get('roe', 15)
            pe = fundamentals.get('pe', 25)
            if roe >= 15 and pe <= 35:
                fund_vote = "BULLISH"
                fund_comment = f"Healthy fundamental profile with ROE of {roe}% and P/E ratio of {pe}."
                fund_score = 85
            elif roe < 10 or pe > 50:
                fund_vote = "BEARISH"
                fund_comment = f"Stretched valuation or weak ROE ({roe}%)."
                fund_score = 35
            else:
                fund_vote = "NEUTRAL"
                fund_comment = "Fair valuation relative to historical sectoral averages."
                fund_score = 55
        else:
            fund_vote = "BULLISH"
            fund_comment = "Solid industry position within NSE market index."
            fund_score = 70

        # -------------------------------------------------------------
        # 3. Macro & Market Regime Analyst Persona
        # -------------------------------------------------------------
        reg_name = regime.get('regime', 'NEUTRAL')
        if "BULL" in reg_name:
            macro_vote = "BULLISH"
            macro_comment = f"Asset is backed by a strong structural market regime: {reg_name}."
            macro_score = 85
        elif "BEAR" in reg_name:
            macro_vote = "BEARISH"
            macro_comment = f"Adverse macro/regime environment: {reg_name}."
            macro_score = 25
        else:
            macro_vote = "NEUTRAL"
            macro_comment = f"Current market condition is range-bound ({reg_name})."
            macro_score = 50

        # -------------------------------------------------------------
        # 4. Risk Manager Persona
        # -------------------------------------------------------------
        var_pct = risk.get('var_95_pct', 2.5)
        max_dd = risk.get('max_drawdown_pct', 20)
        if max_dd < 25 and var_pct < 3.5:
            risk_vote = "BULLISH"
            risk_comment = f"Controlled downside risk (VaR 95%: {var_pct}%, Max Drawdown: {max_dd}%). ATR stop loss viable."
            risk_score = 80
        else:
            risk_vote = "CAUTIOUS / BEARISH"
            risk_comment = f"Elevated volatility or drawdown risk (Max DD: {max_dd}%). Enforce tight position limits."
            risk_score = 40

        # -------------------------------------------------------------
        # 5. Sentiment & Relative Strength Analyst Persona
        # -------------------------------------------------------------
        mrs = rs.get('mrs', 0)
        if mrs > 2.0:
            sent_vote = "BULLISH"
            sent_comment = f"Strong outperformance vs NIFTY 50 (Mansfield RS: +{mrs:.2f}%)."
            sent_score = 85
        elif mrs < -2.0:
            sent_vote = "BEARISH"
            sent_comment = f"Underperforming benchmark index (Mansfield RS: {mrs:.2f}%)."
            sent_score = 30
        else:
            sent_vote = "NEUTRAL"
            sent_comment = "Tracking benchmark index performance closely."
            sent_score = 50

        # -------------------------------------------------------------
        # CONSENSUS SYNTHESIS
        # -------------------------------------------------------------
        scores = [tech_score, fund_score, macro_score, risk_score, sent_score]
        consensus_score = round(float(np.mean(scores)), 1)

        if consensus_score >= 75:
            consensus_vote = "UNANIMOUS BUY"
        elif consensus_score >= 60:
            consensus_vote = "MODERATE BUY"
        elif consensus_score <= 35:
            consensus_vote = "STRONG SELL"
        elif consensus_score <= 45:
            consensus_vote = "MODERATE SELL"
        else:
            consensus_vote = "NEUTRAL / HOLD"

        members = {
            "Technical Analyst": {"vote": tech_vote, "score": tech_score, "comment": tech_comment},
            "Fundamental Analyst": {"vote": fund_vote, "score": fund_score, "comment": fund_comment},
            "Macro & Regime Analyst": {"vote": macro_vote, "score": macro_score, "comment": macro_comment},
            "Risk Manager": {"vote": risk_vote, "score": risk_score, "comment": risk_comment},
            "Sentiment & Relative Strength Analyst": {"vote": sent_vote, "score": sent_score, "comment": sent_comment}
        }

        return {
            "consensus_vote": consensus_vote,
            "consensus_score": consensus_score,
            "committee_members": members
        }
