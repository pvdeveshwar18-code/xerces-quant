import pandas as pd
from typing import List, Dict

def detect_liquidity_sweeps(df: pd.DataFrame, sweep_threshold: float = 0.02) -> List[Dict]:
    """Detect liquidity sweep events in a DataFrame containing depth snapshots.

    Parameters
    ----------
    df: pd.DataFrame
        Must contain columns ``['timestamp', 'volume', 'bid_volume', 'ask_volume']``
        (case-insensitive).
    sweep_threshold: float, default 0.02
        Fraction of the bar's total volume that must be executed in a single
        burst to be considered a sweep (e.g., 0.02 = 2% of volume).

    Returns
    -------
    List[Dict]
        Each dict corresponds to a sweep event with ``timestamp``, ``strength``,
        and ``type`` ('bid' or 'ask').
    """
    sweeps = []
    if df is None or df.empty:
        return sweeps

    col_map = {str(c).lower(): c for c in df.columns}
    vol_col = col_map.get('volume')
    bid_col = col_map.get('bid_volume')
    ask_col = col_map.get('ask_volume')
    ts_col = col_map.get('timestamp') or col_map.get('date') or col_map.get('time')

    if not vol_col:
        return sweeps

    for idx, row in df.iterrows():
        try:
            bar_vol = float(row[vol_col])
        except (ValueError, TypeError):
            continue

        if bar_vol <= 0:
            continue

        required = bar_vol * sweep_threshold
        bid_vol = float(row.get(bid_col, 0) or 0) if bid_col else 0
        ask_vol = float(row.get(ask_col, 0) or 0) if ask_col else 0

        is_bid_sweep = (bid_col is not None and bid_vol < required)
        is_ask_sweep = (ask_col is not None and ask_vol < required)

        if is_bid_sweep or is_ask_sweep:
            strength = round(max(required / bar_vol, 0.0), 4)
            timestamp = row.get(ts_col) if ts_col else idx
            sweeps.append({
                'timestamp': timestamp,
                'strength': strength,
                'type': 'bid' if is_bid_sweep else 'ask'
            })
    return sweeps
