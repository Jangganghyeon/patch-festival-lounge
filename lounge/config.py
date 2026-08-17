from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"


def _streamlit_secret(name: str) -> Any | None:
    """Read a Streamlit secret without making non-Streamlit tools depend on it."""
    try:
        import streamlit as st

        return st.secrets.get(name)
    except Exception:
        return None


def get_setting(name: str, default: str | None = None) -> str | None:
    value = os.getenv(name)
    if value not in (None, ""):
        return value
    secret = _streamlit_secret(name)
    if secret not in (None, ""):
        return str(secret)
    return default


@dataclass(frozen=True)
class RuntimeConfig:
    database_url: str
    field_encryption_key: str
    timezone: str = "Asia/Seoul"


def _load_or_create_local_key() -> str:
    from cryptography.fernet import Fernet

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    key_path = DATA_DIR / ".field.key"
    if key_path.exists():
        return key_path.read_text(encoding="utf-8").strip()
    key = Fernet.generate_key().decode("ascii")
    key_path.write_text(key, encoding="utf-8")
    try:
        key_path.chmod(0o600)
    except OSError:
        pass
    return key


def load_config(database_url: str | None = None) -> RuntimeConfig:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    resolved_url = database_url or get_setting(
        "DATABASE_URL", f"sqlite:///{(DATA_DIR / 'lounge.db').as_posix()}"
    )
    encryption_key = get_setting("FIELD_ENCRYPTION_KEY") or _load_or_create_local_key()
    return RuntimeConfig(
        database_url=str(resolved_url),
        field_encryption_key=encryption_key,
        timezone=get_setting("APP_TIMEZONE", "Asia/Seoul") or "Asia/Seoul",
    )
