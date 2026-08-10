from __future__ import annotations

import json
from typing import Any, TypeVar

import requests
from pydantic import BaseModel, ValidationError

from src.providers.base import ProcessingProviderError

T = TypeVar("T", bound=BaseModel)


def post_json(
    url: str,
    *,
    headers: dict[str, str],
    payload: dict[str, Any],
    timeout: int,
) -> dict[str, Any]:
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=timeout)
    except requests.Timeout as exc:
        raise ProcessingProviderError("El servicio remoto excedió el tiempo de espera.") from exc
    except requests.RequestException as exc:
        raise ProcessingProviderError(f"No fue posible conectar con el servicio remoto: {exc}") from exc
    if response.status_code >= 400:
        detail = response.text[:1000]
        try:
            body = response.json()
            detail = str(body.get("error") or body.get("message") or body)[:1000]
        except ValueError:
            pass
        raise ProcessingProviderError(
            f"El servicio remoto respondió HTTP {response.status_code}: {detail}"
        )
    try:
        data = response.json()
    except ValueError as exc:
        raise ProcessingProviderError("El servicio remoto no devolvió JSON válido.") from exc
    if not isinstance(data, dict):
        raise ProcessingProviderError("El servicio remoto devolvió una estructura inesperada.")
    return data


def validate_json_text[T: BaseModel](text: str, response_model: type[T]) -> T:
    text = (text or "").strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    try:
        return response_model.model_validate_json(text)
    except ValidationError as exc:
        raise ProcessingProviderError(
            "La respuesta remota no cumple la estructura requerida. "
            f"Detalle: {exc}"
        ) from exc
    except json.JSONDecodeError as exc:
        raise ProcessingProviderError("La respuesta remota no contiene JSON válido.") from exc
