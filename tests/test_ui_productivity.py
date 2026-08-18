from __future__ import annotations

from src.ui_productivity import (
    history_matches,
    is_person_label,
    is_provisional_project_code,
    natural_sort_key,
    selection_range,
    unique_person_labels,
)


def test_provisional_project_codes_are_rejected_without_blocking_real_codes() -> None:
    assert is_provisional_project_code("0")
    assert is_provisional_project_code("sin proyecto")
    assert not is_provisional_project_code("P0001")
    assert not is_provisional_project_code("2986")


def test_non_person_transcript_labels_are_filtered_accent_insensitively() -> None:
    assert not is_person_label("Notas de reunión")
    assert not is_person_label("Hablante no identificado")
    assert unique_person_labels(
        ["Notas de reunión", "Ana Pérez", "ana pérez", "Transcripción automática"]
    ) == ["Ana Pérez"]


def test_selection_range_is_inclusive_and_direction_independent() -> None:
    children = ("1", "2", "3", "4")
    assert selection_range(children, "2", "4") == ("2", "3", "4")
    assert selection_range(children, "4", "2") == ("2", "3", "4")
    assert selection_range(children, "missing", "2") == ()


def test_history_search_is_accent_insensitive_and_covers_useful_fields() -> None:
    row = {
        "id": 7,
        "meeting_date": "2026-08-10",
        "minute_number": "P2986-MRE-PR-03",
        "project_code": "P2986",
        "matter": "Reunión de coordinación interna",
        "status": "procesada",
    }
    assert history_matches(row, "coordinacion")
    assert history_matches(row, "MRE-PR-03")
    assert not history_matches(row, "cliente inexistente")


def test_natural_sort_places_numeric_suffixes_in_human_order() -> None:
    assert sorted(["P10", "P2", "P1"], key=natural_sort_key) == ["P1", "P2", "P10"]
