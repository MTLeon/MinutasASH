"""Ejecución por bloques con recuperación, división automática y consolidación jerárquica."""

from __future__ import annotations

import contextlib
import hashlib
import json
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from pathlib import Path
from time import monotonic, sleep
from typing import Any

from src.minute_generator import analyze_chunks, consolidate_minute
from src.models import ChunkAnalysis, MeetingItem, MinuteAnalysis
from src.ollama_client import LocalEngineError, LocalEngineTimeout, StructuredOutputTruncated
from src.processing_checkpoint import (
    ProcessingCheckpoint,
    ProcessingCheckpointStore,
    make_initial_checkpoint,
)
from src.processing_runtime import (
    ProcessingPlan,
    adaptive_timeout_seconds,
    estimate_eta_seconds,
    get_resource_snapshot,
    group_serialized_payloads,
    split_text_chunk,
    stable_processing_key,
)
from src.providers.base import RemoteRateLimitError

LogCallback = Callable[[str], None]
ProgressCallback = Callable[[int, str], None]
TelemetryCallback = Callable[[dict[str, Any]], None]
CancelCallback = Callable[[], bool]
ClientFactory = Callable[[], Any]


class _TransientCheckpointStore:
    """Conserva la interfaz del store cuando el usuario desactiva checkpoints."""

    def load(self, _key: str) -> None:
        return None

    def save(self, _checkpoint: ProcessingCheckpoint) -> Path:
        return Path()

    def delete(self, _key: str) -> None:
        return None

    def mark_completed(self, _checkpoint: ProcessingCheckpoint) -> None:
        return None

    def prune(self, _retention_days: int = 14) -> int:
        return 0


@dataclass
class ResilientPipelineResult:
    analysis: MinuteAnalysis
    checkpoint_key: str
    resumed: bool
    resumed_blocks: int
    initial_chunk_count: int
    final_chunk_count: int
    split_count: int
    retry_count: int
    chunk_durations: list[float] = field(default_factory=list)
    deterministic_consolidations: int = 0
    consolidation_levels: int = 0
    parallel_workers: int = 1
    parallel_completed_blocks: int = 0

    def diagnostics(self) -> dict[str, Any]:
        return {
            "checkpoint_key": self.checkpoint_key,
            "resumed": self.resumed,
            "resumed_blocks": self.resumed_blocks,
            "initial_chunk_count": self.initial_chunk_count,
            "final_chunk_count": self.final_chunk_count,
            "split_count": self.split_count,
            "retry_count": self.retry_count,
            "chunk_durations_seconds": self.chunk_durations,
            "deterministic_consolidations": self.deterministic_consolidations,
            "consolidation_levels": self.consolidation_levels,
            "parallel_workers": self.parallel_workers,
            "parallel_completed_blocks": self.parallel_completed_blocks,
        }


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _configure_runtime(
    client: Any,
    telemetry: TelemetryCallback,
    cancelled: CancelCallback,
) -> None:
    method = getattr(client, "configure_runtime", None)
    if callable(method):
        method(telemetry=telemetry, cancelled=cancelled)


def _configure_request(
    client: Any,
    *,
    timeout_seconds: int,
    context_length: int,
    operation: dict[str, Any],
) -> None:
    method = getattr(client, "configure_request", None)
    if callable(method):
        method(
            timeout_seconds=timeout_seconds,
            context_length=context_length,
            operation=operation,
        )


def cancel_provider_request(client: Any) -> None:
    method = getattr(client, "cancel_current_request", None)
    if callable(method):
        method()


def _work_id(parent_id: str, index: int, depth: int) -> str:
    return f"{parent_id}.{depth}.{index}"


def _chunk_to_minute(chunk: ChunkAnalysis) -> MinuteAnalysis:
    summary = "\n".join(point for point in chunk.summary_points if point).strip()
    return MinuteAnalysis(
        objective=chunk.objective_hint,
        executive_summary=summary,
        items=[item.model_copy(deep=True) for item in chunk.items],
        next_meeting=chunk.next_meeting.model_copy(deep=True) if chunk.next_meeting else None,
        warnings=[],
    )


