import datetime
import json
from pathlib import Path
from unittest.mock import patch

import pytest
from src.cli.main import app
from src.database import SessionLocal
from src.integrations.intel_feed import (
    ingest_threat_intel_file,
    init_threat_intel_db,
    lookup_ip_intel,
    lookup_ips_intel,
    parse_csv_feed,
    parse_misp_event,
    parse_stix_bundle,
)
from src.llm.analyzer import IncidentAnalyzer
from src.llm.base import LocalLLMProvider
from src.models.threat_intel import ThreatIntel
from src.parser.aggregator import aggregate_logs
from src.schemas.llm import NormalizedGenerationResult
from src.schemas.parsed_log_line import ParsedLogLineCreate
from src.schemas.rag import DocumentChunk
from typer.testing import CliRunner

runner = CliRunner()


@pytest.fixture(autouse=True)
def setup_test_db():
    """Ensure clean threat_intel database table before each test."""
    init_threat_intel_db()
    db = SessionLocal()
    try:
        db.query(ThreatIntel).delete()
        db.commit()
    finally:
        db.close()


def test_parse_csv_feed():
    csv_content = (
        "ip_address,threat_type,severity,description\n"
        "198.51.100.1,KNOWN_APT,high,APT29 C2 node\n"
        "203.0.113.5,TOR_NODE,medium,Tor Exit Relay\n"
    )
    entries = parse_csv_feed(csv_content)
    assert len(entries) == 2
    assert entries[0].ip_address == "198.51.100.1"
    assert entries[0].threat_type == "KNOWN_APT"
    assert entries[0].severity == "high"
    assert entries[0].description == "APT29 C2 node"

    assert entries[1].ip_address == "203.0.113.5"
    assert entries[1].threat_type == "TOR_NODE"


def test_parse_stix_bundle():
    stix_data = {
        "type": "bundle",
        "id": "bundle--12345",
        "objects": [
            {
                "type": "indicator",
                "id": "indicator--abcde",
                "pattern": "[ipv4-addr:value = '198.51.100.88']",
                "name": "Cobalt Strike C2",
                "indicator_types": ["malicious-activity"],
                "confidence": 90,
                "description": "Active C2 server",
            }
        ],
    }
    entries = parse_stix_bundle(stix_data)
    assert len(entries) == 1
    assert entries[0].ip_address == "198.51.100.88"
    assert entries[0].threat_type == "MALICIOUS_ACTIVITY"
    assert entries[0].severity == "high"
    assert entries[0].description == "Active C2 server"


def test_parse_misp_event():
    misp_data = {
        "Event": {
            "Attribute": [
                {
                    "type": "ip-src",
                    "value": "198.51.100.99",
                    "category": "Network activity",
                    "comment": "APT41 scanning host",
                    "Tag": [{"name": "threat-type:apt"}, {"name": "tlp:white"}],
                }
            ]
        }
    }
    entries = parse_misp_event(misp_data)
    assert len(entries) == 1
    assert entries[0].ip_address == "198.51.100.99"
    assert "APT" in entries[0].threat_type
    assert entries[0].severity == "high"


def test_ingest_and_lookup_threat_intel(tmp_path: Path):
    feed_file = tmp_path / "threat_feed.csv"
    feed_file.write_text(
        "ip_address,threat_type,severity,description\n"
        "192.0.2.10,KNOWN_BOTNET,high,Mirai botnet node\n"
        "192.0.2.20,TOR_NODE,medium,Tor exit relay\n",
        encoding="utf-8",
    )

    count = ingest_threat_intel_file(feed_file)
    assert count == 2

    # Query matching IP
    match = lookup_ip_intel("192.0.2.10")
    assert match is not None
    assert match.ip_address == "192.0.2.10"
    assert match.threat_type == "KNOWN_BOTNET"
    assert match.severity == "high"

    # Query non-matching IP
    assert lookup_ip_intel("1.1.1.1") is None

    # Bulk lookup
    bulk = lookup_ips_intel(["192.0.2.10", "192.0.2.20", "8.8.8.8"])
    assert len(bulk) == 2
    assert "192.0.2.10" in bulk
    assert "192.0.2.20" in bulk
    assert "8.8.8.8" not in bulk


