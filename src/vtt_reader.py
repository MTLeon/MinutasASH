from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from html import unescape
from pathlib import Path

TIMESTAMP_RE = re.compile(
    r"(?P<start>\d{2}:\d{2}(?::\d{2})?[.,]\d{3})\s*-->\s*"
    r"(?P<end>\d{2}:\d{2}(?::\d{2})?[.,]\d{3})"
)
VOICE_RE = re.compile(r"<v(?:\.[^ >]+)?\s+([^>]+)>(.*?)</v>", re.IGNORECASE | re.DOTALL)
TAG_RE = re.compile(r"<[^>]+>")


@dataclass(frozen=True)
class TranscriptSegment:
    start: str
    end: str
    speaker: str
    text: str

    def to_dict(self) -> dict:
        return asdict(self)


def _normalize_timestamp(value: str) -> str:
    value = value.replace(",", ".")
    if len(value.split(":")) == 2:
        value = f"00:{value}"
    return value


def _timestamp_seconds(value: str) -> float:
    clean = value.replace(",", ".")
    parts = clean.split(":")
    if len(parts) == 2:
        hours = "0"
        minutes, seconds = parts
    else:
        hours, minutes, seconds = parts
    return int(hours) * 3600 + int(minutes) * 60 + float(seconds)


def _clean_text(value: str) -> str:
    value = unescape(value)
    value = TAG_RE.sub("", value)
    return re.sub(r"\s+", " ", value).strip()


def _extract_speaker_and_text(payload: str) -> tuple[str, str]:
    payload = unescape(payload.strip())
    match = VOICE_RE.search(payload)
    if match:
        speaker = _clean_text(match.group(1)) or "Hablante no identificado"
        text = _clean_text(match.group(2))
        return speaker, text
    return "Hablante no identificado", _clean_text(payload)


def read_teams_vtt(
    path: str | Path,
    merge_adjacent: bool = True,
) -> list[TranscriptSegment]:
    vtt_path = Path(path)
    if not vtt_path.exists():
        raise FileNotFoundError(f"No existe la transcripción: {vtt_path}")
    if vtt_path.suffix.lower() != ".vtt":
        raise ValueError("El archivo de entrada debe tener extensión .vtt")

    raw = vtt_path.read_text(encoding="utf-8-sig", errors="replace")
    lines = raw.splitlines()
    segments: list[TranscriptSegment] = []
    index = 0

    while index < len(lines):
        line = lines[index].strip()
        match = TIMESTAMP_RE.search(line)
        if not match:
            index += 1
            continue

        start = _normalize_timestamp(match.group("start"))
        end = _normalize_timestamp(match.group("end"))
        index += 1
        payload_lines: list[str] = []

        while index < len(lines):
            candidate = lines[index].strip()
            if TIMESTAMP_RE.search(candidate):
                break
            if not candidate:
                index += 1
                break
            payload_lines.append(candidate)
            index += 1

        speaker, text = _extract_speaker_and_text(" ".join(payload_lines))
        if text:
            segments.append(TranscriptSegment(start, end, speaker, text))

    if not segments:
        raise ValueError(
            "No se encontraron segmentos de voz. Comprueba que el archivo "
            "corresponda a una transcripción VTT descargada desde Teams."
        )
    return merge_adjacent_segments(segments) if merge_adjacent else segments


def merge_adjacent_segments(
    segments: list[TranscriptSegment],
    maximum_gap_seconds: float = 3.0,
) -> list[TranscriptSegment]:
    if not segments:
        return []

    merged: list[TranscriptSegment] = []
    current = segments[0]
    for segment in segments[1:]:
        gap = _timestamp_seconds(segment.start) - _timestamp_seconds(current.end)
        if segment.speaker == current.speaker and 0 <= gap <= maximum_gap_seconds:
            current = TranscriptSegment(
                current.start,
                segment.end,
                current.speaker,
                f"{current.text} {segment.text}".strip(),
            )
        else:
            merged.append(current)
            current = segment
    merged.append(current)
    return merged


def unique_speakers(segments: list[TranscriptSegment]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for segment in segments:
        speaker = segment.speaker.strip()
        if not speaker or speaker == "Hablante no identificado":
            continue
        key = speaker.casefold()
        if key not in seen:
            seen.add(key)
            result.append(speaker)
    return result


def normalized_transcript(segments: list[TranscriptSegment]) -> str:
    return "\n".join(
        f"[{item.start}] {item.speaker}: {item.text}" for item in segments
    )


def split_transcript(
    segments: list[TranscriptSegment],
    max_chars: int,
    overlap_segments: int = 2,
) -> list[str]:
    if max_chars < 2000:
        raise ValueError("max_chars debe ser al menos 2000")

    chunks: list[str] = []
    current: list[str] = []
    current_size = 0
    for segment in segments:
        line = f"[{segment.start}] {segment.speaker}: {segment.text}"
        if current and current_size + len(line) + 1 > max_chars:
            chunks.append("\n".join(current))
            overlap = current[-max(overlap_segments, 0):] if overlap_segments else []
            current = list(overlap)
            current_size = sum(len(item) + 1 for item in current)
        current.append(line)
        current_size += len(line) + 1
    if current:
        chunks.append("\n".join(current))
    return chunks
