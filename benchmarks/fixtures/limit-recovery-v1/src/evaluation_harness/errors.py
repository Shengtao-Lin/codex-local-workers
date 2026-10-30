"""Stable domain errors safe to expose through the API."""

from __future__ import annotations

from typing import Any


class HarnessError(Exception):
    def __init__(
        self,
        code: str,
        message: str,
        *,
        retryable: bool = False,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.retryable = retryable
        self.details = details or {}


class ConflictError(HarnessError):
    def __init__(self, message: str, *, details: dict[str, Any] | None = None) -> None:
        super().__init__("conflict", message, details=details)


class NotFoundError(HarnessError):
    def __init__(self, resource: str) -> None:
        super().__init__("not_found", f"{resource} was not found")
