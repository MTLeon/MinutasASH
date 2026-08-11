from __future__ import annotations

import json
import queue
import threading
from collections.abc import Callable
from typing import Any, TypeVar, cast

import requests
from pydantic import BaseModel, ValidationError

from src.providers.base import ProcessingProviderError
from src.providers.structured_validation import validate_model_json

T = TypeVar("T", bound=BaseModel)


def post_json(
    url: str,
    *,
    headers: dict[str, str],
    payload: dict[str, Any],
    timeout: int,
    cancelled: Callable[[], bool] | None = None,
) -> dict[str, Any]:
    outcome: queue.Queue[tuple[str, object]] = queue.Queue(maxsize=1)

    def request_worker() -> None:
        try:
            outcome.put(
                ("response", requests.post(url, headers=headers, json=payload, timeout=timeout))
            )
        except BaseException as exc:
            outcome.put(("error", exc))

    worker = threading.Thread(target=request_worker, daemon=True)
    worker.start()
    while worker.is_alive():
        if cancelled and cancelled():
            raise InterruptedError("Proceso cancelado por el usuario.")
        worker.join(0.1)
    if cancelled and cancelled():
        raise InterruptedError("Proceso cancelado por el usuario.")

    kind, value = outcome.get()
    if kind == "error":
        if isinstance(value, requests.Timeout):
            raise ProcessingProviderError(
                "El servicio remoto excedio el tiempo de espera."
            ) from value
        if isinstance(value, requests.RequestException):
            raise ProcessingProviderError(
                f"No fue posible conectar con el servicio remoto: {value}"
            ) from value
        if isinstance(value, BaseException):
            raise value
        raise ProcessingProviderError("La solicitud remota termino de forma inesperada.")

    response = cast(Any, value)
    if not isinstance(response, requests.Response) and not hasattr(response, "status_code"):
        raise ProcessingProviderError("El servicio remoto devolvio una respuesta inesperada.")
    if response.status_code >= 400:
        detail = response.text[:1000]
        try:
            body = response.json()
            detail = str(body.get("error") or body.get("message") or body)[:1000]
        except ValueError:
            pass
        raise ProcessingProviderError(
            f"El servicio remoto respondio HTTP {response.status_code}: {detail}"
        )
    try:
        data = response.json()
    except ValueError as exc:
        raise ProcessingProviderError("El servicio remoto no devolvio JSON valido.") from exc
    if not isinstance(data, dict):
        raise ProcessingProviderError("El servicio remoto devolvio una estructura inesperada.")
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
        return validate_model_json(text, response_model)
    except ValidationError as exc:
        raise ProcessingProviderError(
            f"La respuesta remota no cumple la estructura requerida. Detalle: {exc}"
        ) from exc
    except json.JSONDecodeError as exc:
        raise ProcessingProviderError("La respuesta remota no contiene JSON valido.") from exc
