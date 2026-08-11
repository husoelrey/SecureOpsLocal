import asyncio
import json
import time
import urllib.error
import urllib.request
from typing import Any, Dict

from src.llm.base import LocalLLMProvider
from src.schemas.llm import NormalizedGenerationResult


class FoundryLocalProvider(LocalLLMProvider):
    """LLM provider implementation for Microsoft Foundry Local."""

    def __init__(self, base_url: str, model_name: str):
        self.base_url = base_url.rstrip("/")
        self.model_name = model_name

    def _sync_generate(self, url: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Synchronous HTTP call to Foundry Local."""
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"}
        )
        try:
            with urllib.request.urlopen(req, timeout=300) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.URLError as e:
            raise RuntimeError(f"Foundry Local API request failed: {e}")

    async def generate(
        self,
        prompt: str,
        system_prompt: str,
        schema: Dict[str, Any]
    ) -> NormalizedGenerationResult:
        url = f"{self.base_url}/v1/chat/completions"
        payload = {
            "model": self.model_name,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.0,
            "seed": 42,
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": "model_assessment",
                    "schema": schema,
                    "strict": True
                }
            }
        }
        
        start_time = time.monotonic()
        
        response_data = await asyncio.to_thread(self._sync_generate, url, payload)
        
        total_latency_ms = (time.monotonic() - start_time) * 1000
        
        # Foundry/OpenAI compatible response structure
        choices = response_data.get("choices", [])
        content = ""
        if choices:
            content = choices[0].get("message", {}).get("content", "")
            
        usage = response_data.get("usage", {})
        prompt_tokens = usage.get("prompt_tokens")
        completion_tokens = usage.get("completion_tokens")
        
        return NormalizedGenerationResult(
            content=content,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_latency_ms=total_latency_ms,
            # TTFT not easily extracted from non-streaming OpenAI API
            time_to_first_token_ms=None
        )
