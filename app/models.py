from datetime import datetime, timezone
from sqlalchemy import JSON, Boolean, Float, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base

def utc_now_text() -> str: return datetime.now(timezone.utc).isoformat()

class Event(Base):
    __tablename__ = "events"
    id: Mapped[int] = mapped_column(primary_key=True)
    event_id: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    user_id: Mapped[str] = mapped_column(String(100), index=True)
    event_name: Mapped[str] = mapped_column(String(100), index=True)
    timestamp: Mapped[str] = mapped_column(String(40), index=True)
    source: Mapped[str] = mapped_column(String(50))
    properties: Mapped[dict] = mapped_column(JSON, default=dict)
    experiment_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[str] = mapped_column(String(40), default=utc_now_text)

class Customer(Base):
    __tablename__ = "customers"
    user_id: Mapped[str] = mapped_column(String(100), primary_key=True)
    display_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    acquisition_source: Mapped[str | None] = mapped_column(String(50), nullable=True)
    data_fresh_at: Mapped[str | None] = mapped_column(String(40), nullable=True)
    created_at: Mapped[str] = mapped_column(String(40), default=utc_now_text)

class Identity(Base):
    __tablename__ = "identities"; __table_args__ = (UniqueConstraint("namespace", "external_id"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("customers.user_id"), index=True)
    namespace: Mapped[str] = mapped_column(String(50)); external_id: Mapped[str] = mapped_column(String(255))
    verified: Mapped[bool] = mapped_column(Boolean, default=False); created_at: Mapped[str] = mapped_column(String(40), default=utc_now_text)

class Consent(Base):
    __tablename__ = "consents"
    id: Mapped[int] = mapped_column(primary_key=True); user_id: Mapped[str] = mapped_column(ForeignKey("customers.user_id"), index=True)
    purpose: Mapped[str] = mapped_column(String(50), default="marketing"); status: Mapped[str] = mapped_column(String(20))
    source: Mapped[str] = mapped_column(String(50)); timestamp: Mapped[str] = mapped_column(String(40))

class SequenceEnrollment(Base):
    __tablename__ = "sequence_enrollments"
    id: Mapped[int] = mapped_column(primary_key=True); user_id: Mapped[str] = mapped_column(ForeignKey("customers.user_id"), index=True)
    sequence_id: Mapped[str] = mapped_column(String(100)); product_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="active"); current_step: Mapped[int] = mapped_column(Integer, default=0)
    entered_at: Mapped[str] = mapped_column(String(40), default=utc_now_text); exit_reason: Mapped[str | None] = mapped_column(String(100), nullable=True)

class GrowthAction(Base):
    __tablename__ = "growth_actions"
    action_id: Mapped[str] = mapped_column(String(100), primary_key=True); user_id: Mapped[str] = mapped_column(String(100), index=True)
    product_id: Mapped[str | None] = mapped_column(String(100), nullable=True); action_type: Mapped[str] = mapped_column(String(50))
    status: Mapped[str] = mapped_column(String(20), default="pending", index=True); reason_codes: Mapped[list] = mapped_column(JSON, default=list)
    evidence_event_ids: Mapped[list] = mapped_column(JSON, default=list); context: Mapped[dict] = mapped_column(JSON, default=dict)
    idempotency_key: Mapped[str] = mapped_column(String(200), unique=True); requires_approval: Mapped[bool] = mapped_column(Boolean, default=True)
    state_version: Mapped[str] = mapped_column(String(100)); expires_at: Mapped[str | None] = mapped_column(String(40), nullable=True)
    created_at: Mapped[str] = mapped_column(String(40), default=utc_now_text); approved_at: Mapped[str | None] = mapped_column(String(40), nullable=True)
    approver: Mapped[str | None] = mapped_column(String(100), nullable=True); executed_at: Mapped[str | None] = mapped_column(String(40), nullable=True)
    provider_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    approval_payload_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    rejected_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)

class DecisionAudit(Base):
    __tablename__ = "decision_audits"; id: Mapped[int] = mapped_column(primary_key=True); user_id: Mapped[str] = mapped_column(String(100), index=True)
    action_id: Mapped[str | None] = mapped_column(String(100), nullable=True); snapshot: Mapped[dict] = mapped_column(JSON); created_at: Mapped[str] = mapped_column(String(40), default=utc_now_text)

class OutboxCommand(Base):
    __tablename__ = "outbox_commands"; id: Mapped[int] = mapped_column(primary_key=True); action_id: Mapped[str] = mapped_column(String(100), unique=True)
    command: Mapped[dict] = mapped_column(JSON); status: Mapped[str] = mapped_column(String(20), default="pending"); attempts: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[str] = mapped_column(String(40), default=utc_now_text)
    next_attempt_at: Mapped[str | None] = mapped_column(String(40), nullable=True)
    last_error: Mapped[str | None] = mapped_column(String(500), nullable=True)

class ScanRun(Base):
    __tablename__ = "scan_runs"
    scan_id: Mapped[str] = mapped_column(String(100), primary_key=True)
    cursor: Mapped[str | None] = mapped_column(String(100), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="running")
    processed: Mapped[int] = mapped_column(Integer, default=0)
    candidates: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[str] = mapped_column(String(40), default=utc_now_text)
    completed_at: Mapped[str | None] = mapped_column(String(40), nullable=True)

class Feedback(Base):
    __tablename__ = "feedback"; callback_id: Mapped[str] = mapped_column(String(100), primary_key=True); action_id: Mapped[str] = mapped_column(String(100), index=True)
    event_name: Mapped[str] = mapped_column(String(50)); timestamp: Mapped[str] = mapped_column(String(40)); payload: Mapped[dict] = mapped_column(JSON, default=dict)

class ExperimentAssignment(Base):
    __tablename__ = "experiment_assignments"; __table_args__ = (UniqueConstraint("experiment_id", "user_id"),)
    id: Mapped[int] = mapped_column(primary_key=True); experiment_id: Mapped[str] = mapped_column(String(100), index=True); user_id: Mapped[str] = mapped_column(String(100), index=True)
    variant: Mapped[str] = mapped_column(String(20)); eligible_at: Mapped[str] = mapped_column(String(40)); exposed_at: Mapped[str | None] = mapped_column(String(40), nullable=True)
    converted: Mapped[bool] = mapped_column(Boolean, default=False); metric_value: Mapped[float] = mapped_column(Float, default=0.0)
