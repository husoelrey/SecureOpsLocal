from fastapi.testclient import TestClient
from src.main import app

client = TestClient(app)

def test_upload_valid_file() -> None:
    content = b"Aug 10 14:12:05 server sshd[123]: Accepted password for admin from 192.168.1.100 port 55432 ssh2\n"  # noqa: E501
    response = client.post(
        "/api/upload/ssh",
        files={"file": ("test.log", content, "text/plain")},
    )
    assert response.status_code == 200
    assert response.json()["size"] == len(content)

def test_upload_invalid_extension() -> None:
    content = b"Some content"
    response = client.post(
        "/api/upload/ssh",
        files={"file": ("test.exe", content, "application/octet-stream")},
    )
    assert response.status_code == 400
    assert "extension" in response.json()["detail"]

def test_upload_null_bytes() -> None:
    content = b"Aug 10 14:12:05 server sshd[123]: Accepted \x00 password"
    response = client.post(
        "/api/upload/ssh",
        files={"file": ("test.log", content, "text/plain")},
    )
    assert response.status_code == 400
    assert "null bytes" in response.json()["detail"]

def test_upload_invalid_encoding() -> None:
    content = b"Aug 10 14:12:05 server sshd[123]: \xff\xfe"
    response = client.post(
        "/api/upload/ssh",
        files={"file": ("test.log", content, "text/plain")},
    )
    assert response.status_code == 400
    assert "encoding" in response.json()["detail"]

def test_upload_archive_magic_bytes() -> None:
    content = b"PK\x03\x04some archive data"
    response = client.post(
        "/api/upload/ssh",
        files={"file": ("test.log", content, "text/plain")},
    )
    assert response.status_code == 400
    assert "Archives" in response.json()["detail"]
