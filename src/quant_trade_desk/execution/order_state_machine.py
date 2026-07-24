"""Order lifecycle transitions with unknown-state quarantine."""

from __future__ import annotations

from dataclasses import dataclass

from .models import BrokerOrderState

ALLOWED_TRANSITIONS: dict[BrokerOrderState, frozenset[BrokerOrderState]] = {
    BrokerOrderState.PENDING: frozenset(
        {
            BrokerOrderState.ACCEPTED,
            BrokerOrderState.REJECTED,
            BrokerOrderState.CANCELED,
            BrokerOrderState.PARTIALLY_FILLED,
            BrokerOrderState.FILLED,
            BrokerOrderState.EXPIRED,
            BrokerOrderState.UNKNOWN,
        }
    ),
    BrokerOrderState.ACCEPTED: frozenset(
        {
            BrokerOrderState.CANCELED,
            BrokerOrderState.PARTIALLY_FILLED,
            BrokerOrderState.FILLED,
            BrokerOrderState.EXPIRED,
            BrokerOrderState.REJECTED,
            BrokerOrderState.UNKNOWN,
        }
    ),
    BrokerOrderState.PARTIALLY_FILLED: frozenset(
        {
            BrokerOrderState.PARTIALLY_FILLED,
            BrokerOrderState.FILLED,
            BrokerOrderState.CANCELED,
            BrokerOrderState.EXPIRED,
            BrokerOrderState.UNKNOWN,
        }
    ),
    BrokerOrderState.UNKNOWN: frozenset(
        {
            BrokerOrderState.ACCEPTED,
            BrokerOrderState.REJECTED,
            BrokerOrderState.CANCELED,
            BrokerOrderState.PARTIALLY_FILLED,
            BrokerOrderState.FILLED,
            BrokerOrderState.EXPIRED,
            BrokerOrderState.UNKNOWN,
        }
    ),
    BrokerOrderState.SHADOWED: frozenset(),
    BrokerOrderState.REJECTED: frozenset(),
    BrokerOrderState.CANCELED: frozenset(),
    BrokerOrderState.FILLED: frozenset(),
    BrokerOrderState.EXPIRED: frozenset(),
}


@dataclass(frozen=True, slots=True)
class OrderStateMachine:
    state: BrokerOrderState = BrokerOrderState.PENDING

    @property
    def resubmission_blocked(self) -> bool:
        return self.state not in {
            BrokerOrderState.REJECTED,
            BrokerOrderState.CANCELED,
            BrokerOrderState.EXPIRED,
        }

    def transition(self, new_state: BrokerOrderState) -> OrderStateMachine:
        if new_state not in ALLOWED_TRANSITIONS[self.state]:
            raise ValueError(f"invalid order transition {self.state} -> {new_state}")
        return OrderStateMachine(state=new_state)
