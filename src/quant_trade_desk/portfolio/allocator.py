"""Portfolio conflict resolution and immutable proposed-order creation."""

from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from quant_trade_desk.communication.permissions import Permission, require
from quant_trade_desk.communication.schemas import (
    AssetClass,
    ProposedOrderPayload,
    TradeIntentPayload,
)

from .strategy_lots import StrategyLotLedger


class ProposalResult(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    order: ProposedOrderPayload | None
    conflicts: tuple[str, ...] = ()
    reason_codes: tuple[str, ...] = ()


class PortfolioManager:
    agent_id = "portfolio-manager"
    version = "1.0.0"

    def __init__(self, ledger: StrategyLotLedger) -> None:
        self.ledger = ledger

    def propose(
        self,
        intent: TradeIntentPayload,
        *,
        account_id: str,
        asset_class: AssetClass,
        symbol: str,
        strategy_lot_id: UUID,
        current_price: Decimal,
        max_slippage_bps: Decimal,
    ) -> ProposalResult:
        require(self.agent_id, Permission.PROPOSE_POSITION)
        lot = self.ledger.get(strategy_lot_id)
        if lot is None:
            return ProposalResult(
                order=None,
                conflicts=("UNKNOWN_STRATEGY_LOT",),
                reason_codes=("LOT_OWNERSHIP_UNVERIFIED",),
            )
        if lot.asset_class != asset_class or lot.symbol != symbol.upper():
            return ProposalResult(
                order=None,
                conflicts=("STRATEGY_LOT_ASSET_MISMATCH",),
                reason_codes=("LOT_OWNERSHIP_MISMATCH",),
            )
        if lot.strategy_id != intent.strategy_id:
            return ProposalResult(
                order=None,
                conflicts=("STRATEGY_LOT_OWNER_MISMATCH",),
                reason_codes=("CROSS_STRATEGY_LIQUIDATION_BLOCKED",),
            )
        if intent.side.value == "SELL" and intent.quantity > lot.quantity:
            return ProposalResult(
                order=None,
                conflicts=("SELL_EXCEEDS_STRATEGY_LOT",),
                reason_codes=("STRATEGY_LOT_QUANTITY_EXCEEDED",),
            )
        reference_price = intent.limit_price or current_price
        if reference_price <= 0:
            return ProposalResult(
                order=None,
                reason_codes=("INVALID_REFERENCE_PRICE",),
            )
        return ProposalResult(
            order=ProposedOrderPayload(
                account_id=account_id,
                side=intent.side,
                quantity=intent.quantity,
                order_type=intent.order_type,
                limit_price=intent.limit_price,
                stop_price=intent.stop_price,
                time_in_force=intent.time_in_force,
                strategy_lot_id=lot.lot_id,
                risk_reducing=intent.risk_reducing,
                max_slippage_bps=max_slippage_bps,
                planned_loss=intent.planned_loss,
                time_horizon=intent.time_horizon,
            ),
            reason_codes=("PROPOSAL_CREATED",),
        )
