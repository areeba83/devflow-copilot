"""
Turns raw model text into a validated Pydantic object, or a structured
failure — never a crash. This is the "schema validation checks required
fields and types" + "reliability rules flag ... empty critical outputs"
step from the SRS workflow (Section 12.1, steps 7-8). Generic over any
artifact schema so Day 3's seven artifact types reuse the same logic as
Day 1's spec.
"""

import json
import re
from datetime import datetime, timezone
from typing import Optional, Type

from pydantic import BaseModel, ValidationError


def extract_json(raw_text: str) -> dict:
    """Models sometimes wrap JSON in markdown fences or add a stray
    sentence before/after it despite instructions. Try the whole string
    first, then fall back to the first {...} block."""
    try:
        return json.loads(raw_text)
    except json.JSONDecodeError:
        pass

    match = re.search(r"\{.*\}", raw_text, re.DOTALL)
    if not match:
        raise json.JSONDecodeError("No JSON object found in model output", raw_text, 0)
    return json.loads(match.group(0))


class GenericResult(BaseModel):
    """Generic envelope used for every artifact type. `content` holds the
    validated object as a plain dict (already schema-checked) rather than a
    typed field, so this class doesn't need to change per artifact type."""

    status: str  # "ok" | "invalid_json" | "schema_error" | "model_error"
    content: Optional[dict] = None
    raw_model_output: Optional[str] = None
    error_message: Optional[str] = None
    model_name: str
    prompt_version: str
    artifact_type: str
    generated_at: str


def build_generic_result(
    raw_text: str,
    schema_cls: Type[BaseModel],
    model_name: str,
    prompt_version: str,
    artifact_type: str,
) -> GenericResult:
    now = datetime.now(timezone.utc).isoformat()

    try:
        parsed = extract_json(raw_text)
    except json.JSONDecodeError as e:
        return GenericResult(
            status="invalid_json",
            raw_model_output=raw_text,
            error_message=f"Model output was not valid JSON: {e}",
            model_name=model_name,
            prompt_version=prompt_version,
            artifact_type=artifact_type,
            generated_at=now,
        )

    try:
        validated = schema_cls(**parsed)
    except ValidationError as e:
        return GenericResult(
            status="schema_error",
            raw_model_output=raw_text,
            error_message=f"JSON parsed but did not match the schema: {e}",
            model_name=model_name,
            prompt_version=prompt_version,
            artifact_type=artifact_type,
            generated_at=now,
        )

    return GenericResult(
        status="ok",
        content=validated.model_dump(),
        raw_model_output=raw_text,
        model_name=model_name,
        prompt_version=prompt_version,
        artifact_type=artifact_type,
        generated_at=now,
    )


# --- Backwards-compatible wrapper used by Day 1's spec endpoint ------------

from .schemas import GenerationResult, ProjectSpec  # noqa: E402


def build_result(raw_text: str, model_name: str, prompt_version: str) -> GenerationResult:
    generic = build_generic_result(raw_text, ProjectSpec, model_name, prompt_version, "project_spec")
    return GenerationResult(
        status=generic.status,
        spec=ProjectSpec(**generic.content) if generic.content else None,
        raw_model_output=generic.raw_model_output,
        error_message=generic.error_message,
        model_name=generic.model_name,
        prompt_version=generic.prompt_version,
        generated_at=generic.generated_at,
    )
