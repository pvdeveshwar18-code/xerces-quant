import pandas as pd
from engine.data_loader import fetch_stock_data, calculate_indicators, get_stock_info, get_currency_symbol, INDIAN_WATCHLIST, US_WATCHLIST
from engine.decision_engine import evaluate_stock

def scan_stock_suggestions(market: str = "Indian Market (NSE/BSE)", timeframe: str = "Swing Trading (1-4 Weeks)", custom_tickers: list = None) -> list:
    """
    Scans the selected market (Indian vs US) for high-probability BUY trade setups based on timeframe.
    """
    if custom_tickers:
        tickers = custom_tickers
    elif "Indian" in market:
        tickers = INDIAN_WATCHLIST
    else:
        tickers = US_WATCHLIST
        
    suggestions = []
    
    for ticker in tickers:
        try:
            if "Swing" in timeframe:
                period = "6mo"
            elif "Short-Term" in timeframe:
                period = "1y"
            else:
                period = "2y"
                
            df = fetch_stock_data(ticker, period=period, interval="1d")
            if df.empty:
                continue
                
            df = calculate_indicators(df)
            eval_res = evaluate_stock(df, timeframe=timeframe)
            info = get_stock_info(ticker)
            curr_sym = get_currency_symbol(ticker)
            
            if eval_res["decision"] == "BUY" or eval_res["score_pct"] >= 55:
                suggestions.append({
                    "ticker": ticker,
                    "name": info["name"],
                    "sector": info["sector"],
                    "decision": eval_res["decision"],
                    "confidence": f"{eval_res['confidence']}%",
                    "score_pct": eval_res["score_pct"],
                    "current_price": f"{curr_sym}{eval_res['current_price']:,.2f}",
                    "entry_range": f"{curr_sym}{eval_res['entry_min']:,.2f} - {curr_sym}{eval_res['entry_max']:,.2f}",
                    "target_1": f"{curr_sym}{eval_res['target_1']:,.2f}",
                    "target_2": f"{curr_sym}{eval_res['target_2']:,.2f}",
                    "stop_loss": f"{curr_sym}{eval_res['stop_loss']:,.2f}",
                    "rr_ratio": f"{eval_res['rr_ratio']}x",
                    "key_rationale": eval_res["bullish_factors"][0] if eval_res["bullish_factors"] else "Favorable technical setup."
                })
        except Exception as e:
            print(f"Error scanning {ticker}: {e}")
            continue
            
    suggestions = sorted(suggestions, key=lambda x: x["score_pct"], reverse=True)
    return suggestions
