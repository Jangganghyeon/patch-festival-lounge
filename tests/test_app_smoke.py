from __future__ import annotations

from pathlib import Path

from cryptography.fernet import Fernet
from streamlit.testing.v1 import AppTest

from lounge.config import RuntimeConfig
from lounge.database import Participant, create_db
from lounge.service import LoungeService


def test_all_public_routes_render_without_exception(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'ui.db'}")
    monkeypatch.setenv("FIELD_ENCRYPTION_KEY", Fernet.generate_key().decode("ascii"))
    monkeypatch.setenv("INITIAL_SETUP_CODE", "SETUP123")

    cases = [
        ("home", "입장 등록"),
        ("kiosk", "게임 라운지 입장 등록"),
        ("board", "현재 포인트 순위"),
        ("admin", "운영자 콘솔"),
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
    assert len(app.checkbox) == 0
    app.button[0].click().run(timeout=20)

    assert len(app.exception) == 0
    assert any("ADMISSION COMPLETE" in element.value for element in app.markdown)


def test_board_renders_podium_without_traffic_widgets(tmp_path, monkeypatch):
    database_url = f"sqlite:///{tmp_path / 'board.db'}"
    encryption_key = Fernet.generate_key().decode("ascii")
    monkeypatch.setenv("DATABASE_URL", database_url)
    monkeypatch.setenv("FIELD_ENCRYPTION_KEY", encryption_key)
    monkeypatch.setenv("INITIAL_SETUP_CODE", "SETUP123")
    config = RuntimeConfig(
        database_url=database_url,
        field_encryption_key=encryption_key,
        initial_setup_code="SETUP123",
    )
    _engine, factory = create_db(config)
    service = LoungeService(factory, config)
    participant = service.check_in(
        name="홍길동",
        age=17,
        phone="010-1234-5678",
        category="general",
        privacy_consent=True,
        leaderboard_opt_in=True,
    )
    service.adjust_points(participant.participant_id, 70, "테스트", "", "operator")
    with service.sessions.begin() as session:
        session.get(Participant, participant.participant_id).display_code = "YQNRV2"

    app = AppTest.from_file(Path(__file__).resolve().parents[1] / "app.py")
    app.query_params["view"] = "board"
    app.run(timeout=20)
    rendered = "\n".join(element.value for element in app.markdown)
    assert len(app.exception) == 0
    assert "TOP 3 · LIVE RANKING" in rendered
    migrated_code = service.get_participant(participant.participant_id)["code"]
    assert len(migrated_code) == 2
    assert migrated_code in rendered
    assert "YQNRV2" not in rendered
    assert "입장 흐름" not in rendered
    assert "최근 입장" not in rendered


def test_admin_chip_panel_renders_without_duplicate_streamlit_inputs(tmp_path, monkeypatch):
    database_url = f"sqlite:///{tmp_path / 'admin.db'}"
    encryption_key = Fernet.generate_key().decode("ascii")
    monkeypatch.setenv("DATABASE_URL", database_url)
    monkeypatch.setenv("FIELD_ENCRYPTION_KEY", encryption_key)
    monkeypatch.setenv("INITIAL_SETUP_CODE", "SETUP123")
    config = RuntimeConfig(
        database_url=database_url,
        field_encryption_key=encryption_key,
        initial_setup_code="SETUP123",
    )
    create_db(config)

    app = AppTest.from_file(Path(__file__).resolve().parents[1] / "app.py")
    app.query_params["view"] = "admin"
    app.query_params["panel"] = "chips"
    app.run(timeout=20)
    assert len(app.exception) == 0
    rendered = "\n".join(element.value for element in app.markdown)
    assert "전산 칩 관리" in rendered
    assert len(app.text_input) == 0
