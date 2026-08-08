"""
XERCES Market Data Layer & Smart Caching Module
Configurable TTLs for yfinance market queries to eliminate rate-limiting and accelerate tab switching.
"""

import time
import json
import re
import datetime
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
import numpy as np
import pandas as pd
import yfinance as yf
import streamlit as st

# ── OHLCV DATA LOADING ────────────────────────────────────────────────────────
@st.cache_data(ttl=3600, show_spinner=False)
def load_ohlcv(ticker: str, period: str = "2y") -> pd.DataFrame:
    """
    Cached yfinance OHLCV loader with multi-index normalization and sanitization.
    TTL = 3600 seconds (1 hour).
    """
    try:
        df = yf.download(
            ticker,
            period=period,
            interval="1d",
            auto_adjust=True,
            progress=False,
            timeout=12
        )
        if df is None or df.empty:
            return None
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        df = df.reset_index()
        df.columns = [str(c).strip() for c in df.columns]
        for col in ["Open", "High", "Low", "Close", "Volume"]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")
        df = df.dropna(subset=["Close"])
        return df
    except Exception:
        return None


def add_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculates technical indicators: SMA 20/50/200, EMA 12/26, MACD, RSI, Bollinger Bands, ATR, Stochastic, OBV.
    """
    out = df.copy()
    if len(out) < 20:
        return out
    c = out["Close"].astype(float)
    out["Return"]        = c.pct_change()
    out["SMA_20"]        = c.rolling(20).mean()
    out["SMA_50"]        = c.rolling(50).mean()
    out["SMA_200"]       = c.rolling(200).mean()
    out["EMA_12"]        = c.ewm(span=12, adjust=False).mean()
    out["EMA_26"]        = c.ewm(span=26, adjust=False).mean()
    out["MACD"]          = out["EMA_12"] - out["EMA_26"]
    out["MACD_Signal"]   = out["MACD"].ewm(span=9, adjust=False).mean()
    out["MACD_Hist"]     = out["MACD"] - out["MACD_Signal"]
    out["BB_Mid"]        = c.rolling(20).mean()
    out["BB_Std"]        = c.rolling(20).std()
    out["BB_Upper"]      = out["BB_Mid"] + 2 * out["BB_Std"]
    out["BB_Lower"]      = out["BB_Mid"] - 2 * out["BB_Std"]
    out["Volatility_20"] = out["Return"].rolling(20).std() * np.sqrt(252)

    delta = c.diff()
    gain  = delta.clip(lower=0).rolling(14).mean()
    loss  = (-delta.clip(upper=0)).rolling(14).mean()
    out["RSI_14"] = 100 - (100 / (1 + gain / (loss + 1e-9)))

    if "High" in out.columns and "Low" in out.columns:
        hi = out["High"].astype(float)
        lo = out["Low"].astype(float)
        hl = hi - lo
        hc = (hi - c.shift()).abs()
        lc = (lo - c.shift()).abs()
        out["ATR_14"] = pd.concat([hl, hc, lc], axis=1).max(axis=1).rolling(14).mean()
    else:
        out["ATR_14"] = c.rolling(14).std()

    low14  = out["Low"].astype(float).rolling(14).min() if "Low" in out.columns else c.rolling(14).min()
    high14 = out["High"].astype(float).rolling(14).max() if "High" in out.columns else c.rolling(14).max()
    out["Stoch_K"] = (c - low14) / (high14 - low14 + 1e-9) * 100
    out["Stoch_D"] = out["Stoch_K"].rolling(3).mean()

    if "Volume" in out.columns:
        vol = out["Volume"].astype(float)
        obv = [0.0]
        for i in range(1, len(out)):
            if out["Close"].iloc[i] > out["Close"].iloc[i-1]:
                obv.append(obv[-1] + vol.iloc[i])
            elif out["Close"].iloc[i] < out["Close"].iloc[i-1]:
                obv.append(obv[-1] - vol.iloc[i])
            else:
                obv.append(obv[-1])
        out["OBV"] = obv
    return out


# ── INDEX TELEMETRY ───────────────────────────────────────────────────────────
@st.cache_data(ttl=1800, show_spinner=False)
def load_indices() -> dict:
    """
    Cached loader for market benchmark indices (NIFTY 50, BANK NIFTY, SENSEX, VIX).
    TTL = 1800 seconds (30 mins).
    """
    tickers = ["^NSEI", "^NSEBANK", "^BSESN", "^CRSMID", "^CNXSC", "^INDIAVIX"]
    results = {}
    for t in tickers:
        try:
            d = yf.download(t, period="5d", interval="1d", auto_adjust=True, progress=False)
            if d is not None and not d.empty:
                if isinstance(d.columns, pd.MultiIndex):
                    d.columns = d.columns.get_level_values(0)
                d = d.reset_index()
                results[t] = d
        except Exception:
            pass
    return results


# ── FII / DII FLOWS ───────────────────────────────────────────────────────────
@st.cache_data(ttl=1800, show_spinner=False)
def fetch_fii_dii():
    """
    Cached loader for NSE FII/DII Net Flow data.
    """
    url = "https://www.nseindia.com/api/fiidiiTradeReact"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://www.nseindia.com/market-data/fii-dii-activity",
    }
    try:
        import http.cookiejar
        cj = http.cookiejar.CookieJar()
        opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
        main_req = urllib.request.Request("https://www.nseindia.com", headers=headers)
        opener.open(main_req, timeout=8)
        time.sleep(0.3)
        req = urllib.request.Request(url, headers=headers)
        with opener.open(req, timeout=8) as r:
            data = json.loads(r.read().decode())
        return data
    except Exception:
        return None


def parse_fii_dii(data):
    """
    Parses FII/DII API response into structured DataFrame.
    """
    if not data:
        return None, None
    try:
        rows = data if isinstance(data, list) else data.get("data", [])
        records = []
        for row in rows[:20]:
            try:
                date_str = row.get("date", row.get("Date", ""))
                fii_buy  = float(str(row.get("fiiBuy",  row.get("FII_BUY",  0))).replace(",","") or 0)
                fii_sell = float(str(row.get("fiiSell", row.get("FII_SELL", 0))).replace(",","") or 0)
                dii_buy  = float(str(row.get("diiBuy",  row.get("DII_BUY",  0))).replace(",","") or 0)
                dii_sell = float(str(row.get("diiSell", row.get("DII_SELL", 0))).replace(",","") or 0)
                records.append({
                    "Date": date_str,
                    "FII Net": round(fii_buy - fii_sell, 2),
                    "DII Net": round(dii_buy - dii_sell, 2),
                    "FII Buy": fii_buy, "FII Sell": fii_sell,
                    "DII Buy": dii_buy, "DII Sell": dii_sell,
                })
            except Exception:
                continue
        if not records:
            return None, None
        df = pd.DataFrame(records)
        return df, df.iloc[0] if len(df) > 0 else None
    except Exception:
        return None, None


# ── OPTIONS CHAIN ─────────────────────────────────────────────────────────────
@st.cache_data(ttl=900, show_spinner=False)
def fetch_options_chain(symbol: str):
    """
    Cached option chain fetcher from NSE India API.
    """
    clean = symbol.replace(".NS", "").replace(".BO", "").upper()
    url = f"https://www.nseindia.com/api/option-chain-equities?symbol={clean}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json, text/plain, */*",
        "Referer": f"https://www.nseindia.com/get-quotes/derivatives?symbol={clean}",
    }
    try:
        import http.cookiejar
        cj = http.cookiejar.CookieJar()
        opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
        main_req = urllib.request.Request("https://www.nseindia.com", headers=headers)
        opener.open(main_req, timeout=8)
        time.sleep(0.3)
        req = urllib.request.Request(url, headers=headers)
        with opener.open(req, timeout=10) as r:
            return json.loads(r.read().decode())
    except Exception:
        return None


def parse_options_chain(data, spot_price: float = 0.0):
    """
    Parses option chain response, computes PCR (Put-Call Ratio) and Max Pain strike.
    """
    if not data:
        return None, None, None, None
    try:
        records = data.get("records", {})
        exp_dates = records.get("expiryDates", [])
        nearest_exp = exp_dates[0] if exp_dates else None
        chain_data  = records.get("data", [])

        rows = []
        for item in chain_data:
            if nearest_exp and item.get("expiryDate") != nearest_exp:
                continue
            strike = item.get("strikePrice", 0)
            ce = item.get("CE", {})
            pe = item.get("PE", {})
            rows.append({
                "Strike":   strike,
                "CE OI":    ce.get("openInterest", 0),
                "CE Chg OI": ce.get("changeinOpenInterest", 0),
                "CE LTP":   ce.get("lastPrice", 0),
                "CE IV":    ce.get("impliedVolatility", 0),
                "PE OI":    pe.get("openInterest", 0),
                "PE Chg OI": pe.get("changeinOpenInterest", 0),
                "PE LTP":   pe.get("lastPrice", 0),
                "PE IV":    pe.get("impliedVolatility", 0),
            })

        if not rows:
            return None, None, None, nearest_exp

        df_chain = pd.DataFrame(rows).sort_values("Strike")

        total_ce_oi = df_chain["CE OI"].sum()
        total_pe_oi = df_chain["PE OI"].sum()
        pcr = round(total_pe_oi / total_ce_oi, 3) if total_ce_oi > 0 else None

        strikes = df_chain["Strike"].values
        ce_ois  = df_chain["CE OI"].values
        pe_ois  = df_chain["PE OI"].values
        pain    = []
        for s in strikes:
            ce_pain = sum(max(0, s - k) * o for k, o in zip(strikes, ce_ois))
            pe_pain = sum(max(0, k - s) * o for k, o in zip(strikes, pe_ois))
            pain.append(ce_pain + pe_pain)
        max_pain_strike = float(strikes[int(np.argmin(pain))])

        return df_chain, pcr, max_pain_strike, nearest_exp
    except Exception:
        return None, None, None, None



# ── NEWS & SENTIMENT ──────────────────────────────────────────────────────────
@st.cache_data(ttl=900, show_spinner=False)
def fetch_news(ticker: str, company_name: str = ""):
    """
    Cached RSS news scraper for Google News / Yahoo Finance headlines.
    """
    clean = ticker.replace(".NS", "").replace(".BO", "")
    query = company_name.strip() if company_name.strip() else clean
    items = []
    try:
        gquery = urllib.parse.quote(f"{query} stock NSE")
        gurl = f"https://news.google.com/rss/search?q={gquery}&hl=en-IN&gl=IN&ceid=IN:en"
        req = urllib.request.Request(gurl, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=8) as r:
            root = ET.fromstring(r.read())
        for item in root.findall(".//item")[:15]:
            title   = (item.find("title").text   or "") if item.find("title")   is not None else ""
            link    = (item.find("link").text    or "") if item.find("link")    is not None else ""
            pubdate = (item.find("pubDate").text or "") if item.find("pubDate") is not None else ""
            if title:
                items.append({"title": title, "link": link, "date": pubdate[:16]})
    except Exception:
        pass

    if items:
        return items

    try:
        url = f"https://feeds.finance.yahoo.com/rss/2.0/headline?s={clean}&region=IN&lang=en-IN"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=6) as r:
            root = ET.fromstring(r.read())
        for item in root.findall(".//item"):
            title   = (item.find("title").text   or "") if item.find("title")   is not None else ""
            link    = (item.find("link").text    or "") if item.find("link")    is not None else ""
            pubdate = (item.find("pubDate").text or "") if item.find("pubDate") is not None else ""
            items.append({"title": title, "link": link, "date": pubdate[:16]})
        return items
    except Exception:
        return []


# ── FUNDAMENTALS ──────────────────────────────────────────────────────────────
@st.cache_data(ttl=86400, show_spinner=False)
def fetch_fundamentals(symbol: str):
    """
    Cached scraper for screener.in financial ratios.
    """
    clean = symbol.replace(".NS", "").replace(".BO", "").upper()
    url = f"https://www.screener.in/company/{clean}/consolidated/"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    
    def _parse_ratio(html: str, label: str):
        li_pattern = re.compile(
            r'<li[^>]*>\s*<span class="name">\s*(?:<a[^>]*>)?\s*' + re.escape(label) +
            r'\s*(?:</a>)?\s*</span>(.*?)</li>', re.IGNORECASE | re.DOTALL
        )
        m = li_pattern.search(html)
        if not m:
            return None
        block = m.group(1)
        nums = re.findall(r'-?[\d]+(?:,\d{3})*(?:\.\d+)?', block)
        if not nums:
            return None
        try:
            return float(nums[-1].replace(",", ""))
        except Exception:
            return None

    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as r:
            html = r.read().decode("utf-8", errors="ignore")
    except Exception:
        try:
            url2 = f"https://www.screener.in/company/{clean}/"
            req2 = urllib.request.Request(url2, headers=headers)
            with urllib.request.urlopen(req2, timeout=10) as r:
                html = r.read().decode("utf-8", errors="ignore")
            url = url2
        except Exception:
            return {}, url

    pe   = _parse_ratio(html, "Stock P/E")
    pb   = _parse_ratio(html, "Price to Book value")
    roe  = _parse_ratio(html, "ROE")
    roce = _parse_ratio(html, "ROCE")
    de   = _parse_ratio(html, "Debt to equity")
    prom = _parse_ratio(html, "Promoter holding")
    eps  = _parse_ratio(html, "EPS")
    dy   = _parse_ratio(html, "Dividend Yield")

    return {
        "P/E Ratio":      pe,
        "P/B Ratio":      pb,
        "ROE (%)":        roe,
        "ROCE (%)":       roce,
        "Debt/Equity":    de,
        "Promoter Hold%": prom,
        "EPS (TTM)":      eps,
        "Div Yield (%)":  dy,
    }, url
