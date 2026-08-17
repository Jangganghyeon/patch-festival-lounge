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
        operator_password="test-operator-password",
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
    service.adjust_points(participant.participant_id, 580, "시작 테스트", "", "operator")
    recorded = service.quick_adjust_points(
        f"300{participant.display_code.lower()}140", "operator"
    )
    assert recorded.spent == 300
    assert recorded.earned == 140
    assert recorded.delta == -160
    assert recorded.balance == 420


def test_quick_point_command_records_zero_net_change(service: LoungeService):
    participant = check_in(service)
    recorded = service.quick_adjust_points(f"50{participant.display_code}50", "operator")
    assert recorded.delta == 0
    assert recorded.balance == 0


def test_quick_point_command_cannot_make_balance_negative(service: LoungeService):
    participant = check_in(service)
    with pytest.raises(ValueError, match="보유 칩이 부족"):
        service.quick_adjust_points(f"300{participant.display_code}140", "operator")


def test_quick_point_command_rejects_invalid_input(service: LoungeService):
    with pytest.raises(ValueError, match="300RT140"):
        service.quick_adjust_points("잘못된 입력", "operator")

    with pytest.raises(ValueError, match="두 글자 ID"):
        service.quick_adjust_points("77H1230", "operator")


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


def test_vip_and_general_leaderboards_are_separate(service: LoungeService):
    general = check_in(service, phone="010-3333-3333", name="일반손님")
    vip = check_in(service, phone="010-4444-4444", name="우대손님", category="vip")
    service.adjust_points(general.participant_id, 100, "게임", "", "op")
    service.adjust_points(vip.participant_id, 200, "게임", "", "op")

    assert [row["code"] for row in service.leaderboard("general")] == [general.display_code]
    assert [row["code"] for row in service.leaderboard("vip")] == [vip.display_code]


def test_export_is_utf8_bom_csv(service: LoungeService):
    check_in(service)
    payload = service.export_participants_csv()
    assert payload.startswith(b"\xef\xbb\xbf")
    assert "홍길동" in payload.decode("utf-8-sig")


def test_operator_uses_only_shared_password(service: LoungeService):
    assert service.verify_operator_password("test-operator-password") is True
    assert service.verify_operator_password("wrong") is False
