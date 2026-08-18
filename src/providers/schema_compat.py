from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel

from src.providers.base import ProcessingProviderError

_SCHEMA_ERROR_MARKERS = (
    "schema",
    "response_format",
    "output_config",
    "structured output",
    "structured_outputs",
    "json_schema",
    "grammar compilation timed out",
    "grammar compilation",
)


def is_schema_rejection(error: ProcessingProviderError) -> bool:
    message = str(error).casefold()
    return "http 400" in message and any(marker in message for marker in _SCHEMA_ERROR_MARKERS)


def compact_schema(value: Any) -> Any:
    """Reduce metadatos decorativos; Pydantic conserva la validación local completa."""
    if isinstance(value, list):
        return [compact_schema(item) for item in value]
    if not isinstance(value, dict):
        return value
    ignored = {"title", "description", "examples", "default", "$comment"}
    return {key: compact_schema(item) for key, item in value.items() if key not in ignored}


def json_fallback_prompt(user_prompt: str, response_model: type[BaseModel]) -> str:
    schema = compact_schema(response_model.model_json_schema())
    serialized = json.dumps(schema, ensure_ascii=False, separators=(",", ":"))
    return (
        f"{user_prompt}\n\n"
        "IMPORTANTE: responde únicamente con un objeto JSON válido, sin Markdown ni comentarios. "
        "La respuesta se validará localmente contra esta estructura:\n"
        f"{serialized}"
    )


def strict_object_schema(value: Any) -> Any:
    """Normaliza objetos para proveedores OpenAI con JSON Schema estricto."""
    if isinstance(value, list):
        return [strict_object_schema(item) for item in value]
    if not isinstance(value, dict):
        return value
    result = {key: strict_object_schema(item) for key, item in value.items()}
    properties = result.get("properties")
    if isinstance(properties, dict):
        result["additionalProperties"] = False
        result["required"] = list(properties)
    return result
