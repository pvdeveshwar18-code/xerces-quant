import pandas as pd
import numpy as np
from engine.data_loader import get_currency_symbol

def generate_exit_strategy(
    ticker: str,
    entry_price: float,
    quantity: int,
    current_price: float,
    user_target: float = 0.0,
    user_stop_loss: float = 0.0,
    timeframe: str = "Swing Trading (1-4 Weeks)",
    df: pd.DataFrame = None
) -> dict:
    """
    Evaluates real portfolio holdings and generates an optimal exit strategy for Indian or US markets.
    """
    curr_sym = get_currency_symbol(ticker)
    pnl = (current_price - entry_price) * quantity
    pnl_pct = ((current_price - entry_price) / entry_price) * 100 if entry_price > 0 else 0.0
    
    atr = current_price * 0.02
    rsi = 50.0
    
    if df is not None and not df.empty and len(df) >= 20:
        last_row = df.iloc[-1]
        atr = float(last_row.get('atr_14', current_price * 0.02))
        rsi = float(last_row.get('rsi_14', 50.0))
    
    atr_pct = (atr / current_price) * 100 if current_price > 0 else 2.0
    
    calc_stop_loss = user_stop_loss if user_stop_loss > 0 else round(entry_price * 0.93, 2)
    calc_target_1 = user_target if user_target > 0 else round(entry_price * 1.10, 2)
    calc_target_2 = round(calc_target_1 * 1.08, 2)
    
    distance_to_target = ((calc_target_1 - current_price) / current_price) * 100 if current_price > 0 else 0
    distance_to_stop = ((current_price - calc_stop_loss) / current_price) * 100 if current_price > 0 else 0
    
    recommendation = "BATCH_EXIT"
    strategy_title = "Batch Scaling Exit (Partial Tranches)"
    reasoning = []
    tranches = []
    
    if current_price <= calc_stop_loss:
        recommendation = "LUMP_SUM_EXIT"
        strategy_title = "Immediate 100% Lump-Sum Risk Exit"
        reasoning.append(f"Price ({curr_sym}{current_price:,.2f}) has hit or breached your Stop-Loss ({curr_sym}{calc_stop_loss:,.2f}).")
        reasoning.append("Immediate 100% exit is recommended to preserve capital and prevent further loss.")
        tranches = [
            {"tranche": "Immediate Exit", "percentage": "100%", "shares": quantity, "trigger_price": f"{curr_sym}{current_price:,.2f}", "action": "Sell All Immediately"}
        ]
    elif current_price >= calc_target_1:
        if atr_pct > 3.0 or rsi > 70:
            recommendation = "BATCH_EXIT"
            strategy_title = "Batch Scaling Profit Taking (Recommended)"
            reasoning.append(f"Target 1 ({curr_sym}{calc_target_1:,.2f}) reached with elevated volatility (ATR {atr_pct:.1f}%).")
            reasoning.append("Lock in gains in 2 batches: sell 60% now to guarantee profits, let 40% ride with a trailing stop.")
            
            qty_batch_1 = int(quantity * 0.6)
            qty_batch_2 = quantity - qty_batch_1
            
            tranches = [
                {"tranche": "Tranche 1 (Immediate)", "percentage": "60%", "shares": qty_batch_1, "trigger_price": f"{curr_sym}{current_price:,.2f}", "action": "Lock in solid gains now"},
                {"tranche": "Tranche 2 (Trailing)", "percentage": "40%", "shares": qty_batch_2, "trigger_price": f"{curr_sym}{calc_target_2:,.2f}", "action": "Hold for extended target with Trailing ATR Stop"}
            ]
        else:
            recommendation = "LUMP_SUM_EXIT"
            strategy_title = "100% Lump-Sum Target Exit"
            reasoning.append(f"Target 1 ({curr_sym}{calc_target_1:,.2f}) reached with stable price structure.")
            reasoning.append("Liquidating 100% secures target return without exposing remaining capital to reversal risks.")
            tranches = [
                {"tranche": "Full Exit", "percentage": "100%", "shares": quantity, "trigger_price": f"{curr_sym}{calc_target_1:,.2f}", "action": "Sell 100% of holdings"}
            ]
    else:
        if atr_pct > 2.5:
            recommendation = "BATCH_EXIT"
            strategy_title = "Staggered Batch Exit Plan"
            reasoning.append("High volatility environment detected. Batch scaling protects realized P&L against sharp reversals.")
            
            qty_1 = int(quantity * 0.5)
            qty_2 = quantity - qty_1
            
            tranches = [
                {"tranche": "Tranche 1 (Primary Target)", "percentage": "50%", "shares": qty_1, "trigger_price": f"{curr_sym}{calc_target_1:,.2f}", "action": "Sell half to de-risk"},
                {"tranche": "Tranche 2 (Extension)", "percentage": "50%", "shares": qty_2, "trigger_price": f"{curr_sym}{calc_target_2:,.2f}", "action": "Sell remaining with Trailing ATR Stop"}
            ]
        else:
            recommendation = "DYNAMIC_TRAILING"
            strategy_title = "Dynamic Trailing ATR Stop Exit"
            reasoning.append("Steady trend in progress. Use an adaptive ATR Trailing Stop to maximize upside.")
            trailing_stop_val = round(current_price - (2.0 * atr), 2)
            
            tranches = [
                {"tranche": "Trailing Stop Target", "percentage": "100%", "shares": quantity, "trigger_price": f"{curr_sym}{trailing_stop_val:,.2f}", "action": f"Adjust stop-loss to {curr_sym}{trailing_stop_val:,.2f} as price rises"}
            ]
            
    return {
        "ticker": ticker,
        "currency_symbol": curr_sym,
        "entry_price": entry_price,
        "current_price": current_price,
        "quantity": quantity,
        "pnl": round(pnl, 2),
        "pnl_pct": round(pnl_pct, 2),
        "user_target": calc_target_1,
        "extended_target": calc_target_2,
        "user_stop_loss": calc_stop_loss,
        "distance_to_target_pct": round(distance_to_target, 1),
        "distance_to_stop_pct": round(distance_to_stop, 1),
        "recommendation_code": recommendation,
        "strategy_title": strategy_title,
        "reasoning": reasoning,
        "tranches": tranches
    }
