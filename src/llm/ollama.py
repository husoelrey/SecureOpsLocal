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
            start_time = time.monotonic()
            ttft = None
            content = ""
            final_chunk = {}
            
            with urllib.request.urlopen(req, timeout=300) as response:
                for line in response:
                    if line:
                        chunk = json.loads(line.decode("utf-8"))
                        msg_chunk = chunk.get("message", {}).get("content", "")
                        
                        if msg_chunk and ttft is None:
                            ttft = (time.monotonic() - start_time) * 1000
                            
                        content += msg_chunk
                        
                        if chunk.get("done"):
                            final_chunk = chunk
                            break
                            
            return {
                "content": content,
                "ttft_ms": ttft,
                "metrics": final_chunk
            }
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
            "stream": True,
            "format": schema,
            "options": {
                "temperature": 0.0,
                "seed": 42
            }
        }
        
        start_time = time.monotonic()
        
        result = await asyncio.to_thread(self._sync_generate, url, payload)
        
        total_latency_ms = (time.monotonic() - start_time) * 1000
        metrics = result["metrics"]
        
        prompt_eval_ns = metrics.get("prompt_eval_duration")
        load_duration_ns = metrics.get("load_duration")
        
        # If streaming didn't give TTFT (e.g. empty content?), fallback to prompt_eval
        ttft = result["ttft_ms"]
        if ttft is None and prompt_eval_ns is not None:
            ttft = prompt_eval_ns / 1_000_000
            
        # We can pass extra metrics if needed, but for now we just map to NormalizedGenerationResult
        
        return NormalizedGenerationResult(
            content=result["content"],
            prompt_tokens=metrics.get("prompt_eval_count"),
            completion_tokens=metrics.get("eval_count"),
            total_latency_ms=total_latency_ms,
            time_to_first_token_ms=ttft
        )
