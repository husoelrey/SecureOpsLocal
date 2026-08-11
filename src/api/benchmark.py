import os
import tempfile
import asyncio
from typing import Dict, Any, List
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile, status

from src.api.upload import is_allowed_extension, validate_chunk, MAX_FILE_SIZE_BYTES
from src.job_runner import job_runner
from src.llm.analyzer import IncidentAnalyzer
from src.llm.ollama import OllamaProvider
from src.llm.foundry import FoundryLocalProvider
from src.parser.aggregator import aggregate_logs
from src.parser.ssh import SSHAuthLogParser
from src.rag.query import build_retrieval_query
from src.rag.retriever import TFIDFRetriever
from src.rag.store import global_knowledge_store
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

async def run_benchmark(job_id: str, temp_path_str: str, file_name: str) -> Dict[str, Any]:
    temp_path = Path(temp_path_str)
    try:
        # 1. Parsing Phase (Parse Once)
        parser = SSHAuthLogParser()
        parsed_lines = []
        with open(temp_path, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                parsed = parser.parse_line(line, current_year=2026)
                if parsed:
                    parsed_lines.append(parsed)
                    
        analysis = aggregate_logs(parsed_lines)
        
        # 2. RAG Retrieval (Retrieve Once)
        query = build_retrieval_query(analysis)
        chunks = global_knowledge_store.get_all_chunks()
        retrieved_chunks = []
        if chunks:
            retriever = TFIDFRetriever(chunks)
            retrieved_tuples = retriever.retrieve(query, top_k=5)
            retrieved_chunks = [t[0] for t in retrieved_tuples]

        # 3. Candidate Providers
        candidates = [
            ("Ollama_Foundation-Sec", OllamaProvider(model_name="foundation-sec-8b-reasoning:q4_k_m")),
            ("Ollama_Qwen3.5-9B", OllamaProvider(model_name="qwen3.5:9b-q4_k_m")),
            ("Foundry_DeviceResolved", FoundryLocalProvider(base_url="http://localhost:8080", model_name="foundry-profile"))
        ]
        
        results: List[Dict[str, Any]] = []

        # 4. Benchmark Loop
        for profile_name, provider in candidates:
            analyzer = IncidentAnalyzer(provider=provider, max_retries=0)
            
            # Cold Run
            try:
                cold_report = await analyzer.analyze_incident(f"{job_id}-cold", analysis, retrieved_chunks)
                cold_metrics = cold_report.performance_metrics
                cold_status = cold_report.status
            except Exception as e:
                cold_metrics = {}
                cold_status = f"failed: {e}"

            # Warm Run
            try:
                warm_report = await analyzer.analyze_incident(f"{job_id}-warm", analysis, retrieved_chunks)
                warm_metrics = warm_report.performance_metrics
                warm_status = warm_report.status
            except Exception as e:
                warm_metrics = {}
                warm_status = f"failed: {e}"
                
            results.append({
                "profile": profile_name,
                "cold_run": {
                    "status": cold_status,
                    "metrics": cold_metrics
                },
                "warm_run": {
                    "status": warm_status,
                    "metrics": warm_metrics
                }
            })
            
        return {
            "benchmark_id": job_id,
            "file_name": file_name,
            "profiles_evaluated": len(candidates),
            "results": results
        }
    finally:
        if temp_path.exists():
            temp_path.unlink()

@router.post("/run", status_code=status.HTTP_202_ACCEPTED)
async def submit_benchmark(file: UploadFile = File(...)):
    if not is_allowed_extension(file.filename):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file extension. Only .log and .txt are allowed",
        )

    # Stream to temp file
    total_size = 0
    fd, tmp_path_str = tempfile.mkstemp(prefix="secureops_benchmark_")
    os.close(fd)
    
    with open(tmp_path_str, "wb") as f:
        while chunk := await file.read(8192):
            if total_size == 0:
                if chunk.startswith(b"PK") or chunk.startswith(b"\x1f\x8b") or chunk.startswith(b"BZh"):
                    os.remove(tmp_path_str)
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Archives are not allowed",
                    )
            validate_chunk(chunk)
            total_size += len(chunk)
            if total_size > MAX_FILE_SIZE_BYTES:
                os.remove(tmp_path_str)
                raise HTTPException(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    detail="File exceeds 5 MiB limit",
                )
            f.write(chunk)
            
    try:
        # Let job_runner generate the job_id
        logger.info("Submitting benchmark job", extra={"stage": "submit", "file_size": total_size})
        job_id = await job_runner.submit_job(
            run_benchmark, 
            tmp_path_str, 
            file.filename
        )
    except asyncio.QueueFull:
        os.remove(tmp_path_str)
        logger.error("Job queue is full", extra={"stage": "submit", "error_code": "queue_full"})
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Job queue is full")

    logger.info("Benchmark job submitted successfully", extra={"benchmark_id": job_id, "stage": "accepted"})
    return {"benchmark_id": job_id, "status": "pending", "message": "Benchmark submitted"}

@router.get("/{benchmark_id}")
def get_benchmark_status(benchmark_id: str):
    job_status = job_runner.get_job_status(benchmark_id)
    
    if job_status["status"] == "not_found":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Benchmark not found")
        
    if job_status["status"] == "completed":
        return job_status["result"]
        
    return {
        "benchmark_id": benchmark_id,
        "status": job_status["status"],
        "error": job_status.get("error") if job_status["status"] == "failed" else None
    }
