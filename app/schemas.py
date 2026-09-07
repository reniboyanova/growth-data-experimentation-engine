from datetime import datetime, timezone

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    JsonValue,
    field_validator,
)


class EventCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    event_id: str = Field(min_length=1, max_length=100)
    user_id: str = Field(min_length=1, max_length=100)
    event_name: str = Field(min_length=1, max_length=100)
    timestamp: datetime
    source: str = Field(min_length=1, max_length=50)
    properties: dict[str, JsonValue] = Field(default_factory=dict)
    experiment_id: str | None = None

    @field_validator("timestamp")
    @classmethod
    def normalize_timestamp(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("timestamp must include a timezone")

        return value.astimezone(timezone.utc)


class EventResult(BaseModel):
    accepted: bool
    duplicate: bool
    event: EventCreate