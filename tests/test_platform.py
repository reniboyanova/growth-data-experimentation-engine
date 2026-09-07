from datetime import datetime, timedelta, timezone
import pytest
from fastapi.testclient import TestClient
from app.database import Base, SessionLocal, engine
from app.main import app
from app.services.engine import assign_variant
from app.models import ExperimentAssignment, OutboxCommand

client=TestClient(app)
@pytest.fixture(autouse=True)
def clean_db():
    Base.metadata.drop_all(engine); Base.metadata.create_all(engine); yield

def event(eid,user,name,when="2026-09-01T10:00:00Z",props=None):
    return client.post("/events",json={"event_id":eid,"user_id":user,"event_name":name,"timestamp":when,"source":"demo","properties":props or {}})

def test_event_validation_dedup_and_conflict():
    assert event("e1","u1","user_signed_up").status_code==201
    assert event("e1","u1","user_signed_up").json()["duplicate"] is True
    assert event("e1","u1","other").status_code==409
    assert client.post("/events",json={"event_id":"x"}).status_code==422

def test_ordered_funnel_ignores_out_of_order():
    for i,n in enumerate(["user_signed_up","email_verified","first_project_created","subscription_started"]): event(f"a{i}","a",n,f"2026-09-0{i+1}T10:00:00Z")
    event("b1","b","subscription_started"); event("b2","b","user_signed_up","2026-09-02T10:00:00Z")
    data=client.get("/metrics/funnel").json(); assert [x["users"] for x in data["steps"]]==[2,1,1,1]; assert data["overall_conversion"]==0.5

def test_state_keeps_progress_per_product_and_unknown_consent():
    event("p1","u","course_started",props={"product_id":"python"}); event("p2","u","lesson_completed","2026-09-02T10:00:00Z",{"product_id":"sql","lesson":"1"})
    state=client.get("/customers/u/state").json(); assert set(state["course_progress"])=={"python","sql"}; assert state["marketing_consent"]=="unknown"

def test_support_has_priority():
    event("s1","u","user_signed_up"); event("s2","u","support_case_opened")
    result=client.post("/decisions/evaluate/u").json(); assert result["action_type"]=="notify_support"

def test_unknown_consent_blocks_marketing_candidate():
    event("s1","u","user_signed_up"); result=client.post("/decisions/evaluate/u").json()
    assert result["action_type"]=="take_no_action"; assert result["reason_codes"]==["MARKETING_CONSENT_NOT_GRANTED"]

def test_approved_action_executes_once_in_simulation():
    event("s1","u","user_signed_up"); client.post("/customers/u/consents",json={"status":"granted","source":"fixture","timestamp":"2026-09-01T09:00:00Z"})
    action_id=client.post("/decisions/evaluate/u").json()["action_id"]
    assert client.post(f"/actions/{action_id}/approve",json={"approver":"reviewer"},headers={"x-role":"approver"}).json()["status"]=="approved"
    done=client.post(f"/actions/{action_id}/execute",headers={"x-role":"executor"}).json(); assert done["simulated"] is True
    assert client.post(f"/actions/{action_id}/execute",headers={"x-role":"executor"}).status_code==409

def test_feedback_is_idempotent_and_authenticated():
    body={"callback_id":"cb1","action_id":"a1","event_name":"clicked","timestamp":"2026-09-01T12:00:00Z"}
    assert client.post("/webhooks/provider",json=body).status_code==401
    headers={"x-webhook-secret":"local-demo-secret"}; assert client.post("/webhooks/provider",json=body,headers=headers).json()["duplicate"] is False
    assert client.post("/webhooks/provider",json=body,headers=headers).json()["duplicate"] is True

def test_assignment_is_stable():
    assert assign_variant("exp","u") == assign_variant("exp","u")

def test_identity_create_resolve_and_ambiguous():
    created=client.post("/identities/resolve?create=true",json={"anonymous_id":"anon-1"}).json()
    assert created["status"]=="created"
    resolved=client.post("/identities/resolve",json={"anonymous_id":"anon-1","email_hash":"hash-1"}).json()
    assert resolved["user_id"]==created["user_id"]
    other=client.post("/identities/resolve?create=true",json={"crm_id":"crm-2"}).json()
    ambiguous=client.post("/identities/resolve",json={"anonymous_id":"anon-1","crm_id":"crm-2"}).json()
    assert ambiguous["status"]=="ambiguous" and len(ambiguous["matches"])==2

def test_scan_requires_role_and_has_checkpoint():
    event("scan-1","scan-user","user_signed_up")
    assert client.post("/jobs/scan").status_code==403
    result=client.post("/jobs/scan?limit=10",headers={"x-role":"operator"}).json()
    assert result["processed"]==1 and result["next_cursor"]=="scan-user"

def test_modified_payload_invalidates_approval():
    event("tamper-1","u","user_signed_up"); client.post("/customers/u/consents",json={"status":"granted","source":"fixture","timestamp":"2026-09-01T09:00:00Z"})
    aid=client.post("/decisions/evaluate/u").json()["action_id"]
    client.post(f"/actions/{aid}/approve",json={"approver":"reviewer"},headers={"x-role":"approver"})
    with SessionLocal() as db:
        command=db.query(OutboxCommand).filter_by(action_id=aid).one(); command.command={"type":"send_personalized_email","context":{"tampered":True}}; db.commit()
    assert client.post(f"/actions/{aid}/execute",headers={"x-role":"executor"}).status_code==409

def test_experiment_reports_insufficient_then_ready():
    with SessionLocal() as db:
        for i in range(4):
            db.add(ExperimentAssignment(experiment_id="exp",user_id=f"u{i}",variant="control" if i<2 else "treatment",eligible_at="2026-01-01T00:00:00Z",exposed_at="2026-01-01T00:00:00Z",converted=i in {0,2,3}))
        db.commit()
    low=client.get("/experiments/exp/results").json(); assert low["status"]=="insufficient_data"
    ready=client.get("/experiments/exp/results?minimum_sample=2").json(); assert ready["status"]=="ready" and ready["absolute_uplift"]==0.5
