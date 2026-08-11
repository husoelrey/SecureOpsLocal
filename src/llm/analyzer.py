# ruff: noqa: E501
import logging
from typing import List

from src.llm.base import LocalLLMProvider
from src.llm.prompts import SYSTEM_PROMPT_V1
from src.schemas.analysis import LogAnalysis
from src.schemas.incident_report import IncidentReportCreate
from src.schemas.llm import ModelAssessment
from src.schemas.rag import DocumentChunk

logger = logging.getLogger(__name__)

class IncidentAnalyzer:
    def __init__(self, provider: LocalLLMProvider, max_retries: int = 1):
        self.provider = provider
        self.max_retries = max_retries

    def _build_user_prompt(self, analysis: LogAnalysis, chunks: List[DocumentChunk]) -> str:
        prompt = "## Parser Findings (Deterministic Facts)\n"
        prompt += analysis.model_dump_json(indent=2)
        prompt += "\n\n## Retrieved Context (Security Guidance)\n"
        for chunk in chunks:
            prompt += f"--- Chunk ID: {chunk.chunk_id} ---\n"
            prompt += f"Source: {chunk.source_title}\n"
            prompt += f"Section: {chunk.section_or_page}\n"
            prompt += f"Content:\n{chunk.content}\n\n"
        return prompt

    async def analyze_incident(self, incident_id: str, analysis: LogAnalysis, chunks: List[DocumentChunk]) -> IncidentReportCreate:
        user_prompt = self._build_user_prompt(analysis, chunks)
        schema = ModelAssessment.model_json_schema()
        valid_chunk_ids = {chunk.chunk_id for chunk in chunks}
        
        attempt = 0
        last_error = ""
        current_prompt = user_prompt
        
        while attempt <= self.max_retries:
            try:
                result = await self.provider.generate(
                    prompt=current_prompt,
                    system_prompt=SYSTEM_PROMPT_V1,
                    schema=schema
                )
                
                assessment = ModelAssessment.model_validate_json(result.content)
                
                invalid_citations = [c for c in assessment.citations if c not in valid_chunk_ids]
                if invalid_citations:
                    raise ValueError(f"Model cited invalid chunk IDs: {invalid_citations}")
                
                return IncidentReportCreate(
                    status="completed",
                    summary=assessment.summary,
                    observed_findings=analysis.model_dump(),
                    possible_interpretations=assessment.possible_interpretations,
                    risk_level=assessment.risk_level,
                    risk_reasoning=assessment.risk_reasoning,
                    recommended_actions=assessment.recommended_actions,
                    citations=assessment.citations,
                    limitations=analysis.limitations,
                    parser_statistics={"total_lines": analysis.total_lines, "unparsed_lines": analysis.unparsed_lines},
                    model_information={"provider": self.provider.__class__.__name__, "model": self.provider.model_name},
                    performance_metrics={
                        "prompt_tokens": result.prompt_tokens,
                        "completion_tokens": result.completion_tokens,
                        "total_latency_ms": result.total_latency_ms,
                        "time_to_first_token_ms": result.time_to_first_token_ms
                    }
                )
                
            except Exception as e:
                attempt += 1
                last_error = str(e)
                logger.warning(f"Model generation failed on attempt {attempt}: {last_error}")
                if attempt <= self.max_retries:
                    current_prompt = user_prompt + f"\n\nERROR IN PREVIOUS ATTEMPT:\n{last_error}\nPlease correct this error and ensure strict schema compliance."
        
        return IncidentReportCreate(
            status="invalid_model_output",
            summary=f"Model output validation failed after {self.max_retries + 1} attempts.",
            observed_findings=analysis.model_dump(),
            possible_interpretations=[],
            risk_level="unknown",
            risk_reasoning=f"Validation error: {last_error}",
            recommended_actions=[],
            citations=[],
            limitations=analysis.limitations + ["Failed to produce valid model assessment."],
            parser_statistics={"total_lines": analysis.total_lines, "unparsed_lines": analysis.unparsed_lines},
            model_information={"provider": self.provider.__class__.__name__, "model": self.provider.model_name},
            performance_metrics={}
        )
