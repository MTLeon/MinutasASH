from __future__ import annotations

from dataclasses import asdict, dataclass
from html import unescape
from pathlib import Path
import re
import unicodedata


TIMESTAMP_RE = re.compile(
    r"(?P<start>\d{2}:\d{2}(?::\d{2})?[.,]\d{3})\s*-->\s*"
    r"(?P<end>\d{2}:\d{2}(?::\d{2})?[.,]\d{3})"
)
VOICE_RE = re.compile(r"<v(?:\.[^ >]+)?\s+([^>]+)>(.*?)</v>", re.IGNORECASE | re.DOTALL)
TAG_RE = re.compile(r"<[^>]+>")
_SPEAKER_TIME_RE = re.compile(
    r"^(?:\[?\d{1,2}:\d{2}(?::\d{2})?(?:[.,]\d{1,3})?\]?|"
    r"\d+(?:[.,]\d+)?\s*(?:min(?:uto)?s?|seg(?:undo)?s?|hrs?|horas?))$",
    re.IGNORECASE,
)
_NON_WORD_RE = re.compile(r"[^a-z0-9áéíóúñü]+", re.IGNORECASE)
_NOISE_ONLY = {
    "ah",
    "aja",
    "ajá",
    "eh",
    "em",
    "emm",
    "mmm",
    "este",
    "ya",
    "ok",
    "okay",
}
_NOISE_PHRASES = {
    "prueba de audio",
    "me escuchan",
    "se escucha",
    "se ve mi pantalla",
    "ven mi pantalla",
}


@dataclass(frozen=True)
class TranscriptSegment:
    start: str
    end: str
    speaker: str
    text: str

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class TranscriptOptimizationStats:
    original_segments: int
    optimized_segments: int
    removed_noise_segments: int
    merged_segments: int
    original_chars: int
    optimized_chars: int

    @property
    def reduction_percent(self) -> float:
        if self.original_chars <= 0:
            return 0.0
        return max(0.0, (self.original_chars - self.optimized_chars) / self.original_chars * 100.0)

    def to_dict(self) -> dict:
        payload = asdict(self)
        payload["reduction_percent"] = round(self.reduction_percent, 2)
        return payload


def _normalize_timestamp(value: str) -> str:
    value = value.replace(",", ".")
    if len(value.split(":")) == 2:
        value = f"00:{value}"
    return value


def _timestamp_seconds(value: str) -> float:
    clean = value.replace(",", ".")
    parts = clean.split(":")
    if len(parts) == 2:
        hours = 0
        minutes, seconds = parts
    else:
        hours, minutes, seconds = parts
    return int(hours) * 3600 + int(minutes) * 60 + float(seconds)


def _clean_text(value: str) -> str:
    value = unescape(value)
    value = TAG_RE.sub("", value)
    return re.sub(r"\s+", " ", value).strip()


def _normalize_words(value: str) -> list[str]:
    normalized = unicodedata.normalize("NFKD", value or "")
    normalized = normalized.encode("ascii", "ignore").decode("ascii").casefold()
    normalized = _NON_WORD_RE.sub(" ", normalized)
    return [word for word in normalized.split() if word]


def is_valid_speaker_name(value: str) -> bool:
    """Rechaza tiempos, duraciones y encabezados que no son participantes."""

    text = " ".join(str(value or "").split()).strip()
    if not text or len(text) > 80:
        return False
    lowered = text.casefold()
    if lowered in {"webvtt", "note", "style", "region", "hablante no identificado"}:
        return False
    if "-->" in text or _SPEAKER_TIME_RE.fullmatch(text):
        return False
    if re.search(r"\b(?:minutos?|segundos?|duraci[oó]n)\b", lowered) and re.search(r"\d", text):
        return False
    letters = sum(char.isalpha() for char in text)
    digits = sum(char.isdigit() for char in text)
    if letters < 2 or (digits and digits > letters):
        return False
    return True


def _extract_speaker_and_text(payload: str) -> tuple[str, str]:
    payload = unescape(payload.strip())
    match = VOICE_RE.search(payload)
    if match:
        candidate = _clean_text(match.group(1))
        speaker = candidate if is_valid_speaker_name(candidate) else "Hablante no identificado"
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


def _merge_progressive_text(left: str, right: str) -> str:
    """Une subtítulos progresivos de Teams sin repetir el texto ya mostrado."""

    left_clean = re.sub(r"\s+", " ", left).strip()
    right_clean = re.sub(r"\s+", " ", right).strip()
    if not left_clean:
        return right_clean
    if not right_clean:
        return left_clean

    left_words = _normalize_words(left_clean)
    right_words = _normalize_words(right_clean)
    if not left_words or not right_words:
        return f"{left_clean} {right_clean}".strip()
    if left_words == right_words:
        return right_clean if len(right_clean) >= len(left_clean) else left_clean

    left_norm = " ".join(left_words)
    right_norm = " ".join(right_words)
    if left_norm in right_norm and len(left_norm) / max(len(right_norm), 1) >= 0.45:
        return right_clean
    if right_norm in left_norm and len(right_norm) / max(len(left_norm), 1) >= 0.45:
        return left_clean

    max_overlap = min(len(left_words), len(right_words))
    overlap = 0
    for size in range(max_overlap, 0, -1):
        if left_words[-size:] == right_words[:size]:
            overlap = size
            break
    minimum_overlap = 2 if min(len(left_words), len(right_words)) <= 5 else 3
    if overlap >= minimum_overlap:
        right_original_words = right_clean.split()
        return f"{left_clean} {' '.join(right_original_words[overlap:])}".strip()
    return f"{left_clean} {right_clean}".strip()


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
                _merge_progressive_text(current.text, segment.text),
            )
        else:
            merged.append(current)
            current = segment
    merged.append(current)
    return merged


def _is_noise_segment(segment: TranscriptSegment) -> bool:
    normalized = " ".join(_normalize_words(segment.text))
    if not normalized:
        return True
    if normalized in {"aja", "ah", "eh", "em", "emm", "mmm", "este", "ya", "ok", "okay"}:
        return True
    if normalized in _NOISE_PHRASES:
        return True
    return False


def optimize_transcript_segments(
    segments: list[TranscriptSegment],
    *,
    maximum_gap_seconds: float = 6.0,
    remove_noise: bool = True,
) -> tuple[list[TranscriptSegment], TranscriptOptimizationStats]:
    """Compacta la fuente antes del modelo, conservando tiempos y hablantes."""

    original = list(segments)
    original_chars = sum(len(item.text) for item in original)
    filtered = [item for item in original if not (remove_noise and _is_noise_segment(item))]
    removed = len(original) - len(filtered)
    optimized = merge_adjacent_segments(filtered, maximum_gap_seconds=maximum_gap_seconds)
    optimized_chars = sum(len(item.text) for item in optimized)
    stats = TranscriptOptimizationStats(
        original_segments=len(original),
        optimized_segments=len(optimized),
        removed_noise_segments=removed,
        merged_segments=max(0, len(filtered) - len(optimized)),
        original_chars=original_chars,
        optimized_chars=optimized_chars,
    )
    return optimized, stats


def unique_speakers(segments: list[TranscriptSegment]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for segment in segments:
        speaker = segment.speaker.strip()
        if not is_valid_speaker_name(speaker):
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
