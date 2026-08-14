from unittest.mock import MagicMock, patch

import httpx
import pytest
from src.integrations.webhook import build_webhook_payload, send_webhook
from src.schemas.incident_report import IncidentReportCreate


@pytest.fixture
def sample_incident_report():
    return IncidentReportCreate(
        status="completed",
        summary="Nginx SQL injection attack detected from multiple IPs.",
        observed_findings={
            "total_lines": 5,
            "failed_attempts": 5,
            "source_ip": "198.51.100.22",
        },
        possible_interpretations=["Automated SQL injection probe attempting data exfiltration"],
        risk_level="HIGH",
        risk_reasoning="Multiple SQL syntax injection patterns detected in HTTP GET parameters.",
        recommended_actions=["Deploy WAF block rule for SQL patterns", "Inspect web application logs"],
        citations=["chk_owasp_a03"],
        limitations=["Raw payloads URL-decoded prior to inspection"],
        parser_statistics={"total_lines": 5, "unparsed_lines": 0},
        model_information={"provider": "OllamaProvider", "model": "foundation-sec-8b"},
        performance_metrics={"total_latency_ms": 320},
    )


def test_build_webhook_payload_structure(sample_incident_report):
    payload = build_webhook_payload(sample_incident_report, incident_id="inc_live_sqli_01")
    assert payload["event"] == "security_incident_report"
    assert payload["incident_id"] == "inc_live_sqli_01"
    assert payload["risk_level"] == "HIGH"
    assert "Nginx SQL injection" in payload["summary"]

    # Jira integration fields
    assert "jira" in payload
    assert payload["jira"]["fields"]["project"]["key"] == "SEC"
    assert "[SecureOps Alert] HIGH:" in payload["jira"]["fields"]["summary"]

    # ServiceNow integration fields
    assert "servicenow" in payload
    assert payload["servicenow"]["urgency"] == "1"
    assert payload["servicenow"]["impact"] == "1"
    assert "[SecureOps inc_live_sqli_01]" in payload["servicenow"]["short_description"]


def test_send_webhook_success(sample_incident_report):
    with patch("httpx.Client.post") as mock_post:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_post.return_value = mock_resp

        success = send_webhook("https://webhook.example.com/sec-ops", sample_incident_report, incident_id="inc_001")
        assert success is True
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        assert args[0] == "https://webhook.example.com/sec-ops"
        assert kwargs["json"]["incident_id"] == "inc_001"


def test_send_webhook_non_success_status(sample_incident_report):
    with patch("httpx.Client.post") as mock_post:
        mock_resp = MagicMock()
        mock_resp.status_code = 500
        mock_resp.text = "Internal Server Error"
        mock_post.return_value = mock_resp

        success = send_webhook("https://webhook.example.com/sec-ops", sample_incident_report)
        assert success is False


def test_send_webhook_network_error(sample_incident_report):
    with patch("httpx.Client.post") as mock_post:
        mock_post.side_effect = httpx.RequestError("DNS resolution failed")

        success = send_webhook("https://invalid-host-unreachable/sec-ops", sample_incident_report)
        assert success is False
