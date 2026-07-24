"""Explicit, observable message routing; no hidden agent communication."""

from __future__ import annotations

from quant_trade_desk.communication.message_bus import InMemoryMessageBus
from quant_trade_desk.communication.routing import allowed_recipients
from quant_trade_desk.communication.schemas import AgentMessage, MessageReceipt

from .definitions import AGENT_DEFINITIONS


class Orchestrator:
    agent_id = "desk-orchestrator"
    version = "1.0.0"

    def __init__(self, bus: InMemoryMessageBus) -> None:
        self.bus = bus

    def publish(self, message: AgentMessage) -> MessageReceipt:
        sender = AGENT_DEFINITIONS.get(message.agent_id)
        if sender is None:
            raise ValueError("unknown agent")
        if message.message_type not in sender.allowed_outputs:
            raise ValueError("agent output type is not permitted")
        recipients = allowed_recipients(message.message_type)
        if not recipients:
            raise ValueError("message has no explicit route")
        return self.bus.publish(message)
