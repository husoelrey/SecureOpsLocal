import json
import tempfile
import uuid
from pathlib import Path
from unittest.mock import AsyncMock, patch

from src.cli.main import app
from src.schemas.incident_report import IncidentReportCreate
from typer.testing import CliRunner

runner = CliRunner()


def test_cli_version_command():
    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0
    assert "SecureOps Local" in result.stdout
    assert "v0.1.0" in result.stdout


def test_cli_version_flag():
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert "SecureOps Local" in result.stdout


def test_cli_knowledge_list():
    result = runner.invoke(app, ["knowledge", "list"])
    assert result.exit_code == 0
    # Either lists documents or shows empty banner
    assert "Knowledge Base" in result.stdout or "Indexed Knowledge Base Documents" in result.stdout


def test_cli_knowledge_add_markdown():
    uid = uuid.uuid4().hex
    with tempfile.TemporaryDirectory() as tmp_dir:
        test_file = Path(tmp_dir) / f"nist_guide_{uid}.md"
        test_file.write_text(
            f"# NIST Incident Response Guide {uid}\n\n"
            "## Section 1: Preparation\n"
            "Organizations should establish logging policies and incident handling capabilities.\n\n"
            "## Section 2: Detection and Analysis\n"
            "Monitor SSH logs for multiple failed attempts indicating brute force attacks.\n",
            encoding="utf-8"
        )

        result = runner.invoke(app, ["knowledge", "add", str(test_file)])
        assert result.exit_code == 0
        assert "Ingestion Complete" in result.stdout
        assert f"nist_guide_{uid}.md" in result.stdout


def test_cli_knowledge_add_duplicate():
    uid = uuid.uuid4().hex
    with tempfile.TemporaryDirectory() as tmp_dir:
        test_file = Path(tmp_dir) / f"unique_guide_{uid}.md"
        test_file.write_text(f"# Unique Document {uid}\nContent for duplicate test.", encoding="utf-8")

        # First add
        res1 = runner.invoke(app, ["knowledge", "add", str(test_file)])
        assert res1.exit_code == 0
        assert "Ingestion Complete" in res1.stdout

        # Duplicate add
        res2 = runner.invoke(app, ["knowledge", "add", str(test_file)])
        assert res2.exit_code == 1
        assert "Duplicate document" in res2.stdout


def test_cli_knowledge_add_invalid_extension():
    with tempfile.TemporaryDirectory() as tmp_dir:
        bad_file = Path(tmp_dir) / "test.exe"
        bad_file.write_bytes(b"binary content")

        result = runner.invoke(app, ["knowledge", "add", str(bad_file)])
        assert result.exit_code == 1
        assert "Validation error" in result.stdout or "Unsupported file extension" in result.stdout


def test_cli_analyze_invalid_file():
    # Nonexistent file
    res = runner.invoke(app, ["analyze", "nonexistent.log"])
    assert res.exit_code != 0


def test_cli_analyze_invalid_extension():
    with tempfile.TemporaryDirectory() as tmp_dir:
        bad_file = Path(tmp_dir) / "test.exe"
        bad_file.write_bytes(b"data")
        res = runner.invoke(app, ["analyze", str(bad_file)])
        assert res.exit_code == 1
        assert "Unsupported log file extension" in res.stdout


def test_cli_analyze_empty_file():
    with tempfile.TemporaryDirectory() as tmp_dir:
        empty_file = Path(tmp_dir) / "empty.log"
        empty_file.write_text("", encoding="utf-8")
        res = runner.invoke(app, ["analyze", str(empty_file)])
        assert res.exit_code == 1
        assert "Log file is empty" in res.stdout


