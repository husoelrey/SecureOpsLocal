import datetime
import logging
from unittest.mock import AsyncMock

import pytest
from src.llm.analyzer import IncidentAnalyzer
from src.llm.base import LocalLLMProvider
from src.schemas.analysis import LogAnalysis
from src.schemas.llm import NormalizedGenerationResult
from src.schemas.rag import DocumentChunk


class MockProvider(LocalLLMProvider):
    def __init__(self):
        self.model_name = "mock-model"
        self._mock_generate = AsyncMock()

    async def generate(self, prompt, system_prompt, schema):
        return await self._mock_generate(prompt, system_prompt, schema)


@pytest.fixture
def mock_analysis():
    return LogAnalysis(
        total_lines=10,
        unparsed_lines=0,
        start_time=datetime.datetime.now(),
        end_time=datetime.datetime.now(),
        ip_aggregations=[],
        limitations=[]
    )


@pytest.fixture
def mock_chunks():
    return [
        DocumentChunk(
            chunk_id="chunk-1",
            document_id="doc-1",
            source_title="NIST",
            section_or_page="1",
            content="test",
            word_count=1
        )
    ]


def test_strip_reasoning():
    analyzer = IncidentAnalyzer(provider=MockProvider())
    raw_response = "<think>\nThis is a reasoning trace.\nIt should be removed.\n</think>\n{\"summary\": \"Test\"}"
    cleaned = analyzer._strip_reasoning(raw_response)
    assert cleaned == '{"summary": "Test"}'
    assert "<think>" not in cleaned


def test_strip_markdown_code_blocks():
    analyzer = IncidentAnalyzer(provider=MockProvider())
    raw_response = "```json\n{\"summary\": \"Test\"}\n```"
    cleaned = analyzer._strip_reasoning(raw_response)
    assert cleaned == '{"summary": "Test"}'


@pytest.mark.asyncio
async def test_logs_scrubbed_on_validation_error(caplog, mock_analysis, mock_chunks):
    provider = MockProvider()
    bad_json_with_secret = '{"summary": "SUPER_SECRET_LEAK" '  # Invalid JSON
    provider._mock_generate.return_value = NormalizedGenerationResult(
        content=bad_json_with_secret
    )
    
    analyzer = IncidentAnalyzer(provider=provider, max_retries=0)
    
    with caplog.at_level(logging.WARNING):
        result = await analyzer.analyze_incident("inc-1", mock_analysis, mock_chunks)
        
    assert result.status == "invalid_model_output"
    
    # Check that the log contains the scrubbed generic error, NOT the raw secret
    log_messages = [r.message for r in caplog.records]
    assert len(log_messages) > 0
    
    # "Schema validation failed" or "ValidationError" should be in logs
    assert any("Schema validation failed" in msg or "ValidationError" in msg for msg in log_messages)
    
    # The raw string SUPER_SECRET_LEAK MUST NOT be in the logs
    assert not any("SUPER_SECRET_LEAK" in msg for msg in log_messages)


@pytest.mark.asyncio
async def test_logs_scrubbed_on_value_error(caplog, mock_analysis, mock_chunks):
    provider = MockProvider()
    # Provide valid JSON but cite an invalid chunk. The ValueError should be scrubbed of the raw model response.
    bad_citation_json = '{"summary": "Test", "possible_interpretations": ["Test"], "risk_level": "low", "risk_reasoning": "Test", "recommended_actions": ["Test"], "citations": ["SUPER_SECRET_BAD_CHUNK"]}'
    provider._mock_generate.return_value = NormalizedGenerationResult(
        content=bad_citation_json
    )
    
    analyzer = IncidentAnalyzer(provider=provider, max_retries=0)
    
    with caplog.at_level(logging.WARNING):
        result = await analyzer.analyze_incident("inc-1", mock_analysis, mock_chunks)
        
    assert result.status == "invalid_model_output"
    
    log_messages = [r.message for r in caplog.records]
    assert len(log_messages) > 0
    assert any("ValueError" in msg for msg in log_messages)
    # The raw model content (SUPER_SECRET_BAD_CHUNK) shouldn't be fully logged, although ValueError
    # only logs the exception name now.
    assert not any("SUPER_SECRET_BAD_CHUNK" in msg for msg in log_messages)
