from fastapi import APIRouter
from typing import List, Dict

router = APIRouter()

@router.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}

@router.get("/models")
def get_models() -> Dict[str, List[Dict[str, str]]]:
    """Returns the available local LLM deployment profiles."""
    return {
        "models": [
            {
                "id": "foundation-sec-8b-reasoning:q4_k_m",
                "provider": "ollama",
                "role": "Initial primary candidate and domain-specialized cybersecurity profile"
            },
            {
                "id": "qwen:0.5b",
                "provider": "ollama",
                "role": "Fast-testing baseline model for structural benchmark"
            },
            {
                "id": "Phi-3-mini-4k-instruct-onnx",
                "provider": "foundry",
                "role": "Microsoft Foundry Local compatible baseline model"
            }
        ]
    }