def _deterministic_merge(analyses: list[MinuteAnalysis]) -> MinuteAnalysis:
    objective = next((item.objective for item in analyses if item.objective), None)
    summaries = [
        item.executive_summary.strip() for item in analyses if item.executive_summary.strip()
    ]
    items: list[MeetingItem] = []
    warnings: list[str] = []
    next_meeting = None
    for analysis in analyses:
        items.extend(item.model_copy(deep=True) for item in analysis.items)
        warnings.extend(analysis.warnings)
        if next_meeting is None and analysis.next_meeting is not None:
            next_meeting = analysis.next_meeting.model_copy(deep=True)
    warnings.append(
        "Una etapa de consolidación se completó de forma determinista para no perder "
        "los bloques ya procesados. Revise posibles duplicados."
    )
    return MinuteAnalysis(
        objective=objective,
        executive_summary="\n".join(dict.fromkeys(summaries)),
        items=items,
        next_meeting=next_meeting,
        warnings=list(dict.fromkeys(warnings)),
    )


def _emit(
    telemetry: TelemetryCallback,
    event_type: str,
    **payload: Any,
) -> None:
    # La telemetría es opcional: un observador defectuoso no puede perder trabajo del usuario.
    with contextlib.suppress(Exception):
        telemetry({"type": event_type, **payload})


def _checkpoint_matches(
    checkpoint: ProcessingCheckpoint,
    *,
    source_sha256: str,
    provider_id: str,
    model: str,
    profile_id: str,
) -> bool:
    return (
        checkpoint.source_sha256 == source_sha256
        and checkpoint.provider_id == provider_id
        and checkpoint.model == model
        and checkpoint.profile_id == profile_id
    )


def _wait_cancelably(seconds: float, cancelled: CancelCallback) -> None:
    deadline = monotonic() + max(0.0, seconds)
    while monotonic() < deadline:
        if cancelled():
            raise InterruptedError("Proceso cancelado por el usuario.")
        sleep(min(0.1, max(0.0, deadline - monotonic())))


def _analyze_remote_work_item(
    client_factory: ClientFactory,
    item: dict[str, Any],
    item_index: int,
    total_items: int,
    metadata: dict[str, Any],
    config: dict[str, Any],
    plan: ProcessingPlan,
    knowledge_context: str,
    telemetry: TelemetryCallback,
    cancelled: CancelCallback,
) -> tuple[str, ChunkAnalysis, float]:
    if cancelled():
        raise InterruptedError("Proceso cancelado por el usuario.")
    client = client_factory()
    _configure_runtime(client, telemetry, cancelled)
    text = str(item["text"])
    chunk_id = str(item["id"])
    timeout = adaptive_timeout_seconds(
        plan.effective_profile,
        len(text),
        config,
        snapshot=get_resource_snapshot(),
    )
    _configure_request(
        client,
        timeout_seconds=timeout,
        context_length=plan.effective_profile.context_length,
        operation={
            "stage": "chunk_analysis",
            "block_id": chunk_id,
            "block_index": item_index,
            "total_blocks": total_items,
            "attempt": 1,
            "parallel": True,
        },
    )
    started = monotonic()
    result = analyze_chunks(
        client,
        [text],
        metadata.get("meeting_date"),
        knowledge_context=knowledge_context,
    )[0]
    return chunk_id, result, monotonic() - started


