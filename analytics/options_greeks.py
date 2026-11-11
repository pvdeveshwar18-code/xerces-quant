"""
Black-Scholes Options Greeks Engine for XERCES.
Calculates Delta, Gamma, Theta, Vega, and Rho for European/NSE index and equity options.
Uses analytical normal CDF/PDF implementations via standard math libraries (no heavy external dependencies).
"""

import math
from typing import Dict
import pandas as pd
import numpy as np

try:
    from scipy.special import erf as sp_erf
except ImportError:
    sp_erf = None

def _norm_cdf(x: float) -> float:
    """Cumulative distribution function for standard normal distribution."""
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))

def _norm_pdf(x: float) -> float:
    """Probability density function for standard normal distribution."""
    return math.exp(-0.5 * x * x) / math.sqrt(2.0 * math.pi)

def calc_bs_greeks(
    spot: float,
    strike: float,
    tte_years: float,
    volatility: float,
    risk_free_rate: float = 0.07,
    is_call: bool = True
) -> Dict[str, float]:
    """
    Compute Black-Scholes Greeks for an option contract.

    Parameters:
    -----------
    spot : float
        Current underlying spot price.
    strike : float
        Option strike price.
    tte_years : float
        Time to expiry in years (e.g. 7 days = 7 / 365).
    volatility : float
        Implied Volatility (as decimal, e.g. 0.20 for 20%).
    risk_free_rate : float
        Risk-free interest rate (default 0.07 for RBI 91-day T-Bill).
    is_call : bool
        True for Call (CE), False for Put (PE).

    Returns:
    --------
    dict with keys: 'delta', 'gamma', 'theta', 'vega', 'intrinsic_value'
    """
    # Guard against invalid inputs
    if spot <= 0 or strike <= 0:
        return {"delta": 0.0, "gamma": 0.0, "theta": 0.0, "vega": 0.0, "intrinsic_value": 0.0}

    tte = max(tte_years, 1.0 / 365.0)  # Minimum 1 day to prevent division by zero
    vol = max(volatility, 0.01)       # Minimum 1% IV

    sqrt_t = math.sqrt(tte)
    d1 = (math.log(spot / strike) + (risk_free_rate + 0.5 * vol * vol) * tte) / (vol * sqrt_t)
    d2 = d1 - vol * sqrt_t

    pdf_d1 = _norm_pdf(d1)
    cdf_d1 = _norm_cdf(d1)
    cdf_d2 = _norm_cdf(d2)

    discount = math.exp(-risk_free_rate * tte)

    # Gamma (identical for Call and Put)
    gamma = pdf_d1 / (spot * vol * sqrt_t)

    # Vega (sensitivity per 1% move in IV)
    vega = (spot * sqrt_t * pdf_d1) / 100.0

    if is_call:
        delta = cdf_d1
        # Theta per calendar day
        theta_annual = -(spot * pdf_d1 * vol) / (2.0 * sqrt_t) - (risk_free_rate * strike * discount * cdf_d2)
        theta_day = theta_annual / 365.0
        intrinsic = max(0.0, spot - strike)
    else:
        delta = cdf_d1 - 1.0
        cdf_neg_d2 = _norm_cdf(-d2)
        # Theta per calendar day
        theta_annual = -(spot * pdf_d1 * vol) / (2.0 * sqrt_t) + (risk_free_rate * strike * discount * cdf_neg_d2)
        theta_day = theta_annual / 365.0
        intrinsic = max(0.0, strike - spot)

    return {
        "delta": round(delta, 3),
        "gamma": round(gamma, 5),
        "theta": round(theta_day, 2),
        "vega": round(vega, 2),
        "intrinsic_value": round(intrinsic, 2)
    }

