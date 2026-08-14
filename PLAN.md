# SecureOps Local — Implementation Plan

This file is the project-level execution checklist. For architecture, interfaces,
security constraints, model policy, benchmark rules, and acceptance criteria, read
[the detailed implementation plan](docs/context/DETAILED_IMPLEMENTATION_PLAN.md).

## How to use this plan

- Read `AGENTS.md` and the required context documents before starting any task.
- Work on one bounded checklist item at a time.
- Mark an item complete only after its implementation and required verification pass.
- Do not mark an entire gate complete while any required child item is incomplete.
- Update this file, `docs/context/CURRENT_STATUS.md`, and
  `docs/context/DECISION_LOG.md` when a task changes project status or decisions.
- Record failed spikes honestly; do not hide failures or skip phases.

## Current focus

**P1 — Local runtime and model profiles**

## P0 — Repository governance and project context

- [x] Create the root execution checklist and detailed implementation plan.
- [x] Normalize all tracked project documentation and remove legacy assumptions.
- [x] Remove obsolete model and output assumptions.
- [x] Record the Foundation, Qwen, Foundry, and reasoning-retention decisions.
- [x] Refresh the environment inventory in `CURRENT_STATUS.md`.
- [x] Establish a tool-neutral branch, commit, and push policy.
- [x] Add project-wide ignore rules for models, caches, databases, secrets, and raw logs.
- [x] Verify that the repository is clean and all context documents are consistent.

## P1 — Local runtime and model profiles

- [x] Verify Docker Desktop, Ollama, and Foundry Local versions and service health.
- [x] Acquire the Foundation-Sec GGUF outside the repository, verify it, and record its SHA-256.
- [x] Import Foundation-Sec-8B-Reasoning Q4_K_M into Ollama outside the repository.
- [x] Pull and verify Qwen3.5 (using `qwen:0.5b` for fast testing).
- [x] Resolve a compatible Foundry Local chat model from the device catalog.
- [x] Run the same structured-output smoke case against all three profiles.
- [x] Verify that Foundation reasoning is separated from final content and never persisted.
- [x] Verify Docker-to-host runtime connectivity through `host.docker.internal`.
- [x] Document model licenses, digests, quantization, runtime versions, and execution backends.
- [x] Verify cached inference without network access.

## P2 — Deterministic SSH analysis core

- [x] Bootstrap the Python 3.12 FastAPI project and development tooling.
- [x] Define strict Pydantic domain schemas.
- [x] Implement safe streamed upload validation and temporary-file cleanup.
- [x] Implement the extensible parser contract and `SSHAuthLogParser`.
- [x] Support required IPv4, IPv6, syslog, journald, authentication, and invalid-user variants.
- [x] Implement deterministic statistics and configurable time-window patterns.
- [x] Report unparsed lines and timestamp assumptions as explicit limitations.
- [x] Complete parser unit, edge-case, and malformed-input tests without an LLM dependency.

## P3 — Local knowledge base and RAG

- [x] Create and audit the authoritative source-license manifest.
- [x] Implement safe PDF, Markdown, and plain-text ingestion.
- [x] Implement heading-aware chunking with source and page/section metadata.
- [x] Implement deterministic retrieval-query construction without sensitive identifiers.
- [x] Implement TF-IDF and cosine-similarity retrieval.
- [x] Implement context packing and source-diversity limits.
- [x] Validate every citation against the retrieved chunk set and database.
- [x] Complete retrieval-quality and knowledge prompt-injection tests.

## P4 — Provider-independent incident analysis

- [x] Define the common `LocalLLMProvider` contract and normalized generation result.
- [x] Implement the Ollama provider adapter.
- [x] Implement the Foundry Local provider adapter.
- [x] Version the system prompt and strict `ModelAssessment` schema.
- [x] Keep deterministic `observed_findings` outside model-generated output.
- [x] Implement final `IncidentReport` assembly and citation validation.
- [x] Implement one controlled model-output repair attempt.
- [x] Reject a second invalid response as `invalid_model_output`.
- [x] Prove that raw prompts, raw responses, and reasoning traces are not persisted or logged.
- [x] Complete one end-to-end incident analysis with citations.

## P5 — API, persistence, and job orchestration

- [x] Add SQLite repositories and Alembic migrations.
- [x] Implement the bounded in-process job runner with concurrency one.
- [x] Implement health and model-discovery endpoints.
- [x] Implement knowledge ingestion and source-listing endpoints.
- [x] Implement incident submission and result endpoints.
- [x] Implement benchmark submission and result endpoints.
- [x] Implement structured, privacy-safe application logging.
- [x] Verify interruption, queue-full, provider-failure, and restart behavior.
- [x] Verify that raw security logs are never stored in SQLite.

## P6 — Deployment-profile benchmark and default selection

- [x] Create at least ten version-controlled synthetic SSH benchmark cases.
- [x] Freeze parser results, retrieved context, prompt, schema, and generation settings per case.
- [x] Implement deterministic quality scorers and the manual review rubric.
- [x] Measure cold load, warm inference, TTFT, total time, token rate, and defensible RAM metrics.
- [x] Benchmark Foundation, Qwen, and the resolved Foundry profile sequentially.
- [x] Include failures, repairs, timeouts, and unavailable metrics in published results.
- [x] Select the default profile using the documented quality-first gates.
- [x] Publish the benchmark table and reproducibility manifest.

## P7 — Offline and GitHub readiness

- [x] Verify the complete cached workflow with network access disabled.
- [x] Add deterministic CI checks using fake providers instead of model downloads.
- [x] Add a README, architecture diagram, quickstart, and troubleshooting guide.
- [x] Add safe model bootstrap and license instructions without redistributing weights.
- [x] Add synthetic demo data and a reproducible example report.
- [x] Publish security, privacy, offline, and product-scope limitations.
- [x] Run the complete MVP acceptance checklist.
- [x] Confirm that `main` is in a working, reviewable state.

## Explicitly out of scope

- Model training or fine-tuning
- Cloud LLM fallback
- Automated blocking, account changes, command execution, or remediation
- A separate frontend beyond Swagger UI
- Vector databases and embedding retrieval for the MVP
- Nmap or Nginx parsers
- PDF report generation
