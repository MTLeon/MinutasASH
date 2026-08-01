from __future__ import annotations

from dataclasses import dataclass, field
import gc
from pathlib import Path
from time import monotonic
from typing import Any, Callable

from src.coverage_guard import (
    ActionCandidate,
    apply_deterministic_fallback,
    evaluate_coverage,
    extract_action_candidates,
    format_candidates_for_prompt,
    merge_analyses,
)
from src.documents.registry import get_document_provider
from src.meeting_sources import read_meeting_source
from src.metadata import enrich_attendees
from src.minute_generator import (
    analyze_candidate_recovery,
    analyze_complete_transcript,
)
from src.models import MeetingMetadata, MinuteAnalysis
from src.ollama_client import LocalEngineTimeout, StructuredOutputTruncated
from src.postprocess import normalize_analysis
from src.processing_runtime import (
    adaptive_timeout_seconds,
    get_resource_snapshot,
    resolve_processing_plan,
)
from src.providers.registry import (
    create_processing_provider,
    descriptor_for,
    provider_display_name,
)
from src.resilient_pipeline import analyze_resilient_chunks
from src.storage import (
    MeetingFolder,
    archive_source,
    make_meeting_folder,
    save_evidence_files,
)
from src.vtt_reader import (
    TranscriptSegment,
    merge_adjacent_segments,
    normalized_transcript,
    optimize_transcript_segments,
    split_transcript,
    unique_speakers,
)


LogCallback = Callable[[str], None]
ProgressCallback = Callable[[int, str], None]
TelemetryCallback = Callable[[dict[str, Any]], None]
CancelCallback = Callable[[], bool]


@dataclass
class AnalysisBundle:
    metadata: MeetingMetadata
    analysis: MinuteAnalysis
    segments: list[TranscriptSegment]
    source_path: Path
    model: str
    provider_id: str = "ollama_local"
    provider_name: str = "Procesamiento local"
    diagnostics: dict = field(default_factory=dict)
    candidates: list[dict] = field(default_factory=list)


def _quality_status(candidate_count: int, fallback_added: int, unresolved: int) -> str:
    if candidate_count == 0:
        return "sin_señales_explícitas"
    if unresolved:
        return "revisión_recomendada"
    if fallback_added:
        return "recuperada"
    return "completa"


