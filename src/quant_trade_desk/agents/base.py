"""Common agent contracts."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from quant_trade_desk.communication.schemas import AgentMessage, MessageType


class HealthState(StrEnum):
    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    UNHEALTHY = "UNHEALTHY"
    STOPPED = "STOPPED"


class RetryPolicy(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    max_attempts: int = Field(default=2, ge=0, le=5)
    initial_delay_seconds: float = Field(default=0.5, ge=0, le=30)
    maximum_delay_seconds: float = Field(default=5, ge=0, le=60)
    retryable_errors: tuple[str, ...] = ("TIMEOUT", "TEMPORARY_UNAVAILABLE")


class AgentDefinition(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    agent_id: str
    name: str
    version: str
    responsibility: str
    allowed_inputs: tuple[MessageType, ...]
    allowed_outputs: tuple[MessageType, ...]
    prohibited_actions: tuple[str, ...]
    timeout_seconds: float = Field(ge=0.1, le=300)
    retry_policy: RetryPolicy
    failure_behavior: str


class AgentMetrics(BaseModel):
    model_config = ConfigDict(extra="forbid")

    messages_processed: int = 0
    messages_produced: int = 0
    errors: int = 0
    timeouts: int = 0
    retries: int = 0
    approvals: int = 0
    rejections: int = 0
    total_latency_ms: float = 0.0

    @property
    def average_latency_ms(self) -> float:
        if self.messages_processed == 0:
            return 0.0
        return self.total_latency_ms / self.messages_processed


class AgentRuntime(BaseModel):
    model_config = ConfigDict(extra="forbid")

    definition: AgentDefinition
    health: HealthState = HealthState.HEALTHY
    last_heartbeat: datetime = Field(default_factory=lambda: datetime.now(UTC))
    current_task: str | None = None
    confidence: float = Field(default=0, ge=0, le=1)
    metrics: AgentMetrics = Field(default_factory=AgentMetrics)

    def accept(self, message: AgentMessage) -> None:
        if message.message_type not in self.definition.allowed_inputs:
            self.metrics.errors += 1
            raise ValueError(
                f"{self.definition.agent_id} cannot accept {message.message_type.value}"
            )
        self.metrics.messages_processed += 1
        self.last_heartbeat = datetime.now(UTC)
