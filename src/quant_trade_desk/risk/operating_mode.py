"""Deliberate restricted-live activation records and mode authorizations."""

from __future__ import annotations

import hashlib
import json
import os
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

from quant_trade_desk.communication.schemas import AssetClass
from quant_trade_desk.settings import Settings, TradingMode

EQUITY_CONFIRMATION = "ENABLE RESTRICTED LIVE EQUITY TRADING"
CRYPTO_CONFIRMATION = "ENABLE RESTRICTED LIVE CRYPTO TRADING"
GENERAL_CONFIRMATION = "ENABLE RESTRICTED LIVE TRADING"


class ReadinessChecklist(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    tests_pass: bool
    static_typing_pass: bool
    frontend_build_pass: bool
    secret_scan_pass: bool
    migrations_pass: bool
    capability_discovery_pass: bool
    dedicated_account_verified: bool
    paper_observation_pass: bool
    shadow_observation_pass: bool
    no_unresolved_orders: bool
    account_reconciled: bool
    risk_config_versioned: bool
    kill_switch_tested: bool
    emergency_stop_tested: bool

    @property
    def ready(self) -> bool:
        return all(value for name, value in self.model_dump().items() if name not in {"ready"})


class ActivationRecord(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    record_id: UUID = Field(default_factory=uuid4)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    enabled_asset_classes: frozenset[AssetClass]
    checklist_checksum: str
    dedicated_account_id_hash: str
    restricted_limits_only: bool = True


class ModeAuthorization(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    authorization_id: UUID = Field(default_factory=uuid4)
    mode: TradingMode
    enabled_asset_classes: frozenset[AssetClass]
    issued_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    valid_until: datetime
    activation_record_id: UUID | None = None

    def valid_for(self, asset_class: AssetClass, now: datetime | None = None) -> bool:
        instant = (now or datetime.now(UTC)).astimezone(UTC)
        return instant < self.valid_until and asset_class in self.enabled_asset_classes


class OfflineActivationManager:
    """Writes a local activation record only after exact phrase and readiness.

    This class is never called by API routes or agents.
    """

    def __init__(self, record_path: Path) -> None:
        self.record_path = record_path

    def create_record(
        self,
        *,
        asset_class: AssetClass,
        exact_phrase: str,
        checklist: ReadinessChecklist,
        dedicated_account_id: str,
    ) -> ActivationRecord:
        expected = {
            AssetClass.EQUITY: EQUITY_CONFIRMATION,
            AssetClass.CRYPTO: CRYPTO_CONFIRMATION,
        }.get(asset_class)
        if expected is None or exact_phrase != expected:
            raise ValueError("exact asset-specific activation phrase required")
        if not checklist.ready:
            raise ValueError("live-readiness checklist is incomplete")
        if not dedicated_account_id.strip():
            raise ValueError("dedicated account must be verified")
        checklist_json = checklist.model_dump_json()
        record = ActivationRecord(
            enabled_asset_classes=frozenset({asset_class}),
            checklist_checksum=hashlib.sha256(checklist_json.encode()).hexdigest(),
            dedicated_account_id_hash=hashlib.sha256(dedicated_account_id.encode()).hexdigest(),
        )
        self.record_path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        self.record_path.write_text(record.model_dump_json(indent=2), encoding="utf-8")
        os.chmod(self.record_path, 0o600)
        return record

    def read_record(self) -> ActivationRecord | None:
        if not self.record_path.exists():
            return None
        try:
            return ActivationRecord.model_validate_json(
                self.record_path.read_text(encoding="utf-8")
            )
        except (OSError, ValueError, json.JSONDecodeError):
            return None


def authorize_mode(
    settings: Settings,
    *,
    activation_record: ActivationRecord | None = None,
    activation_records: tuple[ActivationRecord, ...] = (),
    ttl: timedelta = timedelta(minutes=5),
) -> ModeAuthorization:
    if settings.trading_mode in {TradingMode.PAPER, TradingMode.SHADOW}:
        return ModeAuthorization(
            mode=settings.trading_mode,
            enabled_asset_classes=frozenset({AssetClass.EQUITY, AssetClass.CRYPTO}),
            valid_until=datetime.now(UTC) + ttl,
        )
    if settings.trading_mode != TradingMode.RESTRICTED_LIVE:
        return ModeAuthorization(
            mode=settings.trading_mode,
            enabled_asset_classes=frozenset(),
            valid_until=datetime.now(UTC) + ttl,
        )
    records = activation_records + ((activation_record,) if activation_record is not None else ())
    if not records:
        return ModeAuthorization(
            mode=settings.trading_mode,
            enabled_asset_classes=frozenset(),
            valid_until=datetime.now(UTC) + ttl,
        )
    configured: set[AssetClass] = set()
    if settings.live_equities_enabled:
        configured.add(AssetClass.EQUITY)
    if settings.live_crypto_enabled:
        configured.add(AssetClass.CRYPTO)
    activated = frozenset(
        asset_class for record in records for asset_class in record.enabled_asset_classes
    )
    selected_record = records[0]
    return ModeAuthorization(
        mode=settings.trading_mode,
        enabled_asset_classes=frozenset(configured) & activated,
        valid_until=datetime.now(UTC) + ttl,
        activation_record_id=selected_record.record_id,
    )
