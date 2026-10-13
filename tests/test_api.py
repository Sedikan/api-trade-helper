from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_health():
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["data_mode"] == "demo"


def test_analyze_marks_demo_data_fresh():
    response = client.post(
        "/api/analyze",
        json={"instrument": "NVDA", "profile": {"capital": 10000}},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["recommendation"]["instrument"] == "NVDA"
    assert body["recommendation"]["disclaimer"]


def test_portfolio_import_rejects_non_csv():
    response = client.post(
        "/api/portfolio/import",
        files={"file": ("positions.txt", b"instrument,side", "text/plain")},
    )
    assert response.status_code == 400
