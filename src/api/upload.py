import os
import tempfile
from contextlib import contextmanager
from typing import Generator

from fastapi import APIRouter, File, HTTPException, UploadFile, status

router = APIRouter()

MAX_FILE_SIZE_BYTES = 5 * 1024 * 1024  # 5 MiB
ALLOWED_EXTENSIONS = {".log", ".txt"}


@contextmanager
def secure_temp_file() -> Generator[str, None, None]:
    fd, path = tempfile.mkstemp(prefix="secureops_upload_")
    os.close(fd)
    try:
        yield path
    finally:
        if os.path.exists(path):
            os.remove(path)


def is_allowed_extension(filename: str | None) -> bool:
    if not filename:
        return False
    _, ext = os.path.splitext(filename)
    return ext.lower() in ALLOWED_EXTENSIONS


def validate_chunk(chunk: bytes) -> None:
    if b"\x00" in chunk:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Binary content (null bytes) not allowed in log files",
        )
    # Check for valid utf-8 or ascii
    try:
        chunk.decode("utf-8")
    except UnicodeDecodeError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid text encoding, only valid UTF-8/ASCII is allowed",
        )


@router.post("/upload/ssh")
async def upload_ssh_log(file: UploadFile = File(...)) -> dict[str, str | int]:
    if not is_allowed_extension(file.filename):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file extension. Only .log and .txt are allowed",
        )

    # Validate Magic Signature (very basic for text, avoid archives like PK, gzip, etc)
    # But since it's streaming, we do it in chunks.
    
    total_size = 0
    with secure_temp_file() as tmp_path:
        with open(tmp_path, "wb") as f:
            while chunk := await file.read(8192):
                if total_size == 0:
                    # check signature on first chunk
                    if chunk.startswith(b"PK") or chunk.startswith(b"\x1f\x8b") or chunk.startswith(b"BZh"):  # noqa: E501
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Archives are not allowed",
                        )

                validate_chunk(chunk)
                total_size += len(chunk)

                if total_size > MAX_FILE_SIZE_BYTES:
                    raise HTTPException(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        detail="File exceeds 5 MiB limit",
                    )
                f.write(chunk)
                
        # Here we would typically parse the file using our parser and run the workflow,
        # but for this step we just return success after validation and cleanup.
        return {"message": "Upload successful and validated", "size": total_size}
