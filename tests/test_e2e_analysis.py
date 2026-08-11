from unittest.mock import AsyncMock

import pytest
from src.llm.analyzer import IncidentAnalyzer
from src.llm.base import LocalLLMProvider
from src.parser.aggregator import aggregate_logs
from src.parser.ssh import SSHAuthLogParser
from src.rag.query import build_retrieval_query
from src.schemas.llm import NormalizedGenerationResult
from src.schemas.rag import DocumentChunk


class MockProvider(LocalLLMProvider):
    def __init__(self):
        self.model_name = "mock-model"
        self._mock_generate = AsyncMock()

    async def generate(self, prompt, system_prompt, schema):
        return await self._mock_generate(prompt, system_prompt, schema)


@pytest.mark.asyncio
async def test_end_to_end_analysis():
    # 1. Provide raw SSH logs
    raw_logs = [
        "Jan 01 12:00:00 srv sshd[123]: Failed password for root from 192.168.1.100 port 22 ssh2",
        "Jan 01 12:00:01 srv sshd[124]: Failed password for root from 192.168.1.100 port 22 ssh2",
    ]
    
    # 2. Parser Stage (P2)
    parser = SSHAuthLogParser()
    parsed_lines = []
    for line in raw_logs:
        parsed_line = parser.parse_line(line, current_year=2026)
        if parsed_line:
            parsed_lines.append(parsed_line)
    
    analysis = aggregate_logs(parsed_lines)
    
    assert analysis.total_lines == 2
    assert len(analysis.ip_aggregations) == 1
    
    # 3. RAG Retrieval Stage (P3)
    query = build_retrieval_query(analysis)
    assert "192.168.1.100" not in query  # Ensure privacy rule
    
    # Mocking DB chunks for the test
    mock_db_chunks = [
        DocumentChunk(
            chunk_id="chunk-auth-1",
            document_id="doc-1",
            source_title="SSH Hardening",
            section_or_page="Section 2",
            content="Multiple failed root logins from a single IP suggest a brute force attack.",
            word_count=12
        )
    ]
    
    retrieved_chunks = mock_db_chunks
    
    # 4. LLM Analysis Stage (P4)
    provider = MockProvider()
    provider._mock_generate.return_value = NormalizedGenerationResult(
        content='{"summary": "Brute force attempt on root", "possible_interpretations": ["Brute force"], "risk_level": "high", "risk_reasoning": "Multiple failed attempts", "recommended_actions": ["Investigate IP"], "citations": ["chunk-auth-1"]}'
    )
    
    analyzer = IncidentAnalyzer(provider=provider, max_retries=1)
    incident_report = await analyzer.analyze_incident("inc-123", analysis, retrieved_chunks)
    
    # 5. Assert End-to-End Success
    assert incident_report.status == "completed"
    assert incident_report.risk_level == "high"
    assert incident_report.citations == ["chunk-auth-1"]
    assert incident_report.observed_findings["total_lines"] == 2
    assert provider._mock_generate.call_count == 1
