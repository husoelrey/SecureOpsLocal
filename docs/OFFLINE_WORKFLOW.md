# Offline Workflow and Verification Guide

SecureOps Local is an air-gapped-ready incident review decision-support prototype for Linux SSH authentication logs. To run the application in a fully offline or network-disabled environment, you must cache the necessary models and dependencies beforehand.

## Product Scope and Limitations

**IMPORTANT: SecureOps Local is NOT a SIEM, IDS, antivirus product, attack tool, or automated remediation system.**

- **No Automated Blocking**: The application will not automatically block IP addresses, change firewall rules, disable accounts, scan targets, exploit systems, crack credentials, or automate misuse.
- **Cautious Security Language**: The application provides cautiously worded assessments based on deterministic facts. It does not claim that a log pattern definitively proves an attack or compromise.
- **Defensive-Only**: Recommendations are limited to investigation, evidence preservation, correlation, escalation, defensive validation, and hardening.

## Privacy Guarantees

SecureOps Local adheres to strict privacy and locality principles:
- **No Cloud LLM Fallback**: The core product uses only local LLM deployments (e.g., Ollama, Foundry). There is no fallback to cloud-based APIs.
- **Data Locality**: Raw logs, prompts, model responses, or reasoning traces must not be sent to any third party.
- **No Persistence of Sensitive Data**: Raw logs are never persisted by default in the database.
- **RAG is Not Training**: Retrieval-Augmented Generation (RAG) is used strictly for contextualizing an existing local model. The project does not train or fine-tune any LLM on your data.

## Offline Preparation Steps

Follow these steps on a machine with internet access before moving the system to an air-gapped environment.

### 1. Cache Dependencies
Download and cache all required Python dependencies:
```bash
pip download -r requirements.txt -d vendor/
```
In the offline environment, install them using:
```bash
pip install --no-index --find-links vendor/ -r requirements.txt
```

### 2. Cache Local Models
Models must be fully downloaded and verified before offline use.

**Ollama:**
Pull the required models to populate the local Ollama cache:
```bash
ollama pull foundation-sec-8b-reasoning:q4_k_m
ollama pull qwen:0.5b
```

> [!WARNING]
> If you configured a custom model path (e.g., `C:\AI_models`) to isolate your runtime from default OS directories, ensure the `OLLAMA_MODELS` environment variable is set globally before starting `ollama serve`.

**Foundry Local:**
Resolve and cache the compatible Foundry model by downloading it through the Foundry CLI or directly to the configured Foundry cache directory (`C:\Users\husoelrey\Documents\docs\AI_models\foundry`).

### 3. Verify Offline Execution
To verify that the workflow succeeds offline:
1. Disable your network connection (e.g., turn off Wi-Fi or unplug the ethernet cable).
2. Start your local LLM provider (Ollama or Foundry).
3. Run the application tests to confirm no external requests are made:
   ```bash
   pytest tests/
   ```
4. Process a sample log file and confirm that the `IncidentReport.json` is generated successfully without any network access.
