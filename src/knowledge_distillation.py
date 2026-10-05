"""Preparación local de ejemplos oro para destilación y ajuste supervisado."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from src.meeting_sources import read_meeting_source
from src.minute_generator import prompt_identity
from src.models import MeetingItem, MinuteAnalysis
from src.vtt_reader import normalized_transcript

_SKIP_VALUES = {"", "n.a.", "n/a", "informativo", "por confirmar", "-"}
_ACTION_WORDS = re.compile(
    r"\b(?:enviar|entregar|emitir|revisar|coordinar|gestionar|realizar|"
    r"preparar|actualizar|validar|responder|cerrar|informar|comunicar)\w*\b",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class DistillationPreview:
    """Ejemplo local pendiente de validación humana antes de entrenar."""

    transcript_path: Path
    reference_path: Path
    transcript_characters: int
    extracted_items: tuple[MeetingItem, ...]
    warnings: tuple[str, ...]

    def to_lora_record(self, *, project_code: str, client: str) -> dict[str, Any]:
        analysis = MinuteAnalysis(items=list(self.extracted_items))
        transcript = normalized_transcript(read_meeting_source(self.transcript_path).segments)
        return {
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "Extrae puntos de minuta fieles a la transcripción y devuelve "
                        "exclusivamente JSON válido según el esquema de Minutas ASH."
                    ),
                },
                {
                    "role": "user",
                    "content": json.dumps(
                        {
                            "meeting_type": "seguimiento",
                            "project_code": project_code,
                            "transcript": transcript,
                        },
                        ensure_ascii=False,
                    ),
                },
                {"role": "assistant", "content": analysis.model_dump_json()},
            ],
            "metadata": {
                "schema": "minutas-ash-distillation-v1",
                "teacher": "minuta-final-validada",
                "project_code": project_code,
                "client_scope": client,
                "source": str(self.transcript_path),
                "reference": str(self.reference_path),
                "prompt": prompt_identity(),
                "requires_human_approval": True,
            },
        }


def _clean(value: str) -> str:
    return " ".join(value.replace("\n", " ").split()).strip()


def _header_index(values: list[str], terms: tuple[str, ...]) -> int | None:
    for index, value in enumerate(values):
        normalized = _clean(value).casefold()
        if any(term in normalized for term in terms):
            return index
    return None


def _meeting_item(
    description: str,
    responsible: str = "",
    action: str = "",
    due_date_text: str | None = None,
) -> MeetingItem:
    category: Literal["informativo", "acuerdo", "compromiso", "pendiente"] = (
        "compromiso" if _ACTION_WORDS.search(f"{description} {action}") else "informativo"
    )
    return MeetingItem(
        category=category,
        description=description,
        responsible=None if responsible.casefold() in _SKIP_VALUES else responsible,
        due_date_text=due_date_text,
        confidence=1.0,
        origin="manual",
        review_status="pendiente",
        review_notes="Ejemplo extraído de minuta final; requiere validación antes de aprendizaje.",
    )


def _extract_docx_items(path: Path) -> list[MeetingItem]:
    from docx import Document

    document = Document(str(path))
    items: list[MeetingItem] = []
    seen: set[str] = set()
    for table in document.tables:
        header_index = next(
            (
                index
                for index, row in enumerate(table.rows)
                if _header_index([cell.text for cell in row.cells], ("descrip",)) is not None
            ),
            None,
        )
        if header_index is None:
            continue
        header_row = table.rows[header_index]
        headers = [cell.text for cell in header_row.cells]
        description_index = _header_index(headers, ("descrip",))
        responsible_index = _header_index(headers, ("responsable", " por"))
        action_index = _header_index(headers, ("accion",))
        if description_index is None:
            continue
        for row in table.rows[header_index + 1 :]:
            values = [_clean(cell.text) for cell in row.cells]
            if description_index >= len(values):
                continue
            description = values[description_index]
            key = description.casefold()
            if len(description) < 12 or key in seen:
                continue
            if "acuerdos y compromisos" in key or "proxima reunion" in key:
                continue
            seen.add(key)
            responsible = (
                values[responsible_index]
                if responsible_index is not None and responsible_index < len(values)
                else ""
            )
            action = (
                values[action_index]
                if action_index is not None and action_index < len(values)
                else ""
            )
            items.append(_meeting_item(description, responsible, action))
    return items


def _extract_pdf_items(path: Path) -> list[MeetingItem]:
    """Recupera filas numeradas de un PDF de minuta con texto seleccionable."""

    from pypdf import PdfReader

    text = "\n".join(page.extract_text() or "" for page in PdfReader(str(path)).pages)
    lines = [_clean(line) for line in text.splitlines()]
    items: list[MeetingItem] = []
    seen: set[str] = set()
    current: list[str] = []
    current_responsible = ""
    current_due_date: str | None = None
    in_matrix = False

    def flush() -> None:
        description = _clean(" ".join(current))
        key = description.casefold()
        if len(description) >= 12 and key not in seen:
            seen.add(key)
            items.append(
                _meeting_item(description, current_responsible, due_date_text=current_due_date)
            )

    for line in lines:
        normalized = line.casefold()
        if "acuerdos y compromisos" in normalized or (
            "item" in normalized and "descrip" in normalized
        ):
            in_matrix = True
            continue
        if not in_matrix or not line or "descrip" in normalized:
            continue
        match = re.match(r"^(\d+(?:\.\d+)+)\.?\s*(.*)$", line)
        if match:
            flush()
            current = [match.group(2)] if match.group(2) else []
            current_responsible = ""
            current_due_date = None
            continue
        owner = re.match(r"^((?:AAS|ASH)(?:\s*/\s*(?:AAS|ASH))?)\s+(.+)$", line, re.IGNORECASE)
        if current and owner:
            current_responsible = owner.group(1).upper()
            current_due_date = owner.group(2)
            continue
        if current and not any(token in normalized for token in ("responsable", "fecha", "pág")):
            current.append(line)
    flush()
    return items


def extract_reference_items(reference: str | Path) -> tuple[list[MeetingItem], list[str]]:
    """Extrae sólo filas de matriz desde una minuta DOCX o PDF final.

    El resultado no inventa evidencia ni responsables: es un borrador oro que
    requiere aprobación explícita antes de usarse para aprendizaje o LoRA.
    """

    path = Path(reference).expanduser().resolve()
    warnings: list[str] = []
    suffix = path.suffix.casefold()
    if suffix == ".docx":
        items = _extract_docx_items(path)
    elif suffix == ".pdf":
        items = _extract_pdf_items(path)
        warnings.append(
            "La extracción desde PDF requiere revisión: sus tablas pueden perder columnas al convertirse en texto."
        )
    else:
        raise ValueError("La minuta final debe estar en formato DOCX o PDF.")
    if not items:
        warnings.append("No se encontraron filas de acuerdos o compromisos en la minuta final.")
    return items, warnings


def prepare_distillation_preview(
    transcript: str | Path, reference: str | Path
) -> DistillationPreview:
    transcript_path = Path(transcript).expanduser().resolve()
    reference_path = Path(reference).expanduser().resolve()
    source = read_meeting_source(transcript_path)
    text = normalized_transcript(source.segments)
    items, warnings = extract_reference_items(reference_path)
    if not text.strip():
        warnings.append("La transcripción no contiene intervenciones utilizables.")
    return DistillationPreview(
        transcript_path=transcript_path,
        reference_path=reference_path,
        transcript_characters=len(text),
        extracted_items=tuple(items),
        warnings=tuple(warnings),
    )


def export_distillation_record(
    preview: DistillationPreview,
    destination: str | Path,
    *,
    project_code: str,
    client: str,
) -> Path:
    """Escribe un JSONL aislado; no entrena ni sube datos automáticamente."""

    if not preview.extracted_items:
        raise ValueError("No hay puntos extraídos para preparar un ejemplo de destilación.")
    output = Path(destination).expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(
            preview.to_lora_record(project_code=project_code, client=client), ensure_ascii=False
        )
        + "\n",
        encoding="utf-8",
    )
    return output
