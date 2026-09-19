import os
from pathlib import Path
from typing import Dict

# Path to the .env file at the project root
ENV_FILE = Path(__file__).resolve().parents[2] / ".env"

def load_credentials() -> Dict[str, str]:
    """Load Kotak Neo credentials from .env if present.
    Returns a dict with keys: consumer_key, mobile_number, client_code.
    Missing values default to empty strings.
    """
    creds = {"consumer_key": "", "mobile_number": "", "client_code": ""}
    if ENV_FILE.is_file():
        for line in ENV_FILE.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" not in line:
                continue
            key, val = line.split("=", 1)
            key, val = key.strip(), val.strip()
            if key == "KOTAK_CONSUMER_KEY":
                creds["consumer_key"] = val
            elif key == "KOTAK_MOBILE_NUMBER":
                creds["mobile_number"] = val
            elif key == "KOTAK_CLIENT_CODE":
                creds["client_code"] = val
    return creds

def save_credentials(consumer_key: str, mobile_number: str, client_code: str) -> None:
    """Write the provided credentials to .env (overwrites the file)."""
    lines = []
    if consumer_key:
        lines.append(f"KOTAK_CONSUMER_KEY={consumer_key}")
    if mobile_number:
        lines.append(f"KOTAK_MOBILE_NUMBER={mobile_number}")
    if client_code:
        lines.append(f"KOTAK_CLIENT_CODE={client_code}")
    # Ensure directory exists
    ENV_FILE.parent.mkdir(parents=True, exist_ok=True)
    ENV_FILE.write_text("\n".join(lines) + "\n")

def get_kotak_credentials() -> Dict[str, str]:
    """Convenient wrapper returning the dict format expected by KotakNeoAdapter."""
    return load_credentials()
