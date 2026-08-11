import json
from unittest.mock import MagicMock, patch

import pytest
from src.llm.ollama import OllamaProvider


@pytest.fixture
def ollama_provider():
    return OllamaProvider(base_url="http://fake-url", model_name="test-model")


@pytest.mark.asyncio
async def test_ollama_generate_success(ollama_provider):
    mock_response_data = {
        "model": "test-model",
        "message": {"role": "assistant", "content": '{"test": "value"}'},
        "prompt_eval_count": 10,
        "eval_count": 20,
        "prompt_eval_duration": 1500000000,  # 1.5s
        "eval_duration": 2000000000,
    }
    
    with patch("urllib.request.urlopen") as mock_urlopen:
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps(mock_response_data).encode("utf-8")
        mock_response.__enter__.return_value = mock_response
        mock_urlopen.return_value = mock_response
        
        schema = {"type": "object", "properties": {"test": {"type": "string"}}}
        
        result = await ollama_provider.generate(
            prompt="test prompt",
            system_prompt="test system prompt",
            schema=schema
        )
        
        assert result.content == '{"test": "value"}'
        assert result.prompt_tokens == 10
        assert result.completion_tokens == 20
        assert result.time_to_first_token_ms == 1500.0
        assert result.total_latency_ms > 0
        
        # Verify the request payload
        call_args = mock_urlopen.call_args[0][0]
        assert call_args.full_url == "http://fake-url/api/chat"
        payload = json.loads(call_args.data.decode("utf-8"))
        assert payload["model"] == "test-model"
        assert payload["format"] == schema
        assert payload["messages"] == [
            {"role": "system", "content": "test system prompt"},
            {"role": "user", "content": "test prompt"}
        ]
