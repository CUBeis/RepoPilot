from fastapi.testclient import TestClient

from repopilot.main import app


def test_health_endpoint_returns_service_status() -> None:
    client = TestClient(app)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "RepoPilot",
        "version": "0.1.0",
    }
