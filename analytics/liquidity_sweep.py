import pandas as pd
from typing import List, Dict

def detect_liquidity_sweeps(df: pd.DataFrame, sweep_threshold: float = 0.02) -> List[Dict]:
    """Detect liquidity sweep events in a DataFrame containing depth snapshots.

    Parameters
    ----------
    df: pd.DataFrame
        Must contain columns ``['timestamp', 'volume', 'bid_volume', 'ask_volume']``
        where ``volume`` is the total traded volume for the bar and the bid/ask
        volumes represent the order‑book depth at the start of the bar.
    sweep_threshold: float, default 0.02
        Fraction of the bar's total volume that must be executed in a single
        burst to be considered a sweep (e.g., 0.02 = 2 % of volume).

    Returns
    -------
    List[Dict]
        Each dict corresponds to a sweep event with ``timestamp`` and ``strength``
        (fraction of volume swept).
    """
    sweeps = []
    required = df['volume'] * sweep_threshold
    for _, row in df.iterrows():
        # Simple heuristic: if either side's depth drops by more than the threshold
        # we treat it as a sweep. In real data you would compare successive depth
        # snapshots; here we approximate with the provided aggregate.
        if row.get('bid_volume', 0) < required or row.get('ask_volume', 0) < required:
            strength = max(required / row['volume'], 0)
            sweeps.append({
                'timestamp': row['timestamp'],
                'strength': strength,
                'type': 'bid' if row.get('bid_volume', 0) < required else 'ask'
            })
    return sweeps
