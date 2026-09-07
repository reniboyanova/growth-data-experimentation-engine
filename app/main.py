import os, uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from fastapi import Depends, FastAPI, Header, HTTPException, Request, Response
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from app.database import Base, engine, get_db
from app.models import Consent, Customer, Event, Feedback, GrowthAction, OutboxCommand
from app.schemas import ApprovalInput, ConsentInput, EventCreate, EventResult, FeedbackInput, OutreachDraft, RejectionInput
from app.services.engine import approve, build_customer_state, decide, fallback_draft, funnel_metrics, payload_is_approved, policy_verdict
from app.services.experiments import experiment_results
from app.services.identity import resolve_customer
from app.services.monitoring import scan_customers
from app.observability.logging import log_event
from app.ai.agents import draft_with_agent, plan_with_agent
from app.ai.provider import OllamaProvider
from app.ai.schemas import AgentRun

@asynccontextmanager
async def lifespan(_:FastAPI):
    Base.metadata.create_all(bind=engine); yield
app = FastAPI(title="AI Growth Journey Orchestration Platform", version="1.0.0",lifespan=lifespan)
@app.middleware("http")
async def correlation(request:Request,call_next):
    cid=request.headers.get("x-correlation-id",str(uuid.uuid4())); response=await call_next(request); response.headers["x-correlation-id"]=cid
    log_event("http_request",cid,method=request.method,path=request.url.path,status=response.status_code); return response
@app.get("/health")
def health() -> dict: return {"status":"ok","mode":os.getenv("EXECUTION_MODE","simulation")}
@app.get("/ready")
def ready() -> dict: return {"status":"ready"}
def payload(row: Event) -> EventCreate:
    return EventCreate(event_id=row.event_id,user_id=row.user_id,event_name=row.event_name,timestamp=row.timestamp,source=row.source,properties=row.properties,experiment_id=row.experiment_id)
@app.post("/events",status_code=201,response_model=EventResult)
def create_event(event:EventCreate,response:Response,db:Session=Depends(get_db))->EventResult:
    db.add(Event(**event.model_dump(mode="json")))
    if not db.get(Customer,event.user_id): db.add(Customer(user_id=event.user_id,acquisition_source=event.source,data_fresh_at=event.timestamp.isoformat()))
    try: db.commit()
    except IntegrityError:
        db.rollback(); existing=db.scalar(select(Event).where(Event.event_id==event.event_id))
        if not existing: raise
        if payload(existing).model_dump(mode="json")!=event.model_dump(mode="json"): raise HTTPException(409,"event_id has different data")
        response.status_code=200; return EventResult(accepted=True,duplicate=True,event=payload(existing))
    return EventResult(accepted=True,duplicate=False,event=event)
@app.get("/events/{event_id}",response_model=EventCreate)
def read_event(event_id:str,db:Session=Depends(get_db))->EventCreate:
    row=db.scalar(select(Event).where(Event.event_id==event_id))
    if not row: raise HTTPException(404,"Event not found")
    return payload(row)
@app.post("/customers/{user_id}/consents")
def consent(user_id:str,data:ConsentInput,db:Session=Depends(get_db))->dict:
    if not db.get(Customer,user_id): db.add(Customer(user_id=user_id))
    db.add(Consent(user_id=user_id,**data.model_dump(mode="json"))); db.commit(); return {"recorded":True}
@app.get("/customers/{user_id}/state")
def state(user_id:str,db:Session=Depends(get_db))->dict: return build_customer_state(db,user_id)
@app.post("/identities/resolve")
def identity(identifiers:dict[str,str],create:bool=False,db:Session=Depends(get_db))->dict:
    result=resolve_customer(db,identifiers,create); return {"status":result.status,"user_id":result.user_id,"matches":result.matches}
@app.get("/metrics/funnel")
def funnel(source:str|None=None,db:Session=Depends(get_db))->dict: return funnel_metrics(db,source)
@app.post("/decisions/evaluate/{user_id}")
def evaluate(user_id:str,db:Session=Depends(get_db))->dict: return decide(db,user_id)
@app.post("/decisions/preview")
def preview(user_ids:list[str],db:Session=Depends(get_db))->list[dict]: return [build_customer_state(db,u) for u in user_ids]
@app.post("/jobs/scan")
def scan(limit:int=100,after:str|None=None,x_role:str=Header(default="viewer"),db:Session=Depends(get_db))->dict:
    if x_role not in {"operator","admin"}: raise HTTPException(403,"operator role required")
    return scan_customers(db,min(limit,500),after)
