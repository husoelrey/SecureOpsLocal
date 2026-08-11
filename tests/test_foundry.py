import json
from unittest.mock import MagicMock, patch

import pytest
from src.llm.foundry import FoundryLocalProvider


@pytest.fixture
def foundry_provider():
    return FoundryLocalProvider(base_url="http://fake-url", model_name="test-model")


@pytest.mark.asyncio
async def test_foundry_generate_success(foundry_provider):
    mock_response_data = {
        "id": "chatcmpl-123",
        "object": "chat.completion",
        "created": 1677652288,
        "model": "test-model",
        "system_fingerprint": "fp_44709d6fcb",
        "choices": [{
            "index": 0,
            "message": {
                "role": "assistant",
                "content": '{"test": "value"}',
            },
            "finish_reason": "stop"
        }],
        "usage": {
            "prompt_tokens": 9,
            "completion_tokens": 12,
            "total_tokens": 21
        }
    }
    
    with patch("urllib.request.urlopen") as mock_urlopen:
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps(mock_response_data).encode("utf-8")
        mock_response.__enter__.return_value = mock_response
        mock_urlopen.return_value = mock_response
        
        schema = {"type": "object", "properties": {"test": {"type": "string"}}}
        
        result = await foundry_provider.generate(
            prompt="test prompt",
            system_prompt="test system prompt",
            schema=schema
        )
        
        assert result.content == '{"test": "value"}'
        assert result.prompt_tokens == 9
        assert result.completion_tokens == 12
        assert result.time_to_first_token_ms is None
        assert result.total_latency_ms > 0
        
        # Verify the request payload
        call_args = mock_urlopen.call_args[0][0]
        assert call_args.full_url == "http://fake-url/v1/chat/completions"
        payload = json.loads(call_args.data.decode("utf-8"))
        assert payload["model"] == "test-model"
        assert payload["response_format"]["type"] == "json_schema"
        assert payload["response_format"]["json_schema"]["schema"] == schema
        assert payload["messages"] == [
            {"role": "system", "content": "test system prompt"},
            {"role": "user", "content": "test prompt"}
        ]
