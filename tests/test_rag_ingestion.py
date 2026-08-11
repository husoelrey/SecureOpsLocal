import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from src.main import app
from src.rag.ingestion import extract_pdf, extract_text, parse_document

client = TestClient(app)

def test_extract_text_valid():
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", delete=False) as f:
        f.write("Hello World\n\nThis is a test.")
        temp_path = Path(f.name)
        
    try:
        content, metadata = extract_text(temp_path)
        assert content == "Hello World\nThis is a test."
        assert metadata["format"] == "text"
    finally:
        temp_path.unlink()

def test_extract_text_invalid_encoding():
    with tempfile.NamedTemporaryFile(mode="wb", delete=False) as f:
        f.write(b"\xff\xfe\x00\x00")  # Invalid UTF-8
        temp_path = Path(f.name)
        
    try:
        with pytest.raises(HTTPException) as exc_info:
            extract_text(temp_path)
        assert exc_info.value.status_code == 400
        assert "Invalid text encoding" in exc_info.value.detail
    finally:
        temp_path.unlink()

@patch("src.rag.ingestion.PdfReader")
def test_extract_pdf_valid(mock_pdf_reader):
    mock_instance = MagicMock()
    mock_page_1 = MagicMock()
    mock_page_1.extract_text.return_value = "Page 1 Content\nMore text."
    mock_page_2 = MagicMock()
    mock_page_2.extract_text.return_value = "Page 2 Content"
    mock_instance.pages = [mock_page_1, mock_page_2]
    mock_pdf_reader.return_value = mock_instance

    with tempfile.NamedTemporaryFile(mode="wb", suffix=".pdf", delete=False) as f:
        temp_path = Path(f.name)

    try:
        content, metadata = extract_pdf(temp_path)
        assert "--- Page 1 ---" in content
        assert "Page 1 Content" in content
        assert "More text." in content
        assert "--- Page 2 ---" in content
        assert "Page 2 Content" in content
        assert metadata["pages"] == 2
        assert metadata["format"] == "pdf"
    finally:
        temp_path.unlink()

@patch("src.rag.ingestion.PdfReader")
def test_extract_pdf_no_text(mock_pdf_reader):
    mock_instance = MagicMock()
    mock_page = MagicMock()
    mock_page.extract_text.return_value = "   \n "
    mock_instance.pages = [mock_page]
    mock_pdf_reader.return_value = mock_instance

    with tempfile.NamedTemporaryFile(mode="wb", suffix=".pdf", delete=False) as f:
        temp_path = Path(f.name)

    try:
        with pytest.raises(HTTPException) as exc_info:
            extract_pdf(temp_path)
        assert exc_info.value.status_code == 400
        assert "PDF contains no extractable text" in exc_info.value.detail
    finally:
        temp_path.unlink()

def test_api_upload_knowledge_invalid_extension():
    response = client.post(
        "/v1/knowledge/ingest",
        files={"file": ("test.jpg", b"dummy content")}
    )
    assert response.status_code == 400
    assert "Invalid file extension" in response.json()["detail"]

def test_api_upload_knowledge_archive_signature():
    # Test zip archive signature
    response = client.post(
        "/v1/knowledge/ingest",
        files={"file": ("test.txt", b"PK\x03\x04dummy archive")}
    )
    assert response.status_code == 400
    assert "Archives are not allowed" in response.json()["detail"]

def test_api_upload_knowledge_valid_text():
    response = client.post(
        "/v1/knowledge/ingest",
        files={"file": ("test.md", b"# Markdown doc\n\nSome text.")}
    )
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert data["size"] == len(b"# Markdown doc\n\nSome text.")
    assert "sha256" in data

def test_api_list_knowledge_sources():
    response = client.get("/v1/knowledge/sources")
    assert response.status_code == 200
    assert "sources" in response.json()
