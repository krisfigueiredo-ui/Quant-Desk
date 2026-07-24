"""Versioned message and decision schemas.

Every agent transition creates a new immutable message. Messages never contain
credentials or free-form hidden reasoning.
"""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from decimal import Decimal
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)


class AssetClass(StrEnum):
    EQUITY = "EQUITY"
    CRYPTO = "CRYPTO"
    CASH = "CASH"
    SYSTEM = "SYSTEM"


class Side(StrEnum):
    BUY = "BUY"
    SELL = "SELL"


class OrderType(StrEnum):
    LIMIT = "LIMIT"
    MARKET = "MARKET"
    STOP = "STOP"
    STOP_LIMIT = "STOP_LIMIT"


class TimeInForce(StrEnum):
    DAY = "DAY"
    GTC = "GTC"
    IOC = "IOC"


class TradingHorizon(StrEnum):
    DAY = "DAY"
    SWING = "SWING"
    LONG_TERM = "LONG_TERM"


class MessageStatus(StrEnum):
    CREATED = "CREATED"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"
    DUPLICATE = "DUPLICATE"
    FAILED = "FAILED"


class MessageType(StrEnum):
    MARKET_OBSERVATION = "MarketObservation"
    SCANNER_CANDIDATE = "ScannerCandidate"
    TECHNICAL_ASSESSMENT = "TechnicalAssessment"
    FUNDAMENTAL_ASSESSMENT = "FundamentalAssessment"
    EVENT_RISK_ASSESSMENT = "EventRiskAssessment"
    STRATEGY_SIGNAL = "StrategySignal"
    TRADE_INTENT = "TradeIntent"
    PORTFOLIO_DECISION = "PortfolioDecision"
    PROPOSED_ORDER = "ProposedOrder"
    RISK_DECISION = "RiskDecision"
    EXECUTION_REQUEST = "ExecutionRequest"
    BROKER_ACKNOWLEDGEMENT = "BrokerAcknowledgement"
    ORDER_STATUS_UPDATE = "OrderStatusUpdate"
    FILL_UPDATE = "FillUpdate"
    POSITION_UPDATE = "PositionUpdate"
    AGENT_HEALTH_UPDATE = "AgentHealthUpdate"
    SYSTEM_ALERT = "SystemAlert"
    KILL_SWITCH_EVENT = "KillSwitchEvent"
    PLATEAU_EVENT = "PlateauEvent"
    STRATEGY_DECAY_EVENT = "StrategyDecayEvent"
    CONFLICT_EVENT = "ConflictEvent"
    AUDIT_EVENT = "AuditEvent"


class FrozenModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class SourceReference(FrozenModel):
    source_id: str = Field(min_length=1, max_length=128)
    source_type: str = Field(min_length=1, max_length=64)
    uri: str | None = Field(default=None, max_length=2048)
    observed_at: datetime
    checksum: str | None = Field(default=None, max_length=128)

    @field_validator("observed_at")
    @classmethod
    def timezone_required(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("source timestamp must be timezone-aware")
        return value.astimezone(UTC)


class EvidenceItem(FrozenModel):
    kind: str = Field(min_length=1, max_length=64)
    metric: str = Field(min_length=1, max_length=128)
    value: Decimal | str | bool
    interpretation: str = Field(min_length=1, max_length=500)
    source_id: str | None = Field(default=None, max_length=128)


class MarketObservationPayload(FrozenModel):
    bid: Decimal | None = Field(default=None, ge=0)
    ask: Decimal | None = Field(default=None, ge=0)
    last: Decimal = Field(gt=0)
    volume: Decimal | None = Field(default=None, ge=0)
    average_dollar_volume: Decimal | None = Field(default=None, ge=0)
    spread_bps: Decimal | None = Field(default=None, ge=0)
    session: str
    market_open: bool
    quality_flags: tuple[str, ...] = ()

    @model_validator(mode="after")
    def valid_quote(self) -> MarketObservationPayload:
        if self.bid is not None and self.ask is not None and self.bid > self.ask:
            raise ValueError("bid cannot exceed ask")
        return self


class ScannerCandidatePayload(FrozenModel):
    rank: int = Field(ge=1)
    score: Decimal
    eligible: bool
    metrics: dict[str, Decimal | str | bool]
    rejection_reasons: tuple[str, ...] = ()


class AssessmentPayload(FrozenModel):
    score: Decimal = Field(ge=0, le=100)
    decision: str
    bullish_evidence: tuple[EvidenceItem, ...] = ()
    bearish_evidence: tuple[EvidenceItem, ...] = ()
    entry_zone_low: Decimal | None = Field(default=None, ge=0)
    entry_zone_high: Decimal | None = Field(default=None, ge=0)
    invalidation_level: Decimal | None = Field(default=None, ge=0)
    stop_framework: str | None = None
    exit_framework: str | None = None
    time_horizon: str
    reject_reason: str | None = None


class FundamentalAssessmentPayload(FrozenModel):
    score: Decimal | None = Field(default=None, ge=0, le=100)
    reported_facts: dict[str, Decimal | str | bool | None] = Field(default_factory=dict)
    calculated_metrics: dict[str, Decimal | str | bool | None] = Field(default_factory=dict)
    third_party_estimates: dict[str, Decimal | str | bool | None] = Field(default_factory=dict)
    interpretation: tuple[str, ...] = ()
    missing_data: tuple[str, ...] = ()
    decision: str


class EventRiskPayload(FrozenModel):
    event_block: bool
    confirmed_events: tuple[str, ...] = ()
    unconfirmed_reports: tuple[str, ...] = ()
    contradictions: tuple[str, ...] = ()
    next_known_event_at: datetime | None = None
    reason_codes: tuple[str, ...] = ()


class TradeIntentPayload(FrozenModel):
    intent_id: UUID = Field(default_factory=uuid4)
    side: Side
    quantity: Decimal = Field(gt=0)
    order_type: OrderType = OrderType.LIMIT
    limit_price: Decimal | None = Field(default=None, gt=0)
    stop_price: Decimal | None = Field(default=None, gt=0)
    time_in_force: TimeInForce = TimeInForce.DAY
    expected_holding_seconds: int = Field(gt=0)
    invalidation_reason: str
    planned_loss: Decimal = Field(ge=0)
    risk_reducing: bool = False
    time_horizon: TradingHorizon = TradingHorizon.DAY

    @model_validator(mode="after")
    def limit_requires_price(self) -> TradeIntentPayload:
        if self.order_type in {OrderType.LIMIT, OrderType.STOP_LIMIT}:
            if self.limit_price is None:
                raise ValueError("limit price is required for limit orders")
        return self


class PortfolioDecisionPayload(FrozenModel):
    approved: bool
    desired_weight: Decimal = Field(ge=0, le=1)
    allocated_quantity: Decimal = Field(ge=0)
    strategy_lot_id: UUID
    conflicts: tuple[str, ...] = ()
    reason_codes: tuple[str, ...] = ()


class ProposedOrderPayload(FrozenModel):
    proposed_order_id: UUID = Field(default_factory=uuid4)
    account_id: str = Field(min_length=1, max_length=128)
    side: Side
    quantity: Decimal = Field(gt=0)
    order_type: OrderType
    limit_price: Decimal | None = Field(default=None, gt=0)
    stop_price: Decimal | None = Field(default=None, gt=0)
    time_in_force: TimeInForce
    strategy_lot_id: UUID
    risk_reducing: bool = False
    max_slippage_bps: Decimal = Field(ge=0)
    planned_loss: Decimal = Field(default=Decimal("0"), ge=0)
    time_horizon: TradingHorizon = TradingHorizon.DAY


def proposed_order_checksum(order: ProposedOrderPayload) -> str:
    canonical = json.dumps(
        order.model_dump(mode="json"),
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(canonical.encode()).hexdigest()


class RiskOutcome(StrEnum):
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    RISK_REDUCING_ONLY = "RISK_REDUCING_ONLY"
    REQUIRES_MANUAL_REVIEW = "REQUIRES_MANUAL_REVIEW"


class RiskDecisionPayload(FrozenModel):
    risk_decision_id: UUID = Field(default_factory=uuid4)
    proposed_order_id: UUID
    outcome: RiskOutcome
    reason_codes: tuple[str, ...]
    approved_quantity: Decimal = Field(ge=0)
    valid_until: datetime
    risk_config_version: str
    proposed_order_checksum: str = Field(min_length=64, max_length=64)
    verified_account_equity: Decimal = Field(gt=0)
    context_checksum: str


class ExecutionRequestPayload(FrozenModel):
    execution_request_id: UUID = Field(default_factory=uuid4)
    proposed_order: ProposedOrderPayload
    risk_decision: RiskDecisionPayload
    operating_mode_authorization_id: UUID
    adapter_id: str


class BrokerAcknowledgementPayload(FrozenModel):
    broker_order_id: str | None = Field(default=None, max_length=256)
    client_order_id: str
    accepted: bool
    broker_status: str
    reason_code: str | None = None


class OrderStatusPayload(FrozenModel):
    broker_order_id: str
    client_order_id: str
    status: str
    filled_quantity: Decimal = Field(ge=0)
    remaining_quantity: Decimal = Field(ge=0)
    average_fill_price: Decimal | None = Field(default=None, ge=0)
    status_uncertain: bool = False


class FillPayload(FrozenModel):
    broker_order_id: str
    fill_id: str
    quantity: Decimal = Field(gt=0)
    price: Decimal = Field(gt=0)
    fee: Decimal = Field(default=Decimal("0"), ge=0)
    filled_at: datetime


class HealthPayload(FrozenModel):
    health: str
    current_task: str | None = None
    latency_ms: Decimal = Field(default=Decimal("0"), ge=0)
    error_count: int = Field(default=0, ge=0)
    timeout_count: int = Field(default=0, ge=0)
    messages_processed: int = Field(default=0, ge=0)


class AlertPayload(FrozenModel):
    severity: str
    code: str
    summary: str
    recommended_action: str | None = None


SENSITIVE_KEYS = {
    "api_key",
    "secret",
    "token",
    "password",
    "private_key",
    "cookie",
    "session",
    "account_number",
}


def _reject_sensitive(value: Any, path: str = "payload") -> None:
    if isinstance(value, BaseModel):
        _reject_sensitive(value.model_dump(mode="python"), path)
    elif isinstance(value, dict):
        for key, nested in value.items():
            normalized = str(key).lower()
            if normalized in SENSITIVE_KEYS or any(
                fragment in normalized for fragment in ("password", "private_key", "api_secret")
            ):
                raise ValueError(f"sensitive field prohibited in message: {path}.{key}")
            _reject_sensitive(nested, f"{path}.{key}")
    elif isinstance(value, (list, tuple)):
        for index, nested in enumerate(value):
            _reject_sensitive(nested, f"{path}[{index}]")


MessagePayload = (
    MarketObservationPayload
    | ScannerCandidatePayload
    | AssessmentPayload
    | FundamentalAssessmentPayload
    | EventRiskPayload
    | TradeIntentPayload
    | PortfolioDecisionPayload
    | ProposedOrderPayload
    | RiskDecisionPayload
    | ExecutionRequestPayload
    | BrokerAcknowledgementPayload
    | OrderStatusPayload
    | FillPayload
    | HealthPayload
    | AlertPayload
    | dict[str, Any]
)


class AgentMessage(FrozenModel):
    """Immutable, versioned envelope for all inter-agent communication."""

    message_id: UUID = Field(default_factory=uuid4)
    message_type: MessageType
    schema_version: str = Field(default="1.0.0", pattern=r"^\d+\.\d+\.\d+$")
    trace_id: UUID = Field(default_factory=uuid4)
    correlation_id: UUID = Field(default_factory=uuid4)
    causation_id: UUID | None = None
    agent_id: str = Field(min_length=1, max_length=128)
    agent_version: str = Field(min_length=1, max_length=32)
    strategy_id: str | None = Field(default=None, max_length=128)
    asset_class: AssetClass
    symbol: str | None = Field(default=None, max_length=32)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    data_timestamp: datetime
    expires_at: datetime
    confidence: Decimal = Field(ge=0, le=1)
    uncertainty: Decimal = Field(ge=0, le=1)
    source_references: tuple[SourceReference, ...] = ()
    payload: MessagePayload
    status: MessageStatus = MessageStatus.CREATED
    idempotency_key: str = Field(min_length=8, max_length=256)

    @field_validator("created_at", "data_timestamp", "expires_at")
    @classmethod
    def timestamps_are_utc(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("message timestamps must be timezone-aware")
        return value.astimezone(UTC)

    @field_validator("symbol")
    @classmethod
    def normalize_symbol(cls, value: str | None) -> str | None:
        return value.strip().upper() if value else value

    @model_validator(mode="after")
    def validate_envelope(self) -> AgentMessage:
        if self.expires_at <= self.created_at:
            raise ValueError("expires_at must be after created_at")
        if self.data_timestamp > self.created_at:
            raise ValueError("data_timestamp cannot be after created_at")
        _reject_sensitive(self.payload)
        return self

    def expired(self, at: datetime | None = None) -> bool:
        instant = (at or datetime.now(UTC)).astimezone(UTC)
        return instant >= self.expires_at


class MessageReceipt(FrozenModel):
    message_id: UUID
    status: MessageStatus
    reason_code: str
    received_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
