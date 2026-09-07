from datetime import datetime, timezone
from sqlalchemy import JSON, String
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base

def utc_now_text() -> str:
    return datetime.now(timezone.utc).isoformat()

class Event(Base):
    __tablename__ = "events"
    id: Mapped[int] = mapped_column(primary_key=True)
    event_id: Mapped[str] = mapped_column(String(100), unique=True)
    user_id: Mapped[str] = mapped_column(String(100), index=True)
    event_name: Mapped[str] = mapped_column(String(100))
    timestamp: Mapped[str] = mapped_column(String(40))
    source: Mapped[str] = mapped_column(String(50))
    properties: Mapped[dict] = mapped_column(JSON, default=dict)
    experiment_id: Mapped[str | None] = mapped_column(String(100))
    created_at: Mapped[str] = mapped_column(String(40), default=utc_now_text)