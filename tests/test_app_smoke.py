from __future__ import annotations

from pathlib import Path

import pytest
from cryptography.fernet import Fernet
from streamlit.testing.v1 import AppTest

from lounge.config import RuntimeConfig
from lounge.database import Participant, create_db
from lounge.service import LoungeService


@pytest.fixture(autouse=True)
def operator_password(monkeypatch):
    monkeypatch.setenv("OPERATOR_PASSWORD", "test-operator-password")
    monkeypatch.setenv("ANALYTICS_PASSWORD", "test-analytics-password")


def test_all_public_routes_render_without_exception(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'ui.db'}")
    monkeypatch.setenv("FIELD_ENCRYPTION_KEY", Fernet.generate_key().decode("ascii"))

    cases = [
        ("home", "입장 등록"),
        ("kiosk", "게임 라운지 입장 등록"),
        ("checkout", "퇴장 처리"),
        ("board", "현재 포인트 순위"),
        ("admin", "운영자 콘솔"),
        ("analytics", "운영자 콘솔"),
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

    app = AppTest.from_file(Path(__file__).resolve().parents[1] / "app.py")
    app.query_params["view"] = "kiosk"
    app.run(timeout=20)
    assert len(app.get("link_button")) == 0
    kiosk_markup = "\n".join(element.value for element in app.markdown)
    assert "01 · GUEST PROFILE" in kiosk_markup
    assert "02 · FESTIVAL ACCESS" in kiosk_markup
    app.text_input[0].input("홍길동")
    app.text_input[1].input("010-1234-5678")
    assert len(app.checkbox) == 0
    app.button[0].click().run(timeout=20)

    assert len(app.exception) == 0
    assert any("ADMISSION COMPLETE" in element.value for element in app.markdown)
    assert len(app.get("link_button")) == 0


def test_board_renders_podium_without_traffic_widgets(tmp_path, monkeypatch):
    database_url = f"sqlite:///{tmp_path / 'board.db'}"
    encryption_key = Fernet.generate_key().decode("ascii")
    monkeypatch.setenv("DATABASE_URL", database_url)
    monkeypatch.setenv("FIELD_ENCRYPTION_KEY", encryption_key)
    config = RuntimeConfig(
        database_url=database_url,
        field_encryption_key=encryption_key,
        operator_password="test-operator-password",
        analytics_password="test-analytics-password",
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
    app.query_params["category"] = "general"
    app.run(timeout=20)
    rendered = "\n".join(element.value for element in app.markdown)
    assert len(app.exception) == 0
    assert '<span>TOP 3</span> · GENERAL LIVE RANKING' in rendered
    assert 'class="winner-crown"' in rendered
    assert 'class="podium-sparkle sparkle-1"' in rendered
    assert "class='ranking-heading'" in rendered
    migrated_code = service.get_participant(participant.participant_id)["code"]
    assert len(migrated_code) == 2
    assert migrated_code in rendered
    assert "YQNRV2" not in rendered
    assert "입장 흐름" not in rendered
    assert "최근 입장" not in rendered


def test_home_has_separate_vip_and_general_boards(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'home.db'}")
    monkeypatch.setenv("FIELD_ENCRYPTION_KEY", Fernet.generate_key().decode("ascii"))

    app = AppTest.from_file(Path(__file__).resolve().parents[1] / "app.py")
    app.query_params["view"] = "home"
    app.run(timeout=20)
    rendered = "\n".join(element.value for element in app.markdown)
    assert "VIP 라이브 보드" in rendered
    assert "일반 라이브 보드" in rendered
    assert "퇴장 처리" in rendered
    assert "checkout-mode-card" not in rendered


def test_admin_requires_only_shared_password(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'gate.db'}")
    monkeypatch.setenv("FIELD_ENCRYPTION_KEY", Fernet.generate_key().decode("ascii"))

    app = AppTest.from_file(Path(__file__).resolve().parents[1] / "app.py")
    app.query_params["view"] = "admin"
    app.run(timeout=20)
    assert len(app.text_input) == 1
    assert app.text_input[0].label == "운영자 비밀번호"

    app.text_input[0].input("test-operator-password")
    app.button[0].click().run(timeout=20)
    assert len(app.exception) == 0
    rendered = "\n".join(element.value for element in app.markdown)
    assert "전산 칩 관리" in rendered
    assert len(app.text_input) == 0
    assert "화면 표시 초기화" in rendered
    assert len(app.get("link_button")) == 0


def test_admin_internal_navigation_keeps_auth_and_has_back_button(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'admin-navigation.db'}")
    monkeypatch.setenv("FIELD_ENCRYPTION_KEY", Fernet.generate_key().decode("ascii"))

    app = AppTest.from_file(Path(__file__).resolve().parents[1] / "app.py")
    app.query_params["view"] = "admin"
    app.session_state["operator_authenticated"] = True
    app.run(timeout=20)

    next(button for button in app.button if button.label == "초기화 기능 열기").click().run(
        timeout=20
    )
    assert app.query_params["panel"] == ["reset"]
    assert not any(field.label == "운영자 비밀번호" for field in app.text_input)
    assert any(button.label == "← 운영자 메뉴로 돌아가기" for button in app.button)

    next(button for button in app.button if button.label == "← 운영자 메뉴로 돌아가기").click().run(
        timeout=20
    )
    rendered = "\n".join(element.value for element in app.markdown)
    assert "화면 표시 초기화" in rendered
    assert "panel" not in app.query_params


def test_checkout_requires_name_phone_and_id_before_confirmation(tmp_path, monkeypatch):
    database_url = f"sqlite:///{tmp_path / 'checkout.db'}"
    encryption_key = Fernet.generate_key().decode("ascii")
    monkeypatch.setenv("DATABASE_URL", database_url)
    monkeypatch.setenv("FIELD_ENCRYPTION_KEY", encryption_key)
    config = RuntimeConfig(
        database_url=database_url,
        field_encryption_key=encryption_key,
        operator_password="test-operator-password",
        analytics_password="test-analytics-password",
    )
    _engine, factory = create_db(config)
    service = LoungeService(factory, config)
    participant = service.check_in(
        name="퇴장손님",
        age=17,
        phone="010-7777-7777",
        category="general",
        privacy_consent=True,
        leaderboard_opt_in=True,
    )

    app = AppTest.from_file(Path(__file__).resolve().parents[1] / "app.py")
    app.query_params["view"] = "checkout"
    app.run(timeout=20)
    rendered = "\n".join(element.value for element in app.markdown)
    assert "EXIT ONLY · 퇴장 전용 화면" in rendered
    next(field for field in app.text_input if field.label == "이름").input("퇴장손님")
    next(field for field in app.text_input if field.label == "전화번호").input("010-7777-7777")
    next(field for field in app.text_input if field.label == "참가자 ID").input(
        participant.display_code
    )
    next(button for button in app.button if button.label == "입장 정보 확인").click().run(
        timeout=20
    )
    rendered = "\n".join(element.value for element in app.markdown)
    assert "퇴장손님" in rendered
    next(button for button in app.button if button.label == "위 참가자를 퇴장 처리").click().run(
        timeout=20
    )
    assert service.get_participant(participant.participant_id)["status"] == "exited"


def test_analytics_requires_a_separate_password(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'analytics.db'}")
    monkeypatch.setenv("FIELD_ENCRYPTION_KEY", Fernet.generate_key().decode("ascii"))

    app = AppTest.from_file(Path(__file__).resolve().parents[1] / "app.py")
    app.query_params["view"] = "analytics"
    app.run(timeout=20)
    assert len(app.text_input) == 1
    assert app.text_input[0].label == "운영자 비밀번호"
    app.text_input[0].input("test-operator-password")
    next(button for button in app.button if button.label == "운영자 콘솔 열기").click().run(
        timeout=20
    )
    assert len(app.text_input) == 1
    assert app.text_input[0].label == "영업 분석 비밀번호"
    app.text_input[0].input("test-analytics-password")
    next(button for button in app.button if button.label == "영업 분석 열기").click().run(
        timeout=20
    )
    rendered = "\n".join(element.value for element in app.markdown)
    assert "시간대별 방문자 수" in rendered
    assert "오늘 방문자별 입퇴장 정보" in rendered
    assert any(button.label == "← 운영자 메뉴로 돌아가기" for button in app.button)


def test_admin_chip_panel_renders_without_duplicate_streamlit_inputs(tmp_path, monkeypatch):
    database_url = f"sqlite:///{tmp_path / 'admin.db'}"
    encryption_key = Fernet.generate_key().decode("ascii")
    monkeypatch.setenv("DATABASE_URL", database_url)
    monkeypatch.setenv("FIELD_ENCRYPTION_KEY", encryption_key)
    config = RuntimeConfig(
        database_url=database_url,
        field_encryption_key=encryption_key,
        operator_password="test-operator-password",
        analytics_password="test-analytics-password",
    )
    create_db(config)
    from lounge import views

    monkeypatch.setattr(views, "quick_point_input", lambda *, key: None)

    app = AppTest.from_file(Path(__file__).resolve().parents[1] / "app.py")
    app.query_params["view"] = "admin"
    app.query_params["panel"] = "chips"
    app.session_state["operator_authenticated"] = True
    app.run(timeout=20)
    assert len(app.exception) == 0
    rendered = "\n".join(element.value for element in app.markdown)
    assert "전산 칩 관리" in rendered
    assert len(app.text_input) == 0