def _prime_remote_chunks(
    client_factory: ClientFactory | None,
    checkpoint: ProcessingCheckpoint,
    store: ProcessingCheckpointStore | _TransientCheckpointStore,
    metadata: dict[str, Any],
    config: dict[str, Any],
    plan: ProcessingPlan,
    knowledge_context: str,
    *,
    log: LogCallback,
    progress: ProgressCallback,
    telemetry: TelemetryCallback,
    cancelled: CancelCallback,
) -> tuple[int, int]:
    pending = [
        (index, item)
        for index, item in enumerate(checkpoint.work_items, start=1)
        if str(item["id"]) not in checkpoint.completed
    ]
    requested = max(1, min(int(config.get("remote_parallel_requests", 2)), 4))
    workers = min(requested, len(pending))
    if client_factory is None or workers < 2:
        return 0, 1

    log(f"Análisis remoto paralelo: hasta {workers} solicitudes simultáneas.")
    _emit(
        telemetry,
        "remote_parallel_started",
        workers=workers,
        pending_blocks=len(pending),
    )
    completed_now = 0
    was_cancelled = False
    with ThreadPoolExecutor(max_workers=workers, thread_name_prefix="minutas-remote") as executor:
        futures = {
            executor.submit(
                _analyze_remote_work_item,
                client_factory,
                item,
                index,
                len(checkpoint.work_items),
                metadata,
                config,
                plan,
                knowledge_context,
                telemetry,
                cancelled,
            ): str(item["id"])
            for index, item in pending
        }
        for future in as_completed(futures):
            chunk_id = futures[future]
            try:
                completed_id, result, duration = future.result()
            except InterruptedError:
                was_cancelled = True
                continue
            except Exception as exc:
                log(
                    f"El bloque {chunk_id} no terminó en paralelo; se recuperará "
                    f"con el flujo secuencial ({exc})."
                )
                _emit(
                    telemetry,
                    "remote_parallel_fallback",
                    block_id=chunk_id,
                    error_type=type(exc).__name__,
                )
                continue

            checkpoint.completed[completed_id] = result.model_dump()
            checkpoint.durations[completed_id] = duration
            checkpoint.status = "in_progress"
            store.save(checkpoint)
            completed_now += 1
            completed_total = len(checkpoint.completed)
            value = 25 + int(43 * completed_total / max(len(checkpoint.work_items), 1))
            progress(
                value,
                f"Bloque remoto {completed_total} de {len(checkpoint.work_items)} guardado",
            )
            _emit(
                telemetry,
                "chunk_completed",
                stage="chunk_analysis",
                percent=value,
                block_id=completed_id,
                completed_blocks=completed_total,
                total_blocks=len(checkpoint.work_items),
                duration_seconds=duration,
                parallel=True,
            )

    if was_cancelled or cancelled():
        checkpoint.status = "paused"
        store.save(checkpoint)
        raise InterruptedError(
            "Proceso cancelado. Los bloques remotos completados quedaron guardados."
        )
    _emit(
        telemetry,
        "remote_parallel_completed",
        workers=workers,
        completed_blocks=completed_now,
        fallback_blocks=max(len(pending) - completed_now, 0),
    )
    return completed_now, workers


