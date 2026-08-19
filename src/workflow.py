from __future__ import annotations

import contextlib
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from time import monotonic
from typing import Any

from src.coverage_guard import (
    ActionCandidate,
    apply_deterministic_fallback,
    evaluate_coverage,
    extract_action_candidates,
    format_candidates_for_prompt,
    merge_analyses,
)
from src.documents.registry import get_document_provider
from src.evidence_validation import annotate_evidence
from src.meeting_sources import read_meeting_source
from src.metadata import enrich_attendees
from src.minute_generator import (
    analyze_candidate_recovery,
    analyze_complete_transcript,
)
from src.models import MeetingMetadata, MinuteAnalysis
from src.ollama_client import LocalEngineTimeout, StructuredOutputTruncated
from src.pdf_writer import generate_minute_pdf
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
    # La telemetría es opcional: un observador defectuoso no puede perder trabajo del usuario.
    with contextlib.suppress(Exception):
        telemetry({"type": event_type, **payload})


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
    segments = merge_adjacent_segments(raw_segments)
    metadata = metadata.model_copy(
        update={
            "source_type": meeting_source.source_type,
            "source_quality": meeting_source.quality,
        }
    )
    speakers = unique_speakers(raw_segments)
    metadata = enrich_attendees(
        metadata,
        speakers,
        bool(config.get("auto_add_transcript_speakers", True)),
    )
    log(f"Fuente: {meeting_source.display_name} · calidad {meeting_source.quality}")
    for warning in meeting_source.warnings:
        log(f"Advertencia de fuente: {warning}")
    log(f"Intervenciones útiles: {len(segments)}")
    log(f"Participantes detectados: {len(speakers)}")

    guard_enabled = bool(config.get("semantic_guard_enabled", True))
    candidates: list[ActionCandidate] = []
    if guard_enabled:
        candidates = extract_action_candidates(
            raw_segments,
            maximum_candidates=int(config.get("semantic_guard_max_candidates", 500)),
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

    progress(21, "Preparando contenido")
    knowledge_context = str(config.get("technical_dictionary_context", "")).strip()[:8000]
    if knowledge_context:
        log("Se aplicará el diccionario técnico aprobado para normalizar vocabulario.")

    pipeline_diagnostics: dict[str, Any] = {
        "processing_plan": plan.to_dict(),
        "single_pass_attempted": False,
        "single_pass_timed_out": False,
    }

    use_single_pass = not plan.force_chunking and len(transcript_text) <= profile.single_pass_chars
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
        log(f"Procesamiento optimizado en una etapa · espera máxima adaptativa {timeout} s.")
        try:
            analysis = analyze_complete_transcript(
                client,
                transcript_text,
                metadata.model_dump(),
                coverage_hints=format_candidates_for_prompt(candidates),
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
        client_factory = None
        if descriptor.is_remote and int(config.get("remote_parallel_requests", 2)) > 1:
            factory_provider_id = provider_id
            factory_model = str(getattr(client, "model", selected_model))

            def client_factory() -> Any:
                return create_processing_provider(
                    dict(effective_config),
                    factory_provider_id,
                    factory_model,
                )

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
            client_factory=client_factory,
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

    if guard_enabled and should_recover and bool(config.get("semantic_guard_second_pass", True)):
        if cancelled():
            raise InterruptedError("Proceso cancelado por el usuario.")
        recovery_attempted = True
        progress(84, "Verificando puntos omitidos")
        log(
            "El control de cobertura detectó posibles omisiones "
            f"({initial_report.covered_count}/{initial_report.candidate_count})."
        )
        batches = _candidate_batches(list(initial_report.uncovered))
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
            log(f"Se completó la comprobación focalizada en {len(batches)} grupo(s).")

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
            minimum_confidence=float(config.get("semantic_guard_fallback_min_confidence", 0.82)),
        )
        analysis = normalize_analysis(analysis, metadata)
        if fallback_added:
            log(
                f"El control automático recuperó {fallback_added} punto(s) "
                "explícito(s) para revisión humana."
            )

    evidence_checks = annotate_evidence(analysis.items, segments)
    evidence_verified = sum(check.verified is True for check in evidence_checks)
    evidence_unverified = sum(check.verified is False for check in evidence_checks)
    if evidence_unverified:
        analysis.warnings.append(
            f"{evidence_unverified} punto(s) requieren revisar su evidencia temporal."
        )

    final_report = evaluate_coverage(candidates, analysis)
    if final_report.uncovered:
        analysis.warnings.append(
            "Existen expresiones explícitas que no pudieron asociarse con una fila; "
            "revise la transcripción y el registro de cobertura."
        )
    analysis.warnings = list(dict.fromkeys(analysis.warnings))

    final_snapshot = get_resource_snapshot()
    estimated_input_tokens = max(1, len(transcript_text) // 4)
    input_rate = float(
        config.get(
            f"{provider_id}_input_cost_per_million_usd",
            config.get("remote_input_cost_per_million_usd", 0.0),
        )
        or 0.0
    )
    estimated_cost_usd = (
        estimated_input_tokens * input_rate / 1_000_000 if descriptor.is_remote else 0.0
    )
    try:
        source_size_bytes = source.stat().st_size
    except OSError:
        source_size_bytes = 0

    diagnostics = {
        "source_type": meeting_source.source_type,
        "source_quality": meeting_source.quality,
        "source_warnings": list(meeting_source.warnings),
        "evidence": {
            "verified": evidence_verified,
            "unverified": evidence_unverified,
            "not_applicable": len(evidence_checks) - evidence_verified - evidence_unverified,
        },
        "semantic_guard_enabled": guard_enabled,
        "quality_status": _quality_status(
            len(candidates), fallback_added, len(final_report.uncovered)
        ),
        "candidate_count": len(candidates),
        "initial_coverage": initial_report.to_dict(),
        "recovery_attempted": recovery_attempted,
        "recovery_batches": len(_candidate_batches(list(initial_report.uncovered)))
        if recovery_attempted
        else 0,
        "recovery_error": recovery_error,
        "fallback_added": fallback_added,
        "final_coverage": final_report.to_dict(),
        "processing": pipeline_diagnostics,
        "performance": {
            "source_size_bytes": source_size_bytes,
            "transcript_characters": len(transcript_text),
            "segment_count": len(segments),
            "item_count": len(analysis.items),
            "estimated_input_tokens": estimated_input_tokens,
            "estimated_cost_usd": round(estimated_cost_usd, 6),
            "ending_memory_percent": final_snapshot.memory_percent,
            "ending_available_memory_bytes": final_snapshot.available_memory_bytes,
        },
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
    provider = get_document_provider(str(config.get("document_provider", "ash_minutes_v1")))
    provider.generate(
        bundle.analysis,
        bundle.metadata,
        docx_path,
        config,
    )
    if bool(config.get("generate_pdf", True)):
        logo_path = config.get("logo_path")
        generate_minute_pdf(
            bundle.analysis,
            bundle.metadata,
            docx_path.with_suffix(".pdf"),
            logo_path=logo_path,
        )
    return docx_path, json_path, transcript_path, folder


# Compatibilidad con la interfaz anterior.
def generate_word(
    bundle: AnalysisBundle,
    output_dir: str | Path,
    config: dict,
    basename: str | None = None,
) -> tuple[Path, Path, Path]:
    docx, json_path, transcript, _folder = generate_word_package(bundle, output_dir, config)
    return docx, json_path, transcript
