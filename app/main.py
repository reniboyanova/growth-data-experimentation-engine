from fastapi import FastAPI, status

from app.schemas import EventCreate

app = FastAPI(
    title="Growth Data & Experimentation Engine",
    version="0.1.0",
)


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/events", status_code=status.HTTP_201_CREATED)
def create_event(event: EventCreate) -> dict:
    return {"accepted": True, "event": event.model_dump()}