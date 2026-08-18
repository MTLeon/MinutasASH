from __future__ import annotations

import copy
import json
from typing import Any, TypeVar

from pydantic import BaseModel, ValidationError

T = TypeVar("T", bound=BaseModel)


def validate_model_json[T: BaseModel](text: str, response_model: type[T]) -> T:
    """Validate model JSON, tolerating only unknown object keys.

    Providers sometimes add harmless metadata despite a strict schema. Unknown
    keys are removed by their precise Pydantic error paths; every other type,
    required-field and value constraint remains strict.
    """
    payload = json.loads(text)
    try:
        return response_model.model_validate(payload)
    except ValidationError as exc:
        extra_paths = [
            tuple(error["loc"]) for error in exc.errors() if error["type"] == "extra_forbidden"
        ]
        if not extra_paths:
            raise
        sanitized = copy.deepcopy(payload)
        removed = sum(_remove_path(sanitized, path) for path in extra_paths)
        if not removed:
            raise
        return response_model.model_validate(sanitized)


def _remove_path(payload: Any, path: tuple[Any, ...]) -> int:
    if not path:
        return 0
    current = payload
    for part in path[:-1]:
        if (
            isinstance(current, dict)
            and part in current
            or isinstance(current, list)
            and isinstance(part, int)
            and 0 <= part < len(current)
        ):
            current = current[part]
        else:
            return 0
    last = path[-1]
    if isinstance(current, dict) and last in current:
        del current[last]
        return 1
    return 0
