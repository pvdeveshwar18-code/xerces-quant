import datetime
from typing import Tuple, Optional, List, Dict, Any
import pandas as pd
import xerces_plus as xp
from utils.db import get_audit_entries, DEFAULT_DB_PATH

def sync_audit_to_journal(
    journal_df: Optional[pd.DataFrame] = None,
    limit: int = 500,
    db_path: str = DEFAULT_DB_PATH
) -> Tuple[pd.DataFrame, int]:
    """
    Sync executed orders from the SQLite execution audit log into the Trade Journal DataFrame.
    Avoids duplicate entries by checking order IDs against existing 'Notes'.
    Returns (updated_df, count_new_entries).
    """
    if journal_df is None or journal_df.empty:
        _j = xp.load_journal()
    else:
        _j = journal_df.copy()

    audit_entries = get_audit_entries(limit=limit, db_path=db_path)
    if not audit_entries:
        return _j, 0

    existing_notes = set(_j["Notes"].astype(str).tolist()) if not _j.empty and "Notes" in _j.columns else set()
    new_rows = []

    for entry in audit_entries:
        req = entry.get("request", {})
        resp = entry.get("response", {})
        order_id = resp.get("order_id", "")
        if order_id and any(str(order_id) in n for n in existing_notes):
            continue

        ts = entry.get("timestamp", 0)
        dt_str = datetime.datetime.fromtimestamp(ts).strftime("%Y-%m-%d") if ts else str(datetime.date.today())
        symbol = str(req.get("symbol", "")).replace(".NS", "").replace(".BO", "").upper()
        if not symbol:
            continue

        side = "LONG" if str(req.get("transaction_type", "BUY")).upper() == "BUY" else "SHORT"
        try:
            qty = int(req.get("quantity", 1) or 1)
        except (ValueError, TypeError):
            qty = 1

        try:
            px = float(req.get("price", 0.0) or 0.0)
        except (ValueError, TypeError):
            px = 0.0

        broker = req.get("broker_name", "Broker")
        is_paper = bool(entry.get("paper_mode", False))
        note_str = f"Order {order_id} via {broker} ({'Paper' if is_paper else 'Live'})"

        new_rows.append({
            "Date": dt_str,
            "Ticker": symbol,
            "Side": side,
            "Qty": qty,
            "Entry": px,
            "Exit": 0.0,
            "P&L (₹)": 0.0,
            "P&L %": 0.0,
            "Strategy": "Execution Audit",
            "Notes": note_str
        })
        existing_notes.add(note_str)

    if new_rows:
        _j = pd.concat([_j, pd.DataFrame(new_rows)], ignore_index=True)
        return _j, len(new_rows)
    return _j, 0
