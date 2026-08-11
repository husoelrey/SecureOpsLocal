from fastapi.testclient import TestClient
from src.main import app

client = TestClient(app)

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

def test_get_models():
    response = client.get("/models")
    assert response.status_code == 200
    data = response.json()
    assert "models" in data
    assert len(data["models"]) == 3
    
    model_ids = [m["id"] for m in data["models"]]
    assert "foundation-sec-8b-reasoning:q4_k_m" in model_ids
    assert "qwen:0.5b" in model_ids
    assert "Phi-3-mini-4k-instruct-onnx" in model_ids
