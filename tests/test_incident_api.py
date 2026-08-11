import json
from unittest.mock import patch

from fastapi.testclient import TestClient

from src.main import app
from src.job_runner import job_runner
from src.database import SessionLocal
from src.models.incident_report import IncidentReport as DBIncidentReport

client = TestClient(app)

def test_analyze_invalid_extension():
    response = client.post(
        "/v1/incidents/analyze",
        files={"file": ("test.jpg", b"dummy content")}
    )
    assert response.status_code == 400
    assert "Invalid file extension" in response.json()["detail"]

@patch("src.api.incident.job_runner.submit_job")
def test_analyze_success(mock_submit_job):
    # This will return a mock job ID and not run the job synchronously
    
    response = client.post(
        "/v1/incidents/analyze",
        files={"file": ("test.log", b"Jan 01 12:00:00 srv sshd[123]: Failed password for root from 1.1.1.1 port 22 ssh2")}
    )
    
    assert response.status_code == 202
    data = response.json()
    assert "incident_id" in data
    assert data["status"] == "pending"
    
    incident_id = data["incident_id"]
    
    # Check DB
    db = SessionLocal()
    report = db.query(DBIncidentReport).filter(DBIncidentReport.id == int(incident_id)).first()
    assert report is not None
    assert report.status == "pending"
    db.close()

def test_get_incident_not_found():
    response = client.get("/v1/incidents/999999")
    assert response.status_code == 404
