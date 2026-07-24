"""Dependency health and readiness models."""

from __future__ import annotations

from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict, Field


class ComponentHealth(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str
    healthy: bool
    detail: str
    observed_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class SystemHealth(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    status: str
    ready_for_new_exposure: bool
    components: tuple[ComponentHealth, ...]
    observed_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


def combine_health(components: tuple[ComponentHealth, ...]) -> SystemHealth:
    healthy = all(component.healthy for component in components)
    return SystemHealth(
        status="HEALTHY" if healthy else "DEGRADED",
        ready_for_new_exposure=healthy,
        components=components,
    )
