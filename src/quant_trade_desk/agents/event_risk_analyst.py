"""Confirmed-event and contradiction-aware event risk."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from pydantic import BaseModel, ConfigDict

from quant_trade_desk.communication.schemas import EventRiskPayload


class EventRecord(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    event_id: str
    category: str
    summary: str
    source_id: str
    published_at: datetime
    confirmed: bool
    severity: str
    execution_unsafe: bool = False


class EventRiskAnalyst:
    agent_id = "news-event-risk-analyst"
    version = "1.0.0"

    def assess(
        self,
        events: tuple[EventRecord, ...],
        *,
        now: datetime | None = None,
        maximum_age: timedelta = timedelta(days=7),
    ) -> EventRiskPayload:
        instant = (now or datetime.now(UTC)).astimezone(UTC)
        deduplicated: dict[str, EventRecord] = {}
        contradictions: list[str] = []
        for event in events:
            existing = deduplicated.get(event.event_id)
            if existing and (
                existing.confirmed != event.confirmed or existing.summary != event.summary
            ):
                contradictions.append(event.event_id)
            if existing is None or event.published_at > existing.published_at:
                deduplicated[event.event_id] = event
        current = [
            event
            for event in deduplicated.values()
            if timedelta(0) <= instant - event.published_at.astimezone(UTC) <= maximum_age
        ]
        confirmed = tuple(event.summary for event in current if event.confirmed)
        unconfirmed = tuple(event.summary for event in current if not event.confirmed)
        blocked = bool(contradictions) or any(
            event.confirmed and event.execution_unsafe for event in current
        )
        reasons: list[str] = []
        if contradictions:
            reasons.append("CONTRADICTORY_REPORTS")
        if any(event.confirmed and event.execution_unsafe for event in current):
            reasons.append("CONFIRMED_EXECUTION_UNSAFE_EVENT")
        return EventRiskPayload(
            event_block=blocked,
            confirmed_events=confirmed,
            unconfirmed_reports=unconfirmed,
            contradictions=tuple(contradictions),
            reason_codes=tuple(reasons),
        )
