import sqlite3
import json
import os
from typing import List, Dict, Any
from pathlib import Path

def _resolve_db_path() -> str:
    env_dir = os.environ.get("XERCES_DATA_DIR")
    if env_dir:
        p = Path(env_dir)
        p.mkdir(parents=True, exist_ok=True)
        return str(p / "audit_log.db")
    project_root = Path(__file__).resolve().parent.parent
    data_dir = project_root / "data"
    if data_dir.is_dir():
        return str(data_dir / "audit_log.db")
    return str(project_root / "audit_log.db")

DEFAULT_DB_PATH = _resolve_db_path()


def _connect(db_path: str = DEFAULT_DB_PATH) -> sqlite3.Connection:
    """Return a SQLite connection with a Row factory for dict-like access."""
    conn = sqlite3.connect(db_path, detect_types=sqlite3.PARSE_DECLTYPES)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: str = DEFAULT_DB_PATH) -> None:
    """Create audit_log table if it does not already exist."""
    conn = _connect(db_path)
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp REAL NOT NULL,
                paper_mode INTEGER NOT NULL,
                request_json TEXT NOT NULL,
                response_json TEXT NOT NULL
            );
            """
        )
        conn.commit()
    finally:
        conn.close()


def _sanitize_data(obj: Any) -> Any:
    """Recursively mask sensitive keys in nested dicts/lists before JSON serialization."""
    if isinstance(obj, dict):
        clean = {}
        for k, v in obj.items():
            k_lower = str(k).lower()
            if any(secret in k_lower for secret in ["secret", "token", "password", "key", "mobile"]):
                if v:
                    s_v = str(v)
                    clean[k] = f"***{s_v[-4:]}" if len(s_v) > 4 else "***"
                else:
                    clean[k] = ""
            else:
                clean[k] = _sanitize_data(v)
        return clean
    elif isinstance(obj, list):
        return [_sanitize_data(item) for item in obj]
    return obj


def add_audit_entry(entry: Dict[str, Any], db_path: str = DEFAULT_DB_PATH) -> None:
    """Insert a single audit entry with automatic schema creation and sanitized payload."""
    conn = _connect(db_path)
    try:
        req = _sanitize_data(entry.get("request", {}))
        resp = _sanitize_data(entry.get("response", {}))
        conn.execute(
            "INSERT INTO audit_log (timestamp, paper_mode, request_json, response_json) VALUES (?, ?, ?, ?)",
            (
                entry.get("timestamp"),
                1 if entry.get("paper_mode") else 0,
                json.dumps(req),
                json.dumps(resp),
            ),
        )
        conn.commit()
    except sqlite3.OperationalError:
        init_db(db_path)
        conn.execute(
            "INSERT INTO audit_log (timestamp, paper_mode, request_json, response_json) VALUES (?, ?, ?, ?)",
            (
                entry.get("timestamp"),
                1 if entry.get("paper_mode") else 0,
                json.dumps(req),
                json.dumps(resp),
            ),
        )
        conn.commit()
    finally:
        conn.close()


def get_audit_entries(limit: int = 1000, db_path: str = DEFAULT_DB_PATH) -> List[Dict[str, Any]]:
    """Fetch the most recent limit rows, ordered by timestamp descending."""
    try:
        conn = _connect(db_path)
        rows = conn.execute(
            "SELECT timestamp, paper_mode, request_json, response_json FROM audit_log ORDER BY timestamp DESC LIMIT ?",
            (limit,),
        ).fetchall()
        result: List[Dict[str, Any]] = []
        for row in rows:
            result.append(
                {
                    "timestamp": row["timestamp"],
                    "paper_mode": bool(row["paper_mode"]),
                    "request": json.loads(row["request_json"]),
                    "response": json.loads(row["response_json"]),
                }
            )
        conn.close()
        return result
    except sqlite3.OperationalError:
        init_db(db_path)
        return []
