import asyncio
import json
import time
import urllib.error
import urllib.request
from typing import Any, Dict, cast

from src.llm.base import LocalLLMProvider
from src.schemas.llm import NormalizedGenerationResult


class OllamaProvider(LocalLLMProvider):
    """LLM provider implementation for Ollama."""

    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        model_name: str = "qwen3.5:9b"
    ):
        self.base_url = base_url.rstrip("/")
        self.model_name = model_name

    def _sync_generate(self, url: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Synchronous HTTP call to Ollama."""
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"}
        )
        try:
            with urllib.request.urlopen(req, timeout=300) as response:
                return cast(Dict[str, Any], json.loads(response.read().decode("utf-8")))
        except urllib.error.URLError as e:
            raise RuntimeError(f"Ollama API request failed: {e}")

    async def generate(
        self,
        prompt: str,
        system_prompt: str,
        schema: Dict[str, Any]
    ) -> NormalizedGenerationResult:
        url = f"{self.base_url}/api/chat"
        payload = {
            "model": self.model_name,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            "stream": False,
            "format": schema,
            "options": {
                "temperature": 0.0,
                "seed": 42
            }
        }
        
        start_time = time.monotonic()
        
        response_data = await asyncio.to_thread(self._sync_generate, url, payload)
        
        total_latency_ms = (time.monotonic() - start_time) * 1000
        
        # Ollama specific metrics (in nanoseconds, so divide by 1_000_000)
        # load_duration: time spent loading the model
        # prompt_eval_duration: time spent evaluating the prompt
        # eval_duration: time spent generating the response
        
        prompt_eval_ns = response_data.get("prompt_eval_duration")
        time_to_first_token_ms = (
            prompt_eval_ns / 1_000_000 if prompt_eval_ns is not None else None
        )
        
        return NormalizedGenerationResult(
            content=response_data.get("message", {}).get("content", ""),
            prompt_tokens=response_data.get("prompt_eval_count"),
            completion_tokens=response_data.get("eval_count"),
            total_latency_ms=total_latency_ms,
            time_to_first_token_ms=time_to_first_token_ms
        )