def _process_chunks(
    client: Any,
    checkpoint: ProcessingCheckpoint,
    store: ProcessingCheckpointStore | _TransientCheckpointStore,
    metadata: dict[str, Any],
    config: dict[str, Any],
    plan: ProcessingPlan,
    knowledge_context: str,
    *,
    resumed_blocks_at_start: int | None = None,
    log: LogCallback,
    progress: ProgressCallback,
    telemetry: TelemetryCallback,
    cancelled: CancelCallback,
) -> tuple[list[ChunkAnalysis], int, int, list[float]]:
    profile = plan.effective_profile
    completed = checkpoint.completed_analyses()
    resumed_blocks = len(completed) if resumed_blocks_at_start is None else resumed_blocks_at_start
    retry_total = sum(checkpoint.retries.values())
    index = 0
    pipeline_started = monotonic()

    if resumed_blocks:
        log(f"Se reanudará el procesamiento: {resumed_blocks} bloque(s) ya estaban completos.")

    try:
        while index < len(checkpoint.work_items):
            if cancelled():
                checkpoint.status = "paused"
                store.save(checkpoint)
                raise InterruptedError(
                    "Proceso cancelado. Los bloques completados quedaron guardados para continuar después."
                )

            item = checkpoint.work_items[index]
            chunk_id = str(item["id"])
            text = str(item["text"])
            if chunk_id in completed:
                index += 1
                completed_count = sum(
                    1 for work in checkpoint.work_items if str(work["id"]) in completed
                )
                value = 25 + int(43 * completed_count / max(len(checkpoint.work_items), 1))
                progress(
                    value, f"Reutilizando bloque {completed_count} de {len(checkpoint.work_items)}"
                )
                continue

            attempt = int(checkpoint.retries.get(chunk_id, 0))
            snapshot = get_resource_snapshot()
            timeout = adaptive_timeout_seconds(
                profile,
                len(text),
                config,
                attempt=attempt,
                snapshot=snapshot,
            )
            operation = {
                "stage": "chunk_analysis",
                "block_id": chunk_id,
                "block_index": index + 1,
                "total_blocks": len(checkpoint.work_items),
                "attempt": attempt + 1,
            }
            _configure_request(
                client,
                timeout_seconds=timeout,
                context_length=profile.context_length,
                operation=operation,
            )
            completed_count = sum(
                1 for work in checkpoint.work_items if str(work["id"]) in completed
            )
            value = 25 + int(43 * completed_count / max(len(checkpoint.work_items), 1))
            progress(value, f"Procesando bloque {index + 1} de {len(checkpoint.work_items)}")
            durations = list(checkpoint.durations.values())
            remaining = max(len(checkpoint.work_items) - completed_count, 0)
            eta = estimate_eta_seconds(durations, remaining)
            _emit(
                telemetry,
                "pipeline_progress",
                stage="chunk_analysis",
                percent=value,
                block_index=index + 1,
                total_blocks=len(checkpoint.work_items),
                completed_blocks=completed_count,
                timeout_seconds=timeout,
                elapsed_seconds=monotonic() - pipeline_started,
                eta_seconds=eta,
                memory_percent=snapshot.memory_percent,
                available_memory_bytes=snapshot.available_memory_bytes,
            )
            log(
                f"Bloque {index + 1}/{len(checkpoint.work_items)} · "
                f"{len(text)} caracteres · espera máxima adaptativa {timeout} s."
            )

            started = monotonic()
            try:
                result = analyze_chunks(
                    client,
                    [text],
                    metadata.get("meeting_date"),
                    knowledge_context=knowledge_context,
                )[0]
            except RemoteRateLimitError as rate_error:
                duration = monotonic() - started
                checkpoint.retries[chunk_id] = attempt + 1
                retry_total += 1
                max_rate_retries = int(config.get("remote_rate_limit_retries", 3))
                if attempt < max_rate_retries:
                    maximum_wait = float(config.get("remote_retry_max_seconds", 120))
                    suggested = rate_error.retry_after_seconds
                    wait_seconds = min(
                        maximum_wait,
                        suggested if suggested is not None else 2.0 * (2**attempt),
                    )
                    checkpoint.status = "rate_limited"
                    store.save(checkpoint)
                    log(
                        f"El proveedor limitó temporalmente el bloque {chunk_id}; "
                        f"se reintentará en {wait_seconds:.1f} s."
                    )
                    _emit(
                        telemetry,
                        "remote_rate_limited",
                        block_id=chunk_id,
                        attempt=attempt + 1,
                        wait_seconds=wait_seconds,
                        duration_seconds=duration,
                    )
                    _wait_cancelably(wait_seconds, cancelled)
                    continue
                checkpoint.status = "rate_limited"
                store.save(checkpoint)
                raise
            except LocalEngineTimeout as timeout_error:
                duration = monotonic() - started
                checkpoint.retries[chunk_id] = attempt + 1
                retry_total += 1
                can_split = (
                    bool(config.get("processing_split_on_timeout", True))
                    and len(text) > profile.min_chunk_chars * 1.35
                )
                if can_split:
                    target = max(profile.min_chunk_chars, int(len(text) * 0.55))
                    parts = split_text_chunk(
                        text,
                        target,
                        overlap_lines=profile.overlap_lines,
                    )
                    if len(parts) > 1:
                        depth = int(item.get("depth") or 0) + 1
                        children = [
                            {
                                "id": _work_id(chunk_id, child_index, depth),
                                "text": part,
                                "depth": depth,
                                "parent_id": chunk_id,
                            }
                            for child_index, part in enumerate(parts, start=1)
                        ]
                        checkpoint.work_items[index : index + 1] = children
                        checkpoint.split_count += 1
                        checkpoint.status = "in_progress"
                        store.save(checkpoint)
                        log(
                            f"El bloque {chunk_id} excedió el tiempo y se dividió "
                            f"automáticamente en {len(children)} partes más pequeñas."
                        )
                        _emit(
                            telemetry,
                            "chunk_split",
                            block_id=chunk_id,
                            child_count=len(children),
                            duration_seconds=duration,
                            total_blocks=len(checkpoint.work_items),
                        )
                        continue
                if attempt < profile.max_retries:
                    store.save(checkpoint)
                    log(
                        f"El bloque {chunk_id} se reintentará con más tiempo "
                        f"({attempt + 1}/{profile.max_retries})."
                    )
                    _emit(
                        telemetry,
                        "chunk_retry",
                        block_id=chunk_id,
                        attempt=attempt + 1,
                        duration_seconds=duration,
                    )
                    continue
                checkpoint.status = "timeout"
                store.save(checkpoint)
                raise LocalEngineTimeout(
                    "No fue posible completar uno de los bloques mínimos. "
                    "El avance quedó guardado; cierre aplicaciones exigentes o use el perfil Rápido y continúe."
                ) from timeout_error
            except StructuredOutputTruncated as exc:
                duration = monotonic() - started
                checkpoint.retries[chunk_id] = attempt + 1
                retry_total += 1
                can_split = (
                    bool(config.get("processing_split_on_structure_error", True))
                    and len(text) > profile.min_chunk_chars * 1.20
                )
                if can_split:
                    target = max(profile.min_chunk_chars, int(len(text) * 0.50))
                    parts = split_text_chunk(
                        text,
                        target,
                        overlap_lines=profile.overlap_lines,
                    )
                    if len(parts) > 1:
                        depth = int(item.get("depth") or 0) + 1
                        children = [
                            {
                                "id": _work_id(chunk_id, child_index, depth),
                                "text": part,
                                "depth": depth,
                                "parent_id": chunk_id,
                            }
                            for child_index, part in enumerate(parts, start=1)
                        ]
                        checkpoint.work_items[index : index + 1] = children
                        checkpoint.split_count += 1
                        checkpoint.status = "in_progress"
                        store.save(checkpoint)
                        log(
                            f"La respuesta del bloque {chunk_id} quedó incompleta y "
                            f"se dividió automáticamente en {len(children)} partes. "
                            "Los bloques anteriores permanecen guardados."
                        )
                        _emit(
                            telemetry,
                            "chunk_split",
                            block_id=chunk_id,
                            child_count=len(children),
                            duration_seconds=duration,
                            total_blocks=len(checkpoint.work_items),
                            reason="structured_output_truncated",
                        )
                        continue
                if attempt < profile.max_retries:
                    store.save(checkpoint)
                    log(
                        f"El bloque {chunk_id} devolvió un JSON incompleto y se "
                        f"reintentará ({attempt + 1}/{profile.max_retries})."
                    )
                    _emit(
                        telemetry,
                        "chunk_retry",
                        block_id=chunk_id,
                        attempt=attempt + 1,
                        duration_seconds=duration,
                        reason="structured_output_truncated",
                    )
                    continue
                checkpoint.status = "error"
                store.save(checkpoint)
                raise LocalEngineError(
                    "Uno de los bloques mínimos siguió produciendo una respuesta "
                    "incompleta. El avance quedó guardado para continuar después."
                ) from exc
            except InterruptedError:
                checkpoint.status = "paused"
                store.save(checkpoint)
                raise
            except Exception:
                checkpoint.status = "error"
                store.save(checkpoint)
                raise

            duration = monotonic() - started
            completed[chunk_id] = result
            checkpoint.completed[chunk_id] = result.model_dump()
            checkpoint.durations[chunk_id] = duration
            checkpoint.status = "in_progress"
            store.save(checkpoint)
            index += 1

            completed_count = sum(
                1 for work in checkpoint.work_items if str(work["id"]) in completed
            )
            value = 25 + int(43 * completed_count / max(len(checkpoint.work_items), 1))
            durations = list(checkpoint.durations.values())
            remaining = max(len(checkpoint.work_items) - completed_count, 0)
            eta = estimate_eta_seconds(durations, remaining)
            progress(value, f"Bloque {completed_count} de {len(checkpoint.work_items)} guardado")
            _emit(
                telemetry,
                "chunk_completed",
                stage="chunk_analysis",
                percent=value,
                block_id=chunk_id,
                completed_blocks=completed_count,
                total_blocks=len(checkpoint.work_items),
                duration_seconds=duration,
                eta_seconds=eta,
            )
            log(f"Bloque {completed_count}/{len(checkpoint.work_items)} completado y guardado.")

        ordered: list[ChunkAnalysis] = []
        for item in checkpoint.work_items:
            chunk_id = str(item["id"])
            analysis = completed.get(chunk_id)
            if analysis is None:
                try:
                    analysis = ChunkAnalysis.model_validate(checkpoint.completed[chunk_id])
                except Exception as exc:
                    raise RuntimeError(
                        f"El checkpoint no contiene el bloque {chunk_id} completo."
                    ) from exc
            ordered.append(analysis)
        return ordered, resumed_blocks, retry_total, list(checkpoint.durations.values())
    except Exception:
        store.save(checkpoint)
        raise


