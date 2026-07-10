"""Tests for execution domain models."""

from decimal import Decimal

import pytest
from pydantic import ValidationError

from yukinoaaa.domain.execution.models import ExecutionReport, ExecutionState


def test_execution_report_immutability_and_attributes() -> None:
    """Verify ExecutionReport attributes and immutability."""
    report = ExecutionReport(
        order_id="ord_123",
        symbol="BTC/USDT",
        status=ExecutionState.FILLED,
        filled_quantity=Decimal("1.0"),
        remaining_quantity=Decimal("0.0"),
        average_price=Decimal("95000"),
        fee=Decimal("95.0"),
    )
    assert report.status == ExecutionState.FILLED
    assert report.filled_quantity == Decimal("1.0")

    with pytest.raises((ValidationError, AttributeError)):
        report.status = ExecutionState.CANCELLED  # type: ignore
