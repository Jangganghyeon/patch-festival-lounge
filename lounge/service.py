from __future__ import annotations

import csv
import hmac
import io
import json
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy import and_, desc, func, or_, select, update
from sqlalchemy.orm import Session, sessionmaker

from .config import RuntimeConfig
from .database import (
    DB_WRITE_LOCK,
    AppSetting,
    AuditLog,
    Participant,
    PointTransaction,
)
from .security import (
    decrypt_text,
    encrypt_text,
    mask_phone,
    new_display_code,
    normalize_phone,
    phone_digest,
    validate_phone,
)

UTC = timezone.utc


def utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


@dataclass(frozen=True)
class CheckInResult:
    participant_id: int
    display_code: str
    starting_points: int


@dataclass(frozen=True)
class QuickPointResult:
    participant_id: int
    display_code: str
    name: str
    spent: int
    earned: int
    delta: int
    balance: int


class LoungeService:
    def __init__(self, session_factory: sessionmaker, config: RuntimeConfig):
        self.sessions = session_factory
        self.config = config
        self.local_tz = ZoneInfo(config.timezone)

    def _audit(
        self,
        session: Session,
        action: str,
        operator: str,
        participant_id: int | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        session.add(
            AuditLog(
                action=action,
                participant_id=participant_id,
                operator=operator[:40],
                details=json.dumps(details or {}, ensure_ascii=False),
                created_at=utcnow(),
            )
        )

    def setting(self, key: str, default: str = "") -> str:
        with self.sessions() as session:
            row = session.get(AppSetting, key)
            return row.value if row else default

    def settings(self) -> dict[str, str]:
        with self.sessions() as session:
            return {row.key: row.value for row in session.scalars(select(AppSetting)).all()}

    def update_settings(self, values: dict[str, str], operator: str) -> None:
        allowed = {
            "event_name",
            "event_subtitle",
            "general_start_points",
            "vip_start_points",
            "leaderboard_size",
            "privacy_retention_days",
        }
        if not set(values).issubset(allowed):
            raise ValueError("변경할 수 없는 설정이 포함되어 있습니다.")
        for numeric in (
            "general_start_points",
            "vip_start_points",
            "leaderboard_size",
            "privacy_retention_days",
        ):
            if numeric in values and int(values[numeric]) < 0:
                raise ValueError("숫자 설정은 0 이상이어야 합니다.")
        with DB_WRITE_LOCK, self.sessions.begin() as session:
            for key, value in values.items():
                row = session.get(AppSetting, key)
                if row:
                    row.value = str(value)
                else:
                    session.add(AppSetting(key=key, value=str(value)))
            self._audit(session, "settings_update", operator, details=values)

    def verify_operator_password(self, password: str) -> bool:
        expected = self.config.operator_password
        return bool(expected) and hmac.compare_digest(password or "", expected)

    def check_in(
        self,
        *,
        name: str,
        age: int,
        phone: str,
        category: str,
        privacy_consent: bool,
        leaderboard_opt_in: bool,
    ) -> CheckInResult:
        name = " ".join(name.strip().split())
        if not 2 <= len(name) <= 40:
            raise ValueError("이름은 2~40자로 입력해 주세요.")
        if not 7 <= int(age) <= 100:
            raise ValueError("나이를 다시 확인해 주세요.")
        if category not in {"general", "vip"}:
            raise ValueError("참가 유형을 다시 선택해 주세요.")
        if not privacy_consent:
            raise ValueError("입장 기록을 위한 개인정보 수집 동의가 필요합니다.")
        normalized_phone = validate_phone(phone)
        digest = phone_digest(normalized_phone)
        start_key = "vip_start_points" if category == "vip" else "general_start_points"
        starting_points = int(self.setting(start_key, "0"))

        with DB_WRITE_LOCK, self.sessions.begin() as session:
            active_duplicate = session.scalar(
                select(Participant).where(
                    and_(Participant.phone_hash == digest, Participant.status == "active")
                )
            )
            if active_duplicate:
                raise ValueError("이미 입장 처리된 전화번호입니다. 운영자에게 문의해 주세요.")

            used_codes = set(session.scalars(select(Participant.display_code)).all())
            code = new_display_code(used_codes)
            participant = Participant(
                display_code=code,
                name=name,
                age=int(age),
                phone_encrypted=encrypt_text(normalized_phone, self.config.field_encryption_key),
                phone_hash=digest,
                phone_last4=normalized_phone[-4:],
                category=category,
                status="active",
                current_points=starting_points,
                leaderboard_opt_in=bool(leaderboard_opt_in),
                privacy_consent=True,
                checked_in_at=utcnow(),
            )
            session.add(participant)
            session.flush()
            if starting_points:
                session.add(
                    PointTransaction(
                        participant_id=participant.id,
                        delta=starting_points,
                        balance_after=starting_points,
                        activity="입장 기본 포인트",
                        note=category,
                        operator="system",
                        created_at=utcnow(),
                    )
                )
            self._audit(
                session,
                "check_in",
                "kiosk",
                participant.id,
                {"category": category, "code": code},
            )
            return CheckInResult(participant.id, code, starting_points)

    def _participant_dict(self, row: Participant, reveal_phone: bool = False) -> dict[str, Any]:
        phone = decrypt_text(row.phone_encrypted, self.config.field_encryption_key)
        return {
            "id": row.id,
            "code": row.display_code,
            "name": row.name,
            "age": row.age,
            "phone": phone if reveal_phone else mask_phone(phone),
            "phone_last4": row.phone_last4,
            "category": row.category,
            "status": row.status,
            "points": row.current_points,
            "final_points": row.final_points,
            "leaderboard_opt_in": row.leaderboard_opt_in,
            "checked_in_at": row.checked_in_at,
            "checked_out_at": row.checked_out_at,
            "exit_note": row.exit_note,
        }

    def search_participants(
        self, query: str = "", *, active_only: bool = False, limit: int = 50
    ) -> list[dict[str, Any]]:
        query = query.strip()
        normalized = normalize_phone(query)
        with self.sessions() as session:
            stmt = select(Participant)
            filters = []
            if active_only:
                filters.append(Participant.status == "active")
            if query:
                choices = [
                    Participant.name.ilike(f"%{query}%"),
                    Participant.display_code.ilike(f"%{query.upper()}%"),
                ]
                if normalized:
                    choices.append(Participant.phone_last4.like(f"%{normalized[-4:]}%"))
                filters.append(or_(*choices))
            if filters:
                stmt = stmt.where(and_(*filters))
            rows = session.scalars(stmt.order_by(desc(Participant.checked_in_at)).limit(limit)).all()
            return [self._participant_dict(row) for row in rows]

    def get_participant(self, participant_id: int, reveal_phone: bool = False) -> dict[str, Any]:
        with self.sessions() as session:
            row = session.get(Participant, participant_id)
            if not row:
                raise ValueError("참가자를 찾을 수 없습니다.")
            return self._participant_dict(row, reveal_phone=reveal_phone)

    def adjust_points(
        self,
        participant_id: int,
        delta: int,
        activity: str,
        note: str,
        operator: str,
    ) -> int:
        delta = int(delta)
        if delta == 0 or abs(delta) > 100_000:
            raise ValueError("변경 포인트는 0이 아니고 절댓값 100,000 이하여야 합니다.")
        activity = activity.strip()
        if not activity:
            raise ValueError("게임/활동명을 입력해 주세요.")
        with DB_WRITE_LOCK, self.sessions.begin() as session:
            result = session.execute(
                update(Participant)
                .where(
                    and_(
                        Participant.id == participant_id,
                        Participant.status == "active",
                        Participant.current_points + delta >= 0,
                    )
                )
                .values(current_points=Participant.current_points + delta)
            )
            if result.rowcount != 1:
                participant = session.get(Participant, participant_id)
                if not participant or participant.status != "active":
                    raise ValueError("입장 중인 참가자만 포인트를 변경할 수 있습니다.")
                raise ValueError("보유 포인트보다 많이 차감할 수 없습니다.")
            participant = session.get(Participant, participant_id)
            assert participant is not None
            session.add(
                PointTransaction(
                    participant_id=participant_id,
                    delta=delta,
                    balance_after=participant.current_points,
                    activity=activity[:80],
                    note=note.strip()[:200],
                    operator=operator[:40],
                    created_at=utcnow(),
                )
            )
            self._audit(
                session,
                "points_adjusted",
                operator,
                participant_id,
                {"delta": delta, "balance": participant.current_points, "activity": activity[:80]},
            )
            return participant.current_points

    def quick_adjust_points(self, command: str, operator: str) -> QuickPointResult:
        match = re.fullmatch(r"\s*(\d{1,6})\s*([A-Za-z]{2})\s*(\d{1,6})\s*", command or "")
        if not match:
            raise ValueError("300RT140 형식으로 입력해 주세요: 사용 칩 + 두 글자 ID + 획득 점수")
        spent = int(match.group(1))
        code = match.group(2).upper()
        earned = int(match.group(3))
        if spent == 0 and earned == 0:
            raise ValueError("사용 칩과 획득 점수가 모두 0일 수는 없습니다.")
        delta = earned - spent
        normalized_command = f"{spent}{code}{earned}"

        with DB_WRITE_LOCK, self.sessions.begin() as session:
            participant = session.scalar(
                select(Participant).where(
                    and_(Participant.display_code == code, Participant.status == "active")
                )
            )
            if not participant:
                raise ValueError(f"현재 입장 중인 {code} 참가자를 찾을 수 없습니다.")
            new_balance = participant.current_points + delta
            if new_balance < 0:
                raise ValueError(
                    f"{code} 참가자의 보유 칩이 부족합니다. 현재 {participant.current_points:,}P"
                )
            participant.current_points = new_balance
            session.add(
                PointTransaction(
                    participant_id=participant.id,
                    delta=delta,
                    balance_after=new_balance,
                    activity="칩 사용·게임 점수 기록",
                    note=f"사용 {spent}P · 획득 {earned}P · {normalized_command}",
                    operator=operator[:40],
                    created_at=utcnow(),
                )
            )
            self._audit(
                session,
                "chip_score_recorded",
                operator,
                participant.id,
                {
                    "spent": spent,
                    "earned": earned,
                    "delta": delta,
                    "balance": new_balance,
                    "command": normalized_command,
                },
            )
            return QuickPointResult(
                participant.id,
                code,
                participant.name,
                spent,
                earned,
                delta,
                new_balance,
            )

    def check_out(
        self,
        participant_id: int,
        final_points: int,
        exit_note: str,
        operator: str,
    ) -> None:
        final_points = int(final_points)
        if final_points < 0:
            raise ValueError("최종 포인트는 0 이상이어야 합니다.")
        with DB_WRITE_LOCK, self.sessions.begin() as session:
            participant = session.get(Participant, participant_id)
            if not participant or participant.status != "active":
                raise ValueError("이미 퇴장했거나 존재하지 않는 참가자입니다.")
            if final_points != participant.current_points:
                delta = final_points - participant.current_points
                participant.current_points = final_points
                session.add(
                    PointTransaction(
                        participant_id=participant_id,
                        delta=delta,
                        balance_after=final_points,
                        activity="퇴장 정산",
                        note="현장 보유량과 시스템 기록 일치 처리",
                        operator=operator[:40],
                        created_at=utcnow(),
                    )
                )
            participant.status = "exited"
            participant.final_points = final_points
            participant.exit_note = exit_note.strip()[:200]
            participant.checked_out_at = utcnow()
            self._audit(
                session,
                "check_out",
                operator,
                participant_id,
                {"final_points": final_points},
            )

    def reopen_participant(self, participant_id: int, operator: str) -> None:
        with DB_WRITE_LOCK, self.sessions.begin() as session:
            participant = session.get(Participant, participant_id)
            if not participant or participant.status != "exited":
                raise ValueError("퇴장 완료된 참가자만 복구할 수 있습니다.")
            participant.status = "active"
            participant.checked_out_at = None
            participant.final_points = None
            participant.exit_note = ""
            self._audit(session, "check_out_reverted", operator, participant_id)

    def dashboard(self) -> dict[str, Any]:
        with self.sessions() as session:
            total = session.scalar(select(func.count(Participant.id))) or 0
            active = (
                session.scalar(select(func.count(Participant.id)).where(Participant.status == "active")) or 0
            )
            exited = total - active
            vip_active = (
                session.scalar(
                    select(func.count(Participant.id)).where(
                        and_(Participant.status == "active", Participant.category == "vip")
                    )
                )
                or 0
            )
            active_points = (
                session.scalar(
                    select(func.coalesce(func.sum(Participant.current_points), 0)).where(
                        Participant.status == "active"
                    )
                )
                or 0
            )
            recent = session.scalars(
                select(Participant).order_by(desc(Participant.checked_in_at)).limit(8)
            ).all()
            return {
                "total": int(total),
                "active": int(active),
                "exited": int(exited),
                "vip_active": int(vip_active),
                "active_points": int(active_points),
                "recent": [self._public_participant(row) for row in recent],
                "leaderboard": self._leaderboard_in_session(session),
                "general_leaderboard": self._leaderboard_in_session(session, "general"),
                "vip_leaderboard": self._leaderboard_in_session(session, "vip"),
                "traffic": self._traffic_in_session(session),
            }

    def _public_name(self, row: Participant) -> str:
        if row.leaderboard_opt_in:
            return row.name
        if len(row.name) == 2:
            return row.name[0] + "*"
        return row.name[0] + "*" * max(1, len(row.name) - 2) + row.name[-1]

    def _public_participant(self, row: Participant) -> dict[str, Any]:
        return {
            "name": self._public_name(row),
            "code": row.display_code,
            "category": row.category,
            "status": row.status,
            "points": row.current_points,
            "checked_in_at": row.checked_in_at,
        }

    def leaderboard(self, category: str) -> list[dict[str, Any]]:
        if category not in {"general", "vip"}:
            raise ValueError("순위표 참가 유형이 올바르지 않습니다.")
        with self.sessions() as session:
            return self._leaderboard_in_session(session, category)

    def _leaderboard_in_session(
        self, session: Session, category: str | None = None
    ) -> list[dict[str, Any]]:
        size = max(3, min(30, int(self.setting("leaderboard_size", "10"))))
        stmt = select(Participant).where(Participant.status == "active")
        if category is not None:
            stmt = stmt.where(Participant.category == category)
        rows = session.scalars(
            stmt.order_by(desc(Participant.current_points), Participant.checked_in_at).limit(size)
        ).all()
        return [self._public_participant(row) for row in rows]

    def _traffic_in_session(self, session: Session) -> list[dict[str, Any]]:
        since = utcnow() - timedelta(hours=8)
        rows = session.scalars(select(Participant).where(Participant.checked_in_at >= since)).all()
        buckets: dict[str, int] = {}
        for row in rows:
            local = row.checked_in_at.replace(tzinfo=UTC).astimezone(self.local_tz)
            key = local.strftime("%H:00")
            buckets[key] = buckets.get(key, 0) + 1
        return [{"시간": key, "입장": value} for key, value in sorted(buckets.items())]

    def recent_transactions(self, limit: int = 20) -> list[dict[str, Any]]:
        with self.sessions() as session:
            rows = session.execute(
                select(PointTransaction, Participant.name, Participant.display_code)
                .join(Participant, Participant.id == PointTransaction.participant_id)
                .order_by(desc(PointTransaction.created_at))
                .limit(limit)
            ).all()
            return [
                {
                    "time": tx.created_at,
                    "name": name,
                    "code": code,
                    "delta": tx.delta,
                    "balance": tx.balance_after,
                    "activity": tx.activity,
                    "operator": tx.operator,
                }
                for tx, name, code in rows
            ]

    def export_participants_csv(self) -> bytes:
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(
            [
                "입장코드",
                "이름",
                "나이",
                "전화번호",
                "구분",
                "상태",
                "현재포인트",
                "최종포인트",
                "입장시각",
                "퇴장시각",
                "퇴장메모",
            ]
        )
        with self.sessions() as session:
            rows = session.scalars(select(Participant).order_by(Participant.checked_in_at)).all()
            for row in rows:
                item = self._participant_dict(row, reveal_phone=True)
                writer.writerow(
                    [
                        item["code"],
                        item["name"],
                        item["age"],
                        item["phone"],
                        item["category"],
                        item["status"],
                        item["points"],
                        item["final_points"] if item["final_points"] is not None else "",
                        self.format_time(item["checked_in_at"], include_date=True),
                        self.format_time(item["checked_out_at"], include_date=True),
                        item["exit_note"],
                    ]
                )
        return ("\ufeff" + output.getvalue()).encode("utf-8")

    def export_transactions_csv(self) -> bytes:
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["시각", "입장코드", "이름", "변동", "잔액", "활동", "메모", "운영자"])
        with self.sessions() as session:
            rows = session.execute(
                select(PointTransaction, Participant.name, Participant.display_code)
                .join(Participant, Participant.id == PointTransaction.participant_id)
                .order_by(PointTransaction.created_at)
            ).all()
            for tx, name, code in rows:
                writer.writerow(
                    [
                        self.format_time(tx.created_at, include_date=True),
                        code,
                        name,
                        tx.delta,
                        tx.balance_after,
                        tx.activity,
                        tx.note,
                        tx.operator,
                    ]
                )
        return ("\ufeff" + output.getvalue()).encode("utf-8")

    def purge_expired_personal_data(self, operator: str) -> int:
        days = max(1, int(self.setting("privacy_retention_days", "30")))
        cutoff = utcnow() - timedelta(days=days)
        count = 0
        with DB_WRITE_LOCK, self.sessions.begin() as session:
            rows = session.scalars(
                select(Participant).where(
                    and_(Participant.status == "exited", Participant.checked_out_at < cutoff)
                )
            ).all()
            for row in rows:
                row.name = f"삭제된 참가자 {row.id}"
                row.age = 0
                row.phone_encrypted = encrypt_text("0000000000", self.config.field_encryption_key)
                row.phone_hash = "purged-" + str(row.id)
                row.phone_last4 = "0000"
                row.leaderboard_opt_in = False
                count += 1
            self._audit(session, "personal_data_purged", operator, details={"count": count})
        return count

    def format_time(self, value: datetime | None, include_date: bool = False) -> str:
        if value is None:
            return "-"
        local = value.replace(tzinfo=UTC).astimezone(self.local_tz)
        return local.strftime("%m/%d %H:%M" if include_date else "%H:%M")
