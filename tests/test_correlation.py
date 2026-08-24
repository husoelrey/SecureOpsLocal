import datetime
import json
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from src.cli.main import app
from src.llm.analyzer import IncidentAnalyzer
from src.llm.base import LocalLLMProvider
from src.parser.aggregator import CrossLogAggregator, aggregate_logs
from src.parser.nginx import NginxAccessParser
from src.parser.ssh import SSHAuthLogParser
from src.schemas.incident_report import IncidentReportCreate
from src.schemas.llm import NormalizedGenerationResult
from src.schemas.parsed_log_line import ParsedLogLineCreate
from src.schemas.rag import DocumentChunk
from src.watcher.engine import LogWatcherEngine
from src.watcher.window import SlidingWindowEventTracker
from typer.testing import CliRunner

runner = CliRunner()


class MockLLM(LocalLLMProvider):
    def __init__(self, model_name: str = "mock-model"):
        self.model_name = model_name

    async def is_available(self) -> bool:
        return True

    async def generate(
        self, prompt: str, system_prompt: str, schema: dict
    ) -> NormalizedGenerationResult:
        return NormalizedGenerationResult(
            content=json.dumps({
                "summary": "Multi-stage attack detected across web and SSH sources.",
                "possible_interpretations": [
                    "Attacker probed web application then attempted SSH brute-force."
                ],
                "risk_level": "high",
                "risk_reasoning": "Temporal progression from web reconnaissance to SSH authentication failures from the same source IP.",
                "recommended_actions": [
                    "Block or isolate source IP at network boundary",
                    "Audit web and SSH access logs",
                ],
                "citations": ["chunk_001"],
            }),
            prompt_tokens=150,
            completion_tokens=90,
            total_latency_ms=250.0,
            time_to_first_token_ms=50.0,
        )


def test_cross_log_aggregator_multi_source():
    t1 = datetime.datetime(2026, 8, 24, 10, 0, 0, tzinfo=datetime.timezone.utc)
    t2 = datetime.datetime(2026, 8, 24, 10, 5, 0, tzinfo=datetime.timezone.utc)
    t3 = datetime.datetime(2026, 8, 24, 10, 10, 0, tzinfo=datetime.timezone.utc)

    # 1. Nginx SQLi attempt
    ev_nginx = ParsedLogLineCreate(
        timestamp=t1,
        source_ip="198.51.100.50",
        event_type="sqli_attempt",
        raw_content="GET /login?user=admin' OR '1'='1 HTTP/1.1",
        is_parsed=True,
    )

    # 2. SSH Failed login
    ev_ssh = ParsedLogLineCreate(
        timestamp=t2,
        source_ip="198.51.100.50",
        user="root",
        event_type="failed_login",
        port=22,
        raw_content="Failed password for root from 198.51.100.50 port 22 ssh2",
        is_parsed=True,
    )

    # 3. Windows logon failure
    ev_win = ParsedLogLineCreate(
        timestamp=t3,
        source_ip="198.51.100.50",
        user="Administrator",
        event_type="windows_event_4625",
        raw_content="An account failed to log on. Account: Administrator",
        is_parsed=True,
    )

    # Another benign IP
    ev_other = ParsedLogLineCreate(
        timestamp=t1,
        source_ip="10.0.0.1",
        user="service_account",
        event_type="successful_login",
        is_parsed=True,
        raw_content="Accepted password for service_account",
    )

    aggregator = CrossLogAggregator()
    aggregator.add_events([ev_win, ev_nginx, ev_ssh, ev_other])  # deliberately added out of order

    # Verify grouping and sorting by timestamp
    by_ip = aggregator.correlate_by_ip()
    assert "198.51.100.50" in by_ip
    events_50 = by_ip["198.51.100.50"]
    assert len(events_50) == 3
    assert events_50[0].event_type == "sqli_attempt"
    assert events_50[1].event_type == "failed_login"
    assert events_50[2].event_type == "windows_event_4625"

    # Verify aggregation
    analysis = aggregator.aggregate()
    assert analysis.total_lines == 4
    assert analysis.unparsed_lines == 0
    assert len(analysis.ip_aggregations) == 2

    # Top IP should be 198.51.100.50 with 3 failed/attack attempts
    top_ip = analysis.ip_aggregations[0]
    assert top_ip.ip == "198.51.100.50"
    assert top_ip.failed_attempts == 3
    assert top_ip.successful_attempts == 0
    assert set(top_ip.users_attempted) == {"Administrator", "root"}
    assert top_ip.first_seen == t1
    assert top_ip.last_seen == t3

    # Check multi_source_timeline
    assert "198.51.100.50" in analysis.multi_source_timeline
    timeline = analysis.multi_source_timeline["198.51.100.50"]
    assert len(timeline) == 3
    assert timeline[0]["event_type"] == "sqli_attempt"
    assert timeline[1]["event_type"] == "failed_login"
    assert timeline[2]["event_type"] == "windows_event_4625"


