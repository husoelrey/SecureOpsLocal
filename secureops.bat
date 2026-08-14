@echo off
if exist "%~dp0.venv\Scripts\python.exe" (
    "%~dp0.venv\Scripts\python.exe" -m src.cli.main %*
) else (
    python -m src.cli.main %*
)
