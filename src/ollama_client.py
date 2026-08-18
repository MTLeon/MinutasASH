from __future__ import annotations

import contextlib
import json
from collections.abc import Callable
from threading import Event, Lock, Thread
from time import monotonic
from typing import Any, TypeVar

import requests
from pydantic import BaseModel, ValidationError

from src.providers.structured_validation import validate_model_json

T = TypeVar("T", bound=BaseModel)
TelemetryCallback = Callable[[dict[str, Any]], None]
CancelCallback = Callable[[], bool]


class LocalEngineError(RuntimeError):
    """Error del motor local de procesamiento."""


class LocalEngineTimeout(LocalEngineError):
    """La solicitud local no terminó dentro del límite adaptativo."""


class StructuredOutputError(LocalEngineError):
    """La respuesta llegó, pero no pudo validarse contra el esquema."""


class StructuredOutputTruncated(StructuredOutputError):
    """La generación terminó antes de cerrar el JSON estructurado."""


def _validation_indicates_truncation(
    content: str,
    error: ValidationError,
    metrics: dict[str, Any],
) -> bool:
    """Detecta respuestas JSON cortadas sin confundirlas con errores de campos."""

    done_reason = str(metrics.get("done_reason") or "").casefold()
    if done_reason in {"length", "max_tokens", "token_limit"}:
        return True

    messages = " ".join(
        f"{item.get('type', '')} {item.get('msg', '')}" for item in error.errors()
    ).casefold()
    truncation_markers = (
        "eof while parsing",
        "unterminated string",
        "unexpected end",
        "end of data",
        "expected `,` or `}`",
        "expected value at line",
    )
    if any(marker in messages for marker in truncation_markers):
        return True

    try:
        json.loads(content)
    except json.JSONDecodeError as exc:
        near_end = exc.pos >= max(0, len(content) - 16)
        return near_end or "unterminated" in exc.msg.casefold()
    return False


# Alias de compatibilidad con versiones anteriores.
OllamaError = LocalEngineError


