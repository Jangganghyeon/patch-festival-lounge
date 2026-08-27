from __future__ import annotations

from pathlib import Path
from typing import Any

import streamlit.components.v1 as components

FRONTEND_DIR = Path(__file__).with_name("quick_input_frontend")

_quick_point_input = components.declare_component(
    "patch_quick_point_input",
    path=str(FRONTEND_DIR),
)


def quick_point_input(*, key: str) -> dict[str, Any] | None:
    value = _quick_point_input(key=key, default=None)
    return value if isinstance(value, dict) else None
