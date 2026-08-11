# SecureOps Local

SecureOps Local is an air-gapped-ready incident review decision-support prototype for Linux SSH authentication logs. It safely accepts an untrusted log, extracts deterministic facts, retrieves relevant local security guidance, and asks a selected local LLM deployment profile for a cautious, cited assessment. 

By running entirely on the local device via **Microsoft Foundry Local** or **Ollama**, this project strictly isolates sensitive security data from cloud inference endpoints.

---

## What This Project Does

This project is a **decision-support prototype** designed to assist junior SOC analysts, system administrators, and security students with initial incident reviews. 

Authentication logs often contain sensitive IP addresses, account names, and system details. Sending this to a cloud model may violate organizational privacy policies. Furthermore, large language models are known to hallucinate numerical aggregations or falsely declare definitively that an attack occurred. SecureOps Local solves this by:

1. **Keeping all data local**: No cloud LLM fallback is permitted.
2. **Separating deterministic facts from model interpretation**: A robust Python parser counts the events and determines the timeline; the LLM is only asked to *interpret* those facts using retrieved knowledge.
3. **Validating outputs**: The LLM's response is forced into a strict schema, and citations are verified against the local knowledge base.

### What This Project is NOT
- It is **not** a SIEM, IDS, IPS, or forensic platform.
- It is **not** an automated remediation tool (it will not block IPs or change firewall rules).
- It is **not** an enterprise SaaS.

---

## End-to-End Analysis Pipeline

The system processes incidents through a strictly controlled pipeline:

1. **Upload & Validation**: A bounded SSH log is streamed and validated for size, type, encoding, and content.
2. **Parsing (P2)**: `SSHAuthLogParser` converts supported lines into normalized events, extracting deterministic findings (e.g., failed attempts, repeated failures within a time window, invalid users).
3. **Retrieval (P3)**: A privacy-minimized query is constructed from the parsed facts. The local retriever returns a fixed top-k evidence package from local documents (NIST, CISA, MITRE, OWASP) using TF-IDF and cosine similarity.
4. **LLM Inference (P4)**: The selected local provider (Foundry Local or Ollama) receives the parser facts and retrieved context. It is tasked with generating a structured assessment without seeing raw reasoning traces.
5. **Strict Validation**: Pydantic models validate the LLM's output. If validation fails, one controlled repair attempt is made. A second failure is rejected entirely.

---

## Architecture & Topology

SecureOps Local is built as a **modular monolith** with FastAPI, SQLite, SQLAlchemy 2, and Alembic.

### Deployment Topology
* **Windows Host**: Hosts Microsoft Foundry Local, Ollama, and hardware-accelerated model inference. Model caches are explicitly stored outside the repository.
* **Docker Container**: Hosts FastAPI, the deterministic parser, RAG retrieval, persistence, and benchmark orchestration.
* **Docker Volume**: Secures SQLite databases and controlled application data.
* **Bridge**: The container connects to the host inference runtimes via `host.docker.internal`.

### Core Contracts
The application revolves around strict interfaces to ensure provider neutrality:
* **`Parser`**: Extracts logs without any LLM dependency.
* **`Retriever`**: Supports indexing, top-k search, filters, and health reporting.
* **`LocalLLMProvider`**: Supports health checks, model discovery, standard/streaming generation, and handles the differences between Foundry and Ollama transparently.

---

## Deep Dive: Local Models & RAG

### Model Profiles
The project evaluates local deployment profiles rather than abstract model families. The primary benchmark candidates include:
* **Foundation-Sec-8B-Reasoning Q4_K_M** (Security-specialized, via Ollama)
* **Qwen3.5 9B Q4_K_M** (General-purpose reference, via Ollama)
* A concrete device-supported profile via **Microsoft Foundry Local**.

*Note: Model reasoning/chain-of-thought is stripped internally and is never returned, logged, or persisted.*

### Knowledge Base
The initial RAG implementation ingests reviewed sources from authoritative bodies. 
* **Ingestion**: Supports PDF, Markdown, and plain text.
* **Chunking**: Heading-aware chunking with bounded overlap.
* **Retrieval**: Uses TF-IDF baseline for deterministic top-k citations, preserving memory and computing resources without requiring a full vector database in the MVP.

---

## Security & Privacy Promises

* **Untrusted Inputs**: Every uploaded log is treated as untrusted, verified, and cleaned up safely via temporary random filenames.
* **No Persistence of Raw Data**: Raw logs, full prompts, and raw model responses (including reasoning traces) are excluded from application logs and SQLite.
* **Defensive Boundary**: The LLM receives no tool access, shell access, or operating-system privileges.

---

## Current Status & Roadmap

| Phase | Description | Status |
|---|---|---|
| **P0** | Repository governance and project context | **Complete** |
| **P1** | Local runtime and model profiles | **Complete** |
| **P2** | Deterministic SSH analysis core | **Complete** |
| **P3** | Local knowledge base and RAG | **Complete** |
| **P4** | Provider-independent incident analysis | **Complete** |
| **P5** | API, persistence, and job orchestration | Not started |
| **P6** | Deployment-profile benchmark and default selection | Not started |
| **P7** | Offline and GitHub readiness | Not started |

---

## How to Run & Develop

SecureOps Local relies entirely on standard libraries where possible to ensure offline packaging readiness.

### Virtual Environment Setup
```bash
python -m venv .venv
# On Windows
.venv\Scripts\activate
# On Linux/Mac
source .venv/bin/activate

python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

### Validation & Testing
The project uses strict quality gates. Running the deterministic suite does not require downloading massive model weights.

```bash
# Run unit and integration tests (mocked providers)
python -m pytest

# Run linting and static typing
python -m ruff check src tests
python -m ruff format src tests
python -m mypy src
```

### Model Runtimes
To run the full pipeline, ensure that **Ollama** or **Foundry Local** is running on your host, and pull the required test models (e.g., `ollama pull qwen:0.5b` for fast integration testing).

---

## License & Provenance

The SecureOps Local application code is licensed under the terms defined in `LICENSE`.

**Knowledge Sources**: Documents ingested into the RAG pipeline are governed by their respective organizational licenses (e.g., NIST, CISA). Always verify redistribution permissions before committing source PDFs or markdown files to version control.
