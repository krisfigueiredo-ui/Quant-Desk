"""Strategy-owned position lots prevent cross-strategy liquidation."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from threading import RLock
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

from quant_trade_desk.communication.schemas import AssetClass


class StrategyLot(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    lot_id: UUID = Field(default_factory=uuid4)
    strategy_id: str
    asset_class: AssetClass
    symbol: str
    quantity: Decimal = Field(ge=0)
    average_cost: Decimal = Field(ge=0)
    opened_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class StrategyLotLedger:
    def __init__(self) -> None:
        self._lots: dict[UUID, StrategyLot] = {}
        self._lock = RLock()

    def add(self, lot: StrategyLot) -> None:
        with self._lock:
            if lot.lot_id in self._lots:
                raise ValueError("duplicate strategy lot")
            self._lots[lot.lot_id] = lot

    def get(self, lot_id: UUID) -> StrategyLot | None:
        with self._lock:
            return self._lots.get(lot_id)

    def owned_quantity(self, lot_id: UUID) -> Decimal:
        lot = self.get(lot_id)
        return lot.quantity if lot else Decimal("0")

    def apply_fill(
        self,
        lot_id: UUID,
        *,
        side: str,
        quantity: Decimal,
        price: Decimal,
    ) -> StrategyLot:
        if quantity <= 0 or price <= 0:
            raise ValueError("fill quantity and price must be positive")
        with self._lock:
            current = self._lots.get(lot_id)
            if current is None:
                raise KeyError("unknown strategy lot")
            normalized_side = side.upper()
            if normalized_side == "SELL" and quantity > current.quantity:
                raise ValueError("fill exceeds strategy-owned quantity")
            if normalized_side == "BUY":
                new_quantity = current.quantity + quantity
                new_average = (
                    current.quantity * current.average_cost + quantity * price
                ) / new_quantity
            elif normalized_side == "SELL":
                new_quantity = current.quantity - quantity
                new_average = current.average_cost if new_quantity > 0 else Decimal("0")
            else:
                raise ValueError("unsupported fill side")
            updated = current.model_copy(
                update={
                    "quantity": new_quantity,
                    "average_cost": new_average,
                    "updated_at": datetime.now(UTC),
                }
            )
            self._lots[lot_id] = updated
            return updated

    def lots(
        self,
        *,
        strategy_id: str | None = None,
        symbol: str | None = None,
    ) -> tuple[StrategyLot, ...]:
        with self._lock:
            result = tuple(self._lots.values())
        if strategy_id is not None:
            result = tuple(lot for lot in result if lot.strategy_id == strategy_id)
        if symbol is not None:
            result = tuple(lot for lot in result if lot.symbol == symbol.upper())
        return result
