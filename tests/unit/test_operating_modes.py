from datetime import UTC, datetime

from quant_trade_desk.communication.schemas import AssetClass
from quant_trade_desk.risk.operating_mode import (
    ActivationRecord,
    authorize_mode,
)
from quant_trade_desk.settings import Settings, TradingMode


def _record(asset_class: AssetClass) -> ActivationRecord:
    return ActivationRecord(
        created_at=datetime.now(UTC),
        enabled_asset_classes=frozenset({asset_class}),
        checklist_checksum="a" * 64,
        dedicated_account_id_hash="b" * 64,
    )


def test_equity_and_crypto_restricted_live_authorize_independently() -> None:
    settings = Settings(
        trading_mode=TradingMode.RESTRICTED_LIVE,
        live_equities_enabled=True,
        live_crypto_enabled=False,
    )
    authorization = authorize_mode(
        settings,
        activation_records=(_record(AssetClass.EQUITY),),
    )
    assert authorization.enabled_asset_classes == frozenset({AssetClass.EQUITY})


def test_missing_asset_specific_record_blocks_that_asset() -> None:
    settings = Settings(
        trading_mode=TradingMode.RESTRICTED_LIVE,
        live_equities_enabled=True,
        live_crypto_enabled=True,
    )
    authorization = authorize_mode(
        settings,
        activation_records=(_record(AssetClass.EQUITY),),
    )
    assert authorization.enabled_asset_classes == frozenset({AssetClass.EQUITY})