def test_aggregator_threat_intel_flag_injection(tmp_path: Path):
    feed_file = tmp_path / "apt_feed.json"
    feed_file.write_text(
        json.dumps([
            {
                "ip_address": "198.51.100.77",
                "threat_type": "KNOWN_APT",
                "severity": "high",
                "description": "APT infrastructure",
            }
        ]),
        encoding="utf-8",
    )
    ingest_threat_intel_file(feed_file)

    now = datetime.datetime.now(datetime.timezone.utc)
    ev_malicious = ParsedLogLineCreate(
        timestamp=now,
        source_ip="198.51.100.77",
        user="root",
        event_type="failed_login",
        raw_content="Failed password for root",
        is_parsed=True,
    )
    ev_benign = ParsedLogLineCreate(
        timestamp=now,
        source_ip="10.0.0.1",
        user="admin",
        event_type="successful_login",
        raw_content="Accepted password",
        is_parsed=True,
    )

    analysis = aggregate_logs([ev_malicious, ev_benign], enable_threat_intel=True)
    assert len(analysis.ip_aggregations) == 2

    agg_map = {agg.ip: agg for agg in analysis.ip_aggregations}
    assert "KNOWN_APT" in agg_map["198.51.100.77"].intel_flags
    assert len(agg_map["10.0.0.1"].intel_flags) == 0


def test_analyzer_user_prompt_threat_intel():
    now = datetime.datetime.now(datetime.timezone.utc)
    ev = ParsedLogLineCreate(
        timestamp=now,
        source_ip="198.51.100.99",
        user="admin",
        event_type="failed_login",
        raw_content="Failed password",
        is_parsed=True,
    )
    analysis = aggregate_logs([ev], enable_threat_intel=False)
    # Manually attach flag to test prompt rendering
    analysis.ip_aggregations[0].intel_flags = ["KNOWN_APT"]

    chunks = [
        DocumentChunk(
            document_id="doc_1",
            chunk_id="chunk_001",
            source_title="NIST SP 800-61",
            section_or_page="Section 3",
            content="Threat intelligence context.",
            word_count=5,
        )
    ]

    class DummyLLM(LocalLLMProvider):
        model_name = "dummy"

        async def generate(self, prompt, system_prompt, schema):
            return NormalizedGenerationResult(content="{}", prompt_tokens=10, completion_tokens=10)

    analyzer = IncidentAnalyzer(provider=DummyLLM())
    prompt = analyzer._build_user_prompt(analysis, chunks)

    assert "## Offline Threat Intelligence Matches" in prompt
    assert "198.51.100.99" in prompt
    assert "KNOWN_APT" in prompt


def test_cli_intel_commands(tmp_path: Path):
    feed_file = tmp_path / "feed.csv"
    feed_file.write_text(
        "ip_address,threat_type,severity,description\n"
        "203.0.113.99,TOR_NODE,medium,Tor Exit Relay\n",
        encoding="utf-8",
    )

    # 1. Add command
    res_add = runner.invoke(app, ["intel", "add", str(feed_file)])
    assert res_add.exit_code == 0
    assert "Successfully ingested 1 threat indicator" in res_add.stdout

    # 2. List command
    res_list = runner.invoke(app, ["intel", "list"])
    assert res_list.exit_code == 0
    assert "203.0.113.99" in res_list.stdout
    assert "TOR_NODE" in res_list.stdout

    # 3. Lookup command
    res_lookup = runner.invoke(app, ["intel", "lookup", "203.0.113.99"])
    assert res_lookup.exit_code == 0
    assert "Threat Match Found" in res_lookup.stdout
    assert "TOR_NODE" in res_lookup.stdout


def test_strictly_local_no_external_network():
    """Verify that threat intel lookup performs zero network socket connections."""
    with patch("socket.socket.connect") as mock_connect:
        lookup_ip_intel("198.51.100.1")
        mock_connect.assert_not_called()