def test_cli_analyze_success_with_mock():
    with tempfile.TemporaryDirectory() as tmp_dir:
        log_path = Path(tmp_dir) / "auth.log"
        log_path.write_text(
            "Aug 14 10:20:01 server sshd[101]: Failed password for invalid user admin from 192.168.1.50 port 22 ssh2\n"
            "Aug 14 10:20:05 server sshd[102]: Failed password for invalid user admin from 192.168.1.50 port 22 ssh2\n"
            "Aug 14 10:21:00 server sshd[103]: Accepted password for root from 10.0.0.1 port 22 ssh2\n",
            encoding="utf-8"
        )
        json_out = Path(tmp_dir) / "out_report.json"

        mock_report = IncidentReportCreate(
            status="completed",
            summary="Observed multiple failed login attempts against admin followed by root access.",
            observed_findings={"total_lines": 3},
            possible_interpretations=["Potential brute force password guessing on administrative account."],
            risk_level="high",
            risk_reasoning="Multiple authentication failures from an external IP followed by privileged session.",
            recommended_actions=["Investigate source IP 192.168.1.50", "Verify authorized root login from 10.0.0.1"],
            citations=[],
            limitations=["Syslog missing year."],
            parser_statistics={"total_lines": 3, "unparsed_lines": 0},
            model_information={"provider": "OllamaProvider", "model": "foundation-sec-8b-reasoning:q4_k_m"},
            performance_metrics={"prompt_tokens": 120, "completion_tokens": 85}
        )

        with patch("src.cli.analyze.IncidentAnalyzer.analyze_incident", new_callable=AsyncMock) as mock_analyze:
            mock_analyze.return_value = mock_report

            result = runner.invoke(app, ["analyze", str(log_path), "--output-json", str(json_out)])

            assert result.exit_code == 0
            # Check deterministic facts
            assert "192.168.1.50" in result.stdout
            assert "10.0.0.1" in result.stdout
            assert "Deterministic Facts" in result.stdout
            # Check assessment
            assert "HIGH RISK" in result.stdout
            assert "Observed multiple failed login attempts" in result.stdout
            assert "Investigate source IP" in result.stdout
            assert "Structured incident report exported to:" in result.stdout

            # Verify exported JSON
            assert json_out.exists()
            data = json.loads(json_out.read_text(encoding="utf-8"))
            assert data["risk_level"] == "high"
            assert data["status"] == "completed"


def test_cli_analyze_with_syslog_and_webhook():
    with tempfile.TemporaryDirectory() as tmp_dir:
        log_path = Path(tmp_dir) / "auth.log"
        log_path.write_text(
            "Aug 14 10:20:00 server sshd[101]: Failed password for admin from 192.168.1.50 port 1234 ssh2\n",
            encoding="utf-8",
        )

        mock_report = IncidentReportCreate(
            status="completed",
            summary="Single failed login observed.",
            observed_findings={"total_lines": 1},
            possible_interpretations=["Isolated authentication failure."],
            risk_level="LOW",
            risk_reasoning="Single attempt.",
            recommended_actions=["Monitor for further activity."],
            citations=[],
            limitations=[],
            parser_statistics={"total_lines": 1, "unparsed_lines": 0},
            model_information={"provider": "OllamaProvider", "model": "foundation-sec-8b"},
            performance_metrics={},
        )

        with patch("src.cli.analyze.IncidentAnalyzer.analyze_incident", new_callable=AsyncMock) as mock_analyze, \
             patch("src.cli.analyze.send_syslog", return_value=True) as mock_syslog, \
             patch("src.cli.analyze.send_webhook", return_value=True) as mock_webhook:

            mock_analyze.return_value = mock_report

            result = runner.invoke(
                app,
                [
                    "analyze",
                    str(log_path),
                    "--forward-syslog",
                    "127.0.0.1:514",
                    "--webhook",
                    "https://webhook.example.com/alerts",
                ],
            )

            assert result.exit_code == 0
            assert "RFC 5424 Syslog report forwarded to SIEM" in result.stdout
            assert "Incident ticket payload dispatched to webhook" in result.stdout
            mock_syslog.assert_called_once()
            mock_webhook.assert_called_once()
