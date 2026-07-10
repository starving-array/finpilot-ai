from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health_endpoint_degraded():
    """When no model file is present, health returns 503 DEGRADED."""
    response = client.get("/health")
    assert response.status_code == 503
    data = response.json()
    assert data["status"] == "DEGRADED"
    assert data["model_loaded"] is False


def test_predict_no_model():
    """When no model is loaded, predict returns 503 regardless of request."""
    response = client.post("/predict", json={
        "customer_id": "CUST00001",
        "business_type": "retail",
    })
    assert response.status_code == 503
    assert response.json()["detail"] == "Model not loaded"


def test_predict_invalid_body():
    response = client.post("/predict", json={"invalid": "data"})
    assert response.status_code == 422


def test_predict_invalid_business_type():
    """When no model is loaded, predict returns 503 (model check is first)."""
    response = client.post("/predict", json={
        "customer_id": "CUST00001",
        "business_type": "invalid_type",
    })
    assert response.status_code == 503