class OllamaClient:
    def __init__(
        self,
        base_url: str,
        model: str,
        timeout_seconds: int = 900,
        temperature: float = 0.05,
        context_length: int = 6144,
        keep_alive: str = "2m",
        max_output_tokens: int = 1400,
        consolidation_output_tokens: int = 1800,
        recovery_output_tokens: int = 1000,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout_seconds = int(timeout_seconds)
        self.temperature = temperature
        self.context_length = int(context_length)
        self.keep_alive = keep_alive
        self.max_output_tokens = max(128, int(max_output_tokens))
        self.consolidation_output_tokens = max(128, int(consolidation_output_tokens))
        self.recovery_output_tokens = max(128, int(recovery_output_tokens))
        self._telemetry: TelemetryCallback = lambda _event: None
        self._cancelled: CancelCallback = lambda: False
        self._operation: dict[str, Any] = {}
        self._active_lock = Lock()
        self._active_response: requests.Response | None = None
        self._active_session: requests.Session | None = None

    def configure_runtime(
        self,
        *,
        telemetry: TelemetryCallback | None = None,
        cancelled: CancelCallback | None = None,
    ) -> None:
        self._telemetry = telemetry or (lambda _event: None)
        self._cancelled = cancelled or (lambda: False)

    def configure_request(
        self,
        *,
        timeout_seconds: int | None = None,
        context_length: int | None = None,
        operation: dict[str, Any] | None = None,
    ) -> None:
        if timeout_seconds is not None:
            self.timeout_seconds = max(30, int(timeout_seconds))
        if context_length is not None:
            self.context_length = max(2048, int(context_length))
        self._operation = dict(operation or {})

    def cancel_current_request(self) -> None:
        """Cierra la conexión activa para solicitar a Ollama detener la generación."""
        with self._active_lock:
            response = self._active_response
            session = self._active_session
        try:
            if response is not None:
                response.close()
        finally:
            if session is not None:
                session.close()

    def _emit(self, event_type: str, **payload: Any) -> None:
        event = {
            "type": event_type,
            "provider": "ollama_local",
            "model": self.model,
            "timestamp_monotonic": monotonic(),
            **self._operation,
            **payload,
        }
        # La telemetría es observacional: nunca debe abortar la transcripción o el análisis.
        with contextlib.suppress(Exception):
            self._telemetry(event)

    def list_models(self) -> list[str]:
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=15)
            response.raise_for_status()
        except requests.RequestException as exc:
            raise LocalEngineError(
                "El componente de procesamiento local no está disponible. "
                "Use la opción 'Reparar componentes' en Configuración."
            ) from exc
        return sorted(
            model.get("name") for model in response.json().get("models", []) if model.get("name")
        )

    def check_connection(self) -> None:
        installed = set(self.list_models())
        if self.model not in installed:
            raise LocalEngineError(
                "El componente de procesamiento requerido todavía no está preparado. "
                "Use la opción 'Reparar componentes' en Configuración."
            )

    def warmup(self) -> None:
        """Carga el modelo en memoria sin generar contenido visible."""
        payload = {
            "model": self.model,
            "prompt": "",
            "stream": False,
            "keep_alive": self.keep_alive,
            "options": {"num_predict": 1, "num_ctx": self.context_length},
        }
        try:
            response = requests.post(
                f"{self.base_url}/api/generate",
                json=payload,
                timeout=min(self.timeout_seconds, 180),
            )
            response.raise_for_status()
        except requests.RequestException:
            # El calentamiento es una optimización; no debe bloquear el uso.
            return

    def unload(self) -> None:
        """Solicita a Ollama liberar el modelo inmediatamente."""
        payload = {
            "model": self.model,
            "prompt": "",
            "stream": False,
            "keep_alive": 0,
            "options": {"num_predict": 1},
        }
        try:
            response = requests.post(
                f"{self.base_url}/api/generate",
                json=payload,
                timeout=30,
            )
            response.raise_for_status()
        except requests.RequestException:
            return

    def _output_limit(self) -> int:
        stage = str(self._operation.get("stage") or "")
        if stage == "consolidation":
            return self.consolidation_output_tokens
        if stage == "coverage_recovery":
            return self.recovery_output_tokens
        return self.max_output_tokens

    def _stream_chat(self, payload: dict[str, Any]) -> tuple[str, dict[str, Any]]:
        if self._cancelled():
            raise InterruptedError("Proceso cancelado por el usuario.")

        started = monotonic()
        self._emit(
            "request_started",
            timeout_seconds=self.timeout_seconds,
            context_length=self.context_length,
        )
        session = requests.Session()
        response: requests.Response | None = None
        stop_monitor = Event()
        timed_out = Event()

        def monitor_cancel() -> None:
            while not stop_monitor.wait(0.20):
                if self._cancelled():
                    self._emit("cancellation_requested")
                    self.cancel_current_request()
                    return
                if monotonic() - started >= self.timeout_seconds:
                    timed_out.set()
                    self._emit(
                        "request_timeout",
                        elapsed_seconds=monotonic() - started,
                        timeout_seconds=self.timeout_seconds,
                    )
                    self.cancel_current_request()
                    return

        monitor = Thread(target=monitor_cancel, daemon=True)
        try:
            response = session.post(
                f"{self.base_url}/api/chat",
                json=payload,
                stream=True,
                timeout=(15, self.timeout_seconds),
            )
            with self._active_lock:
                self._active_response = response
                self._active_session = session
            monitor.start()
            response.raise_for_status()

            content_parts: list[str] = []
            final_metrics: dict[str, Any] = {}
            chunks_received = 0
            generated_chars = 0
            for raw_line in response.iter_lines(decode_unicode=True):
                if self._cancelled():
                    raise InterruptedError("Proceso cancelado por el usuario.")
                if not raw_line:
                    continue
                try:
                    packet = json.loads(raw_line)
                except (TypeError, json.JSONDecodeError) as exc:
                    raise LocalEngineError(
                        "El motor local devolvió un fragmento de respuesta inesperado."
                    ) from exc
                if packet.get("error"):
                    raise LocalEngineError(
                        f"El motor local informó un error: {packet.get('error')}"
                    )
                message = packet.get("message") or {}
                fragment = message.get("content") or ""
                if fragment:
                    fragment_text = str(fragment)
                    content_parts.append(fragment_text)
                    generated_chars += len(fragment_text)
                chunks_received += 1
                self._emit(
                    "stream_activity",
                    chunks_received=chunks_received,
                    generated_chars=generated_chars,
                    elapsed_seconds=monotonic() - started,
                )
                if packet.get("done"):
                    final_metrics = {
                        key: packet.get(key)
                        for key in (
                            "total_duration",
                            "load_duration",
                            "prompt_eval_count",
                            "prompt_eval_duration",
                            "eval_count",
                            "eval_duration",
                            "done_reason",
                        )
                        if key in packet
                    }
                    break

            if self._cancelled():
                raise InterruptedError("Proceso cancelado por el usuario.")
            if timed_out.is_set():
                raise LocalEngineTimeout(
                    "El bloque actual excedió el tiempo adaptativo. "
                    "Se conservarán los bloques completados y se intentará dividirlo."
                )
            content = "".join(content_parts)
            if not content:
                raise LocalEngineError("El motor local no entregó contenido para validar.")
            self._emit(
                "request_finished",
                elapsed_seconds=monotonic() - started,
                generated_chars=len(content),
                **final_metrics,
            )
            return content, final_metrics
        except InterruptedError:
            self._emit("request_cancelled", elapsed_seconds=monotonic() - started)
            raise
        except (requests.ReadTimeout, requests.ConnectTimeout, requests.Timeout) as exc:
            self._emit(
                "request_timeout",
                elapsed_seconds=monotonic() - started,
                timeout_seconds=self.timeout_seconds,
            )
            raise LocalEngineTimeout(
                "El bloque actual excedió el tiempo adaptativo. "
                "Se conservarán los bloques completados y se intentará dividirlo."
            ) from exc
        except requests.RequestException as exc:
            if self._cancelled():
                raise InterruptedError("Proceso cancelado por el usuario.") from exc
            if timed_out.is_set():
                raise LocalEngineTimeout(
                    "El bloque actual excedió el tiempo adaptativo. "
                    "Se conservarán los bloques completados y se intentará dividirlo."
                ) from exc
            detail = ""
            error_response = getattr(exc, "response", None)
            if error_response is not None:
                try:
                    detail = f" Detalle: {error_response.json().get('error', '')}"
                except Exception:
                    detail = f" Detalle HTTP: {error_response.text[:500]}"
            self._emit(
                "request_error",
                elapsed_seconds=monotonic() - started,
                error=str(exc),
            )
            raise LocalEngineError(
                f"No fue posible completar el procesamiento local.{detail}"
            ) from exc
        finally:
            stop_monitor.set()
            try:
                if response is not None:
                    response.close()
            finally:
                session.close()
                with self._active_lock:
                    self._active_response = None
                    self._active_session = None

    def structured_chat(
        self,
        system_prompt: str,
        user_prompt: str,
        response_model: type[T],
    ) -> T:
        schema = response_model.model_json_schema()
        base_messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
        messages = list(base_messages)
        last_validation_error: ValidationError | None = None
        last_content = ""
        last_was_truncated = False
        base_limit = self._output_limit()
        output_limit = base_limit
        # El límite se amplía solo cuando el JSON efectivamente queda cortado.
        # Así no se penalizan las respuestas normales ni se reserva memoria de más.
        maximum_limit = min(4096, max(base_limit, self.context_length // 2))
        max_attempts = 3

        for attempt in range(max_attempts):
            payload = {
                "model": self.model,
                "messages": messages,
                "stream": True,
                "think": False,
                "format": schema,
                "options": {
                    "temperature": 0.0 if attempt else self.temperature,
                    "num_ctx": self.context_length,
                    "num_predict": output_limit,
                },
                "keep_alive": self.keep_alive,
            }
            self._emit(
                "validation_attempt",
                attempt=attempt + 1,
                output_token_limit=output_limit,
            )
            last_content, metrics = self._stream_chat(payload)

            try:
                return validate_model_json(last_content, response_model)
            except ValidationError as exc:
                last_validation_error = exc
                last_was_truncated = _validation_indicates_truncation(last_content, exc, metrics)
                self._emit(
                    "schema_validation_failed",
                    attempt=attempt + 1,
                    error_count=len(exc.errors()),
                    truncated=last_was_truncated,
                    output_token_limit=output_limit,
                )

                if last_was_truncated and output_limit < maximum_limit:
                    output_limit = min(
                        maximum_limit,
                        max(output_limit + 384, int(output_limit * 1.65)),
                    )
                    correction = (
                        "La respuesta anterior quedó cortada antes de cerrar el JSON. "
                        "Responde nuevamente desde cero, conserva todos los puntos, "
                        "usa descripciones más concisas y entrega exclusivamente un "
                        "JSON completo y válido."
                    )
                else:
                    correction = (
                        "La respuesta anterior no respetó el esquema JSON. "
                        "Vuelve a responder desde cero y entrega exclusivamente "
                        "un JSON válido que cumpla exactamente el esquema solicitado."
                    )
                messages = [
                    base_messages[0],
                    {
                        "role": "user",
                        "content": user_prompt + "\n\n" + correction,
                    },
                ]

        detail = str(last_validation_error or "Error de validación no especificado")
        if last_was_truncated:
            raise StructuredOutputTruncated(
                "La respuesta estructurada quedó incompleta aun después de ampliar "
                "el límite de salida. El bloque debe dividirse automáticamente para "
                "continuar sin perder el avance.\n"
                f"Último fragmento recibido:\n{last_content[-800:]}\n\n"
                f"Error de validación:\n{detail}"
            )
        raise StructuredOutputError(
            "El resultado no cumplió la estructura requerida después de tres intentos.\n"
            f"Última respuesta:\n{last_content[:1200]}\n\n"
            f"Error de validación:\n{detail}"
        )
