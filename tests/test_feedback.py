import datetime

import pytest
from src.cli.main import app
from src.database import SessionLocal
from src.feedback.service import (
    build_feedback_context_note,
    get_all_feedback,
    get_feedback_for_ips_or_users,
    init_feedback_db,
    record_feedback,
)
from src.llm.analyzer import IncidentAnalyzer
from src.llm.base import LocalLLMProvider
from src.models.feedback import Feedback
from src.parser.aggregator import aggregate_logs
from src.schemas.feedback import FeedbackCreate
from src.schemas.llm import NormalizedGenerationResult
from src.schemas.parsed_log_line import ParsedLogLineCreate
from src.schemas.rag import DocumentChunk
from typer.testing import CliRunner

runner = CliRunner()


@pytest.fixture(autouse=True)
def setup_test_db():
    """Ensure clean feedback database table before each test."""
    init_feedback_db()
    db = SessionLocal()
    try:
        db.query(Feedback).delete()
        db.commit()
    finally:
        db.close()


def test_record_feedback_and_get_all():
    fb_data = FeedbackCreate(
        incident_id="inc_abc12345",
        is_false_positive=True,
        admin_notes="Scheduled Nessus security scan",
        source_ip="198.51.100.25",
        target_user="sec_scanner",
    )
    record = record_feedback(fb_data)
    assert record.id is not None
    assert record.incident_id == "inc_abc12345"
    assert record.is_false_positive is True
    assert record.admin_notes == "Scheduled Nessus security scan"

    all_fb = get_all_feedback()
    assert len(all_fb) == 1
    assert all_fb[0].incident_id == "inc_abc12345"


def test_get_feedback_by_ip_and_user():
    record_feedback(
        FeedbackCreate(
            incident_id="inc_1",
            is_false_positive=True,
            admin_notes="Internal monitoring node",
            source_ip="10.0.5.99",
            target_user=None,
        )
    )
    record_feedback(
        FeedbackCreate(
            incident_id="inc_2",
            is_false_positive=True,
            admin_notes="Backup service automated account",
            source_ip=None,
            target_user="backup_admin",
        )
    )

    # Match by IP
    match_ip = get_feedback_for_ips_or_users(ips=["10.0.5.99"])
    assert len(match_ip) == 1
    assert match_ip[0].admin_notes == "Internal monitoring node"

    # Match by User
    match_user = get_feedback_for_ips_or_users(users=["backup_admin"])
    assert len(match_user) == 1
    assert match_user[0].admin_notes == "Backup service automated account"

    # Match neither
    match_none = get_feedback_for_ips_or_users(ips=["1.2.3.4"], users=["random_user"])
    assert len(match_none) == 0


def test_build_feedback_context_note():
    feedbacks = [
        Feedback(
            id=1,
            incident_id="inc_101",
            is_false_positive=True,
            admin_notes="Authorized vulnerability scanner",
            source_ip="198.51.100.25",
            target_user=None,
            created_at=datetime.datetime.now(datetime.timezone.utc),
        ),
        Feedback(
            id=2,
            incident_id="inc_102",
            is_false_positive=True,
            admin_notes="Scheduled QA test account",
            source_ip=None,
            target_user="qa_tester",
            created_at=datetime.datetime.now(datetime.timezone.utc),
        ),
    ]

    note = build_feedback_context_note(feedbacks)
    assert "Note: The administrator previously marked similar activity from IP 198.51.100.25 as a False Positive because: Authorized vulnerability scanner." in note
    assert "Note: The administrator previously marked similar activity targeting user qa_tester as a False Positive because: Scheduled QA test account." in note


@pytest.mark.asyncio
async def test_analyzer_injects_feedback_into_system_prompt():
    # Seed feedback in DB
    record_feedback(
        FeedbackCreate(
            incident_id="inc_prev",
            is_false_positive=True,
            admin_notes="Authorized pen-test source",
            source_ip="198.51.100.88",
            target_user=None,
        )
    )

    now = datetime.datetime.now(datetime.timezone.utc)
    ev = ParsedLogLineCreate(
        timestamp=now,
        source_ip="198.51.100.88",
        user="root",
        event_type="failed_login",
        raw_content="Failed password for root",
        is_parsed=True,
    )
    analysis = aggregate_logs([ev])

    chunks = [
        DocumentChunk(
            document_id="doc1",
            chunk_id="chk1",
            source_title="NIST SP 800-61",
            section_or_page="Section 3",
            content="Incident handling guide.",
            word_count=5,
        )
    ]

    captured_system_prompt = ""

    class MockProvider(LocalLLMProvider):
        model_name = "mock"

        async def generate(self, prompt, system_prompt, schema):
            nonlocal captured_system_prompt
            captured_system_prompt = system_prompt
            dummy_resp = (
                '{"summary": "Test", "risk_level": "low", "risk_reasoning": "Admin marked FP", '
                '"possible_interpretations": ["Pen-test activity"], "recommended_actions": ["Verify scan ticket"], '
                '"citations": ["chk1"]}'
            )
            return NormalizedGenerationResult(content=dummy_resp, prompt_tokens=10, completion_tokens=10)

    analyzer = IncidentAnalyzer(provider=MockProvider())
    report = await analyzer.analyze_incident("inc_curr", analysis, chunks)

    assert report.status == "completed"
    assert "Administrator Historical Feedback:" in captured_system_prompt
    assert "198.51.100.88" in captured_system_prompt
    assert "Authorized pen-test source" in captured_system_prompt


def test_cli_feedback_command():
    # Record feedback via CLI
    res = runner.invoke(
        app,
        [
            "feedback",
            "inc_987654",
            "--false-positive",
            "--reason",
            "Authorized vulnerability scanner",
            "--ip",
            "198.51.100.55",
            "--user",
            "scanner_bot",
        ],
    )
    assert res.exit_code == 0
    assert "Administrator feedback recorded for incident:" in res.stdout
    assert "inc_987654" in res.stdout
    assert "False Positive" in res.stdout

    # List feedback via CLI
    res_list = runner.invoke(app, ["feedback", "list"])
    assert res_list.exit_code == 0
    assert "inc_987654" in res_list.stdout
    assert "scanner" in res_list.stdout
    assert "Authorized" in res_list.stdout
