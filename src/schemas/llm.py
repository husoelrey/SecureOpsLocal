from typing import List, Literal, Optional

from pydantic import BaseModel, Field


class NormalizedGenerationResult(BaseModel):
    content: str = Field(..., description="The generated text content, typically JSON.")
    prompt_tokens: Optional[int] = Field(
        None, description="Number of tokens in the prompt."
    )
    completion_tokens: Optional[int] = Field(
        None, description="Number of tokens generated."
    )
    total_latency_ms: Optional[float] = Field(
        None, description="Total generation time in milliseconds."
    )
    time_to_first_token_ms: Optional[float] = Field(
        None, description="Time to first token in milliseconds."
    )


class ModelAssessment(BaseModel):
    summary: str = Field(
        ..., description="A cautious, high-level summary of the incident based only on the provided facts."
    )
    possible_interpretations: List[str] = Field(
        ..., description="Evidence-supported possibilities and explicit limitations."
    )
    risk_level: Literal["low", "medium", "high"] = Field(
        ..., description="The assessed risk level."
    )
    risk_reasoning: str = Field(
        ..., description="Explanation of the risk level using observed facts and retrieved guidance."
    )
    recommended_actions: List[str] = Field(
        ..., description="Recommendations limited to investigation, evidence preservation, correlation, escalation, defensive validation, and hardening. DO NOT recommend automated blocking, exploiting, or active scanning."
    )
    citations: List[str] = Field(
        ..., description="List of chunk IDs from the provided retrieved context that support the assessment."
    )

