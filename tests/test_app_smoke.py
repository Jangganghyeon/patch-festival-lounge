from __future__ import annotations

from pathlib import Path

from cryptography.fernet import Fernet
from streamlit.testing.v1 import AppTest


def test_all_public_routes_render_without_exception(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'ui.db'}")
    monkeypatch.setenv("FIELD_ENCRYPTION_KEY", Fernet.generate_key().decode("ascii"))
    monkeypatch.setenv("INITIAL_SETUP_CODE", "SETUP123")

    cases = [
        ("home", "입장 등록"),
        ("kiosk", "게임 라운지 입장 등록"),
        ("board", "현재 포인트 순위"),
        ("admin", "최초 관리자 등록"),
    ]
    for view, expected in cases:
        app = AppTest.from_file(Path(__file__).resolve().parents[1] / "app.py")
        app.query_params["view"] = view
        app.run(timeout=20)
        assert len(app.exception) == 0
        rendered = "\n".join(
            (getattr(element, "value", "") or "")
            for element in list(app.markdown) + list(app.title) + list(app.header) + list(app.subheader)
        )
        assert expected in rendered


def test_kiosk_submit_shows_admission_ticket(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'kiosk.db'}")
    monkeypatch.setenv("FIELD_ENCRYPTION_KEY", Fernet.generate_key().decode("ascii"))
    monkeypatch.setenv("INITIAL_SETUP_CODE", "SETUP123")

    app = AppTest.from_file(Path(__file__).resolve().parents[1] / "app.py")
    app.query_params["view"] = "kiosk"
    app.run(timeout=20)
    app.text_input[0].input("홍길동")
    app.text_input[1].input("010-1234-5678")
    app.checkbox[0].check()
    app.button[0].click().run(timeout=20)

    assert len(app.exception) == 0
    assert any("ADMISSION COMPLETE" in element.value for element in app.markdown)
