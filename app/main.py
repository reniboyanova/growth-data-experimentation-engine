from fastapi import Depends, FastAPI, HTTPException, Response
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Event
from app.schemas import EventCreate, EventResult

app = FastAPI(title="Growth Data & Experimentation Engine", version="0.2.0")

@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}

def as_payload(row: Event) -> EventCreate:
    return EventCreate(
        event_id=row.event_id,
        user_id=row.user_id,
        event_name=row.event_name,
        timestamp=row.timestamp,
        source=row.source,
        properties=row.properties,
        experiment_id=row.experiment_id,
    )

@app.post("/events", status_code=201, response_model=EventResult)
def create_event(
    event: EventCreate,
    response: Response,
    db: Session = Depends(get_db),
) -> EventResult:
    row = Event(**event.model_dump(mode="json"))
    db.add(row)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        existing = db.scalar(select(Event).where(Event.event_id == event.event_id))
        if existing is None:
            raise
        if as_payload(existing).model_dump(mode="json") != event.model_dump(mode="json"):
            raise HTTPException(status_code=409, detail="event_id has different data")
        response.status_code = 200
        return EventResult(accepted=True, duplicate=True, event=as_payload(existing))
    return EventResult(accepted=True, duplicate=False, event=event)

@app.get("/events/{event_id}", response_model=EventCreate)
def read_event(event_id: str, db: Session = Depends(get_db)) -> EventCreate:
    row = db.scalar(select(Event).where(Event.event_id == event_id))
    if row is None:
        raise HTTPException(status_code=404, detail="Event not found")
    return as_payload(row)