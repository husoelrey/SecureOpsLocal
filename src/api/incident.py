import json
import os
import tempfile
import uuid
from pathlib import Path
import asyncio

from fastapi import APIRouter, File, HTTPException, UploadFile, status

from src.api.upload import is_allowed_extension, validate_chunk, MAX_FILE_SIZE_BYTES
from src.database import SessionLocal
from src.job_runner import job_runner
from src.llm.analyzer import IncidentAnalyzer
from src.llm.ollama import OllamaProvider
from src.models.incident_report import IncidentReport as DBIncidentReport
from src.parser.aggregator import aggregate_logs
from src.parser.ssh import SSHAuthLogParser
from src.rag.query import build_retrieval_query
from src.rag.retriever import TFIDFRetriever
from src.rag.store import global_knowledge_store

router = APIRouter()

async def process_incident(temp_path_str: str, file_name: str, job_id: str):
    temp_path = Path(temp_path_str)
    db = SessionLocal()
    try:
        # P2: Parse
        parser = SSHAuthLogParser()
        parsed_lines = []
        with open(temp_path, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                parsed = parser.parse_line(line, current_year=2026)
                if parsed:
                    parsed_lines.append(parsed)
                    
        analysis = aggregate_logs(parsed_lines)
        
        # P3: RAG Retrieval
        query = build_retrieval_query(analysis)
        chunks = global_knowledge_store.get_all_chunks()
        retrieved_chunks = []
        if chunks:
            retriever = TFIDFRetriever(chunks)
            retrieved_tuples = retriever.retrieve(query, top_k=5)
            retrieved_chunks = [t[0] for t in retrieved_tuples]
        
        # P4: LLM Analysis (Default Profile)
        provider = OllamaProvider(model_name="foundation-sec-8b-reasoning:q4_k_m")
        analyzer = IncidentAnalyzer(provider=provider, max_retries=1)
        
        incident_create = await analyzer.analyze_incident(job_id, analysis, retrieved_chunks)
        
        # Update DB Report
        db_report = db.query(DBIncidentReport).filter(DBIncidentReport.id == int(job_id)).first()
        if db_report:
            db_report.status = incident_create.status
            db_report.summary = incident_create.summary
            db_report.risk_level = incident_create.risk_level
            db_report.recommendations = json.dumps(incident_create.recommended_actions)
            db_report.raw_model_response = json.dumps(incident_create.model_dump())
            db.commit()
            db.refresh(db_report)
            
        return {"incident_id": job_id, **incident_create.model_dump()}
    except Exception as e:
        db_report = db.query(DBIncidentReport).filter(DBIncidentReport.id == int(job_id)).first()
        if db_report:
            db_report.status = "failed"
            db_report.summary = f"Job failed: {str(e)}"
            db.commit()
        raise e
    finally:
        db.close()
        if temp_path.exists():
            temp_path.unlink()


@router.post("/analyze", status_code=status.HTTP_202_ACCEPTED)
async def submit_incident_analysis(file: UploadFile = File(...)):
    if not is_allowed_extension(file.filename):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file extension. Only .log and .txt are allowed",
        )

    # Stream to temp file
    total_size = 0
    fd, tmp_path_str = tempfile.mkstemp(prefix="secureops_upload_")
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
            
    # Create DB entry for tracking
    db = SessionLocal()
    try:
        db_report = DBIncidentReport(
            status="pending",
            model_profile="foundation-sec-8b-reasoning:q4_k_m",
            summary="",
            risk_level="",
            recommendations="[]",
            raw_model_response="{}"
        )
        db.add(db_report)
        db.commit()
        db.refresh(db_report)
        job_id = str(db_report.id)
    finally:
        db.close()

    # Submit job
    try:
        await job_runner.submit_job(
            process_incident, 
            tmp_path_str, 
            file.filename, 
            job_id,
            job_id=job_id
        )
    except asyncio.QueueFull:
        os.remove(tmp_path_str)
        # Mark as failed in DB
        db = SessionLocal()
        try:
            r = db.query(DBIncidentReport).filter(DBIncidentReport.id == int(job_id)).first()
            if r:
                r.status = "queue_full"
                db.commit()
        finally:
            db.close()
            
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Job queue is full")

    return {"incident_id": job_id, "status": "pending", "message": "Incident analysis submitted"}


@router.get("/{incident_id}")
def get_incident_status(incident_id: str):
    # Check in memory job runner first
    job_status = job_runner.get_job_status(incident_id)
    
    # If job is found and running or pending
    if job_status["status"] in ["pending", "running"]:
        return {"incident_id": incident_id, "status": job_status["status"]}
        
    if job_status["status"] == "completed":
        return job_status["result"]
        
    # Check database
    db = SessionLocal()
    try:
        report = db.query(DBIncidentReport).filter(DBIncidentReport.id == int(incident_id)).first()
        if not report:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Incident not found")
            
        if report.status == "completed":
            return json.loads(report.raw_model_response)
            
        return {
            "incident_id": str(report.id),
            "status": report.status,
            "error": job_status.get("error") if job_status["status"] == "failed" else None
        }
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid incident ID format")
    finally:
        db.close()
