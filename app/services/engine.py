import hashlib, json, uuid
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models import Consent, DecisionAudit, Event, GrowthAction, OutboxCommand
from app.schemas import OutreachDraft

FUNNEL = ["user_signed_up", "email_verified", "first_project_created", "subscription_started"]
MARKETING = {"enroll_in_sequence", "send_personalized_email", "invite_to_webinar", "recommend_next_product"}

def parse_dt(value: str) -> datetime: return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)
def ordered_events(db: Session, user_id: str | None = None) -> list[Event]:
    q = select(Event)
    if user_id: q = q.where(Event.user_id == user_id)
    return list(db.scalars(q.order_by(Event.timestamp, Event.id)))

def build_customer_state(db: Session, user_id: str) -> dict[str, Any]:
    events = ordered_events(db, user_id)
    if not events: return {"user_id": user_id, "known": False, "unknown_fields": ["all"]}
    names = {e.event_name for e in events}; products = set(); progress = {}
    for e in events:
        product = e.properties.get("product_id")
        if product and e.event_name in {"purchase_completed", "subscription_started"}: products.add(str(product))
        if product and e.event_name in {"lesson_completed", "course_started", "course_resumed", "course_completed"}:
            progress[str(product)] = {"status": e.event_name, "last_activity": e.timestamp, "lesson": e.properties.get("lesson")}
    consent = db.scalar(select(Consent).where(Consent.user_id == user_id, Consent.purpose == "marketing").order_by(Consent.timestamp.desc()))
    return {"user_id": user_id, "known": True, "purchases": sorted(products), "course_progress": progress,
            "last_activity": events[-1].timestamp, "open_support_case": "support_case_opened" in names and "support_case_closed" not in names,
            "marketing_consent": consent.status if consent else "unknown", "event_count": len(events),
            "evidence_event_ids": [e.event_id for e in events], "unknown_fields": [] if consent else ["marketing_consent"]}

def funnel_metrics(db: Session, source: str | None = None) -> dict[str, Any]:
    by_user = defaultdict(list)
    for event in ordered_events(db):
        if not source or event.source == source: by_user[event.user_id].append(event)
    counts = [0] * len(FUNNEL)
    for rows in by_user.values():
        cursor = 0
        for row in rows:
            if cursor < len(FUNNEL) and row.event_name == FUNNEL[cursor]: counts[cursor] += 1; cursor += 1
    drops = [counts[i-1] - counts[i] for i in range(1, len(counts))]
    return {"steps": [{"name": n, "users": c} for n,c in zip(FUNNEL, counts)],
            "overall_conversion": counts[-1]/counts[0] if counts[0] else 0.0,
            "largest_drop_off_step": FUNNEL[drops.index(max(drops))+1] if drops else None}

def assign_variant(experiment_id: str, user_id: str) -> str:
    return "treatment" if int(hashlib.sha256(f"{experiment_id}:{user_id}".encode()).hexdigest(), 16) % 2 else "control"

