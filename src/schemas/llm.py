from typing import Optional

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

