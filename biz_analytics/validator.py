"""
Input validation layer.

Wraps Pydantic model parsing with friendly error messages
so callers get a clear explanation of what went wrong.
"""

from __future__ import annotations

from typing import Any

from pydantic import ValidationError

from .models import AnalysisInput, PosterInput


class ValidationResult:
    """Holds either a valid model or a list of human-readable error messages."""

    def __init__(self, model=None, errors: list[str] | None = None):
        self.model = model
        self.errors = errors or []

    @property
    def is_valid(self) -> bool:
        return self.model is not None and not self.errors

    def __repr__(self) -> str:
        if self.is_valid:
            return f"<ValidationResult OK: {self.model}>"
        return f"<ValidationResult FAILED: {self.errors}>"


def _format_pydantic_errors(exc: ValidationError) -> list[str]:
    """Convert Pydantic v2 errors into readable strings."""
    messages = []
    for err in exc.errors():
        field = " → ".join(str(loc) for loc in err["loc"]) if err["loc"] else "input"
        messages.append(f"[{field}] {err['msg']}")
    return messages


def validate_analysis_input(raw: dict[str, Any]) -> ValidationResult:
    """
    Validate a raw dict as an AnalysisInput.

    Args:
        raw: dict with keys matching AnalysisInput fields.

    Returns:
        ValidationResult — check .is_valid before using .model
    """
    try:
        model = AnalysisInput(**raw)
        return ValidationResult(model=model)
    except ValidationError as exc:
        return ValidationResult(errors=_format_pydantic_errors(exc))
    except TypeError as exc:
        return ValidationResult(errors=[f"Unexpected input structure: {exc}"])


def validate_poster_input(raw: dict[str, Any]) -> ValidationResult:
    """
    Validate a raw dict as a PosterInput.

    Args:
        raw: dict with keys matching PosterInput fields.

    Returns:
        ValidationResult — check .is_valid before using .model
    """
    try:
        model = PosterInput(**raw)
        return ValidationResult(model=model)
    except ValidationError as exc:
        return ValidationResult(errors=_format_pydantic_errors(exc))
    except TypeError as exc:
        return ValidationResult(errors=[f"Unexpected input structure: {exc}"])


def assert_valid_analysis(raw: dict[str, Any]) -> AnalysisInput:
    """
    Validate and return an AnalysisInput, raising ValueError on failure.
    Convenience wrapper for scripts that prefer exceptions over result objects.
    """
    result = validate_analysis_input(raw)
    if not result.is_valid:
        raise ValueError("Validation failed:\n" + "\n".join(result.errors))
    return result.model


def assert_valid_poster(raw: dict[str, Any]) -> PosterInput:
    """
    Validate and return a PosterInput, raising ValueError on failure.
    """
    result = validate_poster_input(raw)
    if not result.is_valid:
        raise ValueError("Validation failed:\n" + "\n".join(result.errors))
    return result.model
