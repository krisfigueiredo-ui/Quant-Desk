"""Versioned signed TradingView webhook validation."""

from __future__ import annotations

import hashlib
import hmac
import json
from collections import defaultdict, deque
from datetime import UTC, datetime, timedelta
from threading import RLock

from pydantic import BaseModel, ConfigDict, Field, field_validator

from quant_trade_desk.communication.idempotency import IdempotencyStore
from quant_trade_desk.communication.schemas import AssetClass, Side


class TradingViewSignal(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: str = Field(pattern=r"^\d+\.\d+\.\d+$")
    signal_id: str = Field(min_length=8, max_length=128, pattern=r"^[A-Za-z0-9._:-]+$")
    strategy_id: str
    asset_class: AssetClass
    symbol: str
    side: Side
    timeframe: str
    signal_timestamp: datetime
    expires_at: datetime
    indicator_values: dict[str, float]

    @field_validator("signal_timestamp", "expires_at")
    @classmethod
    def timezone_required(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("TradingView timestamps must be timezone-aware")
        return value.astimezone(UTC)

    @field_validator("symbol")
    @classmethod
    def normalize_symbol(cls, value: str) -> str:
        return value.strip().upper()


class SlidingWindowRateLimiter:
    def __init__(self, limit: int = 30, window: timedelta = timedelta(minutes=1)) -> None:
        self.limit = limit
        self.window = window
        self._events: dict[str, deque[datetime]] = defaultdict(deque)
        self._lock = RLock()

    def allow(self, key: str, now: datetime) -> bool:
        with self._lock:
            events = self._events[key]
            cutoff = now - self.window
            while events and events[0] <= cutoff:
                events.popleft()
            if len(events) >= self.limit:
                return False
            events.append(now)
            return True


class TradingViewVerifier:
    def __init__(
        self,
        *,
        secret: str,
        allowed_equities: frozenset[str],
        allowed_crypto: frozenset[str],
        maximum_body_bytes: int = 32_768,
        maximum_age_seconds: int = 60,
        idempotency: IdempotencyStore | None = None,
        rate_limiter: SlidingWindowRateLimiter | None = None,
    ) -> None:
        if len(secret) < 16:
            raise ValueError("webhook secret must be at least 16 characters")
        self._secret = secret.encode()
        self.allowed_equities = allowed_equities
        self.allowed_crypto = allowed_crypto
        self.maximum_body_bytes = maximum_body_bytes
        self.maximum_age = timedelta(seconds=maximum_age_seconds)
        self.idempotency = idempotency or IdempotencyStore()
        self.rate_limiter = rate_limiter or SlidingWindowRateLimiter()

    def sign(self, body: bytes) -> str:
        return hmac.new(self._secret, body, hashlib.sha256).hexdigest()

    def verify(
        self,
        *,
        body: bytes,
        signature: str,
        source_key: str,
        now: datetime | None = None,
    ) -> TradingViewSignal:
        instant = (now or datetime.now(UTC)).astimezone(UTC)
        if len(body) > self.maximum_body_bytes:
            raise ValueError("REQUEST_TOO_LARGE")
        if not self.rate_limiter.allow(source_key, instant):
            raise ValueError("RATE_LIMITED")
        expected = self.sign(body)
        supplied = signature.removeprefix("sha256=")
        if not hmac.compare_digest(expected, supplied):
            raise ValueError("INVALID_SIGNATURE")
        try:
            raw = json.loads(body)
        except json.JSONDecodeError as exc:
            raise ValueError("INVALID_JSON") from exc
        signal = TradingViewSignal.model_validate(raw)
        age = instant - signal.signal_timestamp
        if age < timedelta(0) or age > self.maximum_age:
            raise ValueError("STALE_SIGNAL")
        if signal.expires_at <= instant:
            raise ValueError("EXPIRED_SIGNAL")
        allowed = (
            self.allowed_equities
            if signal.asset_class == AssetClass.EQUITY
            else self.allowed_crypto
        )
        if signal.symbol not in allowed:
            raise ValueError("UNSUPPORTED_SYMBOL")
        if not self.idempotency.claim(str(signal.signal_id), now=instant):
            raise ValueError("DUPLICATE_OR_REPLAYED_SIGNAL")
        return signal