@app.get("/actions")
def actions(status:str|None=None,db:Session=Depends(get_db))->list[dict]:
    q=select(GrowthAction); q=q.where(GrowthAction.status==status) if status else q
    return [{"action_id":a.action_id,"user_id":a.user_id,"action_type":a.action_type,"status":a.status,"reason_codes":a.reason_codes} for a in db.scalars(q)]
@app.post("/actions/{action_id}/draft",response_model=AgentRun)
def draft(action_id:str,db:Session=Depends(get_db))->AgentRun:
    action=db.get(GrowthAction,action_id)
    if not action or action.status!="pending": raise HTTPException(409,"draft requires pending action")
    return draft_with_agent(action,build_customer_state(db,action.user_id))
@app.post("/agents/plan/{user_id}",response_model=AgentRun)
def agent_plan(user_id:str,db:Session=Depends(get_db))->AgentRun:
    baseline=decide(db,user_id); allowed=[baseline["action_type"]]
    if baseline["action_type"]!="take_no_action": allowed.append("take_no_action")
    return plan_with_agent(baseline["state"],allowed)
@app.get("/agents/health")
def agent_health()->dict:
    try: return OllamaProvider().health()
    except Exception as exc: return {"available":False,"error":type(exc).__name__}
@app.post("/actions/{action_id}/approve")
def approve_endpoint(action_id:str,data:ApprovalInput,x_role:str=Header(default="viewer"),db:Session=Depends(get_db))->dict:
    if x_role not in {"approver","admin"}: raise HTTPException(403,"approver role required")
    action=db.get(GrowthAction,action_id)
    if not action: raise HTTPException(404,"Action not found")
    return approve(db,action,data.approver)
@app.post("/actions/{action_id}/reject")
def reject(action_id:str,data:RejectionInput,x_role:str=Header(default="viewer"),db:Session=Depends(get_db))->dict:
    if x_role not in {"approver","admin"}: raise HTTPException(403,"approver role required")
    action=db.get(GrowthAction,action_id)
    if not action or action.status!="pending": raise HTTPException(409,"pending action required")
    action.status="rejected"; action.approver=data.approver; action.rejected_reason=data.reason; db.commit(); return {"status":"rejected"}
@app.post("/actions/{action_id}/execute")
def execute(action_id:str,x_role:str=Header(default="viewer"),db:Session=Depends(get_db))->dict:
    if x_role not in {"executor","admin"}: raise HTTPException(403,"executor role required")
    if os.getenv("EXECUTION_MODE","simulation")!="simulation": raise HTTPException(503,"live provider is not configured")
    action=db.get(GrowthAction,action_id); command=db.scalar(select(OutboxCommand).where(OutboxCommand.action_id==action_id))
    if not action or action.status!="approved" or not command: raise HTTPException(409,"approved outbox command required")
    verdict=policy_verdict(db,action)
    if not verdict["allowed"]: return verdict
    if not payload_is_approved(action,command.command): raise HTTPException(409,"approved payload changed")
    action.status="executed"; action.executed_at=datetime.now(timezone.utc).isoformat(); action.provider_id=f"fake-{uuid.uuid4()}"; command.status="done"; db.commit()
    return {"status":"executed","simulated":True,"provider_id":action.provider_id}
@app.post("/webhooks/provider")
def webhook(data:FeedbackInput,x_webhook_secret:str=Header(default=""),db:Session=Depends(get_db))->dict:
    if x_webhook_secret!=os.getenv("WEBHOOK_SECRET","local-demo-secret"): raise HTTPException(401,"invalid signature")
    if db.get(Feedback,data.callback_id): return {"accepted":True,"duplicate":True}
    db.add(Feedback(**data.model_dump(mode="json"))); db.commit(); return {"accepted":True,"duplicate":False}
@app.get("/experiments/{experiment_id}/results")
def experiment(experiment_id:str,minimum_sample:int=30,db:Session=Depends(get_db))->dict:
    return experiment_results(db,experiment_id,minimum_sample)
