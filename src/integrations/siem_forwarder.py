import datetime
import logging
import os
import socket
from typing import Tuple, Union

from src.schemas.incident_report import IncidentReport, IncidentReportCreate

logger = logging.getLogger(__name__)

DEFAULT_SYSLOG_PORT = 514
FACILITY_AUTH_SECURITY = 4  # Security / Authorization messages


def compute_syslog_pri(risk_level: str) -> int:
    """
    Compute RFC 5424 PRI value from facility and severity.
    Facility: 4 (Security/Auth)
    Severity:
      - HIGH -> 2 (Critical)
      - MEDIUM -> 4 (Warning)
      - LOW -> 6 (Informational)
      - default -> 5 (Notice)
    """
    normalized_risk = (risk_level or "").strip().upper()
    if normalized_risk == "HIGH":
        severity = 2  # Critical
    elif normalized_risk == "MEDIUM":
        severity = 4  # Warning
    elif normalized_risk == "LOW":
        severity = 6  # Informational
    else:
        severity = 5  # Notice

    return (FACILITY_AUTH_SECURITY * 8) + severity


def parse_syslog_target(target: str) -> Tuple[str, int]:
    """Parse host and port from 'host:port' or 'host' string."""
    target_clean = target.strip()
    if ":" in target_clean and not target_clean.startswith("["):
        parts = target_clean.split(":")
        host = parts[0].strip()
        try:
            port = int(parts[1].strip())
        except ValueError:
            port = DEFAULT_SYSLOG_PORT
        return host, port
    elif target_clean.startswith("[") and "]:" in target_clean:
        # IPv6 [::1]:514
        host_part, port_part = target_clean.rsplit(":", 1)
        host = host_part.strip("[]")
        try:
            port = int(port_part)
        except ValueError:
            port = DEFAULT_SYSLOG_PORT
        return host, port
    else:
        return target_clean, DEFAULT_SYSLOG_PORT


def format_rfc5424_syslog(
    report: Union[IncidentReportCreate, IncidentReport],
    incident_id: str | None = None,
    hostname: str | None = None,
) -> str:
    """
    Format the IncidentReport into a standard RFC 5424 Syslog message.
    Header: <PRI>VERSION TIMESTAMP HOSTNAME APP-NAME PROCID MSGID [STRUCTURED-DATA] MSG
    """
    pri = compute_syslog_pri(report.risk_level)
    version = "1"
    timestamp_utc = datetime.datetime.now(datetime.timezone.utc).strftime(
        "%Y-%m-%dT%H:%M:%S.%fZ"
    )
    host = hostname or socket.gethostname() or "secureops-local"
    app_name = "secureops"
    proc_id = getattr(report, "incident_id", incident_id or str(os.getpid()))
    msg_id = "INCIDENT_REPORT"

    # RFC 5424 Structured Data
    status_str = report.status
    risk_str = report.risk_level.upper()
    structured_data = (
        f'[secureops@53457 incident_id="{proc_id}" risk_level="{risk_str}" status="{status_str}"]'
    )

    # Message payload (JSON serialized IncidentReport)
    # UTF-8 BOM prefix for RFC 5424 unicode MSG compliance
    json_payload = report.model_dump_json()
    bom = "\ufeff"

    syslog_msg = (
        f"<{pri}>{version} {timestamp_utc} {host} {app_name} {proc_id} {msg_id} {structured_data} {bom}{json_payload}"
    )
    return syslog_msg


def send_syslog(
    target: str,
    report: Union[IncidentReportCreate, IncidentReport],
    protocol: str = "udp",
    incident_id: str | None = None,
    timeout: float = 3.0,
) -> bool:
    """
    Transmit an RFC 5424 Syslog incident message over UDP or TCP to a SIEM endpoint.
    Guarantees that raw PII security logs are NEVER transmitted, only the generated report.
    """
    host, port = parse_syslog_target(target)
    message_str = format_rfc5424_syslog(report, incident_id=incident_id)
    message_bytes = message_str.encode("utf-8")

    proto_lower = protocol.strip().lower()

    if proto_lower == "tcp":
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(timeout)
                sock.connect((host, port))
                sock.sendall(message_bytes + b"\n")
            logger.info(f"Successfully forwarded RFC 5424 Syslog report to TCP {host}:{port}")
            return True
        except Exception as e:
            logger.error(f"Failed to send Syslog to TCP {host}:{port}: {e}")
            return False
    else:
        # Default UDP
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
                sock.settimeout(timeout)
                sock.sendto(message_bytes, (host, port))
            logger.info(f"Successfully forwarded RFC 5424 Syslog report to UDP {host}:{port}")
            return True
        except Exception as e:
            logger.error(f"Failed to send Syslog to UDP {host}:{port}: {e}")
            return False
