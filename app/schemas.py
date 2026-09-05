from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field


class EventCreate(BaseModel):
    user_id: str = Field(min_length=1, max_length=100)
    event_name: str = Field(min_length=1, max_length=100)
    timestamp: datetime
    source: str = Field(min_length=1, max_length=50)
    properties: dict[str, Any] = Field(default_factory=dict)
    experiment_id: str | None = None


event = EventCreate(
    user_id="2",
    event_name="buy",
    timestamp=datetime.now(timezone.utc),
    source="Facebook",
    properties={"address": "some address"},
)

print(event.model_dump())