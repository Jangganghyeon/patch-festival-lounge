from __future__ import annotations

import pytest
from cryptography.fernet import Fernet

from lounge.config import RuntimeConfig
from lounge.database import Participant, create_db
from lounge.service import LoungeService


@pytest.fixture()
def service(tmp_path):
    config = RuntimeConfig(
        database_url=f"sqlite:///{tmp_path / 'test.db'}",
        field_encryption_key=Fernet.generate_key().decode("ascii"),
        initial_setup_code="SETUP123",
    )
    _engine, factory = create_db(config)
    return LoungeService(factory, config)


def check_in(service: LoungeService, phone: str = "010-1234-5678", **overrides):
    values = {
        "name": "홍길동",
        "age": 17,
        "phone": phone,
        "category": "general",
        "privacy_consent": True,
        "leaderboard_opt_in": False,
    }
    values.update(overrides)
    return service.check_in(**values)


def test_full_visit_flow(service: LoungeService):
    result = check_in(service)
    assert len(result.display_code) == 2
    assert result.display_code.isalpha()
    assert result.display_code.isupper()
    assert result.starting_points == 0

    balance = service.adjust_points(result.participant_id, 50, "테이블 A", "승인", "operator")
    assert balance == 50
    balance = service.adjust_points(result.participant_id, -20, "테이블 B", "승인", "operator")
    assert balance == 30

    service.check_out(result.participant_id, 27, "상품 교환", "operator")
    participant = service.get_participant(result.participant_id)
    assert participant["status"] == "exited"
    assert participant["final_points"] == 27


def test_two_letter_codes_are_unique(service: LoungeService):
    codes = {
        check_in(service, phone=f"010-1000-{index:04d}", name=f"참가자{index}").display_code
        for index in range(50)
    }
    assert len(codes) == 50
    assert all(len(code) == 2 and code.isalpha() and code.isupper() for code in codes)


def test_quick_point_command_is_case_insensitive(service: LoungeService):
    participant = check_in(service)
    added = service.quick_adjust_points(f"{participant.display_code.lower()}70", "operator")
    assert added.delta == 70
    assert added.balance == 70
    corrected = service.quick_adjust_points(f"{participant.display_code}-20", "operator")
    assert corrected.delta == -20
    assert corrected.balance == 50


def test_quick_point_command_rejects_invalid_input(service: LoungeService):
    with pytest.raises(ValueError, match="RT70"):
        service.quick_adjust_points("잘못된 입력", "operator")


def test_legacy_codes_are_migrated_to_two_letters(service: LoungeService):
    participant = check_in(service)
    with service.sessions.begin() as session:
        row = session.get(Participant, participant.participant_id)
        row.display_code = "ABC123"

    _engine, factory = create_db(service.config)
    migrated = LoungeService(factory, service.config).get_participant(participant.participant_id)
    assert len(migrated["code"]) == 2
    assert migrated["code"].isalpha()
    assert migrated["code"].isupper()


def test_duplicate_active_phone_is_blocked(service: LoungeService):
    check_in(service)
    with pytest.raises(ValueError, match="이미 입장"):
        check_in(service, name="다른 이름")


def test_same_phone_can_reenter_after_checkout(service: LoungeService):
    first = check_in(service)
    service.check_out(first.participant_id, 0, "", "operator")
    second = check_in(service)
    assert second.participant_id != first.participant_id


def test_points_cannot_be_negative(service: LoungeService):
    result = check_in(service)
    with pytest.raises(ValueError, match="많이 차감"):
        service.adjust_points(result.participant_id, -1, "정정", "", "operator")


def test_phone_is_masked_by_default(service: LoungeService):
    result = check_in(service)
    masked = service.get_participant(result.participant_id)
    revealed = service.get_participant(result.participant_id, reveal_phone=True)
    assert masked["phone"] == "010-****-5678"
    assert revealed["phone"] == "01012345678"


def test_leaderboard_respects_name_opt_in(service: LoungeService):
    hidden = check_in(service, phone="010-1111-1111", name="홍길동", leaderboard_opt_in=False)
    shown = check_in(service, phone="010-2222-2222", name="김하늘", leaderboard_opt_in=True)
    service.adjust_points(hidden.participant_id, 20, "미니게임", "", "op")
    service.adjust_points(shown.participant_id, 10, "미니게임", "", "op")
    names = [row["name"] for row in service.dashboard()["leaderboard"]]
    assert "홍*동" in names
    assert "김하늘" in names


def test_export_is_utf8_bom_csv(service: LoungeService):
    check_in(service)
    payload = service.export_participants_csv()
    assert payload.startswith(b"\xef\xbb\xbf")
    assert "홍길동" in payload.decode("utf-8-sig")


def test_admin_password(service: LoungeService):
    service.create_first_admin("patch_admin", "safe-password-123", "SETUP123")
    assert service.authenticate("patch_admin", "safe-password-123") == (True, "admin")
    assert service.authenticate("patch_admin", "wrong") == (False, "")


def test_admin_setup_code_is_required(service: LoungeService):
    with pytest.raises(ValueError, match="설정 코드"):
        service.create_first_admin("patch_admin", "safe-password-123", "WRONG")
