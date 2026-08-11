import json
from unittest.mock import patch

from fastapi.testclient import TestClient

from src.main import app
from src.job_runner import job_runner

client = TestClient(app)

def test_benchmark_run_invalid_extension():
    response = client.post(
        "/v1/benchmarks/run",
        files={"file": ("test.jpg", b"dummy content")}
    )
    assert response.status_code == 400
    assert "Invalid file extension" in response.json()["detail"]

@patch("src.api.benchmark.job_runner.submit_job")
def test_benchmark_run_success(mock_submit_job):
    mock_submit_job.return_value = "bench-123"
    
    response = client.post(
        "/v1/benchmarks/run",
        files={"file": ("test.log", b"Jan 01 12:00:00 srv sshd[123]: Failed password for root from 1.1.1.1 port 22 ssh2")}
    )
    
    assert response.status_code == 202
    data = response.json()
    assert "benchmark_id" in data
    assert data["status"] == "pending"

def test_get_benchmark_not_found():
    response = client.get("/v1/benchmarks/999999")
    assert response.status_code == 404
