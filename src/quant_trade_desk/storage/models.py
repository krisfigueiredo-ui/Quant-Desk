"""SQLAlchemy source-of-truth records.

Audit and message tables are append-only through repository APIs.
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def utcnow() -> datetime:
    return datetime.now(UTC)


class Base(DeclarativeBase):
    pass


class AgentDefinitionRecord(Base):
    __tablename__ = "agent_definitions"

    id: Mapped[int] = mapped_column(primary_key=True)
    agent_id: Mapped[str] = mapped_column(String(128), index=True)
    version: Mapped[str] = mapped_column(String(32))
    definition: Mapped[dict[str, object]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    __table_args__ = (UniqueConstraint("agent_id", "version"),)


class AgentHealthRecord(Base):
    __tablename__ = "agent_health"

    id: Mapped[int] = mapped_column(primary_key=True)
    agent_id: Mapped[str] = mapped_column(String(128), index=True)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    health: Mapped[str] = mapped_column(String(32))
    metrics: Mapped[dict[str, object]] = mapped_column(JSON)


class AgentMessageRecord(Base):
    __tablename__ = "agent_messages"

    id: Mapped[int] = mapped_column(primary_key=True)
    message_id: Mapped[str] = mapped_column(String(36), unique=True, index=True)
    message_type: Mapped[str] = mapped_column(String(64), index=True)
    trace_id: Mapped[str] = mapped_column(String(36), index=True)
    correlation_id: Mapped[str] = mapped_column(String(36), index=True)
    causation_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    agent_id: Mapped[str] = mapped_column(String(128), index=True)
    schema_version: Mapped[str] = mapped_column(String(32))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    data_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    idempotency_key: Mapped[str] = mapped_column(String(256), unique=True)
    status: Mapped[str] = mapped_column(String(32))
    envelope: Mapped[dict[str, object]] = mapped_column(JSON)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class DecisionTraceRecord(Base):
    __tablename__ = "decision_traces"

    id: Mapped[int] = mapped_column(primary_key=True)
    trace_id: Mapped[str] = mapped_column(String(36), unique=True, index=True)
    status: Mapped[str] = mapped_column(String(32))
    summary: Mapped[dict[str, object]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class StrategyRecord(Base):
    __tablename__ = "strategies"

    id: Mapped[int] = mapped_column(primary_key=True)
    strategy_id: Mapped[str] = mapped_column(String(128), index=True)
    version: Mapped[str] = mapped_column(String(32))
    enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    operating_mode: Mapped[str] = mapped_column(String(32), default="PAPER")
    definition: Mapped[dict[str, object]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    __table_args__ = (UniqueConstraint("strategy_id", "version"),)


class RiskDecisionRecord(Base):
    __tablename__ = "risk_decisions"

    id: Mapped[int] = mapped_column(primary_key=True)
    risk_decision_id: Mapped[str] = mapped_column(String(36), unique=True)
    proposed_order_id: Mapped[str] = mapped_column(String(36), index=True)
    outcome: Mapped[str] = mapped_column(String(32), index=True)
    reason_codes: Mapped[list[str]] = mapped_column(JSON)
    context_checksum: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class ProposedOrderRecord(Base):
    __tablename__ = "proposed_orders"

    id: Mapped[int] = mapped_column(primary_key=True)
    proposed_order_id: Mapped[str] = mapped_column(String(36), unique=True)
    trace_id: Mapped[str] = mapped_column(String(36), index=True)
    strategy_id: Mapped[str] = mapped_column(String(128), index=True)
    symbol: Mapped[str] = mapped_column(String(32), index=True)
    asset_class: Mapped[str] = mapped_column(String(16))
    payload: Mapped[dict[str, object]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class BrokerOrderRecord(Base):
    __tablename__ = "broker_orders"

    id: Mapped[int] = mapped_column(primary_key=True)
    broker_order_id: Mapped[str | None] = mapped_column(String(256), index=True)
    client_order_id: Mapped[str] = mapped_column(String(128), unique=True)
    proposed_order_id: Mapped[str] = mapped_column(String(36), index=True)
    adapter_id: Mapped[str] = mapped_column(String(128))
    state: Mapped[str] = mapped_column(String(32), index=True)
    payload: Mapped[dict[str, object]] = mapped_column(JSON)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class FillRecord(Base):
    __tablename__ = "fills"

    id: Mapped[int] = mapped_column(primary_key=True)
    fill_id: Mapped[str] = mapped_column(String(256), unique=True)
    broker_order_id: Mapped[str] = mapped_column(String(256), index=True)
    strategy_lot_id: Mapped[str] = mapped_column(String(36), index=True)
    quantity: Mapped[float] = mapped_column(Numeric(30, 12))
    price: Mapped[float] = mapped_column(Numeric(30, 12))
    filled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class AccountSnapshotRecord(Base):
    __tablename__ = "account_snapshots"

    id: Mapped[int] = mapped_column(primary_key=True)
    account_id_hash: Mapped[str] = mapped_column(String(64), index=True)
    verified_equity: Mapped[float] = mapped_column(Numeric(30, 8))
    cash: Mapped[float] = mapped_column(Numeric(30, 8))
    buying_power: Mapped[float] = mapped_column(Numeric(30, 8))
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class KillSwitchRecord(Base):
    __tablename__ = "kill_switch_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    incident_id: Mapped[str] = mapped_column(String(128), index=True)
    activated: Mapped[bool] = mapped_column(Boolean)
    reason_code: Mapped[str] = mapped_column(String(128))
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class ConfigurationVersionRecord(Base):
    __tablename__ = "configuration_versions"

    id: Mapped[int] = mapped_column(primary_key=True)
    config_type: Mapped[str] = mapped_column(String(64), index=True)
    version: Mapped[str] = mapped_column(String(64))
    checksum: Mapped[str] = mapped_column(String(64))
    payload: Mapped[dict[str, object]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    __table_args__ = (UniqueConstraint("config_type", "version"),)


class AuditEventRecord(Base):
    __tablename__ = "audit_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    event_id: Mapped[str] = mapped_column(String(36), unique=True)
    event_type: Mapped[str] = mapped_column(String(64), index=True)
    actor_id: Mapped[str] = mapped_column(String(128), index=True)
    trace_id: Mapped[str | None] = mapped_column(String(36), index=True)
    reason_code: Mapped[str] = mapped_column(String(128))
    details: Mapped[dict[str, object]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class IncidentRecord(Base):
    __tablename__ = "incidents"

    id: Mapped[int] = mapped_column(primary_key=True)
    incident_id: Mapped[str] = mapped_column(String(128), unique=True)
    severity: Mapped[str] = mapped_column(String(32))
    status: Mapped[str] = mapped_column(String(32))
    summary: Mapped[str] = mapped_column(Text)
    forensic_data: Mapped[dict[str, object]] = mapped_column(JSON)
    opened_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
