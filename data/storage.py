import os
import json
import datetime
from pathlib import Path
import pandas as pd
import streamlit as st

def _resolve_data_dir() -> Path:
    """Pick a writable directory that works locally, in Docker, and on Streamlit Cloud."""
    env_dir = os.environ.get("XERCES_DATA_DIR")
    if env_dir:
        p = Path(env_dir)
        try:
            p.mkdir(parents=True, exist_ok=True)
            return p
        except Exception:
            pass
    try:
        here = Path(__file__).resolve().parent.parent / "data"
        here.mkdir(parents=True, exist_ok=True)
        return here
    except Exception:
        pass
    try:
        cwd = Path.cwd() / "data"
        cwd.mkdir(parents=True, exist_ok=True)
        return cwd
    except Exception:
        pass
    import tempfile
    tmp = Path(tempfile.gettempdir()) / "xerces_data"
    tmp.mkdir(parents=True, exist_ok=True)
    return tmp

DATA_DIR = _resolve_data_dir()
WATCHLIST_FILE = DATA_DIR / "watchlist.json"
JOURNAL_FILE   = DATA_DIR / "journal.csv"
ALERTS_FILE    = DATA_DIR / "alerts.json"
CHAT_HISTORY_FILE = DATA_DIR / "chat_history.json"

# 1. WATCHLIST — persistent JSON file
def load_watchlist() -> list:
    if WATCHLIST_FILE.exists():
        try:
            return json.loads(WATCHLIST_FILE.read_text(encoding="utf-8"))
        except Exception:
            return []
    return []

def save_watchlist(items: list):
    WATCHLIST_FILE.write_text(json.dumps(items, indent=2), encoding="utf-8")

def add_to_watchlist(ticker: str, name: str) -> bool:
    wl = load_watchlist()
    if not any(w["ticker"] == ticker for w in wl):
        wl.append({"ticker": ticker, "name": name,
                   "added": datetime.datetime.now().isoformat()})
        save_watchlist(wl)
        return True
    return False

def remove_from_watchlist(ticker: str):
    wl = [w for w in load_watchlist() if w["ticker"] != ticker]
    save_watchlist(wl)

# 2. ALERTS — persistent JSON
def load_alerts() -> list:
    if ALERTS_FILE.exists():
        try:
            return json.loads(ALERTS_FILE.read_text(encoding="utf-8"))
        except Exception:
            return []
    return []

def save_alerts(items: list):
    ALERTS_FILE.write_text(json.dumps(items, indent=2), encoding="utf-8")

def add_alert(ticker: str, name: str, kind: str, op: str, value: float):
    alerts = load_alerts()
    alerts.append({
        "id": f"{ticker}_{kind}_{op}_{value}_{int(datetime.datetime.now().timestamp())}",
        "ticker": ticker, "name": name, "kind": kind, "op": op,
        "value": float(value), "created": datetime.datetime.now().isoformat(),
        "triggered": False, "triggered_at": None, "last_val": None
    })
    save_alerts(alerts)

def delete_alert(alert_id: str):
    alerts = [a for a in load_alerts() if a["id"] != alert_id]
    save_alerts(alerts)

def evaluate_alerts(price_lookup) -> list:
    alerts = load_alerts()
    newly_triggered = []
    for a in alerts:
        if a.get("triggered"):
            continue
        data = price_lookup(a["ticker"])
        if not data:
            continue
        current = data.get("price") if a["kind"] == "price" else data.get("rsi")
        if current is None:
            continue
        a["last_val"] = float(current)
        trig = (a["op"] == ">" and current > a["value"]) or \
               (a["op"] == "<" and current < a["value"])
        if trig:
            a["triggered"] = True
            a["triggered_at"] = datetime.datetime.now().isoformat()
            newly_triggered.append(a)
    save_alerts(alerts)
    return newly_triggered

# 3. TRADE JOURNAL — CSV persistent
JOURNAL_COLS = ["Date", "Ticker", "Side", "Qty", "Entry", "Exit",
                "P&L (₹)", "P&L %", "Strategy", "Notes"]

def load_journal() -> pd.DataFrame:
    if JOURNAL_FILE.exists():
        try:
            df = pd.read_csv(JOURNAL_FILE, encoding="utf-8")
            for c in JOURNAL_COLS:
                if c not in df.columns:
                    df[c] = ""
            return df[JOURNAL_COLS]
        except Exception:
            pass
    return pd.DataFrame(columns=JOURNAL_COLS)

def save_journal(df: pd.DataFrame):
    df.to_csv(JOURNAL_FILE, index=False, encoding="utf-8")
