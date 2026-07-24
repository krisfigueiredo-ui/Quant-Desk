"""Mode-aware broker routing."""

from __future__ import annotations

from quant_trade_desk.communication.schemas import AssetClass
from quant_trade_desk.settings import TradingMode

from .models import BrokerAdapter


def select_adapter(
    *,
    mode: TradingMode,
    asset_class: AssetClass,
    paper: BrokerAdapter,
    shadow: BrokerAdapter,
    live_equity: BrokerAdapter | None,
    live_crypto: BrokerAdapter | None,
) -> BrokerAdapter:
    if mode == TradingMode.PAPER:
        return paper
    if mode == TradingMode.SHADOW:
        return shadow
    if mode == TradingMode.RESTRICTED_LIVE:
        adapter = live_equity if asset_class == AssetClass.EQUITY else live_crypto
        if adapter is None:
            raise RuntimeError("live adapter is not configured")
        return adapter
    raise RuntimeError(f"mode {mode.value} has no execution route")
