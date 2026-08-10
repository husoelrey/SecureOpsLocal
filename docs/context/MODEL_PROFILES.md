# SecureOps Local — Model Profiles

This document records the provenance, licensing, and acquisition state of the models used by the SecureOps Local project.

## Foundation-Sec-8B-Reasoning Q4_K_M GGUF

- **Role**: Initial primary candidate and domain-specialized cybersecurity profile
- **Source URLs**: 
  - GGUF Repository: https://huggingface.co/fdtn-ai/Foundation-Sec-8B-Reasoning-Q4_K_M-GGUF
  - Base Reasoning Model: https://huggingface.co/fdtn-ai/Foundation-Sec-8B-Reasoning
- **Immutable Revision**: 4a04f7b19513ff9f672169b8fe4288000ab87b07
- **Filename**: `foundation-sec-8b-reasoning-q4_k_m.gguf`
- **Expected Size**: 4920851232 bytes
- **Expected Digest (SHA-256)**: 7a61e41b1ca1b339d41caf3001ea7832469d866e7c52a23980a1e95cbf5cd58b
- **Quantization**: Q4_K_M
- **Lineage**:
  - `Meta Llama-3.1-8B` (Backbone)
  - `fdtn-ai/Foundation-Sec-8B` (Continued-pretrained on cybersecurity text)
  - `fdtn-ai/Foundation-Sec-8B-Reasoning` (Instruction-tuned with reasoning capabilities)
  - `fdtn-ai/Foundation-Sec-8B-Reasoning-Q4_K_M-GGUF` (Quantized via llama.cpp)
- **License Findings**:
  - The underlying base backbone model is governed by the Meta Llama 3.1 Community License.
  - The `fdtn-ai` repositories (both base and GGUF) declare the license for Cisco's project changes as Apache 2.0.
  - There is a distinction between the Apache 2.0 license applied by Cisco and the underlying Llama 3.1 Community License for the model weights.
  - **Redistribution Implications**: The project may document the acquisition and installation process but must not redistribute the model weights due to licensing complexities.
- **Current Acquisition State**: Acquired and imported into Ollama
  - Timestamp: 2026-08-10T17:06:15Z
  - Final Local Path: `C:\Users\husoelrey\Documents\docs\AI_models\foundation-sec\foundation-sec-8b-reasoning-q4_k_m.gguf`
  - Actual Byte Size: 4920851232 bytes
  - Actual SHA-256: 7A61E41B1CA1B339D41CAF3001EA7832469D866E7C52A23980A1E95CBF5CD58B
  - Verification Result: Passed
  - Source Revision: 4a04f7b19513ff9f672169b8fe4288000ab87b07
  - Download Method: HTTPS via `curl.exe`
  - Resumed: Yes
  - Ollama Alias: `foundation-sec-8b-reasoning:q4_k_m`
