"""Tests for presentation API data models."""

from decimal import Decimal

import pytest

from yukinoaaa.presentation.api.models import ApiResponse, BacktestRequest, PortfolioResponse


def test_presentation_models_validation_and_immutability() -> None:
    """Verify API request and response models attributes and frozen config."""
    res = ApiResponse(status="success", data={"msg": "hello"})
    assert res.status == "success"

    port = PortfolioResponse(account_id="acc_1", available_balance=Decimal("100"), total_equity=Decimal("100"))
    assert port.active_orders_count == 0

    req = BacktestRequest(symbol="ETH/USDT")
    assert req.initial_equity == Decimal("10000.00")

    with pytest.raises(Exception):
        req.symbol = "SOL/USDT"  # type: ignore