def _hierarchical_consolidation(
    client: Any,
    chunk_analyses: list[ChunkAnalysis],
    metadata: dict[str, Any],
    config: dict[str, Any],
    plan: ProcessingPlan,
    knowledge_context: str,
    *,
    log: LogCallback,
    progress: ProgressCallback,
    telemetry: TelemetryCallback,
    cancelled: CancelCallback,
) -> tuple[MinuteAnalysis, int, int]:
    profile = plan.effective_profile
    current = [_chunk_to_minute(item) for item in chunk_analyses]
    deterministic = 0
    level = 0
    if not current:
        return MinuteAnalysis(), deterministic, level

    while len(current) > 1:
        if cancelled():
            raise InterruptedError(
                "Proceso cancelado. Los bloques analizados quedaron guardados para continuar después."
            )
        level += 1
        groups = group_serialized_payloads(
            current,
            profile.consolidation_batch_chars,
        )
        if len(groups) == len(current) and len(current) > 1:
            groups = [current[index : index + 2] for index in range(0, len(current), 2)]
        next_level: list[MinuteAnalysis] = []
        log(f"Consolidación jerárquica nivel {level}: {len(groups)} grupo(s).")
        for group_index, group in enumerate(groups, start=1):
            if cancelled():
                raise InterruptedError(
                    "Proceso cancelado. Los bloques analizados quedaron guardados para continuar después."
                )
            if len(group) == 1:
                next_level.append(group[0])
                continue
            serialized_chars = len(
                json.dumps([item.model_dump() for item in group], ensure_ascii=False)
            )
            timeout = adaptive_timeout_seconds(
                profile,
                serialized_chars,
                config,
                attempt=0,
                snapshot=get_resource_snapshot(),
            )
            _configure_request(
                client,
                timeout_seconds=timeout,
                context_length=profile.context_length,
                operation={
                    "stage": "consolidation",
                    "consolidation_level": level,
                    "group_index": group_index,
                    "total_groups": len(groups),
                },
            )
            base_percent = 70 + min(12, int(12 * group_index / max(len(groups), 1)))
            progress(
                base_percent,
                f"Consolidando nivel {level} · grupo {group_index} de {len(groups)}",
            )
            _emit(
                telemetry,
                "pipeline_progress",
                stage="consolidation",
                percent=base_percent,
                consolidation_level=level,
                group_index=group_index,
                total_groups=len(groups),
                timeout_seconds=timeout,
            )
            try:
                result = consolidate_minute(
                    client,
                    group,
                    metadata,
                    knowledge_context=knowledge_context,
                )
            except (LocalEngineTimeout, LocalEngineError) as exc:
                deterministic += 1
                result = _deterministic_merge(group)
                log(
                    "La consolidación del grupo no respondió a tiempo; se aplicó una "
                    f"unión determinista sin perder puntos ({exc})."
                )
                _emit(
                    telemetry,
                    "deterministic_consolidation",
                    consolidation_level=level,
                    group_index=group_index,
                    reason=str(exc),
                )
            next_level.append(result)
        current = next_level
    return current[0], deterministic, level


