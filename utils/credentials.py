import os
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

# Resolve project root (assumes this file is located at <repo_root>/utils)
PROJECT_ROOT = Path(__file__).resolve().parents[1]
ENV_PATH = PROJECT_ROOT / '.env'
if ENV_PATH.exists():
    load_dotenv(dotenv_path=ENV_PATH)

def get_env_var(key: str, default: Optional[str] = None) -> str:
    """Fetch an environment variable.
    Raises an informative error if the variable is missing and no default is provided.
    """
    value = os.getenv(key, default)
    if value is None:
        raise EnvironmentError(f"Required environment variable '{key}' is not set.")
    return value

def get_kotak_credentials() -> tuple[str, str]:
    """Return the Kotak Neo API key and secret from environment variables.

    Expected environment variables:
        - KOTAK_API_KEY
        - KOTAK_API_SECRET
    """
    api_key = get_env_var('KOTAK_API_KEY')
    api_secret = get_env_var('KOTAK_API_SECRET')
    return api_key, api_secret
