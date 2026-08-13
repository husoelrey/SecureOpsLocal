<![CDATA[# SecureOps Local

**Air-gapped incident-review decision-support system for Linux SSH authentication logs,
powered by local LLM inference, deterministic parsing, and document-grounded RAG.**

[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688.svg)](https://fastapi.tiangolo.com)
[![Pydantic v2](https://img.shields.io/badge/Pydantic-v2-e92063.svg)](https://docs.pydantic.dev)
[![SQLite](https://img.shields.io/badge/SQLite-WAL-003B57.svg)](https://www.sqlite.org)
[![License](https://img.shields.io/badge/license-see%20below-lightgrey.svg)](#data-provenance-and-licensing)

---

## Table of Contents

- [Overview](#overview)
- [Why SecureOps Local Exists](#why-secureops-local-exists)
- [Architecture](#architecture)
  - [Deterministic AI — The Zero-Hallucination Guarantee](#deterministic-ai--the-zero-hallucination-guarantee)
  - [System Context and Deployment Topology](#system-context-and-deployment-topology)
  - [Analysis Pipeline](#analysis-pipeline)
- [Core Components](#core-components)
  - [1. SSH Authentication Log Parser (P2)](#1-ssh-authentication-log-parser-p2)
  - [2. Local Knowledge Base and RAG Pipeline (P3)](#2-local-knowledge-base-and-rag-pipeline-p3)
  - [3. Provider-Independent LLM Pipeline (P4)](#3-provider-independent-llm-pipeline-p4)
  - [4. Report Assembly and Validation](#4-report-assembly-and-validation)
- [Model Candidates and Profiles](#model-candidates-and-profiles)
- [Benchmark Methodology](#benchmark-methodology)
- [API Reference](#api-reference)
- [Repository Structure](#repository-structure)
- [Getting Started](#getting-started)
  - [Prerequisites](#prerequisites)
  - [Installation](#installation)
  - [Running the Application](#running-the-application)
  - [Running Tests and Quality Checks](#running-tests-and-quality-checks)
- [Glossary](#glossary)
- [Project Status](#project-status)
- [Security and Privacy Model](#security-and-privacy-model)
- [Data Provenance and Licensing](#data-provenance-and-licensing)
- [Known Limitations](#known-limitations)
- [Contributing](#contributing)

---

## Overview

SecureOps Local is a **local-first, air-gapped-ready** prototype that turns raw SSH
authentication logs into structured, cited incident-review reports — without sending
a single byte to a cloud service.

It is designed for:

| Audience | Use Case |
|---|---|
| **Junior SOC analysts** | Repeatable, evidence-based first-pass incident review |
| **System administrators** | Structured SSH log triage with defensive recommendations |
| **Security students** | Hands-on study of deterministic parsing, RAG, and local inference |
| **Small technical teams** | Privacy-preserving incident assessment on private infrastructure |
| **AI engineers** | Reference implementation for constrained local LLM pipelines |

### What SecureOps Local Is

- An initial incident-review assistant for Linux SSH authentication logs
- A log-summarization and evidence-structuring tool
- A document-grounded decision-support prototype
- A local deployment-profile evaluation and benchmarking platform

### What SecureOps Local Is Not

- A SIEM, IDS, IPS, antivirus, or forensic platform
- An automated remediation or attack-prevention system
- A multi-user production SaaS application
- A source of guaranteed attack attribution or compromise determination

---

## Why SecureOps Local Exists

The common approach of pasting raw logs into a cloud AI is fundamentally broken for
enterprise security. It violates data privacy, risks cloud exfiltration, and suffers
from hallucinations where LLMs invent IP addresses, miscount events, or fabricate
timelines.

**SecureOps Local solves this through four architectural pillars:**

| Pillar | Problem Solved | How |
|---|---|---|
| **Deterministic Constraints** | LLM hallucinations on factual data | A strict Python parser extracts all mathematical truth. The LLM is forbidden from computing counts, addresses, or timestamps. |
| **Air-Gapped Privacy** | Data leakage to cloud services | No cloud LLM fallback. All inference, retrieval, and storage run on the local machine. |
| **Document-Grounded RAG** | Unsubstantiated AI claims | The LLM reasons only against retrieved chunks from audited security literature (NIST, CISA, MITRE ATT&CK, OWASP). Every citation is programmatically validated. |
| **Strict Structured Output** | Unusable free-form AI responses | The LLM must respond in a rigid `ModelAssessment` JSON schema. Schema violations trigger one controlled repair attempt; a second failure produces `invalid_model_output`. |

---

## Architecture

### Deterministic AI — The Zero-Hallucination Guarantee

SecureOps Local enforces a strict separation between **deterministic truth** and
**model interpretation** at the architecture level:

```
┌─────────────────────────────────────────────────────────────────────┐
│                        TRUST BOUNDARY                               │
├─────────────────────────────┬───────────────────────────────────────┤
│   DETERMINISTIC (Trusted)   │     MODEL (Untrusted, Constrained)    │
├─────────────────────────────┼───────────────────────────────────────┤
│ • IP addresses              │ • Summary of observed patterns        │
│ • Event counts              │ • Possible interpretations            │
│ • Success/failure rates     │ • Risk level (low/medium/high)        │
│ • Timestamp ranges          │ • Evidence-based risk reasoning       │
│ • Authentication methods    │ • Defensive recommendations           │
│ • Repeated-attempt patterns │ • Citations to retrieved guidance     │
│ • Invalid-user flags        │                                       │
├─────────────────────────────┼───────────────────────────────────────┤
│ Source: SSHAuthLogParser    │ Source: LocalLLMProvider               │
│ Output: observed_findings   │ Output: ModelAssessment                │
│ Guarantee: Verifiable       │ Guarantee: Schema-validated, cited     │
└─────────────────────────────┴───────────────────────────────────────┘
```

**Parser truth always wins.** If the model contradicts a parser fact, the assessment
is rejected.

### System Context and Deployment Topology

```
Windows Host
├── Microsoft Foundry Local ─── runtime + model cache (DirectML / Intel Arc)
├── Ollama ────────────────── runtime + model cache (CPU / GGUF)
└── Docker Desktop
    └── SecureOps Local Container
        ├── FastAPI ──────────── REST API + Swagger UI
        ├── SSHAuthLogParser ── deterministic log analysis
        ├── TF-IDF Retriever ── local knowledge base search
        ├── IncidentAnalyzer ── LLM orchestration + validation
        ├── Bounded Job Runner ─ in-process queue (concurrency 1)
        └── SQLite Volume ───── persistence + migrations
```

**Key architectural rules:**

- Model runtimes live on the Windows host for hardware acceleration access
- The application container reaches runtimes via `host.docker.internal`
- Foundry Local is never forced into a container if it compromises GPU acceleration
- **Fallback:** Native Windows FastAPI when container networking is unreliable

### Analysis Pipeline

```
  ┌──────────┐     ┌───────────┐     ┌──────────────┐     ┌─────────────┐
  │  Upload   │────▶│  Validate │────▶│    Parse      │────▶│  Aggregate  │
  │ SSH Log   │     │  Stream   │     │  SSH Lines    │     │  Statistics │
  └──────────┘     └───────────┘     └──────────────┘     └──────┬──────┘
                                                                  │
                   ┌───────────┐     ┌──────────────┐             │
                   │  Retrieve │◀────│ Build Query  │◀────────────┘
                   │  Top-K    │     │ (no PII)     │
                   └─────┬─────┘     └──────────────┘
                         │
                   ┌─────▼─────┐     ┌──────────────┐     ┌─────────────┐
                   │   Pack    │────▶│   Generate   │────▶│  Validate   │
                   │  Context  │     │  Assessment  │     │  + Repair   │
                   └───────────┘     └──────────────┘     └──────┬──────┘
                                                                  │
                   ┌───────────┐     ┌──────────────┐             │
                   │   Store   │◀────│  Assemble    │◀────────────┘
                   │  Report   │     │  Report      │
                   └───────────┘     └──────────────┘
```

1. **Upload** — Streamed file validation with size, extension, MIME, encoding, and
   binary content checks. Archives rejected. Random temp filenames.
2. **Parse** — `SSHAuthLogParser` extracts structured events via explicit regex.
3. **Aggregate** — Deterministic statistics: unique IPs, event counts, time windows,
   repeated-attempt patterns, invalid-user flags.
4. **Query** — Privacy-minimized retrieval query built from parser statistics. IP
   addresses and usernames are excluded.
5. **Retrieve** — TF-IDF + cosine similarity returns top-k relevant document chunks.
6. **Pack** — Source-diversity limits enforce max 2 chunks per document, bounded word
   budget.
7. **Generate** — Selected `LocalLLMProvider` receives parser facts + retrieved context.
   Reasoning traces are stripped and never persisted.
8. **Validate** — Strict Pydantic v2 schema validation. Invalid citations rejected.
   One controlled repair attempt; second failure → `invalid_model_output`.
9. **Assemble** — Final `IncidentReport` merges parser truth, validated model assessment,
   verified citations, and safe runtime metadata.
10. **Store** — Validated report persisted to SQLite. Raw logs are never stored.

---

## Core Components

### 1. SSH Authentication Log Parser (P2)

**Location:** `src/parser/`

The extensible parser contract (`LogParser`) provides a streaming, line-by-line parsing
interface. The first implementation, `SSHAuthLogParser`, supports:

| Feature | Details |
|---|---|
| **Timestamp formats** | Syslog (`Aug 10 14:12:05`) and ISO 8601 / journald |
| **Event types** | `successful_login`, `failed_login`, `failed_login_invalid_user`, `invalid_user`, `connection_closed`, `disconnected` |
| **Address formats** | IPv4 and IPv6 |
| **Authentication methods** | Password, public key |
| **Metadata** | Source port, username, host |
| **Prefix formats** | Traditional syslog, journald/systemd |

**Deterministic aggregation** (`aggregator.py`) produces:

- Total events, successful, failed, and unparsed line counts
- Per-IP statistics: failed/successful attempts, first/last seen, targeted users
- Configurable pattern detection:
  - **Repeated attempts:** ≥5 failures from one source within 5 minutes
  - **Success after failure:** Success within 15 minutes after ≥5 failures
- Explicit limitations (year assumption for syslog, unparsed line count)

> **Design principle:** Patterns describe observable activity, never confirmed attacks.

### 2. Local Knowledge Base and RAG Pipeline (P3)

**Location:** `src/rag/`

| Component | File | Responsibility |
|---|---|---|
| **Ingestion** | `ingestion.py` | PDF (via pypdf), Markdown, and plain-text extraction with encoding validation |
| **Chunking** | `chunking.py` | Heading-aware splitting (400-word chunks, 50-word overlap), stable chunk IDs via content hashing |
| **Query Builder** | `query.py` | Deterministic, privacy-minimized query construction from parser statistics |
| **Retriever** | `retriever.py` | Pure-Python TF-IDF + cosine similarity (no external dependencies) |
| **Context Packing** | `packing.py` | Source-diversity limits (max 2 chunks/source), word budget enforcement, citation validation |

**Initial authoritative sources** (5 license-reviewed):

| # | Source | Publisher | License |
|---|---|---|---|
| 1 | SP 800-61 Rev. 3 — Incident Handling Guide | NIST | Public Domain |
| 2 | IR Playbook | CISA | Public Domain |
| 3 | ATT&CK T1110 — Brute Force | MITRE | Terms of Use (attribution) |
| 4 | Logging Cheat Sheet | OWASP | CC BY-SA 3.0 |
| 5 | OpenSSH Security Guidelines | OpenSSH | OpenSSH License |

> **Citation guarantee:** Every model citation is programmatically validated against
> the exact retrieved chunk set. Invented or hallucinated citation IDs cause immediate
> output rejection.

### 3. Provider-Independent LLM Pipeline (P4)

**Location:** `src/llm/`

| Component | File | Role |
|---|---|---|
| **Contract** | `base.py` | Abstract `LocalLLMProvider` with `generate()` returning `NormalizedGenerationResult` |
| **Ollama** | `ollama.py` | Adapter using Ollama's `/api/chat` endpoint with structured output via `format` |
| **Foundry** | `foundry.py` | Adapter using OpenAI-compatible `/v1/chat/completions` with `json_schema` response format |
| **Prompts** | `prompts.py` | Versioned system prompt (`SYSTEM_PROMPT_V1`) with non-negotiable safety rules |
| **Analyzer** | `analyzer.py` | Orchestrator: prompt building, generation, reasoning stripping, validation, repair loop |

**Provider contract (`LocalLLMProvider`):**

```python
class LocalLLMProvider(ABC):
    @abstractmethod
    async def generate(
        self,
        prompt: str,
        system_prompt: str,
        schema: Dict[str, Any]
    ) -> NormalizedGenerationResult: ...
```

**Normalized generation result:**

```python
class NormalizedGenerationResult(BaseModel):
    content: str                           # Generated JSON content
    prompt_tokens: int | None              # Input token count
    completion_tokens: int | None          # Output token count
    total_latency_ms: float | None         # Wall-clock generation time
    time_to_first_token_ms: float | None   # TTFT (Ollama only)
```

**Reasoning trace handling:**

Models that produce `<think>...</think>` blocks (e.g., Foundation-Sec) have their
reasoning traces stripped via regex before any processing, logging, or persistence.
This is a non-negotiable privacy requirement.

### 4. Report Assembly and Validation

**Strict `ModelAssessment` schema (what the LLM must produce):**

```python
class ModelAssessment(BaseModel):
    summary: str                                    # Cautious incident summary
    possible_interpretations: list[str]             # Evidence-supported possibilities
    risk_level: Literal["low", "medium", "high"]    # Assessed risk
    risk_reasoning: str                             # Evidence-based reasoning
    recommended_actions: list[str]                  # Defensive-only recommendations
    citations: list[str]                            # Chunk IDs from retrieved context
```

**Final `IncidentReport` (assembled by the application, not the LLM):**

| Field | Source | Trust Level |
|---|---|---|
| `status` | Application state machine | Trusted |
| `summary` | ModelAssessment (validated) | Constrained |
| `observed_findings` | Parser aggregation | **Deterministic** |
| `possible_interpretations` | ModelAssessment (validated) | Constrained |
| `risk_level` / `risk_reasoning` | ModelAssessment (validated) | Constrained |
| `recommended_actions` | ModelAssessment (validated) | Constrained |
| `citations` | Validated against chunk DB | Verified |
| `limitations` | Parser + model | Mixed |
| `parser_statistics` | Deterministic aggregation | **Deterministic** |
| `model_information` | Provider metadata | Trusted |
| `performance_metrics` | Runtime measurement | Trusted |

**Validation pipeline:**

1. JSON parse the model output
2. Strip reasoning traces (`<think>` blocks, markdown fences)
3. Validate against `ModelAssessment` Pydantic schema (strict, no extra fields)
4. Verify all cited chunk IDs exist in the supplied evidence package
5. On failure → one controlled repair attempt with error feedback
6. Second failure → `invalid_model_output` (not persisted as completed)

---

## Model Candidates and Profiles

The project benchmarks three candidate deployment profiles:

| Profile | Runtime | Model | Quantization | Role |
|---|---|---|---|---|
| **Foundation-Sec** | Ollama | `foundation-sec-8b-reasoning:q4_k_m` | Q4_K_M (GGUF) | Domain-specialized cybersecurity candidate (Llama 3.1 backbone) |
| **Qwen** | Ollama | `qwen:0.5b` (testing) / `qwen3.5:9b-q4_K_M` (benchmark) | Q4_K_M | General-purpose quality reference |
| **Foundry** | Foundry Local | `Phi-3-mini-4k-instruct-onnx` | ONNX INT4 (DirectML) | Hardware-accelerated Windows candidate |

**A deployment profile includes:** model identifier, quantization, runtime version,
execution backend, prompt/schema versions, generation settings, and hardware context.

**No default profile is selected before the benchmark is complete.** The winner is
determined by quality-first gates: 100% schema compliance, 100% citation validity,
and zero unsupported deterministic claims. Latency is only a tie-breaker.

**Normalized generation settings:**

| Setting | Value |
|---|---|
| Context limit | 8,192 tokens |
| Temperature | 0.0 |
| Top-p | 0.9 |
| Seed | 42 |
| Max output tokens | 2,048 |
| Timeout | 300 seconds |
| Keep-alive | 10 minutes |

---

## Benchmark Methodology

The benchmark determines which deployment profile offers the best balance of quality,
structured-output reliability, latency, and memory on the target device.

**Fixed evidence:** Every profile receives identical synthetic inputs, parser results,
retrieved chunks, prompt/schema versions, and generation settings. Retrieval runs once
per case; models receive the same evidence pack.

**Minimum 10 synthetic cases covering:**

| # | Scenario |
|---|---|
| 1 | Normal successful login |
| 2 | Single failed login |
| 3 | Repeated failures from one source |
| 4 | One source targeting multiple accounts |
| 5 | Privileged/root account attempts |
| 6 | Invalid-user attempts |
| 7 | Success after repeated failures |
| 8 | Multiple source addresses |
| 9 | IPv6 input |
| 10 | Malformed or non-SSH input |

**Quality metrics:** Schema compliance (first attempt + post-repair), citation validity,
unsupported-claim count, recommendation completeness, risk consistency, groundedness.

**Performance metrics:** Cold-load time, TTFT, total latency, tokens/second, peak
memory (RSS with declared scope).

**Manual rubric (0–2 scale):** Groundedness, citation support, cautious interpretation,
practical recommendations, readability.

Full methodology: [BENCHMARK_METHODOLOGY.md](docs/context/BENCHMARK_METHODOLOGY.md)

---

## API Reference

The MVP exposes the following endpoints through Swagger UI:

| Method | Endpoint | Description | Status |
|---|---|---|---|
| `GET` | `/health` | API, database, and provider health | ✅ Implemented |
| `POST` | `/api/upload/ssh` | Upload and validate SSH log (≤5 MiB) | ✅ Implemented |
| `POST` | `/api/upload/knowledge` | Ingest knowledge document (≤20 MiB) | ✅ Implemented |
| `GET` | `/models` | Safe model profile metadata | 🔲 Planned (P5) |
| `POST` | `/v1/knowledge/ingest` | Knowledge ingestion with chunking | 🔲 Planned (P5) |
| `GET` | `/v1/knowledge/sources` | List ingested knowledge sources | 🔲 Planned (P5) |
| `POST` | `/v1/incidents/analyze` | Submit SSH log for analysis (→ 202) | 🔲 Planned (P5) |
| `GET` | `/v1/incidents/{id}` | Retrieve incident report | 🔲 Planned (P5) |
| `POST` | `/v1/benchmarks/run` | Submit benchmark run (→ 202) | 🔲 Planned (P6) |
| `GET` | `/v1/benchmarks/{id}` | Retrieve benchmark results | 🔲 Planned (P6) |

---

## Repository Structure

```
SecureOpsLocal/
├── src/
│   ├── main.py                    # FastAPI application entry point
│   ├── database.py                # SQLAlchemy 2 engine, session, and base
│   ├── api/
│   │   ├── upload.py              # Secure SSH log upload with streaming validation
│   │   └── knowledge.py           # Knowledge document ingestion endpoint
│   ├── llm/
│   │   ├── base.py                # LocalLLMProvider abstract contract
│   │   ├── ollama.py              # Ollama provider adapter (/api/chat)
│   │   ├── foundry.py             # Foundry Local provider adapter (/v1/chat/completions)
│   │   ├── analyzer.py            # IncidentAnalyzer: orchestration, validation, repair
│   │   └── prompts.py             # Versioned system prompts (SYSTEM_PROMPT_V1)
│   ├── parser/
│   │   ├── base.py                # LogParser abstract contract
│   │   ├── ssh.py                 # SSHAuthLogParser (regex-based, syslog + journald)
│   │   └── aggregator.py          # Deterministic statistics and pattern detection
│   ├── rag/
│   │   ├── ingestion.py           # PDF, Markdown, text extraction
│   │   ├── chunking.py            # Heading-aware chunking with overlap
│   │   ├── query.py               # Privacy-minimized retrieval query builder
│   │   ├── retriever.py           # Pure-Python TF-IDF + cosine similarity
│   │   └── packing.py             # Context packing and citation validation
│   ├── schemas/
│   │   ├── analysis.py            # LogAnalysis, IPAggregation
│   │   ├── incident_report.py     # IncidentReport, IncidentReportCreate
│   │   ├── llm.py                 # ModelAssessment, NormalizedGenerationResult
│   │   ├── parsed_log_line.py     # ParsedLogLine, ParsedLogLineCreate
│   │   └── rag.py                 # IngestedDocument, DocumentChunk, IngestionResponse
│   └── models/
│       ├── incident_report.py     # SQLAlchemy ORM model for incidents
│       └── parsed_log_line.py     # SQLAlchemy ORM model for parsed events
├── tests/
│   ├── test_parser.py             # SSH parser unit tests (formats, edge cases)
│   ├── test_upload.py             # Upload validation and security tests
│   ├── test_analyzer.py           # IncidentAnalyzer with mocked providers
│   ├── test_e2e_analysis.py       # End-to-end incident analysis integration
│   ├── test_ollama.py             # Ollama adapter unit tests
│   ├── test_foundry.py            # Foundry adapter unit tests
│   ├── test_privacy.py            # Privacy guarantees: no raw logs, no reasoning traces
│   ├── test_rag_ingestion.py      # Document ingestion tests (PDF, text, edge cases)
│   ├── test_rag_chunking.py       # Heading-aware chunking tests
│   ├── test_rag_query.py          # Privacy-minimized query construction tests
│   ├── test_rag_retriever.py      # TF-IDF retriever unit tests
│   ├── test_rag_packing.py        # Context packing and citation validation tests
│   ├── test_rag_quality.py        # Retrieval quality evaluation tests
│   └── test_main.py              # Application startup tests
├── migrations/                    # Alembic database migrations
├── scripts/
│   └── smoke_test.py              # Manual structured-output smoke test
├── docs/
│   ├── context/
│   │   ├── PROJECT_SPEC.md        # Product definition and acceptance criteria
│   │   ├── ARCHITECTURE.md        # System architecture and contracts
│   │   ├── DETAILED_IMPLEMENTATION_PLAN.md
│   │   ├── SECURITY_AND_PRIVACY.md
│   │   ├── RAG_AND_KNOWLEDGE_BASE.md
│   │   ├── BENCHMARK_METHODOLOGY.md
│   │   ├── MODEL_PROFILES.md      # Model provenance, licenses, and digests
│   │   ├── RUNTIME_READINESS.md   # Runtime verification evidence
│   │   ├── SOURCE_MANIFEST.md     # Knowledge source license audit
│   │   ├── CURRENT_STATUS.md      # Verified project state
│   │   ├── DECISION_LOG.md        # Accepted architectural decisions
│   │   ├── DEVELOPMENT_WORKFLOW.md
│   │   └── IMPLEMENTATION_ROADMAP.md
│   └── benchmark_results/         # Future benchmark output
├── AGENTS.md                      # Agent behavioral rules and constraints
├── PLAN.md                        # Executable project checklist
├── pyproject.toml                 # Pytest, Ruff, mypy, Pyright configuration
├── requirements.txt               # Pinned Python dependencies
├── alembic.ini                    # Database migration configuration
└── .gitignore                     # Models, caches, secrets, databases excluded
```

---

## Getting Started

### Prerequisites

| Requirement | Version | Notes |
|---|---|---|
| **Python** | 3.12+ | Project target is 3.12 |
| **Ollama** | 0.32+ | For Foundation-Sec and Qwen inference |
| **Foundry Local** | 0.10+ | For Microsoft model inference (optional) |
| **Docker Desktop** | 4.85+ | For containerized deployment (optional) |
| **WSL 2** | 2.3+ | For synthetic log generation (optional) |

### Installation

```bash
# 1. Clone the repository
git clone https://github.com/husoelrey/SecureOpsLocal.git
cd SecureOpsLocal

# 2. Create and activate virtual environment
python -m venv .venv

# Windows
.venv\Scripts\activate

# Linux / macOS
source .venv/bin/activate

# 3. Install dependencies
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

### Model Setup (Air-Gap Preparation)

Models must be downloaded during an online preparation step. They are stored outside
the repository under an approved external model root.

```bash
# Foundation-Sec (Ollama) — ~4.92 GB
# Download the GGUF from: https://huggingface.co/fdtn-ai/Foundation-Sec-8B-Reasoning-Q4_K_M-GGUF
# Verify SHA-256: 7a61e41b1ca1b339d41caf3001ea7832469d866e7c52a23980a1e95cbf5cd58b
# Import into Ollama:
ollama create foundation-sec-8b-reasoning:q4_k_m -f Modelfile

# Qwen (Ollama)
ollama pull qwen:0.5b              # Fast testing
ollama pull qwen3.5:9b-q4_K_M     # Full benchmark

# Foundry Local
foundry model list                 # Discover device-compatible models
```

> **Important:** Model weights are never committed to the repository. The external model
> root is `C:\Users\<user>\Documents\docs\AI_models` with `ollama/` and `foundry/`
> subdirectories.

### Running the Application

```bash
# Start the FastAPI development server
uvicorn src.main:app --host 127.0.0.1 --port 8000 --reload

# Access Swagger UI
# Open http://127.0.0.1:8000/docs
```

### Running Tests and Quality Checks

Tests use fake/mocked providers — no model downloads required.

```bash
# Run the full test suite
python -m pytest

# Linting and formatting
python -m ruff check src tests
python -m ruff format --check src tests

# Static type checking
python -m mypy src
```

---

## Glossary

| Term | Definition |
|---|---|
| **IncidentReport** | Final assembled report: parser truth + validated model assessment + verified citations + runtime metadata |
| **ModelAssessment** | Strict Pydantic v2 schema representing the LLM's constrained interpretation |
| **Parser Facts** | Deterministic outputs from Python code: IPs, event counts, time windows, patterns |
| **observed_findings** | Application-controlled field containing only deterministic, verifiable facts |
| **Deployment Profile** | Complete specification: model + quantization + runtime + execution backend + prompt/schema versions + generation settings |
| **LocalLLMProvider** | Abstract contract implemented by Ollama and Foundry adapters |
| **NormalizedGenerationResult** | Provider-agnostic response: content + token counts + latency metrics |
| **TF-IDF** | Term Frequency–Inverse Document Frequency: deterministic retrieval baseline |
| **RAG** | Retrieval-Augmented Generation: grounding model output in retrieved document chunks |
| **Reasoning Trace** | `<think>...</think>` blocks from reasoning models — stripped and never persisted |
| **Foundry Local** | Microsoft's local inference runtime with DirectML hardware acceleration |
| **Ollama** | Widely-used local inference runtime for GGUF models |
| **Air-Gapped Ready** | Online preparation + verified cached offline operation |

---

## Project Status

| Phase | Description | Status | Evidence |
|---|---|---|---|
| **P0** | Repository governance and project context | ✅ Complete | Ignore policy, context consistency, reference and link checks pass |
| **P1** | Local runtime and model profiles | ✅ Complete | Runtime health, offline simulation, model verification, smoke test passed |
| **P2** | Deterministic SSH analysis core | ✅ Complete | Parser implementation, test suite, and validation passed |
| **P3** | Local knowledge base and RAG | ✅ Complete | Ingestion, chunking, retrieval, packing, and tests passing |
| **P4** | Provider-independent incident analysis | ✅ Complete | Provider adapters, strict assembly, privacy guarantees, E2E test complete |
| **P5** | API, persistence, and job orchestration | 🔲 Not started | SQLite repos and Alembic migrations created; job runner and endpoints pending |
| **P6** | Deployment-profile benchmark | 🔲 Not started | No benchmark cases or results |
| **P7** | Offline and GitHub readiness | 🔲 Not started | No offline workflow or CI |

**Current focus:** P5 — API, persistence, and job orchestration

---

## Security and Privacy Model

SecureOps Local processes sensitive security data and must not create greater risk than
the data it reviews.

### Upload Security

| Control | SSH Logs | Knowledge Docs |
|---|---|---|
| **Max size** | 5 MiB (streamed) | 20 MiB (streamed) |
| **Extensions** | `.log`, `.txt` | `.pdf`, `.md`, `.txt` |
| **Archives** | Rejected (PK, gzip, bz2) | Rejected |
| **Null bytes** | Rejected | Rejected |
| **Encoding** | UTF-8 only | UTF-8 only |
| **Filenames** | Never used as disk paths | Never used as disk paths |
| **Temp files** | Random names, cleaned on all exit paths | Random names, cleaned on all exit paths |

### Privacy Guarantees

- **No cloud fallback.** The core path never sends data to external services.
- **No raw log persistence.** Only hashes, sizes, and structured metadata are stored.
- **No prompt/response logging.** Application logs exclude raw prompts, model responses,
  and reasoning traces.
- **No reasoning trace retention.** `<think>` blocks are stripped before any processing.
- **Privacy-minimized retrieval.** IP addresses and usernames are excluded from queries.
- **Synthetic test data.** All repository fixtures use synthetic addresses and accounts.

### Defensive Boundary

The application does **not**:
- Execute commands from model or file content
- Block addresses or modify firewall rules
- Disable accounts or scan targets
- Automate any offensive or remediation activity

Recommendations are limited to: investigation, evidence preservation, correlation,
escalation, defensive validation, and hardening.

Full details: [SECURITY_AND_PRIVACY.md](docs/context/SECURITY_AND_PRIVACY.md)

---

## Data Provenance and Licensing

| Asset | License | Redistribution |
|---|---|---|
| **Application code** | Repository license | ✅ |
| **Knowledge sources** | Original publisher licenses (NIST: Public Domain, MITRE: Terms of Use, OWASP: CC BY-SA 3.0) | Per-source (see [SOURCE_MANIFEST.md](docs/context/SOURCE_MANIFEST.md)) |
| **Foundation-Sec weights** | Meta Llama 3.1 Community License + Apache 2.0 (Cisco changes) | ❌ Not redistributed |
| **Qwen weights** | Tongyi Qianwen License | ❌ Not redistributed |
| **Phi-3-mini weights** | MIT License | ❌ Not redistributed |

> This repository does **not** redistribute model weights. The source manifest documents
> provenance, SHA-256 digests, and acquisition instructions for each model.

---

## Known Limitations

1. **Parser scope:** Only SSH authentication logs are supported. Nmap, Nginx, and other
   log formats are explicitly deferred beyond the MVP.
2. **Retrieval baseline:** TF-IDF has weaker semantic matching than embedding-based
   retrieval. This is a deliberate choice for determinism, simplicity, and offline
   packaging.
3. **Year assumption:** Syslog timestamps lack year information. The parser assumes the
   current year and exposes this as an explicit limitation.
4. **Single-threaded inference:** Job concurrency is limited to one to prevent memory
   contention on the 16 GB target device.
5. **No OCR:** Image-only PDFs are rejected. OCR support is outside the MVP.
6. **No vector database:** The small knowledge collection does not justify an external
   vector store. Optional embedding retrieval may be evaluated post-MVP.
7. **Manual benchmark review:** Free-form model interpretation quality requires human
   evaluation. Deterministic scoring covers structure, citations, and constraints only.
8. **Intel Arc acceleration:** GPU acceleration behavior through DirectML on Intel Arc
   is an open investigation item.

---

## Contributing

SecureOps Local follows a structured development workflow:

- **Branches:** `feature/p<phase>-<feature>`, `fix/<topic>`, `docs/<topic>`,
  `spike/<topic>`
- **Commits:** Small, single-purpose, only after relevant checks pass
- **Quality gates:** Pytest + Ruff + mypy must pass before merge
- **Main branch:** Always in a verified state

See [DEVELOPMENT_WORKFLOW.md](docs/context/DEVELOPMENT_WORKFLOW.md) for full workflow
rules and [PLAN.md](PLAN.md) for the executable project checklist.
]]>
