"""
SQLite Local Database Storage Engine for Xerces.
Persists broker credentials, watchlists, trade journal records, and settings permanently.
"""

import sqlite3
import os
import json
from pathlib import Path

def _resolve_data_dir() -> Path:
    """Pick a writable data directory without tying the app to one machine."""
    env_dir = os.environ.get("XERCES_DATA_DIR")
    candidates = [
        Path(env_dir) if env_dir else None,
        Path(__file__).resolve().parent,
        Path.cwd() / "data",
    ]
    for candidate in candidates:
        if candidate is None:
            continue
        try:
            candidate.mkdir(parents=True, exist_ok=True)
            return candidate
        except Exception:
            continue

    import tempfile
    fallback = Path(tempfile.gettempdir()) / "xerces_data"
    fallback.mkdir(parents=True, exist_ok=True)
    return fallback

DB_PATH = _resolve_data_dir() / "xerces.db"

def init_db():
    """Initialize SQLite database schema."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 1. Credentials Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS broker_credentials (
        broker_name TEXT PRIMARY KEY,
        credentials_json TEXT,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    
    # 2. Watchlist Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS watchlist (
        ticker TEXT PRIMARY KEY,
        name TEXT,
        market TEXT,
        target_entry REAL,
        added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    
    # 3. Trade Journal Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS trade_journal (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT,
        ticker TEXT,
        action TEXT,
        quantity INTEGER,
        entry_price REAL,
        exit_price REAL,
        pnl REAL,
        notes TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    
    conn.commit()
    conn.close()

# Initialize DB schema on import
init_db()

def save_broker_credentials(broker_name: str, creds_dict: dict):
    """Save or update broker credentials in SQLite."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT OR REPLACE INTO broker_credentials (broker_name, credentials_json) VALUES (?, ?)",
        (broker_name, json.dumps(creds_dict))
    )
    conn.commit()
    conn.close()

def load_broker_credentials(broker_name: str) -> dict:
    """Load broker credentials from SQLite."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT credentials_json FROM broker_credentials WHERE broker_name = ?", (broker_name,))
    row = cursor.fetchone()
    conn.close()
    if row and row[0]:
        try:
            return json.loads(row[0])
        except Exception:
            return {}
    return {}

def save_journal_entry(date: str, ticker: str, action: str, quantity: int, entry_price: float, exit_price: float = 0.0, notes: str = ""):
    """Save trade journal entry."""
    pnl = (exit_price - entry_price) * quantity if exit_price > 0 and action == "BUY" else (entry_price - exit_price) * quantity if exit_price > 0 else 0.0
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO trade_journal (date, ticker, action, quantity, entry_price, exit_price, pnl, notes) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (date, ticker, action, quantity, entry_price, exit_price, pnl, notes)
    )
    conn.commit()
    conn.close()

def get_journal_entries() -> list:
    """Get all trade journal entries as list of dicts."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM trade_journal ORDER BY id DESC")
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]
