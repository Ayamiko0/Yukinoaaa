"""Trading domain models: Order, Position, Portfolio, and TradeSignal."""

import uuid
from datetime import UTC, datetime
from decimal import Decimal
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from yukinoaaa.domain.exceptions import ValidationException


class OrderSide(str, Enum):
    """Side of order or trade signal."""
    BUY = "BUY"
    SELL = "SELL"


class OrderType(str, Enum):
    """Type of trading order."""
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP_LOSS = "STOP_LOSS"
    TAKE_PROFIT = "TAKE_PROFIT"


class OrderStatus(str, Enum):
    """Lifecycle status of a trading order."""
    PENDING = "PENDING"
    OPEN = "OPEN"
    FILLED = "FILLED"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"


class PositionSide(str, Enum):
    """Direction of an active trading position."""
    LONG = "LONG"
    SHORT = "SHORT"


class Order(BaseModel):
    """Entity representing a trading order sent to an exchange or simulation."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    symbol: str = Field(..., description="Standardized symbol, e.g. 'BTC/USDT'")
    side: OrderSide = Field(...)
    order_type: OrderType = Field(default=OrderType.MARKET)
    status: OrderStatus = Field(default=OrderStatus.PENDING)
    price: Decimal | None = Field(default=None, description="Limit price if LIMIT order")
    quantity: Decimal = Field(..., gt=0, description="Order volume quantity")
    filled_quantity: Decimal = Field(default=Decimal("0"), ge=0)
    average_fill_price: Decimal | None = Field(default=None)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    metadata: dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(validate_assignment=True)


class Position(BaseModel):
    """Entity representing an open trading position with real-time PnL tracking."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    symbol: str = Field(..., description="Standardized symbol, e.g. 'BTC/USDT'")
    side: PositionSide = Field(...)
    entry_price: Decimal = Field(..., gt=0)
    mark_price: Decimal = Field(..., gt=0)
    quantity: Decimal = Field(..., gt=0)
    leverage: Decimal = Field(default=Decimal("1.0"), ge=1.0)
    unrealized_pnl: Decimal = Field(default=Decimal("0.0"))
    realized_pnl: Decimal = Field(default=Decimal("0.0"))
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))

    model_config = ConfigDict(validate_assignment=True)

    def update_mark_price(self, new_price: Decimal) -> Decimal:
        """Update current mark price and recalculate unrealized PnL."""
        if new_price <= Decimal("0"):
            raise ValidationException(f"Mark price must be positive: {new_price}")
        self.mark_price = new_price
        if self.side == PositionSide.LONG:
            self.unrealized_pnl = (self.mark_price - self.entry_price) * self.quantity
        else:
            self.unrealized_pnl = (self.entry_price - self.mark_price) * self.quantity
        return self.unrealized_pnl


class TradeSignal(BaseModel):
    """Immutable value object representing a quantitative trade setup emitted by a strategy."""
    signal_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    symbol: str = Field(...)
    timeframe: str = Field(...)
    side: OrderSide = Field(...)
    strategy_name: str = Field(...)
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Signal confidence score between 0 and 1")
    target_price: Decimal | None = Field(default=None)
    stop_loss: Decimal | None = Field(default=None)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    metadata: dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(frozen=True)


class Portfolio(BaseModel):
    """Aggregate Root managing account balance, margin, and active positions."""
    account_id: str = Field(...)
    available_balance: Decimal = Field(..., ge=0)
    margin_used: Decimal = Field(default=Decimal("0.0"), ge=0)
    positions: dict[str, Position] = Field(default_factory=dict, description="Mapping: symbol -> active Position")
    orders: dict[str, Order] = Field(default_factory=dict, description="Mapping: order_id -> Order")

    model_config = ConfigDict(validate_assignment=True)

    @property
    def total_unrealized_pnl(self) -> Decimal:
        """Sum of unrealized PnL across all active positions."""
        return sum((pos.unrealized_pnl for pos in self.positions.values()), Decimal("0.0"))

    @property
    def total_equity(self) -> Decimal:
        """Total equity = available balance + margin used + total unrealized PnL."""
        return self.available_balance + self.margin_used + self.total_unrealized_pnl

    def open_position(self, pos: Position, required_margin: Decimal) -> None:
        """Open a new position or increase existing one, allocating margin from available balance."""
        if required_margin > self.available_balance:
            raise ValidationException(
                f"Insufficient balance to open position. Required: {required_margin}, Available: {self.available_balance}"
            )
        self.available_balance -= required_margin
        self.margin_used += required_margin
        self.positions[pos.symbol.upper()] = pos

    def close_position(self, symbol: str, close_price: Decimal) -> Position:
        """Close an active position and realize its PnL into available balance."""
        sym = symbol.upper()
        if sym not in self.positions:
            raise ValidationException(f"No active position found for symbol: {sym}")
        pos = self.positions.pop(sym)
        pos.update_mark_price(close_price)
        final_pnl = pos.unrealized_pnl

        # Return margin used for this position and add realized PnL
        # Simplified margin return calculation assuming proportional release
        self.available_balance += (self.margin_used + final_pnl)
        pos.realized_pnl += final_pnl
        pos.unrealized_pnl = Decimal("0.0")
        self.margin_used = Decimal("0.0") if not self.positions else self.margin_used
        return pos

    def update_position_price(self, symbol: str, new_price: Decimal) -> Decimal | None:
        """Update mark price of an open position if present."""
        pos = self.positions.get(symbol.upper())
        if pos is not None:
            return pos.update_mark_price(new_price)
        return None

    def add_order(self, order: Order) -> None:
        """Register an order in the portfolio."""
        self.orders[order.id] = order
