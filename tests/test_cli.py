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
