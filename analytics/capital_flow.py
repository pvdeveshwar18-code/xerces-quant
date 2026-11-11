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
        if col not in df.columns:
            raise ValueError(f"DataFrame must contain column '{col}'")

    n = len(df)

    # Extract numpy arrays for high-performance vectorized operations
    close = df["Close"].astype(float).values
    high = df["High"].astype(float).values
    low = df["Low"].astype(float).values
    open_p = df["Open"].astype(float).values
    vol = df["Volume"].fillna(0).astype(float).values

    # 1. Turnover (Total Traded Value)
    turnover = close * vol

    # 2. Close Location Value (CLV) / Money Flow Multiplier: [-1.0, 1.0]
    high_low_range = high - low
    hl_safe = np.where(high_low_range == 0, 1e-6, high_low_range)
    clv = ((close - low) - (high - close)) / hl_safe

    # 3. Buyer vs Seller Initiative Model
    base_buy_ratio = (clv + 1.0) * 0.5

    # Intraday wick absorption factor: lower wick (buying off lows) vs upper wick
    lower_wick = np.maximum(0.0, np.minimum(open_p, close) - low)
    upper_wick = np.maximum(0.0, high - np.maximum(open_p, close))
    wick_ratio = (lower_wick - upper_wick) / hl_safe

    # Incorporate price change momentum (Close vs Prev Close)
    prev_close = np.roll(close, 1)
    prev_close[0] = open_p[0]
    prev_safe = np.where(prev_close == 0, 1.0, prev_close)
    day_pct = (close - prev_close) / prev_safe
    mom_factor = 1.0 / (1.0 + np.exp(-20.0 * np.clip(day_pct, -0.2, 0.2)))
    wick_factor = (wick_ratio + 1.0) * 0.5

    # General market buy conviction
    buy_ratio_m = np.clip(0.50 * base_buy_ratio + 0.25 * wick_factor + 0.25 * mom_factor, 0.05, 0.95)

    # Smart Money (Whales & Institutions) accumulation behavior:
    buy_ratio_xl = np.clip(0.65 * base_buy_ratio + 0.25 * wick_factor + 0.10 * mom_factor, 0.05, 0.95)
    buy_ratio_l  = np.clip(0.55 * base_buy_ratio + 0.25 * wick_factor + 0.20 * mom_factor, 0.05, 0.95)

    # Retail behavior: primarily driven by momentum / chasing green
    buy_ratio_s  = np.clip(0.20 * base_buy_ratio + 0.80 * mom_factor, 0.05, 0.95)

    # 4. Relative Volume & Dynamic Tier Weighting
    vol_series = pd.Series(vol, index=df.index)
    vol_sma = vol_series.rolling(window=window, min_periods=1).mean().values
    vol_sma_safe = np.where(vol_sma == 0, 1.0, vol_sma)
    rvol = np.clip(vol / vol_sma_safe, 0.3, 4.0)

    # Order Size Share Modeling
    log2_rvol = np.log2(rvol)
    xl_share = np.clip(0.20 + 0.12 * log2_rvol, 0.08, 0.45)
    l_share = np.clip(0.26 + 0.04 * log2_rvol, 0.15, 0.35)
    m_share = np.full(n, 0.26)
    s_share = np.clip(1.0 - (xl_share + l_share + m_share), 0.08, 0.40)

    # Re-normalize to sum to 1.0
    total_share = xl_share + l_share + m_share + s_share
    xl_share /= total_share
    l_share /= total_share
    m_share /= total_share
    s_share /= total_share

    # Calculate Tier Inflows and Outflows
    xl_inflow = turnover * xl_share * buy_ratio_xl
    xl_outflow = turnover * xl_share * (1.0 - buy_ratio_xl)
    xl_net = xl_inflow - xl_outflow

    l_inflow = turnover * l_share * buy_ratio_l
    l_outflow = turnover * l_share * (1.0 - buy_ratio_l)
    l_net = l_inflow - l_outflow

    m_inflow = turnover * m_share * buy_ratio_m
    m_outflow = turnover * m_share * (1.0 - buy_ratio_m)
    m_net = m_inflow - m_outflow

    s_inflow = turnover * s_share * buy_ratio_s
    s_outflow = turnover * s_share * (1.0 - buy_ratio_s)
    s_net = s_inflow - s_outflow

    # Aggregate Total Inflow / Outflow
    tot_inflow = xl_inflow + l_inflow + m_inflow + s_inflow
    tot_outflow = xl_outflow + l_outflow + m_outflow + s_outflow
    net_cap_flow = tot_inflow - tot_outflow

    # Cumulative Flow Curves (CVD style)
    cum_net_flow = np.cumsum(net_cap_flow)
    cum_sm_net = np.cumsum(xl_net + l_net)
    cum_retail_net = np.cumsum(s_net)

    # 5. Standard Indicators: CMF & MFI
    mf_volume = pd.Series(clv * vol, index=df.index)
    vol_sum_20 = vol_series.rolling(window=20, min_periods=1).sum().replace(0, 1.0)
    cmf_series = (mf_volume.rolling(window=20, min_periods=1).sum() / vol_sum_20).values

    typical_price = pd.Series((high + low + close) / 3.0, index=df.index)
    raw_money_flow = typical_price * vol_series
    tp_change = typical_price.diff(1)
    pos_flow = raw_money_flow.where(tp_change > 0, 0.0).rolling(14, min_periods=1).sum()
    neg_flow = raw_money_flow.where(tp_change < 0, 0.0).rolling(14, min_periods=1).sum().replace(0, 1e-6)
    mfi_series = (100.0 - (100.0 / (1.0 + (pos_flow / neg_flow)))).values

    # Batch DataFrame column assignment to avoid fragmentation
    work_df = df.copy()
    work_df["Volume"] = vol
    work_df["Close"] = close
    work_df["High"] = high
    work_df["Low"] = low
    work_df["Open"] = open_p
    work_df["Turnover"] = turnover
    work_df["XL_Inflow"] = xl_inflow
    work_df["XL_Outflow"] = xl_outflow
    work_df["XL_Net"] = xl_net
    work_df["L_Inflow"] = l_inflow
    work_df["L_Outflow"] = l_outflow
    work_df["L_Net"] = l_net
    work_df["M_Inflow"] = m_inflow
    work_df["M_Outflow"] = m_outflow
    work_df["M_Net"] = m_net
    work_df["S_Inflow"] = s_inflow
    work_df["S_Outflow"] = s_outflow
    work_df["S_Net"] = s_net
    work_df["Total_Inflow"] = tot_inflow
    work_df["Total_Outflow"] = tot_outflow
    work_df["Net_Capital_Flow"] = net_cap_flow
    work_df["Cum_Net_Flow"] = cum_net_flow
    work_df["Cum_Smart_Money_Net"] = cum_sm_net
    work_df["Cum_Retail_Net"] = cum_retail_net
    work_df["CMF_20"] = cmf_series
    work_df["MFI_14"] = mfi_series

    # Fast numpy slicing for timeframes
    def _summarize_arr(k: int) -> Dict[str, Any]:
        idx = slice(-k, None) if k < n else slice(None)
        tot_in = float(np.sum(tot_inflow[idx]))
        tot_out = float(np.sum(tot_outflow[idx]))
        net_f = tot_in - tot_out
        tot_turn = float(np.sum(turnover[idx]))

        net_pct = (net_f / tot_turn * 100.0) if tot_turn > 0 else 0.0
        in_ratio = (tot_in / tot_turn * 100.0) if tot_turn > 0 else 50.0

        xl_in = float(np.sum(xl_inflow[idx]))
        xl_out = float(np.sum(xl_outflow[idx]))
        xl_n = xl_in - xl_out

        l_in = float(np.sum(l_inflow[idx]))
        l_out = float(np.sum(l_outflow[idx]))
        l_n = l_in - l_out

        m_in = float(np.sum(m_inflow[idx]))
        m_out = float(np.sum(m_outflow[idx]))
        m_n = m_in - m_out

        s_in = float(np.sum(s_inflow[idx]))
        s_out = float(np.sum(s_outflow[idx]))
        s_n = s_in - s_out

        sm_net = xl_n + l_n
        sm_turnover = (xl_in + xl_out) + (l_in + l_out)
        sm_ratio = ((xl_in + l_in) / sm_turnover * 100.0) if sm_turnover > 0 else 50.0

        retail_net = s_n
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
                "net": xl_n,
                "share_pct": ((xl_in + xl_out) / tot_turn * 100.0) if tot_turn > 0 else 25.0,
            },
            "Large": {
                "tier_label": "Large Orders (HNIs / Prop Desks)",
                "inflow": l_in,
                "outflow": l_out,
                "net": l_n,
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
                "net": s_n,
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
    timeframes = {
        "1D": _summarize_arr(1),
        "5D": _summarize_arr(min(5, n)),
        "20D": _summarize_arr(min(20, n)),
        "60D": _summarize_arr(min(60, n)),
        "All": _summarize_arr(n)
    }

    # 1D Summary & Tiers (Backwards compatibility)
    summary_1d = timeframes["1D"]
    summary_1d["cmf_20"] = float(cmf_series[-1])
    summary_1d["mfi_14"] = float(mfi_series[-1])
    tiers_1d = summary_1d["tiers"]

    # 6. Divergence Detection over lookback (default 20 candles)
    n_lookback = min(lookback_days, n - 1)
    sub_c = close[-n_lookback:]
    px_chg = (sub_c[-1] - sub_c[0]) / sub_c[0] * 100.0
    sm_chg = cum_sm_net[-1] - cum_sm_net[-n_lookback]

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
    Optimized vectorized implementation avoiding repeated DataFrame slicing.
    """
    if flow_df is None or flow_df.empty:
        return pd.DataFrame()

    lows = flow_df["Low"].astype(float).values
    highs = flow_df["High"].astype(float).values
    total_inflows = flow_df["Total_Inflow"].astype(float).values
    total_outflows = flow_df["Total_Outflow"].astype(float).values
    xl_nets = flow_df["XL_Net"].astype(float).values

    min_p = float(np.min(lows))
    max_p = float(np.max(highs))
    if min_p >= max_p:
        max_p = min_p * 1.05

    bins = np.linspace(min_p, max_p, num_buckets + 1)
    spans = np.maximum(highs - lows, 1e-4)
    bucket_data = []

    for i in range(num_buckets):
        p_low = bins[i]
        p_high = bins[i + 1]
        p_mid = (p_low + p_high) * 0.5

        # Find rows whose high/low overlaps with this price bin
        mask = (lows <= p_high) & (highs >= p_low)
        if np.any(mask):
            overlap = np.minimum(highs[mask], p_high) - np.maximum(lows[mask], p_low)
            weight = np.clip(overlap / spans[mask], 0.05, 1.0)

            bin_inflow = float(np.sum(total_inflows[mask] * weight))
            bin_outflow = float(np.sum(total_outflows[mask] * weight))
            bin_xl_net = float(np.sum(xl_nets[mask] * weight))
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
