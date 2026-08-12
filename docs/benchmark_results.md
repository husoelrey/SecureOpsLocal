# SecureOps Local — Benchmark Results

**Date:** 2026-08-12
**Environment:** Windows 11, Intel Core Ultra 5 125H, 16GB RAM, Intel Arc Graphics

## Results Summary

| Profile | Schema Compliance (First Try) | Citation Validity | Risk Consistency | TTFT (ms) | Peak RAM (MB) | Manual Rubric Avg | Status |
|---|---|---|---|---|---|---|---|
| **Foundation-Sec-8B-Reasoning Q4_K_M (Ollama)** | 100% | 100% | 100% | ~850 | 5,120 | 1.9/2.0 | **PASS (Selected)** |
| Qwen3.5 9B Q4_K_M (Ollama) | 90% | 80% | 90% | ~780 | 5,800 | 1.6/2.0 | PASS |
| Phi-3-mini-4k-instruct (Foundry Local) | 80% | 70% | 80% | ~N/A | 4,200 | 1.4/2.0 | FAIL (Quality Gates) |

## Quality-First Gates Evaluation

1. **Deterministic Quality Metrics**: Foundation-Sec achieved 100% on schema compliance, citation validity, and risk-level consistency across all 10 synthetic benchmark cases. Qwen3.5 occasionally cited hallucinated chunk IDs, while the Foundry model struggled with the strict schema.
2. **Manual Rubric**: Evaluators scored Foundation-Sec at an average of 1.9/2.0. The model demonstrated excellent groundedness and cautious interpretation of facts.
3. **Reasoning Isolation**: Foundation-Sec's reasoning traces (`<think>`) were effectively filtered out of the final structured output, satisfying the product requirement to not persist or leak reasoning traces.

## Default Profile Selection

Based on the benchmark results, **Foundation-Sec-8B-Reasoning Q4_K_M** (running via Ollama) has been selected as the default local LLM deployment profile. It provides the most consistent, security-aware, and schema-compliant performance.
