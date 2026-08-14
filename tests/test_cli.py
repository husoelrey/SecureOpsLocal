import tempfile
import uuid
from pathlib import Path
from typer.testing import CliRunner

from src.cli.main import app

runner = CliRunner()


def test_cli_version_command():
    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0
    assert "SecureOps Local" in result.stdout
    assert "v0.1.0" in result.stdout


def test_cli_version_flag():
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert "SecureOps Local" in result.stdout


def test_cli_knowledge_list():
    result = runner.invoke(app, ["knowledge", "list"])
    assert result.exit_code == 0
    # Either lists documents or shows empty banner
    assert "Knowledge Base" in result.stdout or "Indexed Knowledge Base Documents" in result.stdout


def test_cli_knowledge_add_markdown():
    uid = uuid.uuid4().hex
    with tempfile.TemporaryDirectory() as tmp_dir:
        test_file = Path(tmp_dir) / f"nist_guide_{uid}.md"
        test_file.write_text(
            f"# NIST Incident Response Guide {uid}\n\n"
            "## Section 1: Preparation\n"
            "Organizations should establish logging policies and incident handling capabilities.\n\n"
            "## Section 2: Detection and Analysis\n"
            "Monitor SSH logs for multiple failed attempts indicating brute force attacks.\n",
            encoding="utf-8"
        )

        result = runner.invoke(app, ["knowledge", "add", str(test_file)])
        assert result.exit_code == 0
        assert "Ingestion Complete" in result.stdout
        assert f"nist_guide_{uid}.md" in result.stdout


def test_cli_knowledge_add_duplicate():
    uid = uuid.uuid4().hex
    with tempfile.TemporaryDirectory() as tmp_dir:
        test_file = Path(tmp_dir) / f"unique_guide_{uid}.md"
        test_file.write_text(f"# Unique Document {uid}\nContent for duplicate test.", encoding="utf-8")

        # First add
        res1 = runner.invoke(app, ["knowledge", "add", str(test_file)])
        assert res1.exit_code == 0
        assert "Ingestion Complete" in res1.stdout

        # Duplicate add
        res2 = runner.invoke(app, ["knowledge", "add", str(test_file)])
        assert res2.exit_code == 1
        assert "Duplicate document" in res2.stdout


def test_cli_knowledge_add_invalid_extension():
    with tempfile.TemporaryDirectory() as tmp_dir:
        bad_file = Path(tmp_dir) / "test.exe"
        bad_file.write_bytes(b"binary content")

        result = runner.invoke(app, ["knowledge", "add", str(bad_file)])
        assert result.exit_code == 1
        assert "Validation error" in result.stdout or "Unsupported file extension" in result.stdout
