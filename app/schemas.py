from datetime import datetime, timezone
from typing import Any, Literal
from pydantic import BaseModel, ConfigDict, Field, JsonValue, field_validator

class EventCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    event_id: str = Field(min_length=1, max_length=100); user_id: str = Field(min_length=1, max_length=100)
    event_name: str = Field(min_length=1, max_length=100); timestamp: datetime; source: str = Field(min_length=1, max_length=50)
    properties: dict[str, JsonValue] = Field(default_factory=dict); experiment_id: str | None = None
    @field_validator("timestamp")
    @classmethod
    def normalize_timestamp(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None: raise ValueError("timestamp must include a timezone")
        return value.astimezone(timezone.utc)

class EventResult(BaseModel): accepted: bool; duplicate: bool; event: EventCreate
class ConsentInput(BaseModel):
    purpose: str = "marketing"; status: Literal["granted", "withdrawn", "suppressed"]; source: str; timestamp: datetime
class ApprovalInput(BaseModel): approver: str = Field(min_length=1)
class RejectionInput(BaseModel):
    approver: str = Field(min_length=1); reason: str = Field(min_length=1, max_length=255)
class FeedbackInput(BaseModel):
    callback_id: str; action_id: str
    event_name: Literal["sent", "delivered", "opened", "clicked", "failed", "course_resumed", "course_completed", "purchase_completed", "assistant_contacted"]
    timestamp: datetime; payload: dict[str, Any] = Field(default_factory=dict)
class OutreachDraft(BaseModel):
    subject: str; body: str; cta: str; facts_used: list[str]; risk_flags: list[str] = Field(default_factory=list)
    confidence: float = Field(ge=0, le=1); template_version: str; provider: str
