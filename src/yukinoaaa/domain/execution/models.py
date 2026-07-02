"""Execution domain models: ExecutionState and ExecutionReport."""

from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Any
import uuid
from pydantic import BaseModel, ConfigDict, Field


class ExecutionState(str, Enum):
    """Lifecycle status of an order execution report."""
    SUBMITTED = "SUBMITTED"
    PARTIAL_FILLED = "PARTIAL_FILLED"
    FILLED = "FILLED"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"
    FAILED = "FAILED"


class ExecutionReport(BaseModel):
    """Immutable value object capturing order fill status, execution price, and fees."""
    report_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    order_id: str = Field(...)
    symbol: str = Field(...)
    status: ExecutionState = Field(...)
    filled_quantity: Decimal = Field(default=Decimal("0.0"), ge=0)
    remaining_quantity: Decimal = Field(default=Decimal("0.0"), ge=0)
    last_price: Decimal | None = Field(default=None, description="Price of the most recent fill")
    average_price: Decimal | None = Field(default=None, description="Volume-weighted average fill price")
    fee: Decimal = Field(default=Decimal("0.0"), ge=0, description="Trading commission fee deducted")
    reason: str | None = Field(default=None, description="Explanation for REJECTED or FAILED status")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(frozen=True)
