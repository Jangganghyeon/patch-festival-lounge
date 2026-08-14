from __future__ import annotations

import logging

import streamlit as st

from lounge.config import load_config
from lounge.database import create_db
from lounge.service import LoungeService
from lounge.styles import GLOBAL_CSS
from lounge.views import footer, render_admin, render_board, render_home, render_kiosk

st.set_page_config(
    page_title="PATCH Festival Lounge",
    page_icon="✦",
    layout="wide",
    initial_sidebar_state="collapsed",
    menu_items={
        "About": "PATCH 소프트웨어 개발반 학교 축제 운영 시스템",
    },
)
st.markdown(GLOBAL_CSS, unsafe_allow_html=True)


@st.cache_resource
def get_service() -> LoungeService:
    config = load_config()
    _engine, session_factory = create_db(config)
    return LoungeService(session_factory, config)


service = get_service()
view = str(st.query_params.get("view", "home")).lower()

try:
    if view == "kiosk":
        render_kiosk(service)
    elif view == "board":
        render_board(service)
    elif view == "admin":
        render_admin(service)
    else:
        render_home(service)
except Exception:
    logging.exception("Unhandled application error")
    st.error("화면을 불러오는 중 문제가 발생했습니다. 운영자에게 알려 주세요.")
    footer()
