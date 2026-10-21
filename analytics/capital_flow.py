"""
Capital Flow / Inflow-Outflow & Order Size Analytics Engine.
Calculates institutional order size tier distribution (Extra-Large, Large, Medium, Small),
inflow vs. outflow capital dynamics, multi-timeframe aggregations (1D, 5D, 20D, 60D, All),
price-level order flow (Footprint Profile), and Smart Money divergence.
"""

from typing import Dict, Any, List, Optional
import numpy as np
import pandas as pd

def compute_capital_flow(
    df: pd.DataFrame,
    window: int = 20,
    lookback_days: int = 30,
) -> Dict[str, Any]:
    """
    Computes comprehensive capital inflow/outflow metrics and order-size tiers from OHLCV data.

    Returns:
        dict containing:
            - summary: 1D total inflow, outflow, net flow, and sentiment score
            - tiers: Breakdown across Extra-Large, Large, Medium, Small orders for 1D
            - timeframes: Aggregated flow metrics for 1D, 5D, 20D, 60D, and All
            - price_levels: Price-level footprint order flow distribution
            - historical_flow_df: DataFrame with daily Inflow, Outflow, Net, and Cumulative Flows
            - divergence: Detected smart money divergence signals
            - cmf_20: 20-period Chaikin Money Flow
            - mfi_14: 14-period Money Flow Index
    """
    if df is None or len(df) < 5:
        return {}

    work_df = df.copy()

    # Ensure required columns
    required = ["Open", "High", "Low", "Close", "Volume"]
    for col in required:
        if col not in work_df.columns:
            raise ValueError(f"DataFrame must contain column '{col}'")

    # Clean zero volume or invalid values
    work_df["Volume"] = work_df["Volume"].fillna(0).astype(float)
    work_df["Close"] = work_df["Close"].astype(float)
    work_df["High"] = work_df["High"].astype(float)
    work_df["Low"] = work_df["Low"].astype(float)
    work_df["Open"] = work_df["Open"].astype(float)

    # 1. Turnover (Total Traded Value)
    work_df["Turnover"] = work_df["Close"] * work_df["Volume"]

    # 2. Close Location Value (CLV) / Money Flow Multiplier: [-1.0, 1.0]
    high_low_range = work_df["High"] - work_df["Low"]
    high_low_range = high_low_range.replace(0, 1e-6)
    clv = ((work_df["Close"] - work_df["Low"]) - (work_df["High"] - work_df["Close"])) / high_low_range

    # 3. Buyer vs Seller Initiative Model
    base_buy_ratio = (clv + 1.0) / 2.0

    # Intraday wick absorption factor: lower wick (buying off lows) vs upper wick
    lower_wick = np.maximum(0.0, np.minimum(work_df["Open"], work_df["Close"]) - work_df["Low"])
    upper_wick = np.maximum(0.0, work_df["High"] - np.maximum(work_df["Open"], work_df["Close"]))
    wick_ratio = (lower_wick - upper_wick) / high_low_range

    # Incorporate price change momentum (Close vs Prev Close)
    prev_close = work_df["Close"].shift(1).fillna(work_df["Open"])
    day_pct = (work_df["Close"] - prev_close) / prev_close.replace(0, 1.0)
    mom_factor = 1.0 / (1.0 + np.exp(-20.0 * np.clip(day_pct, -0.2, 0.2)))
    wick_factor = (wick_ratio + 1.0) / 2.0

    # General market buy conviction
    buy_ratio_m = np.clip(0.50 * base_buy_ratio + 0.25 * wick_factor + 0.25 * mom_factor, 0.05, 0.95)

    # Smart Money (Whales & Institutions) accumulation behavior:
    # Institutions accumulate on dips when CLV and lower wick rejection are high
    buy_ratio_xl = np.clip(0.65 * base_buy_ratio + 0.25 * wick_factor + 0.10 * mom_factor, 0.05, 0.95)
    buy_ratio_l  = np.clip(0.55 * base_buy_ratio + 0.25 * wick_factor + 0.20 * mom_factor, 0.05, 0.95)

    # Retail behavior: primarily driven by momentum / chasing green
    buy_ratio_s  = np.clip(0.20 * base_buy_ratio + 0.80 * mom_factor, 0.05, 0.95)

    # 4. Relative Volume & Dynamic Tier Weighting
    vol_sma = work_df["Volume"].rolling(window=window, min_periods=1).mean().replace(0, 1.0)
    rvol = np.clip(work_df["Volume"] / vol_sma, 0.3, 4.0)

    # Order Size Share Modeling:
    # Extra-Large (Whales / Institutional Blocks): surges with high RVol
    xl_share = np.clip(0.20 + 0.12 * np.log2(rvol), 0.08, 0.45)
    # Large (HNIs / Pro Desks)
    l_share = np.clip(0.26 + 0.04 * np.log2(rvol), 0.15, 0.35)
    # Medium (Active Traders)
    m_share = np.full(len(work_df), 0.26)
    # Small (Retail): absorbs the remainder
    s_share = np.clip(1.0 - (xl_share + l_share + m_share), 0.08, 0.40)

    # Re-normalize to sum to 1.0
    total_share = xl_share + l_share + m_share + s_share
    xl_share /= total_share
    l_share /= total_share
    m_share /= total_share
    s_share /= total_share

    # Calculate Tier Inflows and Outflows
    turnover = work_df["Turnover"]
    
    # Extra Large
    work_df["XL_Inflow"] = turnover * xl_share * buy_ratio_xl
    work_df["XL_Outflow"] = turnover * xl_share * (1.0 - buy_ratio_xl)
    work_df["XL_Net"] = work_df["XL_Inflow"] - work_df["XL_Outflow"]

    # Large
    work_df["L_Inflow"] = turnover * l_share * buy_ratio_l
    work_df["L_Outflow"] = turnover * l_share * (1.0 - buy_ratio_l)
    work_df["L_Net"] = work_df["L_Inflow"] - work_df["L_Outflow"]

    # Medium
    work_df["M_Inflow"] = turnover * m_share * buy_ratio_m
    work_df["M_Outflow"] = turnover * m_share * (1.0 - buy_ratio_m)
    work_df["M_Net"] = work_df["M_Inflow"] - work_df["M_Outflow"]

    # Small (Retail)
    work_df["S_Inflow"] = turnover * s_share * buy_ratio_s
    work_df["S_Outflow"] = turnover * s_share * (1.0 - buy_ratio_s)
    work_df["S_Net"] = work_df["S_Inflow"] - work_df["S_Outflow"]

    # Aggregate Total Inflow / Outflow
    work_df["Total_Inflow"] = work_df["XL_Inflow"] + work_df["L_Inflow"] + work_df["M_Inflow"] + work_df["S_Inflow"]
    work_df["Total_Outflow"] = work_df["XL_Outflow"] + work_df["L_Outflow"] + work_df["M_Outflow"] + work_df["S_Outflow"]
    work_df["Net_Capital_Flow"] = work_df["Total_Inflow"] - work_df["Total_Outflow"]

    # Cumulative Flow Curves (CVD style)
    work_df["Cum_Net_Flow"] = work_df["Net_Capital_Flow"].cumsum()
    work_df["Cum_Smart_Money_Net"] = (work_df["XL_Net"] + work_df["L_Net"]).cumsum()
    work_df["Cum_Retail_Net"] = work_df["S_Net"].cumsum()

    # 5. Standard Indicators: CMF & MFI
    # Chaikin Money Flow (CMF 20)
    mf_volume = clv * work_df["Volume"]
    vol_sum_20 = work_df["Volume"].rolling(window=20, min_periods=1).sum().replace(0, 1.0)
    cmf_series = mf_volume.rolling(window=20, min_periods=1).sum() / vol_sum_20
    work_df["CMF_20"] = cmf_series

    # Money Flow Index (MFI 14)
    typical_price = (work_df["High"] + work_df["Low"] + work_df["Close"]) / 3.0
    raw_money_flow = typical_price * work_df["Volume"]
    tp_change = typical_price.diff(1)
    pos_flow = raw_money_flow.where(tp_change > 0, 0.0)
    neg_flow = raw_money_flow.where(tp_change < 0, 0.0)
    pos_flow_sum = pos_flow.rolling(14, min_periods=1).sum()
    neg_flow_sum = neg_flow.rolling(14, min_periods=1).sum().replace(0, 1e-6)
    mfr = pos_flow_sum / neg_flow_sum
    work_df["MFI_14"] = 100.0 - (100.0 / (1.0 + mfr))

    # Helper function to summarize any slice of work_df
    def _summarize_slice(slice_df: pd.DataFrame) -> Dict[str, Any]:
        tot_in = float(slice_df["Total_Inflow"].sum())
        tot_out = float(slice_df["Total_Outflow"].sum())
        net_f = tot_in - tot_out
        tot_turn = float(slice_df["Turnover"].sum())
        
        net_pct = (net_f / tot_turn * 100.0) if tot_turn > 0 else 0.0
        in_ratio = (tot_in / tot_turn * 100.0) if tot_turn > 0 else 50.0

        xl_in = float(slice_df["XL_Inflow"].sum())
        xl_out = float(slice_df["XL_Outflow"].sum())
        xl_net = xl_in - xl_out

        l_in = float(slice_df["L_Inflow"].sum())
        l_out = float(slice_df["L_Outflow"].sum())
        l_net = l_in - l_out

        m_in = float(slice_df["M_Inflow"].sum())
        m_out = float(slice_df["M_Outflow"].sum())
        m_net = m_in - m_out

        s_in = float(slice_df["S_Inflow"].sum())
        s_out = float(slice_df["S_Outflow"].sum())
        s_net = s_in - s_out

        sm_net = xl_net + l_net
        sm_turnover = (xl_in + xl_out) + (l_in + l_out)
        sm_ratio = ((xl_in + l_in) / sm_turnover * 100.0) if sm_turnover > 0 else 50.0

        retail_net = s_net
        retail_turnover = s_in + s_out
        retail_ratio = (s_in / retail_turnover * 100.0) if retail_turnover > 0 else 50.0

        if net_pct > 10.0 and sm_net > 0:
            sentiment = "STRONG INFLOW (Whale Accumulation)"
            sentiment_clr = "#00e87a"
            score = min(100, int(50 + net_pct * 2.5))
        elif net_pct > 0:
            sentiment = "MILD INFLOW (Net Buying)"
            sentiment_clr = "#00c8ff"
            score = min(100, int(50 + net_pct))
        elif net_pct < -10.0 and sm_net < 0:
            sentiment = "HEAVY OUTFLOW (Whale Distribution)"
            sentiment_clr = "#ff3355"
            score = max(-100, int(-50 + net_pct * 2.5))
        elif net_pct < 0:
            sentiment = "MILD OUTFLOW (Net Selling)"
            sentiment_clr = "#ffcc00"
            score = max(-100, int(net_pct))
        else:
            sentiment = "NEUTRAL (Balanced Flow)"
            sentiment_clr = "#6a90aa"
            score = 0

        tiers_slice = {
            "Extra-Large": {
                "tier_label": "Extra-Large Orders (Institutions / Whales)",
                "inflow": xl_in,
                "outflow": xl_out,
                "net": xl_net,
                "share_pct": ((xl_in + xl_out) / tot_turn * 100.0) if tot_turn > 0 else 25.0,
            },
            "Large": {
                "tier_label": "Large Orders (HNIs / Prop Desks)",
                "inflow": l_in,
                "outflow": l_out,
                "net": l_net,
                "share_pct": ((l_in + l_out) / tot_turn * 100.0) if tot_turn > 0 else 25.0,
            },
            "Medium": {
                "tier_label": "Medium Orders (Active Traders)",
                "inflow": m_in,
                "outflow": m_out,
                "net": m_net,
                "share_pct": ((m_in + m_out) / tot_turn * 100.0) if tot_turn > 0 else 25.0,
            },
            "Small": {
                "tier_label": "Small Orders (Retail Traders)",
                "inflow": s_in,
                "outflow": s_out,
                "net": s_net,
                "share_pct": ((s_in + s_out) / tot_turn * 100.0) if tot_turn > 0 else 25.0,
            },
        }

        return {
            "total_inflow": tot_in,
            "total_outflow": tot_out,
            "net_capital_flow": net_f,
            "net_flow_pct": net_pct,
            "inflow_ratio": in_ratio,
            "smart_money_net": sm_net,
            "smart_money_ratio": sm_ratio,
            "retail_net": retail_net,
            "retail_ratio": retail_ratio,
            "sentiment": sentiment,
            "sentiment_color": sentiment_clr,
            "flow_score": score,
            "tiers": tiers_slice,
        }

    # Generate Timeframe Summaries: 1D, 5D, 20D, 60D, All
    timeframes = {}
    timeframes["1D"] = _summarize_slice(work_df.iloc[-1:])
    timeframes["5D"] = _summarize_slice(work_df.iloc[-min(5, len(work_df)):])
    timeframes["20D"] = _summarize_slice(work_df.iloc[-min(20, len(work_df)):])
    timeframes["60D"] = _summarize_slice(work_df.iloc[-min(60, len(work_df)):])
    timeframes["All"] = _summarize_slice(work_df)

    # 1D Summary & Tiers (Backwards compatibility)
    last_row = work_df.iloc[-1]
    summary_1d = timeframes["1D"]
    summary_1d["cmf_20"] = float(last_row["CMF_20"])
    summary_1d["mfi_14"] = float(last_row["MFI_14"])
    tiers_1d = summary_1d["tiers"]

    # 6. Divergence Detection over lookback (default 20 candles)
    n_lookback = min(lookback_days, len(work_df) - 1)
    sub = work_df.iloc[-n_lookback:]
    px_chg = (sub["Close"].iloc[-1] - sub["Close"].iloc[0]) / sub["Close"].iloc[0] * 100.0
    sm_chg = sub["Cum_Smart_Money_Net"].iloc[-1] - sub["Cum_Smart_Money_Net"].iloc[0]

    divergence_type = "NONE"
    divergence_desc = "Price and capital flow are synchronized."
    divergence_clr = "#6a90aa"

    if px_chg <= -1.0 and sm_chg > 0:
        divergence_type = "BULLISH DIVERGENCE (Whale Accumulation)"
        divergence_desc = f"Price declined {px_chg:.1f}% while Institutional Smart Money net accumulated. Strong accumulation signal."
        divergence_clr = "#00e87a"
    elif px_chg >= 1.0 and sm_chg < 0:
        divergence_type = "BEARISH DIVERGENCE (Whale Distribution)"
        divergence_desc = f"Price gained {px_chg:.1f}% while Institutional Smart Money distributed into the rally. Potential reversal risk."
        divergence_clr = "#ff3355"
    elif px_chg > 0 and sm_chg > 0:
        divergence_type = "BULLISH CONVERGENCE"
        divergence_desc = "Strong institutional buying backing the uptrend."
        divergence_clr = "#00e87a"
    elif px_chg < 0 and sm_chg < 0:
        divergence_type = "BEARISH CONVERGENCE"
        divergence_desc = "Institutional outflow confirming downward pressure."
        divergence_clr = "#ff3355"

    # 7. Price-Level Order Flow Profile (Footprint distribution across price brackets)
    price_levels = compute_price_level_order_flow(work_df.iloc[-min(60, len(work_df)):], num_buckets=12)

    return {
        "summary": summary_1d,
        "tiers": tiers_1d,
        "timeframes": timeframes,
        "price_levels": price_levels,
        "divergence": {
            "type": divergence_type,
            "description": divergence_desc,
            "color": divergence_clr,
            "price_chg_pct": px_chg,
            "smart_money_flow_chg": sm_chg,
        },
        "historical_flow_df": work_df,
    }


