"""Append-only persistence repositories."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from quant_trade_desk.communication.schemas import AgentMessage, MessageReceipt

from .database import Database
from .models import AgentMessageRecord, AuditEventRecord


class SqlAuditSink:
    def __init__(self, database: Database) -> None:
        self.database = database

    @property
    def available(self) -> bool:
        return self.database.ping()

    def append_message(self, message: AgentMessage, receipt: MessageReceipt) -> None:
        envelope = message.model_dump(mode="json")
        with self.database.sessions.begin() as session:
            session.add(
                AgentMessageRecord(
                    message_id=str(message.message_id),
                    message_type=message.message_type.value,
                    trace_id=str(message.trace_id),
                    correlation_id=str(message.correlation_id),
                    causation_id=(str(message.causation_id) if message.causation_id else None),
                    agent_id=message.agent_id,
                    schema_version=message.schema_version,
                    created_at=message.created_at,
                    data_timestamp=message.data_timestamp,
                    expires_at=message.expires_at,
                    idempotency_key=message.idempotency_key,
                    status=receipt.status.value,
                    envelope=envelope,
                    recorded_at=datetime.now(UTC),
                )
            )
            try:
                session.flush()
            except IntegrityError as exc:
                raise ValueError("duplicate immutable message") from exc

    def messages_for_trace(self, trace_id: str) -> tuple[dict[str, object], ...]:
        with self.database.sessions() as session:
            rows = session.scalars(
                select(AgentMessageRecord)
                .where(AgentMessageRecord.trace_id == trace_id)
                .order_by(AgentMessageRecord.created_at)
            ).all()
            return tuple(row.envelope for row in rows)


class SqlControlAuditSink:
    """Append-only audit events for authenticated operator controls."""

    def __init__(self, database: Database) -> None:
        self.database = database

    def append(
        self,
        *,
        event_type: str,
        actor_id: str,
        reason_code: str,
        details: dict[str, object],
    ) -> str:
        event_id = str(uuid4())
        with self.database.sessions.begin() as session:
            session.add(
                AuditEventRecord(
                    event_id=event_id,
                    event_type=event_type,
                    actor_id=actor_id,
                    trace_id=None,
                    reason_code=reason_code,
                    details=details,
                    created_at=datetime.now(UTC),
                )
            )
        return event_id
