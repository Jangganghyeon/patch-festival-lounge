from __future__ import annotations

import sqlite3
from datetime import datetime

import pytest
from cryptography.fernet import Fernet

from lounge.config import RuntimeConfig
from lounge.database import (
    AuditLog,
    Participant,
    ParticipantIdentity,
    PointTransaction,
    create_db,
)
from lounge.service import LoungeService


@pytest.fixture()
def service(tmp_path):
    config = RuntimeConfig(
        database_url=f"sqlite:///{tmp_path / 'test.db'}",
        field_encryption_key=Fernet.generate_key().decode("ascii"),
        operator_password="test-operator-password",
        analytics_password="test-analytics-password",
        reset_password="test-reset-password",
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


def test_existing_database_migrates_historical_codes_to_permanent_identities(tmp_path):
    database_path = tmp_path / "legacy.db"
    connection = sqlite3.connect(database_path)
    connection.executescript(
        """
        CREATE TABLE participants (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            display_code VARCHAR(8) NOT NULL UNIQUE,
            name VARCHAR(40) NOT NULL,
            age INTEGER NOT NULL,
            phone_encrypted TEXT NOT NULL,
            phone_hash VARCHAR(64) NOT NULL,
            phone_last4 VARCHAR(4) NOT NULL,
            category VARCHAR(12) NOT NULL,
            status VARCHAR(12) NOT NULL,
            current_points INTEGER NOT NULL,
            final_points INTEGER,
            leaderboard_opt_in BOOLEAN NOT NULL,
            privacy_consent BOOLEAN NOT NULL,
            checked_in_at DATETIME NOT NULL,
            checked_out_at DATETIME,
            exit_note VARCHAR(200) NOT NULL
        );
        INSERT INTO participants VALUES
            (1, 'AA', '입장중', 17, 'unused', 'hash1', '0001', 'general', 'active',
             0, NULL, 1, 1, '2026-08-17 00:00:00', NULL, ''),
            (2, 'BB', '퇴장함', 17, 'unused', 'hash2', '0002', 'general', 'exited',
             0, 0, 1, 1, '2026-08-17 00:01:00', '2026-08-17 00:02:00', '');
        """
    )
    connection.close()
    config = RuntimeConfig(
        database_url=f"sqlite:///{database_path}",
        field_encryption_key=Fernet.generate_key().decode("ascii"),
    )

    _engine, factory = create_db(config)
    with factory() as session:
        active = session.get(Participant, 1)
        exited = session.get(Participant, 2)
        assert active is not None and active.active_code == "AA"
        assert active.legacy_key != "AA"
        assert exited is not None and exited.active_code is None
        assert exited.legacy_key != "BB"
        assert active.identity is not None and active.identity.permanent_code == "AA"
        assert exited.identity is not None and exited.identity.permanent_code == "BB"
        assert active.identity.entry_count == 1
        assert exited.identity.entry_count == 1

    _engine, second_factory = create_db(config)
    with second_factory() as session:
        identities = session.query(ParticipantIdentity).order_by(ParticipantIdentity.id).all()
        assert [(row.permanent_code, row.entry_count) for row in identities] == [
            ("AA", 1),
            ("BB", 1),
        ]


def test_full_visit_flow(service: LoungeService):
    result = check_in(service)
    assert len(result.display_code) == 2
    assert result.display_code.isalpha()
    assert result.display_code.isupper()
    assert result.starting_points == 25000

    balance = service.adjust_points(result.participant_id, 50, "테이블 A", "승인", "operator")
    assert balance == 25050
    balance = service.adjust_points(result.participant_id, -20, "테이블 B", "승인", "operator")
    assert balance == 25030

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
    assert recorded.spent_points == 30000
    assert recorded.earned_points == 14000
    assert recorded.delta == -16000
    assert recorded.balance == 9580


def test_quick_point_command_records_zero_net_change(service: LoungeService):
    participant = check_in(service)
    recorded = service.quick_adjust_points(f"50{participant.display_code}50", "operator")
    assert recorded.delta == 0
    assert recorded.balance == 25000


def test_quick_point_command_cannot_make_balance_negative(service: LoungeService):
    participant = check_in(service)
    with pytest.raises(ValueError, match="보유 칩이 부족"):
        service.quick_adjust_points(f"1000{participant.display_code}500", "operator")


def test_check_in_grants_the_default_starting_points(service: LoungeService):
    general = check_in(service)
    vip = check_in(service, phone="010-2222-3333", name="김브이", category="vip")
    assert general.starting_points == 25000
    assert vip.starting_points == 25000
    assert service.get_participant(general.participant_id)["points"] == 25000
    assert service.get_participant(vip.participant_id)["points"] == 25000


def test_quick_point_command_without_trailing_number_means_zero(service: LoungeService):
    participant = check_in(service)
    omitted = service.quick_adjust_points(f"200{participant.display_code}", "operator")
    assert omitted.earned == 0
    assert omitted.earned_points == 0
    assert omitted.delta == -20000
    assert omitted.balance == 5000

    explicit = check_in(service, phone="010-4444-5555", name="이확인")
    spelled = service.quick_adjust_points(f"200{explicit.display_code}0", "operator")
    assert (omitted.spent, omitted.earned, omitted.delta) == (
        spelled.spent,
        spelled.earned,
        spelled.delta,
    )
    assert omitted.balance == spelled.balance


def test_quick_point_command_rejects_invalid_input(service: LoungeService):
    with pytest.raises(ValueError, match="300RT140"):
        service.quick_adjust_points("잘못된 입력", "operator")

    with pytest.raises(ValueError, match="300RT140"):
        service.quick_adjust_points("77H1230", "operator")


def test_legacy_codes_are_migrated_to_two_letters(service: LoungeService):
    participant = check_in(service)
    with service.sessions.begin() as session:
        row = session.get(Participant, participant.participant_id)
        row.legacy_key = "ABC123"
        row.active_code = None

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
    assert second.display_code == first.display_code
    assert second.entry_count == 2
    assert second.is_returning is True


def test_reentry_keeps_person_state_and_does_not_repeat_starting_grant(
    service: LoungeService,
):
    first = check_in(service)
    service.adjust_points(first.participant_id, 25, "상태 유지 확인", "", "operator")
    service.check_out(first.participant_id, 25, "", "operator")

    second = check_in(service)
    assert second.display_code == first.display_code
    assert second.starting_points == 25
    assert service.get_participant(second.participant_id)["points"] == 25


def test_sixth_check_in_is_blocked_without_creating_a_visit(service: LoungeService):
    first = check_in(service)
    code = first.display_code
    latest_id = first.participant_id
    for expected_count in range(2, 6):
        service.check_out(latest_id, 0, "", "operator")
        entered = check_in(service, phone="01012345678", name="  홍길동  ")
        assert entered.display_code == code
        assert entered.entry_count == expected_count
        latest_id = entered.participant_id

    service.check_out(latest_id, 0, "", "operator")
    with pytest.raises(ValueError, match="5회를 모두 사용"):
        check_in(service)

    with service.sessions() as session:
        identity = session.scalar(
            session.query(ParticipantIdentity).where(
                ParticipantIdentity.permanent_code == code
            ).statement
        )
        assert identity is not None and identity.entry_count == 5
        assert session.query(Participant).filter_by(identity_id=identity.id).count() == 5


def test_677th_distinct_person_receives_three_letter_code(
    service: LoungeService, monkeypatch
):
    monkeypatch.setattr("lounge.security.secrets.choice", lambda choices: choices[0])
    with service.sessions.begin() as session:
        for first in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
            for second in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
                code = first + second
                session.add(
                    ParticipantIdentity(
                        identity_hash=f"reserved-{code}",
                        permanent_code=code,
                        entry_count=1,
                        is_active=False,
                        created_at=datetime(2026, 8, 27),
                    )
                )

    result = check_in(service, phone="010-9000-0677", name="육백칠십칠")
    assert result.display_code == "AAA"
    assert len(result.display_code) == 3
    assert service.active_participant_by_code("aaa")["id"] == result.participant_id
    verified = service.verify_checkout_identity(
        name="육백칠십칠",
        phone="01090000677",
        code="aaa",
    )
    assert verified["id"] == result.participant_id


def test_public_display_reset_keeps_permanent_identity_and_entry_count(
    service: LoungeService,
):
    first = check_in(service)
    service.check_out(first.participant_id, 0, "", "operator")
    service.reset_public_display("operator")

    second = check_in(service)
    assert second.display_code == first.display_code
    assert second.entry_count == 2


def test_permanent_code_is_kept_after_checkout_and_never_reused(
    service: LoungeService, monkeypatch
):
    monkeypatch.setattr("lounge.security.secrets.choice", lambda choices: choices[0])
    first = check_in(service, phone="010-7000-0001", name="첫방문")
    assert first.display_code == "AA"

    service.check_out(first.participant_id, 0, "", "operator")
    exited = service.get_participant(first.participant_id)
    assert exited["code"] == "AA"
    with service.sessions() as session:
        row = session.get(Participant, first.participant_id)
        assert row.active_code is None
        assert row.legacy_key != first.display_code
        assert row.identity is not None and row.identity.permanent_code == "AA"

    second = check_in(service, phone="010-7000-0002", name="다음방문")
    assert second.display_code == "AB"
    assert second.display_code != first.display_code


def test_checkout_identity_requires_matching_name_phone_and_code(service: LoungeService):
    participant = check_in(service, name="퇴장 손님", phone="010-7777-7777")

    verified = service.verify_checkout_identity(
        name="  퇴장   손님 ",
        phone="01077777777",
        code=participant.display_code.lower(),
    )
    assert verified["id"] == participant.participant_id

    for wrong_values in (
        {"name": "다른 손님", "phone": "010-7777-7777", "code": participant.display_code},
        {"name": "퇴장 손님", "phone": "010-0000-0000", "code": participant.display_code},
        {"name": "퇴장 손님", "phone": "010-7777-7777", "code": "ZZ"},
    ):
        with pytest.raises(ValueError, match="입력 정보와 일치"):
            service.verify_checkout_identity(**wrong_values)


def test_points_cannot_be_negative(service: LoungeService):
    result = check_in(service)
    service.adjust_points(result.participant_id, -25000, "정산", "", "operator")
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


def test_public_display_reset_hides_old_visitors_without_deleting_records(
    service: LoungeService,
):
    old = check_in(service, phone="010-3000-0001", name="기존방문")
    service.adjust_points(old.participant_id, 10, "기록 확인", "", "op")
    assert service.dashboard()["total"] == 1
    assert [row["code"] for row in service.leaderboard("general")] == [old.display_code]

    reset_at = service.reset_public_display("operator")

    assert service.public_display_reset_at() == reset_at
    assert service.dashboard()["total"] == 0
    assert service.leaderboard("general") == []
    assert service.get_participant(old.participant_id)["name"] == "기존방문"
    assert service.search_participants("기존방문")[0]["id"] == old.participant_id
    assert service.recent_transactions()[0]["code"] == old.display_code

    new = check_in(service, phone="010-3000-0002", name="신규방문")
    assert service.dashboard()["total"] == 1
    assert [row["code"] for row in service.leaderboard("general")] == [new.display_code]


def test_export_is_utf8_bom_csv(service: LoungeService):
    participant = check_in(service)
    payload = service.export_participants_csv()
    assert payload.startswith(b"\xef\xbb\xbf")
    assert "홍길동" in payload.decode("utf-8-sig")
    assert participant.display_code in payload.decode("utf-8-sig")
    assert "참가자ID" in payload.decode("utf-8-sig")
    assert "입장회차" in payload.decode("utf-8-sig")


def test_stored_logs_and_transaction_exports_do_not_duplicate_permanent_codes(
    service: LoungeService,
):
    participant = check_in(service)
    service.quick_adjust_points(f"0{participant.display_code}5", "operator")
    service.check_out(participant.participant_id, 5, "", "operator")

    _engine, factory = create_db(service.config)
    with factory() as session:
        assert all(
            participant.display_code not in (log.details or "")
            for log in session.query(AuditLog).all()
        )
        assert all(
            participant.display_code not in (transaction.note or "")
            for transaction in session.query(PointTransaction).all()
        )
    assert participant.display_code not in LoungeService(
        factory, service.config
    ).export_transactions_csv().decode("utf-8-sig")


def test_operator_uses_only_shared_password(service: LoungeService):
    assert service.verify_operator_password("test-operator-password") is True
    assert service.verify_operator_password("wrong") is False


def test_analytics_uses_a_different_password(service: LoungeService):
    assert service.analytics_password_issue() == ""
    assert service.verify_analytics_password("test-analytics-password") is True
    assert service.verify_analytics_password("test-operator-password") is False


def test_reset_uses_a_different_password(service: LoungeService):
    assert service.reset_password_issue() == ""
    assert service.verify_reset_password("test-reset-password") is True
    assert service.verify_reset_password("test-operator-password") is False


def test_visit_analytics_tracks_attendance_without_point_history(service: LoungeService):
    general = check_in(service, phone="010-5555-5555", name="일반방문")
    check_in(service, phone="010-6666-6666", name="우대방문", category="vip")
    service.check_out(general.participant_id, 0, "", "checkout_station")

    stats = service.visit_analytics()
    assert stats["total"] == 2
    assert stats["active"] == 1
    assert stats["exited"] == 1
    assert stats["general"] == 1
    assert stats["vip"] == 1
    assert sum(row["count"] for row in stats["hourly"]) == 2
    general_visit = next(visit for visit in stats["visits"] if visit["name"] == "일반방문")
    assert general_visit["age"] == 17
    assert general_visit["phone"] == "010-****-5555"
    assert general_visit["code"] == general.display_code
    assert general_visit["visit_number"] == 1
    assert general_visit["entry_count"] == 1
    assert all("points" not in visit for visit in stats["visits"])
