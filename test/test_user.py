from datetime import UTC, datetime, timedelta
from uuid import uuid4
from starlette.testclient import TestClient
from app.main import app

client = TestClient(app)

def _register_user_if_needed(username: str, password: str) -> None:
    response = client.post(
        "/auth/register",
        json={"username": username, "password": password},
    )
    assert response.status_code == 200, response.text


def _get_auth_token(username: str, password: str) -> str:
    response = client.post(
        "/auth/token",
        data={"username": username, "password": password},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert "access_token" in body
    return body["access_token"]


def test_login_create_and_delete_task():
    username = f"testuser_{uuid4().hex[:8]}"
    password = "password123"

    _register_user_if_needed(username, password)
    token = _get_auth_token(username, password)

    create_payload = {
        "title": "Test Task",
        "description": "This is a test task.",
        "status": "pending",
        "deadline": (datetime.now(UTC) + timedelta(days=1)).isoformat(),
    }

    create_response = client.post(
        "/tasks",
        json=create_payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert create_response.status_code == 200, create_response.text

    created_task = create_response.json()
    assert created_task["title"] == create_payload["title"]
    task_id = created_task["id"]

    delete_response = client.delete(
        f"/tasks/{task_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert delete_response.status_code == 200, delete_response.text
    assert delete_response.json()["message"] == "Task deleted successfully"

    get_response = client.get(
        f"/tasks/{task_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert get_response.status_code == 404, get_response.text