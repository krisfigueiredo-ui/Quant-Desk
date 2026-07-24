from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from quant_trade_desk.strategies.validation import (
    DatasetSplit,
    ReturnObservation,
    validate_strategy,
)


def _rows(test_return: Decimal = Decimal("0.001")) -> list[ReturnObservation]:
    start = datetime(2020, 1, 1, tzinfo=UTC)
    rows: list[ReturnObservation] = []
    for index in range(90):
        split = (
            DatasetSplit.TRAIN
            if index < 30
            else DatasetSplit.VALIDATION
            if index < 60
            else DatasetSplit.TEST
        )
        rows.append(
            ReturnObservation(
                timestamp=start + timedelta(days=index),
                split=split,
                strategy_return=test_return if split == DatasetSplit.TEST else Decimal("0"),
                benchmark_return=Decimal("0.0001"),
                turnover=Decimal("0.2"),
            )
        )
    return rows


def test_validation_never_automatically_promotes_strategy() -> None:
    result = validate_strategy("fixture", _rows())
    assert result.automatic_promotion_permitted is False
    assert result.test_metrics.observations == 30


def test_weak_untouched_test_is_quarantined() -> None:
    result = validate_strategy("fixture", _rows(Decimal("-0.001")))
    assert result.status == "QUARANTINED"
    assert "NON_POSITIVE_TEST_EXCESS_RETURN" in result.reason_codes


def test_overlapping_or_non_chronological_splits_are_rejected() -> None:
    rows = _rows()
    rows[0] = rows[0].model_copy(update={"split": DatasetSplit.TEST})
    with pytest.raises(ValueError, match="NON_CHRONOLOGICAL_OR_OVERLAPPING"):
        validate_strategy("fixture", rows)
