from __future__ import annotations

import json
import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class DiarizationTurn:
    start: float
    end: float
    speaker: str


def parse_rttm_text(text: str) -> list[DiarizationTurn]:
    turns: list[DiarizationTurn] = []
    for line in text.splitlines():
        fields = line.split()
        if not fields or fields[0].upper() != "SPEAKER" or len(fields) < 8:
            continue
        try:
            start = float(fields[3])
            duration = float(fields[4])
        except ValueError:
            continue
        if duration <= 0:
            continue
        turns.append(DiarizationTurn(start, start + duration, fields[7]))
    return sorted(turns, key=lambda turn: (turn.start, turn.end, turn.speaker))


def load_rttm(path: str | Path) -> list[DiarizationTurn]:
    return parse_rttm_text(Path(path).read_text(encoding="utf-8-sig"))


def _overlap(start: float, end: float, turn: DiarizationTurn) -> float:
    return max(0.0, min(end, turn.end) - max(start, turn.start))


def assign_speakers(
    segments: list[dict[str, Any]], turns: list[DiarizationTurn]
) -> list[dict[str, Any]]:
    assigned: list[dict[str, Any]] = []
    for segment in segments:
        item = dict(segment)
        start = float(item.get("start") or 0.0)
        end = max(start, float(item.get("end") or start))
        candidates = [(_overlap(start, end, turn), turn) for turn in turns]
        overlap, best = max(candidates, default=(0.0, None), key=lambda pair: pair[0])
        if best is not None and overlap > 0:
            item["speaker"] = best.speaker
        assigned.append(item)
    return assigned


def _sidecar(source: Path) -> Path | None:
    candidates = (source.with_suffix(source.suffix + ".rttm"), source.with_suffix(".rttm"))
    return next((path for path in candidates if path.is_file()), None)


def _worker_turns(source: Path, worker: Path) -> list[DiarizationTurn]:
    completed = subprocess.run(
        [str(worker), "--source", str(source), "--format", "json"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=14400,
        check=False,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    if completed.returncode:
        raise RuntimeError(completed.stderr.strip() or "La diarización externa falló.")
    payload = json.loads(completed.stdout)
    rows = payload.get("turns", payload) if isinstance(payload, dict) else payload
    if not isinstance(rows, list):
        raise ValueError("El motor de diarización no devolvió una lista de turnos.")
    return [
        DiarizationTurn(float(row["start"]), float(row["end"]), str(row["speaker"]))
        for row in rows
        if isinstance(row, dict)
    ]


def diarize_segments(
    source: str | Path,
    segments: list[dict[str, Any]],
    worker_path: str | Path | None = None,
) -> tuple[list[dict[str, Any]], bool, str]:
    source_path = Path(source)
    sidecar = _sidecar(source_path)
    if sidecar:
        turns = load_rttm(sidecar)
        return assign_speakers(segments, turns), bool(turns), f"RTTM: {sidecar.name}"

    configured = str(worker_path or os.environ.get("MINUTAS_ASH_DIARIZATION_WORKER") or "").strip()
    if not configured:
        return segments, False, "Diarización solicitada, pero no hay RTTM ni motor configurado."
    worker = Path(configured).expanduser()
    if not worker.is_file():
        return segments, False, f"No existe el motor de diarización: {worker}"
    turns = _worker_turns(source_path, worker)
    return assign_speakers(segments, turns), bool(turns), f"Motor: {worker.name}"