def test_cross_log_aggregator_add_file(tmp_path: Path):
    nginx_file = tmp_path / "nginx.log"
    nginx_file.write_text(
        '198.51.100.77 - - [24/Aug/2026:10:00:00 +0000] "GET /app?id=1%20UNION%20SELECT%20null HTTP/1.1" 200 450 "-" "curl/7.68.0"\n',
        encoding="utf-8",
    )

    ssh_file = tmp_path / "auth.log"
    ssh_file.write_text(
        "Aug 24 10:05:00 server sshd[123]: Failed password for invalid user admin from 198.51.100.77 port 4422 ssh2\n",
        encoding="utf-8",
    )

    aggregator = CrossLogAggregator(current_year=2026)
    aggregator.add_file(nginx_file, NginxAccessParser())
    aggregator.add_file(ssh_file, SSHAuthLogParser())

    analysis = aggregator.aggregate()
    assert analysis.total_lines == 2
    assert len(analysis.ip_aggregations) == 1
    assert analysis.ip_aggregations[0].ip == "198.51.100.77"
    assert analysis.ip_aggregations[0].failed_attempts == 2

    timeline = analysis.multi_source_timeline["198.51.100.77"]
    assert len(timeline) == 2
    assert timeline[0]["event_type"] == "sqli_attempt"
    assert timeline[1]["event_type"] == "failed_login_invalid_user"


def test_incident_analyzer_user_prompt_multi_source_timeline():
    t1 = datetime.datetime(2026, 8, 24, 10, 0, 0, tzinfo=datetime.timezone.utc)
    t2 = datetime.datetime(2026, 8, 24, 10, 2, 0, tzinfo=datetime.timezone.utc)

    ev1 = ParsedLogLineCreate(
        timestamp=t1,
        source_ip="1.2.3.4",
        event_type="sqli_attempt",
        raw_content="GET /?q=UNION SELECT",
        is_parsed=True,
    )
    ev2 = ParsedLogLineCreate(
        timestamp=t2,
        source_ip="1.2.3.4",
        user="root",
        event_type="failed_login",
        port=22,
        raw_content="Failed password for root",
        is_parsed=True,
    )

    analysis = aggregate_logs([ev1, ev2])
    chunks = [
        DocumentChunk(
            document_id="doc_001",
            chunk_id="chunk_001",
            source_title="NIST SP 800-61",
            section_or_page="Section 3.2",
            content="Correlation across multiple log sources aids in detecting multi-stage attack campaigns.",
            word_count=12,
        )
    ]

    provider = MockLLM(model_name="mock-model")
    analyzer = IncidentAnalyzer(provider=provider)
    prompt = analyzer._build_user_prompt(analysis, chunks)

    assert "## Multi-Source Correlation Timeline" in prompt
    assert "### Source IP: 1.2.3.4" in prompt
    assert "Event: sqli_attempt" in prompt
    assert "Event: failed_login | User: root" in prompt
    assert "--- Chunk ID: chunk_001 ---" in prompt


@pytest.mark.asyncio
async def test_incident_analyzer_assessment_flow():
    t1 = datetime.datetime(2026, 8, 24, 10, 0, 0, tzinfo=datetime.timezone.utc)
    ev = ParsedLogLineCreate(
        timestamp=t1,
        source_ip="1.2.3.4",
        event_type="sqli_attempt",
        raw_content="SQLi",
        is_parsed=True,
    )
    analysis = aggregate_logs([ev])
    chunks = [
        DocumentChunk(
            document_id="doc_001",
            chunk_id="chunk_001",
            source_title="OWASP Top 10",
            section_or_page="A03:2021-Injection",
            content="SQL Injection security guidelines.",
            word_count=5,
        )
    ]

    provider = MockLLM(model_name="mock-model")
    analyzer = IncidentAnalyzer(provider=provider)
    report = await analyzer.analyze_incident("inc_test_001", analysis, chunks)

    assert report.status == "completed"
    assert report.risk_level.upper() == "HIGH"
    assert "Multi-stage attack" in report.summary
    assert "chunk_001" in report.citations


