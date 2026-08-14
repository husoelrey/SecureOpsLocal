"""SecureOps Local Command Line Interface."""

from typing import Any


def __getattr__(name: str) -> Any:
    if name == "app":
        from src.cli.main import app
        return app
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")


__all__ = ["app"]
