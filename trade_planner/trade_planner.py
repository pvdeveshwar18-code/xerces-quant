"""
XERCES Institutional Trade Planner Engine
Automates exact position sizing, share counts, capital allocation, and risk management parameters.
"""

import numpy as np

class InstitutionalTradePlanner:
    """
    Computes exact trade execution parameters based on portfolio capital and risk limits.
    """

    @staticmethod
    def calculate_trade_plan(
        total_capital: float = 500000.0,
        risk_per_trade_pct: float = 1.0,
        entry_price: float = 1000.0,
        stop_loss: float = 950.0,
        target_1: float = 1100.0,
        target_2: float = 1200.0,
        max_position_pct: float = 20.0
    ) -> dict:
        """
        Calculates trade parameters based on fixed account risk.
        """
        if entry_price <= 0 or stop_loss >= entry_price:
            return {
                "error": "Invalid entry price or stop loss. Stop loss must be below entry price for long trades.",
                "shares_to_buy": 0,
                "capital_required": 0.0,
                "risk_amount": 0.0
            }

        # 1. Dollar Risk allowed per trade
        max_risk_amount = total_capital * (risk_per_trade_pct / 100.0)

        # 2. Risk per share
        risk_per_share = entry_price - stop_loss

        # 3. Raw Quantity based on Risk
        raw_quantity = max_risk_amount / risk_per_share
        shares = int(np.floor(raw_quantity))

        if shares == 0:
            shares = 1  # Minimum 1 share

        # 4. Total Capital Required
        capital_required = shares * entry_price
        position_pct = (capital_required / total_capital) * 100.0

        # 5. Position Limit Adjustments
        max_capital_allowed = total_capital * (max_position_pct / 100.0)
        capped_flag = False

        if capital_required > max_capital_allowed:
            shares = int(np.floor(max_capital_allowed / entry_price))
            capital_required = shares * entry_price
            position_pct = (capital_required / total_capital) * 100.0
            capped_flag = True

        actual_risk_amount = shares * risk_per_share
        actual_risk_pct = (actual_risk_amount / total_capital) * 100.0

        # 6. Target Profits
        profit_t1 = shares * (target_1 - entry_price)
        profit_t2 = shares * (target_2 - entry_price)

        rr_t1 = (target_1 - entry_price) / max(1e-4, risk_per_share)
        rr_t2 = (target_2 - entry_price) / max(1e-4, risk_per_share)

        return {
            "total_capital": total_capital,
            "risk_per_trade_pct": risk_per_trade_pct,
            "entry_price": entry_price,
            "stop_loss": stop_loss,
            "risk_per_share": round(risk_per_share, 2),
            "shares_to_buy": shares,
            "capital_required": round(capital_required, 2),
            "position_pct": round(position_pct, 2),
            "max_risk_amount": round(actual_risk_amount, 2),
            "actual_risk_pct": round(actual_risk_pct, 2),
            "target_1": target_1,
            "target_2": target_2,
            "profit_t1": round(profit_t1, 2),
            "profit_t2": round(profit_t2, 2),
            "rr_t1": round(rr_t1, 2),
            "rr_t2": round(rr_t2, 2),
            "position_capped_by_max_limit": capped_flag
        }
