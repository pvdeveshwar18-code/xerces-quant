import numpy as np
import pandas as pd
from typing import Tuple, List

def calc_volume_profile(df: pd.DataFrame, price_bins: int = 100) -> Tuple[pd.DataFrame, Tuple[float, float]]:
    """Calculate a volume‑by‑price histogram (Volume Profile).

    Parameters
    ----------
    df: pd.DataFrame
        Must contain columns ``['high', 'low', 'close', 'volume']``. The
        function distributes each bar's volume across the price range it spans.
    price_bins: int, optional
        Number of price buckets to use for the histogram. Default 100.

    Returns
    -------
    profile_df: pd.DataFrame
        DataFrame with ``price`` (mid‑point of each bucket) and ``volume``
        (total volume accumulated in that bucket).
    value_area: Tuple[float, float]
        Lower and upper price bounds that contain ~70 % of total volume
        (the classic value area).
    """
    if not {'high', 'low', 'volume'}.issubset(df.columns):
        raise ValueError("DataFrame must contain 'high', 'low', and 'volume' columns")

    # Determine global price range
    min_price = df['low'].min()
    max_price = df['high'].max()
    bins = np.linspace(min_price, max_price, price_bins + 1)
    volume_per_bin = np.zeros(price_bins, dtype=float)

    for _, row in df.iterrows():
        # proportion of the bar's volume assigned to each intersecting bin
        bar_low, bar_high, vol = row['low'], row['high'], row['volume']
        # Find intersecting bin indices
        intersect_idxs = np.where((bins[:-1] < bar_high) & (bins[1:] > bar_low))[0]
        if intersect_idxs.size == 0:
            continue
        # Approximate equal distribution across intersected bins
        vol_per_idx = vol / intersect_idxs.size
        volume_per_bin[intersect_idxs] += vol_per_idx

    # Build result DataFrame
    mid_prices = (bins[:-1] + bins[1:]) / 2
    profile_df = pd.DataFrame({"price": mid_prices, "volume": volume_per_bin})
    profile_df = profile_df.sort_values('price')

    # Compute value area (70% of total volume around the POC)
    total_vol = profile_df['volume'].sum()
    target_vol = total_vol * 0.7
    # Sort bins by volume descending to find POC (point of control)
    sorted_by_vol = profile_df.sort_values('volume', ascending=False)
    cumulative = sorted_by_vol['volume'].cumsum()
    poc_idx = cumulative >= (total_vol * 0.01)  # first 1% as rough POC cutoff
    poc_price = sorted_by_vol.loc[poc_idx, 'price'].iloc[0]
    # Expand around POC until target volume reached
    lower, upper = poc_price, poc_price
    vol_acc = sorted_by_vol.loc[poc_idx, 'volume'].iloc[0]
    i = 0
    while vol_acc < target_vol and i < len(sorted_by_vol):
        price_i = sorted_by_vol.iloc[i]['price']
        if price_i < lower:
            lower = price_i
        elif price_i > upper:
            upper = price_i
        vol_acc += sorted_by_vol.iloc[i]['volume']
        i += 1
    value_area = (lower, upper)
    return profile_df, value_area