def enrich_options_chain_with_greeks(
    df_chain: pd.DataFrame,
    spot_price: float,
    days_to_expiry: int = 7,
    risk_free_rate: float = 0.07
) -> pd.DataFrame:
    """
    Enrich an options chain DataFrame with real-time Black-Scholes Greeks for both CE and PE.
    Optimized vectorized implementation.
    """
    if df_chain is None or df_chain.empty or spot_price <= 0:
        return df_chain

    df = df_chain.copy()
    tte = max(float(days_to_expiry), 1.0) / 365.0
    sqrt_t = math.sqrt(tte)
    discount = math.exp(-risk_free_rate * tte)

    try:
        if sp_erf is None:
            raise ImportError("scipy not available")

        strikes = df["Strike"].astype(float).values
        ce_iv_raw = df["CE IV"].fillna(20.0).astype(float).values if "CE IV" in df.columns else np.full(len(df), 20.0)
        pe_iv_raw = df["PE IV"].fillna(20.0).astype(float).values if "PE IV" in df.columns else np.full(len(df), 20.0)

        ce_vols = np.clip(np.where(ce_iv_raw > 1.0, ce_iv_raw / 100.0, ce_iv_raw), 0.01, None)
        pe_vols = np.clip(np.where(pe_iv_raw > 1.0, pe_iv_raw / 100.0, pe_iv_raw), 0.01, None)

        # Vectorized CE Greeks
        d1_ce = (np.log(spot_price / strikes) + (risk_free_rate + 0.5 * ce_vols * ce_vols) * tte) / (ce_vols * sqrt_t)
        d2_ce = d1_ce - ce_vols * sqrt_t
        pdf_ce = np.exp(-0.5 * d1_ce * d1_ce) / math.sqrt(2.0 * math.pi)
        cdf_d1_ce = 0.5 * (1.0 + sp_erf(d1_ce / math.sqrt(2.0)))
        cdf_d2_ce = 0.5 * (1.0 + sp_erf(d2_ce / math.sqrt(2.0)))

        df["CE Delta"] = np.round(cdf_d1_ce, 3)
        df["CE Gamma"] = np.round(pdf_ce / (spot_price * ce_vols * sqrt_t), 5)
        theta_ann_ce = -(spot_price * pdf_ce * ce_vols) / (2.0 * sqrt_t) - (risk_free_rate * strikes * discount * cdf_d2_ce)
        df["CE Theta"] = np.round(theta_ann_ce / 365.0, 2)
        df["CE Vega"] = np.round((spot_price * sqrt_t * pdf_ce) / 100.0, 2)

        # Vectorized PE Greeks
        d1_pe = (np.log(spot_price / strikes) + (risk_free_rate + 0.5 * pe_vols * pe_vols) * tte) / (pe_vols * sqrt_t)
        d2_pe = d1_pe - pe_vols * sqrt_t
        pdf_pe = np.exp(-0.5 * d1_pe * d1_pe) / math.sqrt(2.0 * math.pi)
        cdf_d1_pe = 0.5 * (1.0 + sp_erf(d1_pe / math.sqrt(2.0)))
        cdf_neg_d2_pe = 0.5 * (1.0 + sp_erf(-d2_pe / math.sqrt(2.0)))

        df["PE Delta"] = np.round(cdf_d1_pe - 1.0, 3)
        df["PE Gamma"] = np.round(pdf_pe / (spot_price * pe_vols * sqrt_t), 5)
        theta_ann_pe = -(spot_price * pdf_pe * pe_vols) / (2.0 * sqrt_t) + (risk_free_rate * strikes * discount * cdf_neg_d2_pe)
        df["PE Theta"] = np.round(theta_ann_pe / 365.0, 2)
        df["PE Vega"] = np.round((spot_price * sqrt_t * pdf_pe) / 100.0, 2)
        return df
    except Exception:
        # Fallback to scalar iteration if vectorized library unavailable
        ce_deltas, ce_gammas, ce_thetas, ce_vegas = [], [], [], []
        pe_deltas, pe_gammas, pe_thetas, pe_vegas = [], [], [], []
        for _, row in df.iterrows():
            strike = float(row.get("Strike", 0.0))
            ce_iv_pct = float(row.get("CE IV", 0.0) or 20.0)
            pe_iv_pct = float(row.get("PE IV", 0.0) or 20.0)
            ce_vol = ce_iv_pct / 100.0 if ce_iv_pct > 1.0 else ce_iv_pct
            pe_vol = pe_iv_pct / 100.0 if pe_iv_pct > 1.0 else pe_iv_pct
            ce_greeks = calc_bs_greeks(spot=spot_price, strike=strike, tte_years=tte, volatility=ce_vol, risk_free_rate=risk_free_rate, is_call=True)
            pe_greeks = calc_bs_greeks(spot=spot_price, strike=strike, tte_years=tte, volatility=pe_vol, risk_free_rate=risk_free_rate, is_call=False)
            ce_deltas.append(ce_greeks["delta"])
            ce_gammas.append(ce_greeks["gamma"])
            ce_thetas.append(ce_greeks["theta"])
            ce_vegas.append(ce_greeks["vega"])
            pe_deltas.append(pe_greeks["delta"])
            pe_gammas.append(pe_greeks["gamma"])
            pe_thetas.append(pe_greeks["theta"])
            pe_vegas.append(pe_greeks["vega"])

        df["CE Delta"] = ce_deltas
        df["CE Theta"] = ce_thetas
        df["CE Gamma"] = ce_gammas
        df["CE Vega"] = ce_vegas
        df["PE Delta"] = pe_deltas
        df["PE Theta"] = pe_thetas
        df["PE Gamma"] = pe_gammas
        df["PE Vega"] = pe_vegas
        return df
