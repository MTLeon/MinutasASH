from src.evaluation import description_similarity, evaluate_files, evaluate_items, save_report
from src.models import MeetingItem


def item(category: str, description: str, **values) -> MeetingItem:
    return MeetingItem(category=category, description=description, **values)


def test_evaluation_reports_matches_and_field_accuracy():
    expected = [
        item(
            "compromiso",
            "Diego enviará los planos eléctricos",
            responsible="Diego",
            due_date_text="lunes",
        ),
        item("pendiente", "Confirmar el número de señales"),
    ]
    detected = [
        item(
            "compromiso",
            "Diego enviará planos eléctricos el lunes",
            responsible="Diego",
            due_date_text="lunes",
            evidence="00:02:00",
        ),
        item("informativo", "Se revisó el cronograma"),
    ]
    report = evaluate_items(expected, detected)
    assert report.matched == 1
    assert report.precision == report.recall == 0.5
    assert report.responsible_accuracy == 1.0
    assert report.evidence_coverage == 0.5
    assert report.unmatched_expected == (1,)
    assert report.unmatched_detected == (1,)
    assert report.false_positives == 1
    assert report.false_negatives == 1


def test_empty_evaluation_is_perfect_and_safe():
    report = evaluate_items([], [])
    assert report.precision == report.recall == report.f1 == 1.0


def test_evaluation_files_and_report_roundtrip(tmp_path):
    expected = tmp_path / "expected.json"
    detected = tmp_path / "detected.json"
    expected.write_text(
        '{"items":[{"category":"acuerdo","description":"Aprobar diseño"}]}', encoding="utf-8"
    )
    detected.write_text(
        '[{"category":"acuerdo","description":"Aprobar el diseño"}]', encoding="utf-8"
    )
    report = evaluate_files(expected, detected)
    output = save_report(report, tmp_path / "report.json")
    assert report.f1 == 1.0
    assert '"false_positives": 0' in output.read_text(encoding="utf-8")


def test_similarity_handles_spanish_inflection_and_context():
    assert (
        description_similarity(
            "Preparar la matriz de interfaces",
            "Persona A preparara la matriz de interfaces para el martes",
        )
        >= 0.35
    )
    assert (
        description_similarity(
            "Revisar el presupuesto",
            "Para P9002, revisare el presupuesto manana",
        )
        >= 0.35
    )
    assert (
        description_similarity(
            "Enviar el informe",
            "Persona A enviara el informe el lunes",
        )
        >= 0.35
    )


def test_similarity_rejects_unrelated_descriptions():
    assert description_similarity("Enviar planos electricos", "Revisar contrato comercial") < 0.35


def test_due_date_accuracy_accepts_equivalent_detail_without_hiding_missing_detail():
    expected = [item("informativo", "Proxima reunion", due_date_text="jueves")]
    detected = [item("informativo", "La proxima reunion", due_date_text="el jueves a las diez")]
    assert evaluate_items(expected, detected).due_date_accuracy == 1.0

    expected_with_time = [item("informativo", "Proxima reunion", due_date_text="jueves a las diez")]
    detected_without_time = [item("informativo", "La proxima reunion", due_date_text="jueves")]
    assert evaluate_items(expected_with_time, detected_without_time).due_date_accuracy == 0.0
