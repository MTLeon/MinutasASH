from __future__ import annotations

import json
import re
import unicodedata
from dataclasses import dataclass
from difflib import SequenceMatcher
from pathlib import Path

from src.models import MeetingItem

_WORD_RE = re.compile(r"[a-z0-9]+", re.IGNORECASE)
_STOPWORDS = {
    "acuerdo",
    "compromiso",
    "el",
    "en",
    "informativo",
    "la",
    "las",
    "los",
    "para",
    "pendiente",
    "persona",
    "por",
    "queda",
    "riesgo",
    "un",
    "una",
    "y",
}
_DATE_FILLER = {"a", "al", "de", "del", "el", "la", "las", "los", "para"}


def _ascii_text(value: str | None) -> str:
    normalized = unicodedata.normalize("NFKD", value or "")
    return normalized.encode("ascii", "ignore").decode("ascii").casefold()


def _tokens(value: str | None) -> set[str]:
    ascii_text = _ascii_text(value)
    return {
        word
        for word in _WORD_RE.findall(ascii_text)
        if len(word) > 2 and word not in _STOPWORDS and not re.fullmatch(r"p\d+", word)
    }


def _equivalent_token(left: str, right: str) -> bool:
    if left == right:
        return True
    return min(len(left), len(right)) >= 5 and SequenceMatcher(None, left, right).ratio() >= 0.78


def description_similarity(left: str, right: str) -> float:
    left_tokens, right_tokens = _tokens(left), _tokens(right)
    if not left_tokens and not right_tokens:
        return 1.0
    unmatched = set(right_tokens)
    matches = 0
    for token in left_tokens:
        candidates = [candidate for candidate in unmatched if _equivalent_token(token, candidate)]
        if not candidates:
            continue
        best = max(
            candidates, key=lambda candidate: SequenceMatcher(None, token, candidate).ratio()
        )
        unmatched.remove(best)
        matches += 1
    return 2 * matches / max(1, len(left_tokens) + len(right_tokens))


@dataclass(frozen=True)
class EvaluationReport:
    expected: int
    detected: int
    matched: int
    precision: float
    recall: float
    f1: float
    responsible_accuracy: float
    due_date_accuracy: float
    evidence_coverage: float
    false_positives: int
    false_negatives: int
    duplicate_count: int
    unmatched_expected: tuple[int, ...]
    unmatched_detected: tuple[int, ...]


def evaluate_items(
    expected: list[MeetingItem], detected: list[MeetingItem], *, similarity_threshold: float = 0.35
) -> EvaluationReport:
    available = set(range(len(detected)))
    matches: list[tuple[int, int]] = []
    for expected_index, reference in enumerate(expected):
        candidates = [
            (description_similarity(reference.description, detected[index].description), index)
            for index in available
            if reference.category == detected[index].category
        ]
        if candidates:
            score, detected_index = max(candidates)
            if score >= similarity_threshold:
                matches.append((expected_index, detected_index))
                available.remove(detected_index)
    matched = len(matches)
    precision = matched / len(detected) if detected else (1.0 if not expected else 0.0)
    recall = matched / len(expected) if expected else 1.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0

    def field_accuracy(field: str) -> float:
        comparable = [pair for pair in matches if getattr(expected[pair[0]], field)]
        if not comparable:
            return 1.0

        def field_matches(reference: str | None, actual: str | None) -> bool:
            if field != "due_date_text":
                return _ascii_text(reference) == _ascii_text(actual)
            reference_tokens = {
                token
                for token in _WORD_RE.findall(_ascii_text(reference))
                if token not in _DATE_FILLER
            }
            actual_tokens = {
                token
                for token in _WORD_RE.findall(_ascii_text(actual))
                if token not in _DATE_FILLER
            }
            return bool(reference_tokens) and reference_tokens <= actual_tokens

        correct = sum(
            field_matches(getattr(expected[a], field), getattr(detected[b], field))
            for a, b in comparable
        )
        return correct / len(comparable)

    duplicate_count = 0
    for index, item in enumerate(detected):
        if any(
            item.category == previous.category
            and description_similarity(item.description, previous.description) >= 0.75
            for previous in detected[:index]
        ):
            duplicate_count += 1

    return EvaluationReport(
        expected=len(expected),
        detected=len(detected),
        matched=matched,
        precision=precision,
        recall=recall,
        f1=f1,
        responsible_accuracy=field_accuracy("responsible"),
        due_date_accuracy=field_accuracy("due_date_text"),
        evidence_coverage=sum(bool(item.evidence) for item in detected) / max(1, len(detected)),
        false_positives=len(detected) - matched,
        false_negatives=len(expected) - matched,
        duplicate_count=duplicate_count,
        unmatched_expected=tuple(sorted(set(range(len(expected))) - {a for a, _ in matches})),
        unmatched_detected=tuple(sorted(available)),
    )


def load_items(path: str | Path) -> list[MeetingItem]:
    payload = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    if isinstance(payload, dict):
        payload = payload.get("items", [])
    if not isinstance(payload, list):
        raise ValueError("El archivo de evaluación debe contener una lista o un objeto con items.")
    return [MeetingItem.model_validate(item) for item in payload]


def evaluate_files(expected_path: str | Path, detected_path: str | Path) -> EvaluationReport:
    return evaluate_items(load_items(expected_path), load_items(detected_path))


def save_report(report: EvaluationReport, destination: str | Path) -> Path:
    target = Path(destination)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(report.__dict__, ensure_ascii=False, indent=2), encoding="utf-8")
    return target