def decide(db: Session, user_id: str, now: datetime | None = None) -> dict[str, Any]:
    now = now or datetime.now(timezone.utc); state = build_customer_state(db, user_id)
    if not state["known"]: result = {"action_type":"take_no_action","reason_codes":["UNKNOWN_CUSTOMER"]}
    elif state["open_support_case"]: result = {"action_type":"notify_support","reason_codes":["OPEN_SUPPORT_CASE"]}
    elif state["marketing_consent"] != "granted": result = {"action_type":"take_no_action","reason_codes":["MARKETING_CONSENT_NOT_GRANTED"]}
    else:
        names = {e.event_name for e in ordered_events(db, user_id)}
        if "checkout_started" in names and not state["purchases"]: result = {"action_type":"enroll_in_sequence","sequence":"checkout_recovery","reason_codes":["CHECKOUT_WITHOUT_PURCHASE"]}
        elif state["purchases"] and "course_started" not in names: result = {"action_type":"enroll_in_sequence","sequence":"activation","reason_codes":["PURCHASE_WITHOUT_ACTIVATION"]}
        elif "course_completed" in names: result = {"action_type":"recommend_next_product","reason_codes":["COURSE_COMPLETED"]}
        elif now - parse_dt(state["last_activity"]) >= timedelta(days=14): result = {"action_type":"enroll_in_sequence","sequence":"re_engagement","reason_codes":["INACTIVE_14_DAYS"]}
        elif "user_signed_up" in names and not state["purchases"]: result = {"action_type":"enroll_in_sequence","sequence":"educational","reason_codes":["LEAD_WITHOUT_PURCHASE"]}
        else: result = {"action_type":"take_no_action","reason_codes":["NO_ELIGIBLE_ACTION"]}
    result.update(user_id=user_id, state=state, requires_approval=result["action_type"] != "take_no_action")
    db.add(DecisionAudit(user_id=user_id, snapshot=result))
    if result["action_type"] != "take_no_action":
        key = f"{user_id}:{result.get('sequence',result['action_type'])}:{result['reason_codes'][0]}"
        action = db.scalar(select(GrowthAction).where(GrowthAction.idempotency_key == key))
        if not action:
            action = GrowthAction(action_id=str(uuid.uuid4()), user_id=user_id, action_type=result["action_type"], reason_codes=result["reason_codes"],
                evidence_event_ids=state["evidence_event_ids"], context={"sequence":result.get("sequence")}, idempotency_key=key,
                requires_approval=True, state_version=state["last_activity"], expires_at=(now+timedelta(days=2)).isoformat())
            db.add(action); db.flush()
        result["action_id"] = action.action_id
    db.commit(); return result

def policy_verdict(db: Session, action: GrowthAction, now: datetime | None = None) -> dict[str, Any]:
    now = now or datetime.now(timezone.utc); state = build_customer_state(db, action.user_id); reasons = []
    if action.action_type in MARKETING and state.get("marketing_consent") != "granted": reasons.append("NO_MARKETING_CONSENT")
    if state.get("open_support_case") and action.action_type in MARKETING: reasons.append("OPEN_SUPPORT_CASE")
    if action.expires_at and parse_dt(action.expires_at) < now: reasons.append("EXPIRED_DECISION")
    if action.state_version != state.get("last_activity"): reasons.append("STALE_STATE")
    recent = db.scalar(select(Event).where(Event.user_id==action.user_id, Event.event_name=="message_sent", Event.timestamp >= (now-timedelta(hours=24)).isoformat()))
    if recent and action.action_type in MARKETING: reasons.append("FREQUENCY_CAP")
    return {"allowed": not reasons, "reason_codes": reasons or ["POLICY_PASS"]}

def fallback_draft(action: GrowthAction, state: dict[str, Any]) -> OutreachDraft:
    product = (state.get("purchases") or ["your course"])[0]
    return OutreachDraft(subject="Your next step", body=f"Continue when it suits you: {product}.", cta="open_course", facts_used=[product],
        confidence=1.0, template_version="fallback-v1", provider="deterministic-fallback")

def approve(db: Session, action: GrowthAction, approver: str) -> dict[str, Any]:
    verdict = policy_verdict(db, action)
    if not verdict["allowed"]: return verdict
    command={"type":action.action_type,"context":action.context,"user_id":action.user_id}
    action.status="approved"; action.approver=approver; action.approved_at=datetime.now(timezone.utc).isoformat()
    action.approval_payload_hash=hashlib.sha256(json.dumps(command,sort_keys=True,separators=(",",":")).encode()).hexdigest()
    db.add(OutboxCommand(action_id=action.action_id, command=command)); db.commit()
    return {"allowed":True,"status":"approved","action_id":action.action_id}

def payload_is_approved(action:GrowthAction,command:dict)->bool:
    actual=hashlib.sha256(json.dumps(command,sort_keys=True,separators=(",",":")).encode()).hexdigest()
    return bool(action.approval_payload_hash) and actual==action.approval_payload_hash
