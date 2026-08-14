from __future__ import annotations

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
)
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, sessionmaker

from .config import RuntimeConfig, load_config

DB_WRITE_LOCK = RLock()


class Base(DeclarativeBase):
    pass


class Participant(Base):
    __tablename__ = "participants"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    display_code: Mapped[str] = mapped_column(String(8), unique=True, index=True)
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


class AdminUser(Base):
    __tablename__ = "admin_users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(Text)
    role: Mapped[str] = mapped_column(String(12), default="admin")
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime)


DEFAULT_SETTINGS = {
    "event_name": "PATCH FESTIVAL LOUNGE",
    "event_subtitle": "Software Club Festival · Live Operations",
    "general_start_points": "0",
    "vip_start_points": "20",
    "leaderboard_size": "10",
    "privacy_retention_days": "30",
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
    factory = sessionmaker(bind=engine, expire_on_commit=False, future=True)
    with factory.begin() as session:
        for key, value in DEFAULT_SETTINGS.items():
            if session.get(AppSetting, key) is None:
                session.add(AppSetting(key=key, value=value))
    return engine, factory
