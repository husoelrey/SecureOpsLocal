# SecureOps Local

SecureOps Local is an air-gapped-ready incident review decision-support prototype for Linux SSH authentication logs. It safely accepts an untrusted log, extracts deterministic facts, retrieves relevant local security guidance, and asks a selected local LLM deployment profile for a cautious, cited assessment.

**Status**: Alpha / Under Development (Completed up to Phase 4: Provider-independent incident analysis)

## Core Philosophy

* **Locality and Privacy**: No cloud LLM fallback. Raw logs, prompts, model responses, and reasoning traces must never be sent to a third party.
* **Deterministic Truth**: The LLM must not calculate addresses, usernames, timestamps, success/failure counts, or other parser facts. Parser truth always wins.
* **Cautious Security Language**: The model does not definitively claim a compromise, but expresses evidence-supported possibilities based on local guidance.
* **Defensive-only**: Does not execute commands, block addresses, or automate remediation.

## Architecture

SecureOps Local relies on a strict, modular pipeline:
1. **Parser Stage (P2)**: Extensible Python-based parsers extract events from SSH logs (e.g., successful/failed attempts, invalid users, targeted IPs).
2. **Knowledge Base / RAG (P3)**: Ingests documents (NIST, CISA, OWASP, etc.) into a local chunked datastore. Constructs privacy-safe queries to retrieve top-k evidence via TF-IDF/cosine similarity.
3. **Local LLM Analysis (P4)**: Bridges the parser facts and retrieved context, pushing them to a local inference provider (Ollama or Microsoft Foundry Local) via an adapter. Enforces strict schema output (`ModelAssessment`) and automatically validates citations.
4. **API & Persistence (P5 - Planned)**: Bounded job runner using FastAPI, SQLite, and SQLAlchemy.

## Getting Started

### Prerequisites
* **Python 3.12** or higher
* **Ollama** and/or **Microsoft Foundry Local** installed and running on the local host.
* Supported LLMs (e.g., Foundation-Sec-8B-Reasoning Q4_K_M, Qwen3.5)

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/husoelrey/SecureOpsLocal.git
   cd SecureOpsLocal
   ```

2. **Create a virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

### Development & Testing

SecureOps Local enforces strict quality boundaries. Standard library usage is prioritized over external dependencies.

* Run tests using `pytest`:
  ```bash
  python -m pytest
  ```
* Linting and formatting using `ruff`:
  ```bash
  python -m ruff check src tests
  python -m ruff format src tests
  ```

For detailed contributing guidelines, review the `docs/context/DEVELOPMENT_WORKFLOW.md`.

## Repository Structure

* `src/`: Core application modules.
  * `parser/`: Deterministic log parsers and aggregators.
  * `rag/`: Knowledge ingestion, chunking, and TF-IDF retrieval.
  * `llm/`: `LocalLLMProvider` abstractions and `IncidentAnalyzer`.
  * `schemas/`: Strict Pydantic domain models.
* `tests/`: Unit and End-to-End test suites.
* `docs/context/`: Product specifications, architecture documents, decision logs, and roadmaps.

## License & Disclaimer

SecureOps Local is an initial incident-review assistant and a decision-support prototype. It is **not** a SIEM, IDS, IPS, antivirus product, or automated remediation system. It is designed to evaluate local RAG and local inference runtimes under strict privacy constraints.

See `docs/context/PROJECT_SPEC.md` for full project boundaries and limitations.
