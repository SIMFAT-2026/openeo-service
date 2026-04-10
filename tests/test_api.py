from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_returns_ok() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["service"] == "openeo-service"


def test_config_check_endpoint_exists() -> None:
    response = client.get("/config/check")
    assert response.status_code == 200
    body = response.json()
    assert "configured" in body
    assert "missingFields" in body


def test_ndvi_placeholder_accepts_request() -> None:
    payload = {
        "regionId": "region-001",
        "periodStart": "2025-01-01",
        "periodEnd": "2025-01-31",
    }
    response = client.post("/jobs/ndvi", json=payload)
    assert response.status_code == 202
    body = response.json()
    assert body["indicatorType"] == "NDVI"
    assert body["status"] == "accepted"
    assert body["source"] == "openEO"