def test_cli_analyze_multiple_files(tmp_path: Path):
    nginx_log = tmp_path / "web_access.log"
    nginx_log.write_text(
        '198.51.100.99 - - [24/Aug/2026:12:00:00 +0000] "GET /search?q=<script>alert(1)</script> HTTP/1.1" 200 120 "-" "Mozilla"\n',
        encoding="utf-8",
    )

    ssh_log = tmp_path / "auth.log"
    ssh_log.write_text(
        "Aug 24 12:05:00 host sshd[401]: Failed password for root from 198.51.100.99 port 2222 ssh2\n",
        encoding="utf-8",
    )

    json_out = tmp_path / "correlated_report.json"

    mock_report = IncidentReportCreate(
        status="completed",
        summary="Correlated multi-source attack from 198.51.100.99 (XSS in Nginx followed by SSH brute-force).",
        observed_findings={"total_lines": 2},
        possible_interpretations=["Coordinated reconnaissance and credential testing."],
        risk_level="HIGH",
        risk_reasoning="Same source IP attempted XSS web injection then moved to SSH brute-force.",
        recommended_actions=["Review web application sanitization", "Verify SSH host firewall rules"],
        citations=[],
        limitations=[],
        parser_statistics={"total_lines": 2, "unparsed_lines": 0},
        model_information={"provider": "OllamaProvider", "model": "foundation-sec-8b"},
        performance_metrics={},
    )

    with patch("src.cli.analyze.IncidentAnalyzer.analyze_incident", new_callable=AsyncMock) as mock_analyze:
        mock_analyze.return_value = mock_report

        result = runner.invoke(
            app,
            [
                "analyze",
                "--file",
                str(nginx_log),
                "--log-type",
                "nginx",
                "--file",
                str(ssh_log),
                "--log-type",
                "ssh",
                "--year",
                "2026",
                "--output-json",
                str(json_out),
            ],
        )

        assert result.exit_code == 0
        assert "web_access.log, auth.log" in result.stdout or "web_access.log" in result.stdout
        assert "NGINX, SSH" in result.stdout
        assert "198.51.100.99" in result.stdout
        assert "Correlated Multi-Source Event Timeline" in result.stdout
        assert "xss_attempt" in result.stdout
        assert "failed_login" in result.stdout
        assert "HIGH RISK" in result.stdout

        assert json_out.exists()
        saved_data = json.loads(json_out.read_text(encoding="utf-8"))
        assert saved_data["risk_level"] == "HIGH"


def test_log_watcher_engine_multi_target(tmp_path: Path):
    f1 = tmp_path / "n.log"
    f2 = tmp_path / "s.log"
    f1.write_text("", encoding="utf-8")
    f2.write_text("", encoding="utf-8")

    breaches = []

    def on_breach(events):
        breaches.append(events)

    tracker = SlidingWindowEventTracker(threshold=2, window_seconds=60)
    targets = [
        (f1, NginxAccessParser()),
        (f2, SSHAuthLogParser()),
    ]

    engine = LogWatcherEngine(
        targets=targets,
        tracker=tracker,
        on_breach=on_breach,
        current_year=2026,
        start_from_beginning=True,
    )

    # 1. Append Nginx SQLi line
    with open(f1, "a", encoding="utf-8") as f:
        f.write('1.2.3.4 - - [24/Aug/2026:10:00:00 +0000] "GET /?id=1\'%20OR%201=1 HTTP/1.1" 200 100 "-" "-"\n')

    engine.process_new_events()
    assert len(breaches) == 0

    # 2. Append SSH failure line -> threshold breached across both sources!
    with open(f2, "a", encoding="utf-8") as f:
        f.write("Aug 24 10:00:05 server sshd[10]: Failed password for root from 1.2.3.4 port 22 ssh2\n")

    engine.process_new_events()
    assert len(breaches) == 1
    assert len(breaches[0]) == 2
