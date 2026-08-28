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
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload, sessionmaker

from .config import RuntimeConfig
from .database import (
    DB_WRITE_LOCK,
    DEFAULT_START_POINTS,
    AppSetting,
    AuditLog,
    Participant,
    ParticipantIdentity,
    PointTransaction,
)
from .security import (
    decrypt_text,
    encrypt_text,
    identity_digest,
    mask_phone,
    mask_phone_last4,
    new_display_code,
    new_internal_record_key,
    normalize_name,
    normalize_phone,
    phone_digest,
    validate_phone,
)

UTC = timezone.utc


QUICK_POINT_UNIT = 100
"""운영진 입력 편의를 위해 전산 칩 입력값 1은 실제 100P로 환산한다."""


def utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


@dataclass(frozen=True)
class CheckInResult:
    participant_id: int
    display_code: str
    starting_points: int
    entry_count: int
    is_returning: bool


@dataclass(frozen=True)
class QuickPointResult:
    participant_id: int
    display_code: str
    name: str
    spent: int
    earned: int
    spent_points: int
    earned_points: int
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

    def analytics_password_issue(self) -> str:
        if not self.config.analytics_password:
            return "ANALYTICS_PASSWORD가 설정되지 않았습니다."
        if self.config.analytics_password == self.config.operator_password:
            return "영업 분석 비밀번호는 운영자 콘솔 비밀번호와 다르게 설정해야 합니다."
        return ""

    def verify_analytics_password(self, password: str) -> bool:
        expected = self.config.analytics_password
        return not self.analytics_password_issue() and hmac.compare_digest(password or "", expected)

    def reset_password_issue(self) -> str:
        if not self.config.reset_password:
            return "RESET_PASSWORD가 설정되지 않았습니다."
        if self.config.reset_password == self.config.operator_password:
            return "초기화 비밀번호는 운영자 콘솔 비밀번호와 다르게 설정해야 합니다."
        return ""

    def verify_reset_password(self, password: str) -> bool:
        expected = self.config.reset_password
        return not self.reset_password_issue() and hmac.compare_digest(password or "", expected)

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
        name = normalize_name(name)
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
        fingerprint = identity_digest(name, normalized_phone, self.config.field_encryption_key)
        start_key = "vip_start_points" if category == "vip" else "general_start_points"
        configured_starting_points = int(self.setting(start_key, DEFAULT_START_POINTS))

        for attempt in range(3):
            try:
                with DB_WRITE_LOCK, self.sessions.begin() as session:
                    identity = session.scalar(
                        select(ParticipantIdentity).where(
                            ParticipantIdentity.identity_hash == fingerprint
                        )
                    )
                    if identity is None:
                        known_person = session.scalar(
                            select(Participant)
                            .options(selectinload(Participant.identity))
                            .where(
                                and_(
                                    Participant.name == name,
                                    Participant.phone_hash == digest,
                                )
                            )
                            .order_by(desc(Participant.checked_in_at), desc(Participant.id))
                            .limit(1)
                        )
                        if known_person is not None and known_person.identity is not None:
                            identity = known_person.identity
                            identity.identity_hash = fingerprint
                    is_returning = identity is not None
                    if identity is None:
                        known_phone = session.scalar(
                            select(Participant)
                            .where(Participant.phone_hash == digest)
                            .order_by(desc(Participant.checked_in_at), desc(Participant.id))
                            .limit(1)
                        )
                        if known_phone is not None:
                            if known_phone.status == "active":
                                raise ValueError(
                                    "이미 입장 처리된 전화번호입니다. 운영자에게 문의해 주세요."
                                )
                            raise ValueError(
                                "기존 방문 기록의 이름과 일치하지 않습니다. 운영자에게 문의해 주세요."
                            )
                        used_codes = set(
                            session.scalars(select(ParticipantIdentity.permanent_code)).all()
                        )
                        identity = ParticipantIdentity(
                            identity_hash=fingerprint,
                            permanent_code=new_display_code(used_codes),
                            entry_count=1,
                            is_active=True,
                            created_at=utcnow(),
                        )
                        session.add(identity)
                        session.flush()
                        current_points = configured_starting_points
                    else:
                        latest = session.scalar(
                            select(Participant)
                            .where(Participant.identity_id == identity.id)
                            .order_by(desc(Participant.checked_in_at), desc(Participant.id))
                            .limit(1)
                        )
                        claimed = session.execute(
                            update(ParticipantIdentity)
                            .where(
                                and_(
                                    ParticipantIdentity.id == identity.id,
                                    ParticipantIdentity.is_active.is_(False),
                                    ParticipantIdentity.entry_count < 5,
                                )
                            )
                            .values(
                                is_active=True,
                                entry_count=ParticipantIdentity.entry_count + 1,
                            )
                        )
                        if claimed.rowcount != 1:
                            session.refresh(identity)
                            if identity.is_active:
                                raise ValueError(
                                    "이미 입장 처리된 방문자입니다. 운영자에게 문의해 주세요."
                                )
                            raise ValueError(
                                "입장 가능 횟수 5회를 모두 사용하여 추가 입장이 불가능합니다."
                            )
                        session.refresh(identity)
                        current_points = latest.current_points if latest else configured_starting_points

                    used_keys = set(session.scalars(select(Participant.legacy_key)).all())
                    participant = Participant(
                        legacy_key=new_internal_record_key(used_keys),
                        active_code=identity.permanent_code,
                        identity_id=identity.id,
                        visit_number=identity.entry_count,
                        name=name,
                        age=int(age),
                        phone_encrypted=encrypt_text(
                            normalized_phone, self.config.field_encryption_key
                        ),
                        phone_hash=digest,
                        phone_last4=normalized_phone[-4:],
                        category=category,
                        status="active",
                        current_points=current_points,
                        leaderboard_opt_in=bool(leaderboard_opt_in),
                        privacy_consent=True,
                        checked_in_at=utcnow(),
                    )
                    session.add(participant)
                    session.flush()
                    if not is_returning and current_points:
                        session.add(
                            PointTransaction(
                                participant_id=participant.id,
                                delta=current_points,
                                balance_after=current_points,
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
                        {
                            "category": category,
                            "entry_count": identity.entry_count,
                            "returning": is_returning,
                        },
                    )
                    return CheckInResult(
                        participant.id,
                        identity.permanent_code,
                        current_points,
                        identity.entry_count,
                        is_returning,
                    )
            except IntegrityError as exc:
                if attempt == 2:
                    raise ValueError(
                        "동시에 여러 입장 등록이 처리되었습니다. 잠시 후 다시 시도해 주세요."
                    ) from exc

        raise ValueError("입장 등록을 완료할 수 없습니다.")

    def _phone_for_display(
        self, row: Participant, *, reveal_phone: bool = False
    ) -> tuple[str, bool]:
        try:
            phone = decrypt_text(row.phone_encrypted, self.config.field_encryption_key)
        except ValueError:
            return mask_phone_last4(row.phone_last4), True
        return (phone if reveal_phone else mask_phone(phone)), False

    def _participant_dict(self, row: Participant, reveal_phone: bool = False) -> dict[str, Any]:
        phone, phone_decryption_failed = self._phone_for_display(
            row, reveal_phone=reveal_phone
        )
        permanent_code = row.identity.permanent_code if row.identity else row.active_code or ""
        return {
            "id": row.id,
            "code": permanent_code,
            "name": row.name,
            "age": row.age,
            "phone": phone,
            "phone_decryption_failed": phone_decryption_failed,
            "phone_last4": row.phone_last4,
            "category": row.category,
            "status": row.status,
            "points": row.current_points,
            "final_points": row.final_points,
            "leaderboard_opt_in": row.leaderboard_opt_in,
            "checked_in_at": row.checked_in_at,
            "checked_out_at": row.checked_out_at,
            "exit_note": row.exit_note,
            "visit_number": row.visit_number,
            "entry_count": row.identity.entry_count if row.identity else row.visit_number,
        }

    def search_participants(
        self, query: str = "", *, active_only: bool = False, limit: int = 50
    ) -> list[dict[str, Any]]:
        query = query.strip()
        normalized = normalize_phone(query)
        with self.sessions() as session:
            stmt = select(Participant).join(ParticipantIdentity)
            filters = []
            if active_only:
                filters.append(Participant.status == "active")
            if query:
                choices = [
                    Participant.name.ilike(f"%{query}%"),
                    ParticipantIdentity.permanent_code.ilike(f"%{query.upper()}%"),
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

    def active_participant_by_code(self, code: str) -> dict[str, Any]:
        normalized = (code or "").strip().upper()
        if not re.fullmatch(r"[A-Z]{2,4}", normalized):
            raise ValueError("영문 2~4글자 ID를 입력해 주세요.")
        with self.sessions() as session:
            row = session.scalar(
                select(Participant).join(ParticipantIdentity).where(
                    and_(
                        ParticipantIdentity.permanent_code == normalized,
                        Participant.status == "active",
                    )
                )
            )
            if not row:
                raise ValueError(f"현재 입장 중인 {normalized} 참가자를 찾을 수 없습니다.")
            return self._participant_dict(row)

    def verify_checkout_identity(self, *, name: str, phone: str, code: str) -> dict[str, Any]:
        normalized_name = normalize_name(name)
        normalized_phone = validate_phone(phone)
        normalized_code = (code or "").strip().upper()
        if not 2 <= len(normalized_name) <= 40:
            raise ValueError("이름을 정확히 입력해 주세요.")
        if not re.fullmatch(r"[A-Z]{2,4}", normalized_code):
            raise ValueError("영문 2~4글자 ID를 입력해 주세요.")

        with self.sessions() as session:
            row = session.scalar(
                select(Participant).join(ParticipantIdentity).where(
                    and_(
                        Participant.name == normalized_name,
                        Participant.phone_hash == phone_digest(normalized_phone),
                        ParticipantIdentity.permanent_code == normalized_code,
                        Participant.status == "active",
                    )
                )
            )
            if not row:
                raise ValueError("입력 정보와 일치하는 현재 입장 기록을 찾을 수 없습니다.")
            return self._participant_dict(row)

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
        match = re.fullmatch(r"\s*(\d{1,6})\s*([A-Za-z]{2,4})\s*(\d{0,6})\s*", command or "")
        if not match:
            raise ValueError("300RT140 형식으로 입력해 주세요: 앞 수치 + 참가자 ID + 뒤 수치")
        spent = int(match.group(1))
        code = match.group(2).upper()
        earned = int(match.group(3) or 0)
        if spent == 0 and earned == 0:
            raise ValueError("사용 칩과 획득 점수가 모두 0일 수는 없습니다.")
        spent_points = spent * QUICK_POINT_UNIT
        earned_points = earned * QUICK_POINT_UNIT
        delta = earned_points - spent_points
        with DB_WRITE_LOCK, self.sessions.begin() as session:
            participant = session.scalar(
                select(Participant).join(ParticipantIdentity).where(
                    and_(
                        ParticipantIdentity.permanent_code == code,
                        Participant.status == "active",
                    )
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
                    note=f"사용 {spent_points}P · 획득 {earned_points}P",
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
                    "spent_points": spent_points,
                    "earned_points": earned_points,
                    "delta": delta,
                    "balance": new_balance,
                },
            )
            return QuickPointResult(
                participant.id,
                code,
                participant.name,
                spent,
                earned,
                spent_points,
                earned_points,
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
            if participant.identity:
                participant.identity.is_active = False
            participant.active_code = None

    def reopen_participant(self, participant_id: int, operator: str) -> None:
        with DB_WRITE_LOCK, self.sessions.begin() as session:
            participant = session.get(Participant, participant_id)
            if not participant or participant.status != "exited":
                raise ValueError("퇴장 완료된 참가자만 복구할 수 있습니다.")
            if not participant.identity:
                raise ValueError("영구 ID 정보를 찾을 수 없습니다.")
            if participant.identity.is_active:
                raise ValueError("이미 재입장한 방문자의 이전 퇴장 기록은 복구할 수 없습니다.")
            newer_visit = session.scalar(
                select(Participant.id)
                .where(
                    and_(
                        Participant.identity_id == participant.identity_id,
                        Participant.checked_in_at > participant.checked_in_at,
                    )
                )
                .limit(1)
            )
            if newer_visit is not None:
                raise ValueError("가장 최근 방문 기록만 퇴장 취소할 수 있습니다.")
            participant.status = "active"
            participant.checked_out_at = None
            participant.final_points = None
            participant.exit_note = ""
            participant.identity.is_active = True
            participant.active_code = participant.identity.permanent_code
            self._audit(session, "check_out_reverted", operator, participant_id)

    @staticmethod
    def _parse_reset_at(value: str) -> datetime | None:
        if not value:
            return None
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            return None

    def _public_display_cutoff(self, session: Session) -> datetime | None:
        setting = session.get(AppSetting, "public_display_reset_at")
        return self._parse_reset_at(setting.value if setting else "")

    def public_display_reset_at(self) -> datetime | None:
        return self._parse_reset_at(self.setting("public_display_reset_at", ""))

    def reset_public_display(self, operator: str) -> datetime:
        reset_at = utcnow()
        value = reset_at.isoformat(timespec="microseconds")
        with DB_WRITE_LOCK, self.sessions.begin() as session:
            setting = session.get(AppSetting, "public_display_reset_at")
            if setting:
                setting.value = value
            else:
                session.add(AppSetting(key="public_display_reset_at", value=value))
            self._audit(
                session,
                "public_display_reset",
                operator,
                details={"reset_at": value, "records_deleted": False},
            )
        return reset_at

    def dashboard(self) -> dict[str, Any]:
        with self.sessions() as session:
            cutoff = self._public_display_cutoff(session)
            visible = Participant.checked_in_at >= cutoff if cutoff else None
            total_stmt = select(func.count(Participant.id))
            if visible is not None:
                total_stmt = total_stmt.where(visible)
            total = session.scalar(total_stmt) or 0
            active_filters = [Participant.status == "active"]
            if visible is not None:
                active_filters.append(visible)
            active = (
                session.scalar(select(func.count(Participant.id)).where(and_(*active_filters))) or 0
            )
            exited = total - active
            vip_filters = [Participant.status == "active", Participant.category == "vip"]
            if visible is not None:
                vip_filters.append(visible)
            vip_active = (
                session.scalar(
                    select(func.count(Participant.id)).where(and_(*vip_filters))
                )
                or 0
            )
            point_filters = [Participant.status == "active"]
            if visible is not None:
                point_filters.append(visible)
            active_points = (
                session.scalar(
                    select(func.coalesce(func.sum(Participant.current_points), 0)).where(
                        and_(*point_filters)
                    )
                )
                or 0
            )
            recent_stmt = select(Participant)
            if visible is not None:
                recent_stmt = recent_stmt.where(visible)
            recent = session.scalars(
                recent_stmt.order_by(desc(Participant.checked_in_at)).limit(8)
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

    def visit_analytics(self) -> dict[str, Any]:
        now = utcnow()
        now_local = now.replace(tzinfo=UTC).astimezone(self.local_tz)
        start_local = now_local.replace(hour=0, minute=0, second=0, microsecond=0)
        start_utc = start_local.astimezone(UTC).replace(tzinfo=None)

        with self.sessions() as session:
            rows = session.scalars(
                select(Participant)
                .options(selectinload(Participant.identity))
                .where(Participant.checked_in_at >= start_utc)
                .order_by(desc(Participant.checked_in_at))
            ).all()

        hourly_counts: dict[str, int] = {}
        completed_durations: list[int] = []
        visits: list[dict[str, Any]] = []
        undecryptable_phone_count = 0
        for row in rows:
            checked_in_local = row.checked_in_at.replace(tzinfo=UTC).astimezone(self.local_tz)
            hour = checked_in_local.strftime("%H:00")
            hourly_counts[hour] = hourly_counts.get(hour, 0) + 1

            end = row.checked_out_at or now
            duration_minutes = max(0, int((end - row.checked_in_at).total_seconds() // 60))
            if row.checked_out_at is not None:
                completed_durations.append(duration_minutes)
            phone, phone_decryption_failed = self._phone_for_display(row)
            if phone_decryption_failed:
                undecryptable_phone_count += 1
            visits.append(
                {
                    "name": row.name,
                    "code": row.identity.permanent_code if row.identity else row.active_code or "",
                    "age": row.age,
                    "phone": phone,
                    "category": row.category,
                    "status": row.status,
                    "checked_in": self.format_time(row.checked_in_at),
                    "checked_out": self.format_time(row.checked_out_at),
                    "duration_minutes": duration_minutes,
                    "visit_number": row.visit_number,
                    "entry_count": row.identity.entry_count if row.identity else row.visit_number,
                }
            )

        total = len(rows)
        active = sum(row.status == "active" for row in rows)
        exited = total - active
        vip = sum(row.category == "vip" for row in rows)
        general = total - vip
        average_duration = (
            round(sum(completed_durations) / len(completed_durations))
            if completed_durations
            else 0
        )
        return {
            "date": now_local.strftime("%Y-%m-%d"),
            "total": total,
            "active": active,
            "exited": exited,
            "vip": vip,
            "general": general,
            "average_duration_minutes": average_duration,
            "undecryptable_phone_count": undecryptable_phone_count,
            "hourly": [
                {"hour": hour, "count": count}
                for hour, count in sorted(hourly_counts.items())
            ],
            "visits": visits,
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
            "code": row.identity.permanent_code if row.identity else row.active_code or "",
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
        stmt = select(Participant).options(selectinload(Participant.identity))
        cutoff = self._public_display_cutoff(session)
        if cutoff is not None:
            stmt = stmt.where(Participant.checked_in_at >= cutoff)
        if category is not None:
            stmt = stmt.where(Participant.category == category)
        rows = session.scalars(
            stmt.order_by(desc(Participant.checked_in_at), desc(Participant.id))
        ).all()
        latest_visits: list[Participant] = []
        seen_identities: set[object] = set()
        for row in rows:
            identity_key: object = (
                ("identity", row.identity_id) if row.identity_id is not None else ("visit", row.id)
            )
            if identity_key in seen_identities:
                continue
            seen_identities.add(identity_key)
            latest_visits.append(row)

        returning_ids = [row.id for row in latest_visits if row.visit_number > 1]
        deltas_by_participant: dict[int, int] = {}
        if returning_ids:
            delta_rows = session.execute(
                select(
                    PointTransaction.participant_id,
                    func.coalesce(func.sum(PointTransaction.delta), 0),
                )
                .where(PointTransaction.participant_id.in_(returning_ids))
                .group_by(PointTransaction.participant_id)
            ).all()
            deltas_by_participant = {
                int(participant_id): int(delta) for participant_id, delta in delta_rows
            }

        scored_visits: list[tuple[Participant, int]] = []
        for row in latest_visits:
            points = row.current_points
            if row.visit_number > 1:
                start_key = (
                    "vip_start_points" if row.category == "vip" else "general_start_points"
                )
                starting_points = int(self.setting(start_key, DEFAULT_START_POINTS))
                points = max(0, starting_points + deltas_by_participant.get(row.id, 0))
            scored_visits.append((row, points))

        scored_visits.sort(key=lambda item: (-item[1], item[0].checked_in_at, item[0].id))
        leaderboard: list[dict[str, Any]] = []
        for row, points in scored_visits[:size]:
            public_row = self._public_participant(row)
            public_row["points"] = points
            leaderboard.append(public_row)
        return leaderboard

    def _traffic_in_session(self, session: Session) -> list[dict[str, Any]]:
        since = utcnow() - timedelta(hours=8)
        cutoff = self._public_display_cutoff(session)
        if cutoff is not None:
            since = max(since, cutoff)
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
                select(
                    PointTransaction,
                    Participant.name,
                    ParticipantIdentity.permanent_code,
                )
                .join(Participant, Participant.id == PointTransaction.participant_id)
                .join(ParticipantIdentity, ParticipantIdentity.id == Participant.identity_id)
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
                "참가자ID",
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
                "입장회차",
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
                        item["visit_number"],
                    ]
                )
        return ("\ufeff" + output.getvalue()).encode("utf-8")

    def export_transactions_csv(self) -> bytes:
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["시각", "이름", "변동", "잔액", "활동", "메모", "운영자"])
        with self.sessions() as session:
            rows = session.execute(
                select(PointTransaction, Participant.name)
                .join(Participant, Participant.id == PointTransaction.participant_id)
                .order_by(PointTransaction.created_at)
            ).all()
            for tx, name in rows:
                writer.writerow(
                    [
                        self.format_time(tx.created_at, include_date=True),
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
            affected_identity_ids: set[int] = set()
            for row in rows:
                if row.identity_id is not None:
                    affected_identity_ids.add(row.identity_id)
                row.name = f"삭제된 참가자 {row.id}"
                row.age = 0
                row.phone_encrypted = encrypt_text("0000000000", self.config.field_encryption_key)
                row.phone_hash = "purged-" + str(row.id)
                row.phone_last4 = "0000"
                row.leaderboard_opt_in = False
                count += 1
            session.flush()
            for identity_id in affected_identity_ids:
                remaining = session.scalar(
                    select(func.count(Participant.id)).where(
                        and_(
                            Participant.identity_id == identity_id,
                            ~Participant.phone_hash.startswith("purged-"),
                        )
                    )
                )
                identity = session.get(ParticipantIdentity, identity_id)
                if identity is not None and not remaining and not identity.is_active:
                    identity.identity_hash = f"purged-{identity.id}"
            self._audit(session, "personal_data_purged", operator, details={"count": count})
        return count

    def format_time(self, value: datetime | None, include_date: bool = False) -> str:
        if value is None:
            return "-"
        local = value.replace(tzinfo=UTC).astimezone(self.local_tz)
        return local.strftime("%m/%d %H:%M" if include_date else "%H:%M")
