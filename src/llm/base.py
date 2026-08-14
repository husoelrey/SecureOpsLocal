from abc import ABC, abstractmethod
from typing import Any, Dict

from src.schemas.llm import NormalizedGenerationResult


class LocalLLMProvider(ABC):
    """Abstract contract for local LLM providers."""

    model_name: str

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        system_prompt: str,
        schema: Dict[str, Any]
    ) -> NormalizedGenerationResult:
        """
        Generate a structured response based on the prompts and schema.
        
        Args:
            prompt: The user prompt containing the evidence package.
            system_prompt: The system prompt guiding the model.
            schema: The JSON schema definition the model must adhere to.
            
        Returns:
            NormalizedGenerationResult containing the raw generated content and metrics.
        """
        pass