def _configure_runtime(
    client: Any,
    *,
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


def _emit(telemetry: TelemetryCallback, event_type: str, **payload: Any) -> None:
    try:
        telemetry({"type": event_type, **payload})
    except Exception:
        pass


def _candidate_batches(
    candidates: list[ActionCandidate],
    *,
    max_chars: int = 7000,
    max_items: int = 40,
) -> list[list[ActionCandidate]]:
    batches: list[list[ActionCandidate]] = []
    current: list[ActionCandidate] = []
    current_size = 0
    for candidate in candidates:
        size = len(format_candidates_for_prompt([candidate]))
        if current and (len(current) >= max_items or current_size + size > max_chars):
            batches.append(current)
            current = []
            current_size = 0
        current.append(candidate)
        current_size += size
    if current:
        batches.append(current)
    return batches


def _candidate_subset_for_prompt(
    candidates: list[ActionCandidate],
    config: dict,
) -> list[ActionCandidate]:
    """Limita ayudas al modelo sin afectar el control final de cobertura."""

    maximum = max(10, int(config.get("semantic_guard_prompt_max_candidates", 80)))
    maximum_chars = max(1000, int(config.get("semantic_guard_prompt_max_chars", 5500)))
    ordered = sorted(
        candidates,
        key=lambda item: (-item.confidence, item.index),
    )
    selected: list[ActionCandidate] = []
    size = 0
    for candidate in ordered:
        rendered = format_candidates_for_prompt([candidate])
        if selected and (len(selected) >= maximum or size + len(rendered) > maximum_chars):
            break
        selected.append(candidate)
        size += len(rendered)
    return sorted(selected, key=lambda item: item.index)


def _warmup_and_replan_local(
    client: Any,
    config: dict,
    transcript_chars: int,
    model: str,
    plan,
    *,
    log: LogCallback,
    progress: ProgressCallback,
    telemetry: TelemetryCallback,
):
    if not bool(config.get("processing_warmup_resource_recheck", True)):
        return plan
    warmup = getattr(client, "warmup", None)
    if not callable(warmup):
        return plan
    progress(18, "Preparando el modelo local y comprobando memoria")
    log("Preparando el modelo local para medir la memoria real disponible.")
    warmup()
    snapshot = get_resource_snapshot()
    revised = resolve_processing_plan(
        config,
        transcript_chars,
        is_remote=False,
        snapshot=snapshot,
        model=model,
        model_loaded=True,
    )
    rank = {"fast": 0, "balanced": 1, "precise": 2}
    previous_rank = rank.get(plan.effective_profile.profile_id, 1)
    revised_rank = rank.get(revised.effective_profile.profile_id, 1)
    selected = revised
    retained_for_stability = False
    if revised_rank > previous_rank:
        # Una ejecución iniciada en modo conservador no debe aumentar después
        # el tamaño de bloque. La memoria puede fluctuar durante el calentamiento
        # y un ascenso produciría exactamente el pico que se intentó evitar.
        selected = plan
        retained_for_stability = True

    _emit(
        telemetry,
        "resource_recheck",
        percent=19,
        previous_profile=plan.effective_profile.profile_id,
        previous_profile_name=plan.effective_profile.display_name,
        effective_profile=selected.effective_profile.to_dict(),
        resource_snapshot=snapshot.to_dict(),
        reason=(
            "Se conserva el perfil preventivo para evitar un aumento de carga."
            if retained_for_stability
            else revised.reason
        ),
        retained_for_stability=retained_for_stability,
    )
    if retained_for_stability:
        log(
            "La memoria posterior permitiría un perfil mayor, pero se mantiene "
            f"{plan.effective_profile.display_name} por estabilidad."
        )
        if revised.memory_warning:
            log(f"Advertencia posterior a la carga: {revised.memory_warning}")
        return plan
    if revised.effective_profile.profile_id != plan.effective_profile.profile_id:
        log(
            "Perfil ajustado después de cargar el modelo: "
            f"{revised.effective_profile.display_name}."
        )
    if revised.memory_warning:
        log(f"Advertencia posterior a la carga: {revised.memory_warning}")
    return revised


def _release_local_model(client: Any, config: dict, log: LogCallback) -> None:
    if not bool(config.get("unload_model_after_processing", True)):
        return
    unload = getattr(client, "unload", None)
    if callable(unload):
        unload()
        log("Memoria del modelo local liberada al finalizar el procesamiento.")


def analyze_meeting(
    vtt_path: str | Path,
    metadata: MeetingMetadata,
    config: dict,
    model: str,
    log: LogCallback | None = None,
    progress: ProgressCallback | None = None,
    telemetry: TelemetryCallback | None = None,
    cancelled: CancelCallback | None = None,
) -> AnalysisBundle:
    source = Path(vtt_path)
    if not source.exists():
        raise FileNotFoundError(f"No se encontró la fuente de reunión: {source}")

    log = log or (lambda _message: None)
    progress = progress or (lambda _value, _message: None)
    telemetry = telemetry or (lambda _event: None)
    cancelled = cancelled or (lambda: False)
    pipeline_started = monotonic()

    progress(5, "Leyendo fuente de reunión")
    log(f"Leyendo archivo: {source.name}")
    meeting_source = read_meeting_source(source, preferred_type=metadata.source_type)
    raw_segments = meeting_source.segments
    source_type = meeting_source.source_type
    source_quality = meeting_source.quality
    source_display_name = meeting_source.display_name
    source_warnings = tuple(meeting_source.warnings)
    segments, transcript_stats = optimize_transcript_segments(
        raw_segments,
        maximum_gap_seconds=float(config.get("transcript_merge_gap_seconds", 6.0)),
        remove_noise=bool(config.get("transcript_remove_noise", True)),
    )
    metadata = metadata.model_copy(
        update={
            "source_type": source_type,
            "source_quality": source_quality,
        }
    )
    speakers = unique_speakers(raw_segments)
    metadata = enrich_attendees(
        metadata,
        speakers,
        bool(config.get("auto_add_transcript_speakers", True)),
    )
    log(f"Fuente: {source_display_name} · calidad {source_quality}")
    for warning in source_warnings:
        log(f"Advertencia de fuente: {warning}")
    log(
        f"Intervenciones: {transcript_stats.original_segments} originales → "
        f"{transcript_stats.optimized_segments} optimizadas · "
        f"reducción de texto {transcript_stats.reduction_percent:.1f} %."
    )
    log(f"Participantes detectados: {len(speakers)}")

    guard_enabled = bool(config.get("semantic_guard_enabled", True))
    candidates: list[ActionCandidate] = []
    if guard_enabled:
        candidates = extract_action_candidates(
            segments,
            maximum_candidates=int(config.get("semantic_guard_max_candidates", 300)),
        )
        log(f"Expresiones explícitas para control de cobertura: {len(candidates)}")

    if cancelled():
        raise InterruptedError("Proceso cancelado por el usuario.")

    progress(12, "Evaluando longitud y recursos")
    transcript_text = normalized_transcript(segments)
    provider_id = str(config.get("processing_provider", "ollama_local"))
    selected_model = model or ""
    descriptor = descriptor_for(provider_id)
    plan = resolve_processing_plan(
        config,
        len(transcript_text),
        is_remote=descriptor.is_remote,
        model=selected_model or str(config.get("model", "qwen3:8b")),
    )
    profile = plan.effective_profile
    effective_config = dict(config)
    effective_config.update(
        {
            "timeout_seconds": profile.timeout_seconds,
            "context_length": profile.context_length,
            "max_chars_per_chunk": profile.chunk_chars,
            "single_pass_max_chars": profile.single_pass_chars,
        }
    )
    log(
        f"Perfil de procesamiento: {profile.display_name} · "
        f"bloques objetivo {profile.chunk_chars} caracteres · contexto {profile.context_length}."
    )
    log(f"Motivo del perfil: {plan.reason}")
    if plan.memory_warning:
        log(f"Advertencia de recursos: {plan.memory_warning}")
    _emit(
        telemetry,
        "processing_plan",
        percent=12,
        elapsed_seconds=monotonic() - pipeline_started,
        **plan.to_dict(),
    )

    progress(16, "Verificando método de procesamiento")
    try:
        client = create_processing_provider(
            effective_config,
            provider_id,
            selected_model or None,
        )
        _configure_runtime(client, telemetry=telemetry, cancelled=cancelled)
        client.check_connection()
        log(f"Método disponible: {client.display_name}.")
    except Exception as primary_error:
        if provider_id != "ollama_local" and bool(config.get("fallback_to_local", True)):
            log(f"El método seleccionado no está disponible: {primary_error}")
            log("Se intentará continuar con el procesamiento local.")
            provider_id = "ollama_local"
            descriptor = descriptor_for(provider_id)
            plan = resolve_processing_plan(
                config,
                len(transcript_text),
                is_remote=False,
                model=str(config.get("model", "qwen3:8b")),
            )
            profile = plan.effective_profile
            effective_config.update(
                {
                    "timeout_seconds": profile.timeout_seconds,
                    "context_length": profile.context_length,
                    "max_chars_per_chunk": profile.chunk_chars,
                    "single_pass_max_chars": profile.single_pass_chars,
                }
            )
            client = create_processing_provider(effective_config, provider_id, None)
            _configure_runtime(client, telemetry=telemetry, cancelled=cancelled)
            client.check_connection()
            log("Procesamiento local disponible.")
        else:
            raise

    if provider_id == "ollama_local":
        plan = _warmup_and_replan_local(
            client,
            config,
            len(transcript_text),
            getattr(client, "model", selected_model) or str(config.get("model", "qwen3:8b")),
            plan,
            log=log,
            progress=progress,
            telemetry=telemetry,
        )
        profile = plan.effective_profile
        effective_config.update(
            {
                "timeout_seconds": profile.timeout_seconds,
                "context_length": profile.context_length,
                "max_chars_per_chunk": profile.chunk_chars,
                "single_pass_max_chars": profile.single_pass_chars,
            }
        )

    progress(21, "Preparando contenido")
    knowledge_context = str(config.get("technical_dictionary_context", "")).strip()[:4000]
    if knowledge_context:
        log("Se aplicará el diccionario técnico aprobado para normalizar vocabulario.")

    pipeline_diagnostics: dict[str, Any] = {
        "processing_plan": plan.to_dict(),
        "single_pass_attempted": False,
        "single_pass_timed_out": False,
    }

    use_single_pass = (
        not plan.force_chunking
        and len(transcript_text) <= profile.single_pass_chars
    )
    analysis: MinuteAnalysis
    if use_single_pass:
        if cancelled():
            raise InterruptedError("Proceso cancelado por el usuario.")
        pipeline_diagnostics["single_pass_attempted"] = True
        timeout = adaptive_timeout_seconds(
            profile,
            len(transcript_text),
            config,
            snapshot=get_resource_snapshot(),
        )
        _configure_request(
            client,
            timeout_seconds=timeout,
            context_length=profile.context_length,
            operation={"stage": "single_pass", "block_index": 1, "total_blocks": 1},
        )
        progress(30, "Analizando reunión en una etapa")
        log(
            "Procesamiento optimizado en una etapa · "
            f"espera máxima adaptativa {timeout} s."
        )
        try:
            analysis = analyze_complete_transcript(
                client,
                transcript_text,
                metadata.model_dump(),
                coverage_hints=format_candidates_for_prompt(
                    _candidate_subset_for_prompt(candidates, config)
                ),
                knowledge_context=knowledge_context,
            )
            progress(76, "Comprobando resultados")
        except (LocalEngineTimeout, StructuredOutputTruncated) as exc:
            pipeline_diagnostics["single_pass_timed_out"] = isinstance(exc, LocalEngineTimeout)
            pipeline_diagnostics["single_pass_structure_incomplete"] = isinstance(
                exc, StructuredOutputTruncated
            )
            if isinstance(exc, StructuredOutputTruncated):
                log(
                    "La respuesta de la etapa única quedó incompleta. Se cambiará "
                    "automáticamente a bloques pequeños sin perder la fuente."
                )
            else:
                log(
                    "La etapa única excedió el tiempo. Se cambiará automáticamente a "
                    "bloques pequeños sin perder la fuente."
                )
            use_single_pass = False

    if not use_single_pass:
        chunks = split_transcript(
            segments,
            profile.chunk_chars,
            overlap_segments=profile.overlap_lines,
        )
        log(f"Bloques iniciales de procesamiento: {len(chunks)}")
        progress(24, f"Preparando {len(chunks)} bloque(s) recuperables")
        resilient = analyze_resilient_chunks(
            client,
            chunks,
            metadata.model_dump(),
            effective_config,
            plan,
            source,
            provider_id,
            getattr(client, "model", selected_model),
            knowledge_context=knowledge_context,
            log=log,
            progress=progress,
            telemetry=telemetry,
            cancelled=cancelled,
        )
        analysis = resilient.analysis
        pipeline_diagnostics.update(resilient.diagnostics())

    analysis = normalize_analysis(analysis, metadata)
    initial_report = evaluate_coverage(candidates, analysis)
    recovery_attempted = False
    recovery_error: str | None = None
    fallback_added = 0

    minimum_coverage = float(config.get("semantic_guard_min_coverage", 0.80))
    should_recover = bool(candidates) and (
        not analysis.items or initial_report.ratio < minimum_coverage
    )

    if (
        guard_enabled
        and should_recover
        and bool(config.get("semantic_guard_second_pass", True))
    ):
        if cancelled():
            raise InterruptedError("Proceso cancelado por el usuario.")
        recovery_attempted = True
        progress(84, "Verificando puntos omitidos")
        log(
            "El control de cobertura detectó posibles omisiones "
            f"({initial_report.covered_count}/{initial_report.candidate_count})."
        )
        recovery_candidates = sorted(
            initial_report.uncovered,
            key=lambda item: (-item.confidence, item.index),
        )[: max(10, int(config.get("semantic_guard_second_pass_max_candidates", 120)))]
        batches = _candidate_batches(
            list(recovery_candidates),
            max_chars=int(config.get("semantic_guard_recovery_batch_chars", 5000)),
            max_items=int(config.get("semantic_guard_recovery_batch_items", 30)),
        )
        recovery_errors: list[str] = []
        for batch_index, batch in enumerate(batches, start=1):
            if cancelled():
                raise InterruptedError("Proceso cancelado por el usuario.")
            candidates_text = format_candidates_for_prompt(batch)
            recovery_timeout = adaptive_timeout_seconds(
                profile,
                len(candidates_text),
                config,
                snapshot=get_resource_snapshot(),
            )
            _configure_request(
                client,
                timeout_seconds=recovery_timeout,
                context_length=profile.context_length,
                operation={
                    "stage": "coverage_recovery",
                    "group_index": batch_index,
                    "total_groups": len(batches),
                },
            )
            progress(
                84 + min(6, int(6 * batch_index / max(len(batches), 1))),
                f"Verificando omisiones {batch_index} de {len(batches)}",
            )
            try:
                recovery = analyze_candidate_recovery(
                    client,
                    candidates_text,
                    metadata.model_dump(),
                    knowledge_context=knowledge_context,
                )
                analysis = merge_analyses(analysis, recovery)
                analysis = normalize_analysis(analysis, metadata)
            except Exception as exc:
                # La recuperación es una protección adicional. Su fallo no debe
                # perder el análisis principal ni los otros grupos.
                recovery_errors.append(str(exc))
                log(
                    f"La comprobación focalizada {batch_index}/{len(batches)} "
                    f"no pudo completarse: {exc}"
                )
        recovery_error = " | ".join(recovery_errors) or None
        if not recovery_errors:
            log(
                f"Se completó la comprobación focalizada en {len(batches)} grupo(s)."
            )

    after_recovery = evaluate_coverage(candidates, analysis)
    if (
        guard_enabled
        and after_recovery.uncovered
        and bool(config.get("semantic_guard_deterministic_fallback", True))
    ):
        analysis, fallback_added = apply_deterministic_fallback(
            analysis,
            after_recovery.uncovered,
            metadata,
            minimum_confidence=float(
                config.get("semantic_guard_fallback_min_confidence", 0.82)
            ),
        )
        analysis = normalize_analysis(analysis, metadata)
        if fallback_added:
            log(
                f"El control automático recuperó {fallback_added} punto(s) "
                "explícito(s) para revisión humana."
            )

    final_report = evaluate_coverage(candidates, analysis)
    if final_report.uncovered:
        analysis.warnings.append(
            "Existen expresiones explícitas que no pudieron asociarse con una fila; "
            "revise la transcripción y el registro de cobertura."
        )
    analysis.warnings = list(dict.fromkeys(analysis.warnings))

    diagnostics = {
        "source_type": source_type,
        "source_quality": source_quality,
        "source_warnings": list(source_warnings),
        "transcript_optimization": transcript_stats.to_dict(),
        "semantic_guard_enabled": guard_enabled,
        "quality_status": _quality_status(
            len(candidates), fallback_added, len(final_report.uncovered)
        ),
        "candidate_count": len(candidates),
        "initial_coverage": initial_report.to_dict(),
        "recovery_attempted": recovery_attempted,
        "recovery_batches": len(batches) if recovery_attempted else 0,
        "recovery_error": recovery_error,
        "fallback_added": fallback_added,
        "final_coverage": final_report.to_dict(),
        "processing": pipeline_diagnostics,
        "total_elapsed_seconds": monotonic() - pipeline_started,
    }

    log(f"Puntos identificados: {len(analysis.items)}")
    if candidates:
        log(
            "Cobertura final de expresiones explícitas: "
            f"{final_report.covered_count}/{final_report.candidate_count}."
        )
    progress(96, "Contenido listo para revisión")
    _emit(
        telemetry,
        "pipeline_completed",
        percent=96,
        elapsed_seconds=monotonic() - pipeline_started,
        item_count=len(analysis.items),
    )
    _release_local_model(client, config, log)
    gc.collect()
    return AnalysisBundle(
        metadata=metadata,
        analysis=analysis,
        segments=segments,
        source_path=source,
        model=getattr(client, "model", selected_model),
        provider_id=provider_id,
        provider_name=provider_display_name(provider_id),
        diagnostics=diagnostics,
        candidates=[candidate.to_dict() for candidate in candidates],
    )


def generate_word_package(
    bundle: AnalysisBundle,
    base_output_dir: str | Path,
    config: dict,
) -> tuple[Path, Path, Path, MeetingFolder]:
    folder = make_meeting_folder(base_output_dir, bundle.metadata)
    archive_source(bundle.source_path, folder)
    json_path, transcript_path = save_evidence_files(
        folder,
        bundle.metadata,
        bundle.analysis,
        bundle.segments,
        bundle.source_path,
        bundle.model,
        bundle.provider_id,
        bundle.provider_name,
        diagnostics=bundle.diagnostics,
        candidates=bundle.candidates,
    )
    from src.storage import safe_component

    number = safe_component(bundle.metadata.minute_number, "Minuta")
    docx_path = folder.document_dir / f"{number}.docx"
    provider = get_document_provider(
        str(config.get("document_provider", "ash_minutes_v1"))
    )
    provider.generate(
        bundle.analysis,
        bundle.metadata,
        docx_path,
        config,
    )
    return docx_path, json_path, transcript_path, folder


# Compatibilidad con la interfaz anterior.
def generate_word(
    bundle: AnalysisBundle,
    output_dir: str | Path,
    config: dict,
    basename: str | None = None,
) -> tuple[Path, Path, Path]:
    docx, json_path, transcript, _folder = generate_word_package(
        bundle, output_dir, config
    )
    return docx, json_path, transcript
