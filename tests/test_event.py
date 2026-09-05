from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_create_valid_event() -> None:
    response = client.post(
        "/events",
        json={
            "user_id": "user-001",
            "event_name": "user_signed_up",
            "timestamp": "2026-09-02T12:00:00Z",
            "source": "linkedin",
            "properties": {"plan": "trial"},
        },
    )

    assert response.status_code == 201
    assert response.json()["accepted"] is True


def test_reject_event_without_user_id() -> None:
    response = client.post(
        "/events",
        json={
            "event_name": "user_signed_up",
            "timestamp": "2026-09-02T12:00:00Z",
            "source": "linkedin",
        },
    )

    assert response.status_code == 422