def analyze_resilient_chunks(
    client: Any,
    chunks: list[str],
    metadata: dict[str, Any],
    config: dict[str, Any],
    plan: ProcessingPlan,
    source_path: Path,
    provider_id: str,
    model: str,
    knowledge_context: str = "",
    client_factory: ClientFactory | None = None,
    *,
    log: LogCallback | None = None,
    progress: ProgressCallback | None = None,
    telemetry: TelemetryCallback | None = None,
    cancelled: CancelCallback | None = None,
) -> ResilientPipelineResult:
    log = log or (lambda _message: None)
    progress = progress or (lambda _value, _message: None)
    telemetry = telemetry or (lambda _event: None)
    cancelled = cancelled or (lambda: False)
    _configure_runtime(client, telemetry, cancelled)

    source_sha = sha256_file(source_path)
    # En perfil automático, la clave debe permanecer estable aunque la memoria
    # disponible cambie entre una ejecución y la siguiente y el plan efectivo
    # pase de rápido a equilibrado (o viceversa). Así se conservan los bloques
    # ya completados.
    checkpoint_profile_id = (
        "auto" if plan.requested_profile == "auto" else plan.effective_profile.profile_id
    )
    key = stable_processing_key(
        source_sha,
        metadata,
        provider_id,
        model,
        checkpoint_profile_id,
    )
    checkpoint_enabled = bool(config.get("processing_checkpoint_enabled", True))
    store = ProcessingCheckpointStore() if checkpoint_enabled else _TransientCheckpointStore()
    store.prune(int(config.get("processing_checkpoint_retention_days", 14)))
    checkpoint = store.load(key) if checkpoint_enabled else None
    resumed = False
    if checkpoint and _checkpoint_matches(
        checkpoint,
        source_sha256=source_sha,
        provider_id=provider_id,
        model=model,
        profile_id=checkpoint_profile_id,
    ):
        resumed = bool(checkpoint.completed)
    else:
        checkpoint = make_initial_checkpoint(
            key=key,
            source_path=str(source_path),
            source_sha256=source_sha,
            provider_id=provider_id,
            model=model,
            profile_id=checkpoint_profile_id,
            chunks=chunks,
        )
        store.save(checkpoint)

    initial_count = len(chunks)
    resumed_blocks_at_start = len(checkpoint.completed) if resumed else 0
    parallel_completed, parallel_workers = _prime_remote_chunks(
        client_factory,
        checkpoint,
        store,
        metadata,
        config,
        plan,
        knowledge_context,
        log=log,
        progress=progress,
        telemetry=telemetry,
        cancelled=cancelled,
    )
    chunk_analyses, resumed_blocks, retries, durations = _process_chunks(
        client,
        checkpoint,
        store,
        metadata,
        config,
        plan,
        knowledge_context,
        resumed_blocks_at_start=resumed_blocks_at_start,
        log=log,
        progress=progress,
        telemetry=telemetry,
        cancelled=cancelled,
    )
    analysis, deterministic, levels = _hierarchical_consolidation(
        client,
        chunk_analyses,
        metadata,
        config,
        plan,
        knowledge_context,
        log=log,
        progress=progress,
        telemetry=telemetry,
        cancelled=cancelled,
    )

    checkpoint.status = "completed"
    checkpoint.consolidation_levels.append(
        {
            "levels": levels,
            "deterministic_consolidations": deterministic,
        }
    )
    if bool(config.get("processing_keep_completed_checkpoint", False)):
        store.mark_completed(checkpoint)
    else:
        store.delete(checkpoint.key)

    return ResilientPipelineResult(
        analysis=analysis,
        checkpoint_key=key,
        resumed=resumed,
        resumed_blocks=resumed_blocks,
        initial_chunk_count=initial_count,
        final_chunk_count=len(checkpoint.work_items),
        split_count=checkpoint.split_count,
        retry_count=retries,
        chunk_durations=durations,
        deterministic_consolidations=deterministic,
        consolidation_levels=levels,
        parallel_workers=parallel_workers,
        parallel_completed_blocks=parallel_completed,
    )
