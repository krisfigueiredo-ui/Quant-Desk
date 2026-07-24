from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

import pytest
from pydantic import ValidationError

from quant_trade_desk.communication.message_bus import (
    InMemoryAuditSink,
    InMemoryMessageBus,
)
from quant_trade_desk.communication.schemas import (
    AgentMessage,
    AssetClass,
    MessageStatus,
    MessageType,
)


def _message(now: object, key: str = "fixture-key-0001") -> AgentMessage:
    from datetime import datetime

    assert isinstance(now, datetime)
    return AgentMessage(
        message_type=MessageType.SYSTEM_ALERT,
        agent_id="auditor-communication-reporter",
        agent_version="1.0.0",
        asset_class=AssetClass.SYSTEM,
        created_at=now,
        data_timestamp=now,
        expires_at=now + timedelta(minutes=1),
        confidence=Decimal("1"),
        uncertainty=Decimal("0"),
        payload={"code": "FIXTURE", "summary": "safe"},
        idempotency_key=key,
    )


def test_sensitive_payload_fields_are_rejected(now: object) -> None:
    from datetime import datetime

    assert isinstance(now, datetime)
    with pytest.raises(ValidationError, match="sensitive field"):
        AgentMessage(
            message_type=MessageType.SYSTEM_ALERT,
            agent_id="auditor-communication-reporter",
            agent_version="1.0.0",
            asset_class=AssetClass.SYSTEM,
            created_at=now,
            data_timestamp=now,
            expires_at=now + timedelta(minutes=1),
            confidence=Decimal("1"),
            uncertainty=Decimal("0"),
            payload={"api_key": "prohibited"},
            idempotency_key="fixture-sensitive-0001",
        )


def test_message_bus_rejects_expired_and_duplicates(now: object) -> None:
    from datetime import datetime

    assert isinstance(now, datetime)
    audit = InMemoryAuditSink()
    bus = InMemoryMessageBus(audit)
    message = _message(now)
    first = bus.publish(message, now=now)
    duplicate = bus.publish(message, now=now)
    expired = bus.publish(
        _message(now, "fixture-key-expired"),
        now=now + timedelta(minutes=2),
    )
    assert first.status == MessageStatus.ACCEPTED
    assert duplicate.status == MessageStatus.DUPLICATE
    assert expired.status == MessageStatus.EXPIRED


def test_audit_failure_blocks_message(now: object) -> None:
    audit = InMemoryAuditSink()
    audit.set_available(False)
    receipt = InMemoryMessageBus(audit).publish(_message(now))
    assert receipt.status == MessageStatus.REJECTED
    assert receipt.reason_code == "AUDIT_UNAVAILABLE"


def test_agent_cannot_emit_an_unauthorized_message_type(now: object) -> None:
    unauthorized = _message(now).model_copy(update={"agent_id": "equity-market-scanner"})
    receipt = InMemoryMessageBus(InMemoryAuditSink()).publish(
        unauthorized,
        now=now,  # type: ignore[arg-type]
    )
    assert receipt.status == MessageStatus.REJECTED
    assert receipt.reason_code == "PRODUCER_PERMISSION_DENIED"
