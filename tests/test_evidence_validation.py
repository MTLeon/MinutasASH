from __future__ import annotations

from src.evidence_validation import annotate_evidence, timestamp_seconds, verify_item_evidence
from src.models import MeetingItem
from src.vtt_reader import TranscriptSegment


def segment(start: str, end: str, text: str) -> TranscriptSegment:
    return TranscriptSegment(start, end, "Ana", text)


def test_timestamp_accepts_short_and_full_formats():
    assert timestamp_seconds("01:02.500") == 62.5
    assert timestamp_seconds("01:01:02,500") == 3662.5
    assert timestamp_seconds("invalida") is None


def test_evidence_is_verified_from_nearby_context():
    item = MeetingItem(
        category="compromiso",
        description="Ana enviará el informe de costos",
        responsible="Ana",
        evidence="00:00:12.000",
    )
    segments = [
        segment("00:00:10.000", "00:00:15.000", "Yo enviaré el informe de costos mañana."),
    ]
    check = verify_item_evidence(item, segments)
    assert check.verified is True
    assert check.score is not None and check.score >= 0.18


def test_weak_or_distant_evidence_is_rejected():
    item = MeetingItem(
        category="acuerdo",
        description="Se aprobó el presupuesto anual",
        evidence="00:02:00.000",
    )
    segments = [segment("00:00:01.000", "00:00:03.000", "Buenos días a todos.")]
    check = verify_item_evidence(item, segments)
    assert check.verified is False
    assert check.score == 0.0


def test_missing_evidence_is_not_applicable():
    item = MeetingItem(category="informativo", description="Estado general")
    check = verify_item_evidence(item, [])
    assert check.verified is None
    assert check.score is None


def test_annotation_recovers_missing_evidence_from_best_segment():
    item = MeetingItem(
        category="compromiso",
        description="Ana enviará el informe de costos",
        responsible="Ana",
    )
    checks = annotate_evidence(
        [item],
        [
            segment("00:00:01.000", "00:00:03.000", "Buenos días."),
            segment("00:00:10.000", "00:00:14.000", "Enviaré el informe de costos mañana."),
        ],
    )
    assert item.evidence == "00:00:10.000"
    assert item.source_speaker == "Ana"
    assert checks[0].verified is True


def test_annotation_does_not_invent_unrelated_evidence():
    item = MeetingItem(category="acuerdo", description="Aprobar presupuesto anual")
    checks = annotate_evidence(
        [item],
        [segment("00:00:01.000", "00:00:03.000", "Buenos días a todos.")],
    )
    assert item.evidence is None
    assert checks[0].verified is False


def test_annotation_updates_items():
    item = MeetingItem(
        category="pendiente",
        description="Confirmar fecha de entrega final",
        evidence="00:00:05.000",
    )
    checks = annotate_evidence(
        [item],
        [segment("00:00:04.000", "00:00:07.000", "Falta confirmar fecha de entrega final.")],
    )
    assert len(checks) == 1
    assert item.evidence_verified is True
    assert item.evidence_score == checks[0].score
