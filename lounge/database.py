from __future__ import annotations

import json
from datetime import datetime
from threading import RLock

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    create_engine,
    event,
    inspect,
    select,
    text,
)
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, sessionmaker

from .config import RuntimeConfig, load_config
from .security import (
    identity_digest_from_phone_hash,
    is_display_code,
    new_display_code,
    new_internal_record_key,
)

DB_WRITE_LOCK = RLock()


class Base(DeclarativeBase):
    pass


class ParticipantIdentity(Base):
    __tablename__ = "participant_identities"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    identity_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    permanent_code: Mapped[str] = mapped_column(String(4), unique=True, index=True)
    entry_count: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, index=True)

    participants: Mapped[list["Participant"]] = relationship(back_populates="identity")


class Participant(Base):
    __tablename__ = "participants"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    legacy_key: Mapped[str] = mapped_column("display_code", String(8), unique=True, index=True)
    active_code: Mapped[str | None] = mapped_column(String(4), nullable=True, unique=True, index=True)
    identity_id: Mapped[int | None] = mapped_column(
        ForeignKey("participant_identities.id"), nullable=True, index=True
    )
    visit_number: Mapped[int] = mapped_column(Integer, default=1)
    name: Mapped[str] = mapped_column(String(40), index=True)
    age: Mapped[int] = mapped_column(Integer)
    phone_encrypted: Mapped[str] = mapped_column(Text)
    phone_hash: Mapped[str] = mapped_column(String(64), index=True)
    phone_last4: Mapped[str] = mapped_column(String(4), index=True)
    category: Mapped[str] = mapped_column(String(12), default="general", index=True)
    status: Mapped[str] = mapped_column(String(12), default="active", index=True)
    current_points: Mapped[int] = mapped_column(Integer, default=0)
    final_points: Mapped[int | None] = mapped_column(Integer, nullable=True)
    leaderboard_opt_in: Mapped[bool] = mapped_column(Boolean, default=False)
    privacy_consent: Mapped[bool] = mapped_column(Boolean, default=False)
    checked_in_at: Mapped[datetime] = mapped_column(DateTime, index=True)
    checked_out_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True)
    exit_note: Mapped[str] = mapped_column(String(200), default="")

    transactions: Mapped[list["PointTransaction"]] = relationship(
        back_populates="participant", cascade="all, delete-orphan"
    )
    identity: Mapped[ParticipantIdentity | None] = relationship(back_populates="participants")

    __table_args__ = (Index("ix_participant_search", "status", "name", "phone_last4"),)


class PointTransaction(Base):
    __tablename__ = "point_transactions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    participant_id: Mapped[int] = mapped_column(ForeignKey("participants.id", ondelete="CASCADE"), index=True)
    delta: Mapped[int] = mapped_column(Integer)
    balance_after: Mapped[int] = mapped_column(Integer)
    activity: Mapped[str] = mapped_column(String(80))
    note: Mapped[str] = mapped_column(String(200), default="")
    operator: Mapped[str] = mapped_column(String(40))
    created_at: Mapped[datetime] = mapped_column(DateTime, index=True)

    participant: Mapped[Participant] = relationship(back_populates="transactions")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    action: Mapped[str] = mapped_column(String(40), index=True)
    participant_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    operator: Mapped[str] = mapped_column(String(40))
    details: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime, index=True)


class AppSetting(Base):
    __tablename__ = "app_settings"

    key: Mapped[str] = mapped_column(String(80), primary_key=True)
    value: Mapped[str] = mapped_column(Text)


DEFAULT_SETTINGS = {
    "event_name": "PATCH FESTIVAL LOUNGE",
    "event_subtitle": "Software Club Festival · Live Operations",
    "general_start_points": "0",
    "vip_start_points": "20",
    "leaderboard_size": "10",
    "privacy_retention_days": "30",
    "public_display_reset_at": "",
}


