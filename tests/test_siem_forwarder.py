import socket
from unittest.mock import MagicMock, patch

import pytest
from src.integrations.siem_forwarder import (
    compute_syslog_pri,
    format_rfc5424_syslog,
    parse_syslog_target,
    send_syslog,
)
from src.schemas.incident_report import IncidentReportCreate


@pytest.fixture
def sample_incident_report():
    return IncidentReportCreate(
        status="completed",
        summary="Repeated SSH authentication failures detected.",
        observed_findings={
            "total_lines": 10,
            "failed_attempts": 10,
            "source_ip": "192.168.1.100",
        },
        possible_interpretations=["Automated credential stuffing or dictionary attack"],
        risk_level="HIGH",
        risk_reasoning="High failure volume within short interval targeting privileged accounts.",
        recommended_actions=["Review bastion logs", "Verify MFA enforcement"],
        citations=["chk_nist_01"],
        limitations=["Assumed current year for timestamps"],
        parser_statistics={"total_lines": 10, "unparsed_lines": 0},
        model_information={"provider": "OllamaProvider", "model": "foundation-sec-8b"},
        performance_metrics={"total_latency_ms": 450},
    )


def test_compute_syslog_pri():
    assert compute_syslog_pri("HIGH") == 34  # 4 * 8 + 2 (Critical)
    assert compute_syslog_pri("MEDIUM") == 36  # 4 * 8 + 4 (Warning)
    assert compute_syslog_pri("LOW") == 38  # 4 * 8 + 6 (Informational)
    assert compute_syslog_pri("UNKNOWN") == 37  # 4 * 8 + 5 (Notice)


def test_parse_syslog_target():
    assert parse_syslog_target("127.0.0.1:514") == ("127.0.0.1", 514)
    assert parse_syslog_target("siem.local:5514") == ("siem.local", 5514)
    assert parse_syslog_target("10.0.0.1") == ("10.0.0.1", 514)
    assert parse_syslog_target("[::1]:514") == ("::1", 514)


def test_format_rfc5424_syslog(sample_incident_report):
    msg = format_rfc5424_syslog(sample_incident_report, incident_id="inc_test_1234", hostname="sec-host")
    assert msg.startswith("<34>1 ")
    assert "sec-host secureops inc_test_1234 INCIDENT_REPORT" in msg
    assert '[secureops@53457 incident_id="inc_test_1234" risk_level="HIGH" status="completed"]' in msg
    assert "Repeated SSH authentication failures detected." in msg
    assert "Automated credential stuffing" in msg


def test_send_syslog_udp(sample_incident_report):
    with patch("socket.socket") as mock_sock_cls:
        mock_sock = MagicMock()
        mock_sock_cls.return_value.__enter__.return_value = mock_sock

        success = send_syslog("127.0.0.1:514", sample_incident_report, protocol="udp", incident_id="inc_123")
        assert success is True
        mock_sock.sendto.assert_called_once()
        args, kwargs = mock_sock.sendto.call_args
        assert args[1] == ("127.0.0.1", 514)
        assert b"<34>1 " in args[0]


def test_send_syslog_tcp(sample_incident_report):
    with patch("socket.socket") as mock_sock_cls:
        mock_sock = MagicMock()
        mock_sock_cls.return_value.__enter__.return_value = mock_sock

        success = send_syslog("10.0.0.5:6514", sample_incident_report, protocol="tcp", incident_id="inc_123")
        assert success is True
        mock_sock.connect.assert_called_once_with(("10.0.0.5", 6514))
        mock_sock.sendall.assert_called_once()


def test_send_syslog_error_handled(sample_incident_report):
    with patch("socket.socket") as mock_sock_cls:
        mock_sock = MagicMock()
        mock_sock.connect.side_effect = socket.error("Connection refused")
        mock_sock_cls.return_value.__enter__.return_value = mock_sock

        success = send_syslog("127.0.0.1:514", sample_incident_report, protocol="tcp")
        assert success is False