def compute_price_level_order_flow(flow_df: pd.DataFrame, num_buckets: int = 12) -> pd.DataFrame:
    """
    Computes horizontal price-level capital distribution (Inflow, Outflow, and Net Footprint)
    across discrete price levels over the lookback window.
    """
    if flow_df is None or flow_df.empty:
        return pd.DataFrame()

    min_p = float(flow_df["Low"].min())
    max_p = float(flow_df["High"].max())
    if min_p >= max_p:
        max_p = min_p * 1.05

    bins = np.linspace(min_p, max_p, num_buckets + 1)
    bucket_data = []

    for i in range(num_buckets):
        p_low = bins[i]
        p_high = bins[i + 1]
        p_mid = (p_low + p_high) / 2.0

        # Find rows whose high/low overlaps with this price bin
        mask = (flow_df["Low"] <= p_high) & (flow_df["High"] >= p_low)
        subset = flow_df[mask]

        if not subset.empty:
            # Weight by price overlap factor
            overlap = np.minimum(subset["High"], p_high) - np.maximum(subset["Low"], p_low)
            span = np.maximum(subset["High"] - subset["Low"], 1e-4)
            weight = np.clip(overlap / span, 0.05, 1.0)

            bin_inflow = float((subset["Total_Inflow"] * weight).sum())
            bin_outflow = float((subset["Total_Outflow"] * weight).sum())
            bin_xl_net = float((subset["XL_Net"] * weight).sum())
        else:
            bin_inflow = 0.0
            bin_outflow = 0.0
            bin_xl_net = 0.0

        bin_net = bin_inflow - bin_outflow
        bucket_data.append({
            "price_low": p_low,
            "price_high": p_high,
            "price_mid": p_mid,
            "price_label": f"{p_mid:,.2f}",
            "inflow": bin_inflow,
            "outflow": bin_outflow,
            "net_flow": bin_net,
            "smart_money_net": bin_xl_net,
            "total_turnover": bin_inflow + bin_outflow,
        })

    bdf = pd.DataFrame(bucket_data)
    if not bdf.empty and bdf["total_turnover"].max() > 0:
        poc_idx = bdf["total_turnover"].idxmax()
        bdf["is_poc"] = False
        bdf.loc[poc_idx, "is_poc"] = True
    else:
        bdf["is_poc"] = False
    return bdf