def create_db(config: RuntimeConfig | None = None) -> tuple[Engine, sessionmaker]:
    runtime = config or load_config()
    connect_args: dict[str, object] = {}
    if runtime.database_url.startswith("sqlite"):
        connect_args = {"check_same_thread": False, "timeout": 30}
    engine = create_engine(
        runtime.database_url,
        future=True,
        pool_pre_ping=True,
        connect_args=connect_args,
    )

    if runtime.database_url.startswith("sqlite"):

        @event.listens_for(engine, "connect")
        def _set_sqlite_pragma(dbapi_connection, _connection_record) -> None:
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA busy_timeout=30000")
            cursor.close()

    Base.metadata.create_all(engine)
    with engine.begin() as connection:
        columns = {column["name"] for column in inspect(connection).get_columns("participants")}
        if "active_code" not in columns:
            connection.execute(text("ALTER TABLE participants ADD COLUMN active_code VARCHAR(4)"))
        if "identity_id" not in columns:
            connection.execute(text("ALTER TABLE participants ADD COLUMN identity_id INTEGER"))
        if "visit_number" not in columns:
            connection.execute(
                text("ALTER TABLE participants ADD COLUMN visit_number INTEGER NOT NULL DEFAULT 1")
            )
        connection.execute(
            text(
                "CREATE UNIQUE INDEX IF NOT EXISTS ix_participants_active_code "
                "ON participants (active_code)"
            )
        )
        connection.execute(
            text(
                "CREATE INDEX IF NOT EXISTS ix_participants_identity_id "
                "ON participants (identity_id)"
            )
        )
    factory = sessionmaker(bind=engine, expire_on_commit=False, future=True)
    with factory.begin() as session:
        for key, value in DEFAULT_SETTINGS.items():
            if session.get(AppSetting, key) is None:
                session.add(AppSetting(key=key, value=value))

        participants = session.scalars(select(Participant).order_by(Participant.id)).all()
        preferred_codes = {
            row.id: (
                row.active_code
                if is_display_code(row.active_code or "")
                else row.legacy_key if is_display_code(row.legacy_key) else ""
            )
            for row in participants
        }
        for participant in participants:
            participant.active_code = None
        session.flush()

        identities = session.scalars(select(ParticipantIdentity)).all()
        identities_by_hash = {row.identity_hash: row for row in identities}
        used_codes = {row.permanent_code for row in identities}
        used_keys = {row.legacy_key for row in participants}
        grouped: dict[int, list[Participant]] = {}

        for participant in participants:
            fingerprint = identity_digest_from_phone_hash(
                participant.name,
                participant.phone_hash,
                runtime.field_encryption_key,
            )
            identity = identities_by_hash.get(fingerprint)
            if identity is None:
                preferred = preferred_codes[participant.id]
                code = preferred if preferred and preferred not in used_codes else new_display_code(used_codes)
                identity = ParticipantIdentity(
                    identity_hash=fingerprint,
                    permanent_code=code,
                    entry_count=0,
                    is_active=False,
                    created_at=participant.checked_in_at,
                )
                session.add(identity)
                session.flush()
                identities_by_hash[fingerprint] = identity
                used_codes.add(code)
            participant.identity_id = identity.id
            grouped.setdefault(identity.id, []).append(participant)

            if not participant.legacy_key.startswith("~"):
                replacement = new_internal_record_key(used_keys)
                used_keys.add(replacement)
                participant.legacy_key = replacement

        for identity in identities_by_hash.values():
            rows = grouped.get(identity.id, [])
            if not rows:
                continue
            rows.sort(key=lambda row: (row.checked_in_at, row.id))
            for visit_number, participant in enumerate(rows, start=1):
                participant.visit_number = visit_number
            identity.entry_count = max(identity.entry_count, len(rows))
            active_rows = [row for row in rows if row.status == "active"]
            current = active_rows[-1] if active_rows else None
            for stale_active in active_rows[:-1]:
                stale_active.status = "exited"
                stale_active.checked_out_at = stale_active.checked_out_at or current.checked_in_at
                stale_active.final_points = stale_active.current_points
            identity.is_active = current is not None
            if current is not None:
                current.active_code = identity.permanent_code

        for log in session.scalars(select(AuditLog)).all():
            try:
                details = json.loads(log.details or "{}")
            except json.JSONDecodeError:
                details = {}
            if isinstance(details, dict):
                details.pop("code", None)
                details.pop("command", None)
                log.details = json.dumps(details, ensure_ascii=False)

        for transaction in session.scalars(
            select(PointTransaction).where(
                PointTransaction.activity == "칩 사용·게임 점수 기록"
            )
        ).all():
            transaction.note = " · ".join(transaction.note.split(" · ")[:2])
    return engine, factory
