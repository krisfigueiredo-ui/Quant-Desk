"""Event bus contracts and a deterministic development implementation."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable
from datetime import UTC, datetime
from threading import RLock
from typing import Protocol

from .dead_letter_queue import DeadLetter, InMemoryDeadLetterQueue
from .idempotency import IdempotencyStore
from .schemas import AgentMessage, MessageReceipt, MessageStatus, MessageType

MessageHandler = Callable[[AgentMessage], None]


class AuditSink(Protocol):
    @property
    def available(self) -> bool: ...

    def append_message(self, message: AgentMessage, receipt: MessageReceipt) -> None: ...


class InMemoryAuditSink:
    def __init__(self) -> None:
        self._records: list[tuple[AgentMessage, MessageReceipt]] = []
        self._available = True
        self._lock = RLock()

    @property
    def available(self) -> bool:
        return self._available

    def set_available(self, value: bool) -> None:
        self._available = value

    def append_message(self, message: AgentMessage, receipt: MessageReceipt) -> None:
        if not self._available:
            raise RuntimeError("audit sink unavailable")
        with self._lock:
            self._records.append((message, receipt))

    def records(self) -> tuple[tuple[AgentMessage, MessageReceipt], ...]:
        with self._lock:
            return tuple(self._records)


class InMemoryMessageBus:
    """Synchronous bus for tests and local development.

    New-exposure messages fail closed when the audit sink is unavailable.
    """

    def __init__(
        self,
        audit_sink: AuditSink,
        *,
        dead_letters: InMemoryDeadLetterQueue | None = None,
        idempotency: IdempotencyStore | None = None,
    ) -> None:
        self._audit = audit_sink
        self._dead_letters = dead_letters or InMemoryDeadLetterQueue()
        self._idempotency = idempotency or IdempotencyStore()
        self._handlers: dict[MessageType, list[MessageHandler]] = defaultdict(list)
        self._lock = RLock()

    @property
    def available(self) -> bool:
        return self._audit.available

    def subscribe(self, message_type: MessageType, handler: MessageHandler) -> None:
        with self._lock:
            self._handlers[message_type].append(handler)

    def publish(
        self,
        message: AgentMessage,
        *,
        now: datetime | None = None,
    ) -> MessageReceipt:
        instant = (now or datetime.now(UTC)).astimezone(UTC)
        if not self._audit.available:
            return MessageReceipt(
                message_id=message.message_id,
                status=MessageStatus.REJECTED,
                reason_code="AUDIT_UNAVAILABLE",
                received_at=instant,
            )
        if message.expired(instant):
            receipt = MessageReceipt(
                message_id=message.message_id,
                status=MessageStatus.EXPIRED,
                reason_code="MESSAGE_EXPIRED",
                received_at=instant,
            )
            self._audit.append_message(message, receipt)
            return receipt
        if not self._idempotency.claim(message.idempotency_key, now=instant):
            receipt = MessageReceipt(
                message_id=message.message_id,
                status=MessageStatus.DUPLICATE,
                reason_code="IDEMPOTENT_DUPLICATE",
                received_at=instant,
            )
            self._audit.append_message(message, receipt)
            return receipt

        receipt = MessageReceipt(
            message_id=message.message_id,
            status=MessageStatus.ACCEPTED,
            reason_code="ACCEPTED",
            received_at=instant,
        )
        self._audit.append_message(message, receipt)
        for handler in tuple(self._handlers.get(message.message_type, ())):
            try:
                handler(message)
            except Exception as exc:
                self._dead_letters.append(
                    DeadLetter(
                        reason_code="HANDLER_FAILURE",
                        detail=type(exc).__name__,
                        redacted_message={
                            "message_id": str(message.message_id),
                            "message_type": message.message_type.value,
                            "agent_id": message.agent_id,
                        },
                    )
                )
        return receipt

    def dead_letters(self) -> tuple[DeadLetter, ...]:
        return self._dead_letters.records()
