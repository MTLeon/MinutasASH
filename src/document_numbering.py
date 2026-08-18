from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass

_COMPONENT_RE = re.compile(r"[^A-Z0-9]+")


def normalize_component(value: str, fallback: str = "") -> str:
    text = _COMPONENT_RE.sub("", (value or "").upper().strip())
    return text or fallback


@dataclass(frozen=True)
class NumberingPolicy:
    document_type: str = "MRE"
    discipline: str = "PR"
    digits: int = 2

    def normalized(self) -> NumberingPolicy:
        return NumberingPolicy(
            document_type=normalize_component(self.document_type, "MRE"),
            discipline=normalize_component(self.discipline, "PR"),
            digits=max(2, min(int(self.digits), 5)),
        )


def build_minute_number(
    project_code: str,
    sequence: int,
    policy: NumberingPolicy | None = None,
) -> str:
    policy = (policy or NumberingPolicy()).normalized()
    project = normalize_component(project_code)
    if not project:
        raise ValueError("Ingrese un código de proyecto para sugerir el número de minuta.")
    if int(sequence) < 0:
        raise ValueError("El correlativo no puede ser negativo.")
    return f"{project}-{policy.document_type}-{policy.discipline}-{int(sequence):0{policy.digits}d}"


def _sequence_pattern(project_code: str, policy: NumberingPolicy) -> re.Pattern[str]:
    project = re.escape(normalize_component(project_code))
    document_type = re.escape(policy.document_type)
    discipline = re.escape(policy.discipline)
    return re.compile(
        rf"^{project}-{document_type}-{discipline}-(\d+)$",
        re.IGNORECASE,
    )


def next_sequence(
    existing_numbers: Iterable[str],
    project_code: str,
    policy: NumberingPolicy | None = None,
) -> int:
    normalized_policy = (policy or NumberingPolicy()).normalized()
    pattern = _sequence_pattern(project_code, normalized_policy)
    current = -1
    for number in existing_numbers:
        match = pattern.match((number or "").strip())
        if match:
            current = max(current, int(match.group(1)))
    return current + 1


def suggest_minute_number(
    repository,
    project_code: str,
    document_type: str = "MRE",
    discipline: str = "PR",
    digits: int = 2,
) -> str:
    policy = NumberingPolicy(document_type, discipline, digits).normalized()
    if hasattr(repository, "list_minute_numbers"):
        existing = repository.list_minute_numbers(project_code)
    else:
        existing = [
            str(row.get("minute_number") or "")
            for row in repository.list_meetings(limit=5000)
            if str(row.get("project_code") or "").upper() == project_code.upper()
        ]
    return build_minute_number(
        project_code,
        next_sequence(existing, project_code, policy),
        policy,
    )
