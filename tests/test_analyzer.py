# ruff: noqa: E501
import datetime
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
            source_title="NIST SP 800-61",
            section_or_page="Section 3",
            content="Some security guidance.",
            word_count=4
        )
    ]


@pytest.mark.asyncio
async def test_analyzer_success(mock_analysis, mock_chunks):
    provider = MockProvider()
    provider._mock_generate.return_value = NormalizedGenerationResult(
        content='{"summary": "Test", "possible_interpretations": ["Test"], "risk_level": "low", "risk_reasoning": "Test", "recommended_actions": ["Test"], "citations": ["chunk-1"]}',
        prompt_tokens=10,
        completion_tokens=20,
        total_latency_ms=100.0,
        time_to_first_token_ms=50.0
    )
    
    analyzer = IncidentAnalyzer(provider=provider)
    result = await analyzer.analyze_incident("inc-1", mock_analysis, mock_chunks)
    
    assert result.status == "completed"
    assert result.risk_level == "low"
    assert result.citations == ["chunk-1"]
    assert provider._mock_generate.call_count == 1


@pytest.mark.asyncio
async def test_analyzer_repair_success(mock_analysis, mock_chunks):
    provider = MockProvider()
    # First response fails schema validation (missing risk_level)
    bad_result = NormalizedGenerationResult(
        content='{"summary": "Test", "possible_interpretations": ["Test"], "risk_reasoning": "Test", "recommended_actions": ["Test"], "citations": ["chunk-1"]}',
    )
    # Second response succeeds
    good_result = NormalizedGenerationResult(
        content='{"summary": "Test", "possible_interpretations": ["Test"], "risk_level": "medium", "risk_reasoning": "Test", "recommended_actions": ["Test"], "citations": ["chunk-1"]}',
    )
    
    provider._mock_generate.side_effect = [bad_result, good_result]
    
    analyzer = IncidentAnalyzer(provider=provider)
    result = await analyzer.analyze_incident("inc-1", mock_analysis, mock_chunks)
    
    assert result.status == "completed"
    assert result.risk_level == "medium"
    assert provider._mock_generate.call_count == 2
    
    # Ensure second call contains error feedback
    second_call_prompt = provider._mock_generate.call_args_list[1][0][0]  # first positional arg is prompt
    assert "ERROR IN PREVIOUS ATTEMPT" in second_call_prompt


@pytest.mark.asyncio
async def test_analyzer_invalid_citations(mock_analysis, mock_chunks):
    provider = MockProvider()
    # Cite an invalid chunk
    provider._mock_generate.return_value = NormalizedGenerationResult(
        content='{"summary": "Test", "possible_interpretations": ["Test"], "risk_level": "low", "risk_reasoning": "Test", "recommended_actions": ["Test"], "citations": ["fake-chunk"]}',
    )
    
    analyzer = IncidentAnalyzer(provider=provider, max_retries=0)  # no retries for simplicity
    result = await analyzer.analyze_incident("inc-1", mock_analysis, mock_chunks)
    
    assert result.status == "invalid_model_output"
    assert "fake-chunk" in result.risk_reasoning


@pytest.mark.asyncio
async def test_analyzer_second_failure_rejected(mock_analysis, mock_chunks):
    provider = MockProvider()
    # Fails both times
    bad_result = NormalizedGenerationResult(
        content='{"bad": "schema"}',
    )
    provider._mock_generate.side_effect = [bad_result, bad_result]
    
    analyzer = IncidentAnalyzer(provider=provider, max_retries=1)
    result = await analyzer.analyze_incident("inc-1", mock_analysis, mock_chunks)
    
    assert result.status == "invalid_model_output"
    assert provider._mock_generate.call_count == 2
