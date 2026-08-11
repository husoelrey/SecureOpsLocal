import hashlib
import os
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile, status

from src.api.upload import secure_temp_file
from src.rag.ingestion import parse_document
from src.schemas.rag import IngestionResponse

router = APIRouter()

MAX_KNOWLEDGE_SIZE_BYTES = 20 * 1024 * 1024  # 20 MiB
ALLOWED_KNOWLEDGE_EXTENSIONS = {".pdf", ".md", ".txt"}


def is_allowed_knowledge_extension(filename: str | None) -> bool:
    if not filename:
        return False
    _, ext = os.path.splitext(filename)
    return ext.lower() in ALLOWED_KNOWLEDGE_EXTENSIONS


@router.post("/upload/knowledge", response_model=IngestionResponse)
async def upload_knowledge_document(
    file: UploadFile = File(...),
) -> IngestionResponse:
    if not is_allowed_knowledge_extension(file.filename):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file extension. Only .pdf, .md, and .txt are allowed",
        )

    hasher = hashlib.sha256()
    total_size = 0

    with secure_temp_file() as tmp_path_str:
        tmp_path = Path(tmp_path_str)
        with open(tmp_path, "wb") as f:
            while chunk := await file.read(8192):
                if total_size == 0:
                    # Basic signature check for archives
                    if chunk.startswith(b"PK") or chunk.startswith(b"\x1f\x8b") or chunk.startswith(b"BZh"):  # noqa: E501
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Archives are not allowed",
                        )

                total_size += len(chunk)
                if total_size > MAX_KNOWLEDGE_SIZE_BYTES:
                    raise HTTPException(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        detail="File exceeds 20 MiB limit",
                    )
                
                f.write(chunk)
                hasher.update(chunk)
        
        file_hash = hasher.hexdigest()
        filename = file.filename or "unknown"
        
        # Parse and extract text
        doc = parse_document(tmp_path, filename, file_hash)
        
        # Here we will later call chunking and db persistence.
        # For now, we return success after ingestion validation.
        
        return IngestionResponse(
            message="Document successfully ingested and validated",
            sha256=file_hash,
            size=total_size,
        )
