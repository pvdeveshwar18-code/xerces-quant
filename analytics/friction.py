"""
Indian Financial Markets Friction and Regulatory Cost Engine for XERCES.
Accurately models STT, Exchange Turnover Fees, GST, SEBI charges, Stamp Duty, Brokerage, and Execution Slippage.
"""

def calculate_indian_equity_friction(
    entry_price: float,
    exit_price: float,
    quantity: int = 100,
    trade_type: str = "delivery",  # 'delivery' (CNC) or 'intraday' (MIS)
    broker_model: str = "discount_flat20",  # 'discount_flat20' (Zerodha/Groww) or 'zero_brokerage'
    slippage_bps: float = 5.0,  # 5 basis points (0.05%) execution slippage per trade
) -> dict:
    buy_turnover = entry_price * quantity
    sell_turnover = exit_price * quantity
    total_turnover = buy_turnover + sell_turnover

    if buy_turnover <= 0 or sell_turnover <= 0:
        return {
            "gross_pnl": 0.0, "gross_pnl_pct": 0.0,
            "net_pnl": 0.0, "net_pnl_pct": 0.0,
            "total_friction": 0.0, "friction_pct_of_trade": 0.0,
            "breakdown": {"stt": 0, "brokerage": 0, "exchange_charges": 0, "gst": 0, "sebi_fees": 0, "stamp_duty": 0, "slippage": 0}
        }

    # 1. Slippage (Bid/Ask spread + market impact)
    slippage_cost = total_turnover * (slippage_bps / 10000.0)

    # 2. Brokerage
    if broker_model == "zero_brokerage":
        brokerage = 0.0
    elif trade_type == "intraday":
        b_buy = min(20.0, buy_turnover * 0.0003)
        b_sell = min(20.0, sell_turnover * 0.0003)
        brokerage = b_buy + b_sell
    else:
        # Standard delivery: Flat ₹20 per executed order (buy + sell legs = ₹40)
        brokerage = 40.0

    # 3. STT (Securities Transaction Tax)
    if trade_type == "delivery":
        # 0.1% on buy AND 0.1% on sell
        stt = (buy_turnover * 0.001) + (sell_turnover * 0.001)
    else:
        # Intraday: 0.025% on sell side only
        stt = sell_turnover * 0.00025

    # 4. Exchange Turnover Charges (NSE: ~0.00297%, BSE: ~0.00375%, average ~0.00345%)
    exchange_charges = total_turnover * 0.0000345

    # 5. GST (18% on Brokerage + Exchange Charges)
    gst = (brokerage + exchange_charges) * 0.18

    # 6. SEBI Turnover Charges (₹10 per crore = 0.0001%)
    sebi_fees = total_turnover * 0.000001

    # 7. Stamp Duty (Buy side only: Delivery = 0.015%, Intraday = 0.003%)
    stamp_rate = 0.00015 if trade_type == "delivery" else 0.00003
    stamp_duty = buy_turnover * stamp_rate

    total_statutory = stt + exchange_charges + gst + sebi_fees + stamp_duty
    total_friction = total_statutory + brokerage + slippage_cost

    gross_pnl = (exit_price - entry_price) * quantity
    gross_pnl_pct = ((exit_price - entry_price) / entry_price) * 100.0
    net_pnl = gross_pnl - total_friction
    net_pnl_pct = (net_pnl / buy_turnover) * 100.0

    return {
        "gross_pnl": round(gross_pnl, 2),
        "gross_pnl_pct": round(gross_pnl_pct, 2),
        "net_pnl": round(net_pnl, 2),
        "net_pnl_pct": round(net_pnl_pct, 2),
        "total_friction": round(total_friction, 2),
        "friction_pct_of_trade": round((total_friction / buy_turnover) * 100.0, 3),
        "breakdown": {
            "stt": round(stt, 2),
            "brokerage": round(brokerage, 2),
            "exchange_charges": round(exchange_charges, 2),
            "gst": round(gst, 2),
            "sebi_fees": round(sebi_fees, 2),
            "stamp_duty": round(stamp_duty, 2),
            "slippage": round(slippage_cost, 2),
        }
    }
