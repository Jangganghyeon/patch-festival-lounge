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
from .security import is_display_code, new_display_code, new_internal_record_key

DB_WRITE_LOCK = RLock()


class Base(DeclarativeBase):
    pass


class Participant(Base):
    __tablename__ = "participants"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    legacy_key: Mapped[str] = mapped_column("display_code", String(8), unique=True, index=True)
    active_code: Mapped[str | None] = mapped_column(String(2), nullable=True, unique=True, index=True)
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
            connection.execute(text("ALTER TABLE participants ADD COLUMN active_code VARCHAR(2)"))
        connection.execute(
            text(
                "CREATE UNIQUE INDEX IF NOT EXISTS ix_participants_active_code "
                "ON participants (active_code)"
            )
        )
    factory = sessionmaker(bind=engine, expire_on_commit=False, future=True)
    with factory.begin() as session:
        for key, value in DEFAULT_SETTINGS.items():
            if session.get(AppSetting, key) is None:
                session.add(AppSetting(key=key, value=value))
        participants = session.scalars(select(Participant).order_by(Participant.id)).all()
        used_codes = {
            row.active_code for row in participants if is_display_code(row.active_code or "")
        }
        used_keys = {row.legacy_key for row in participants}
        for participant in participants:
            if participant.status == "active":
                if not is_display_code(participant.active_code or ""):
                    legacy_code = participant.legacy_key
                    if is_display_code(legacy_code) and legacy_code not in used_codes:
                        participant.active_code = legacy_code
                    else:
                        participant.active_code = new_display_code(used_codes)
                    used_codes.add(participant.active_code)
            else:
                participant.active_code = None

            if not participant.legacy_key.startswith("~"):
                replacement = new_internal_record_key(used_keys)
                used_keys.add(replacement)
                participant.legacy_key = replacement

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
