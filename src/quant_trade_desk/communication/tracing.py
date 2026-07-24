"""Trace-context helpers."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID, uuid4


@dataclass(frozen=True, slots=True)
class TraceContext:
    trace_id: UUID
    correlation_id: UUID
    causation_id: UUID | None = None

    @classmethod
    def root(cls) -> TraceContext:
        trace_id = uuid4()
        return cls(trace_id=trace_id, correlation_id=uuid4())

    def caused_by(self, message_id: UUID) -> TraceContext:
        return TraceContext(
            trace_id=self.trace_id,
            correlation_id=self.correlation_id,
            causation_id=message_id,
        )
