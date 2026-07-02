"""Domain event definitions.

Events represent state changes or significant occurrences within the domain.
They form the backbone of the Event-Driven Architecture (EDA).
"""

from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4
from pydantic import BaseModel, Field


class DomainEvent(BaseModel):
    """Base immutable class for all domain events in Yukinoaaa."""

    event_id: UUID = Field(default_factory=uuid4, description="Unique identifier for the event")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC timestamp when the event occurred",
    )
    event_type: str = Field(..., description="Name/type of the event")
    correlation_id: UUID | None = Field(
        default=None, description="Optional ID to trace workflows across modules"
    )
    payload: dict[str, Any] = Field(
        default_factory=dict, description="Event-specific data payload"
    )

    model_config = {
        "frozen": True,
        "arbitrary_types_allowed": True,
    }
