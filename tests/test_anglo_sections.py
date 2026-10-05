from src.anglo_sections import classify_anglo_section
from src.models import MeetingItem


def test_classifies_operational_sections_without_overriding_unknown_items() -> None:
    assert (
        classify_anglo_section(
            MeetingItem(category="informativo", description="Se reportó un incidente de seguridad.")
        )
        == "HSE"
    )
    assert (
        classify_anglo_section(
            MeetingItem(category="compromiso", description="Actualizar cronograma de avance.")
        )
        == "Control y Programación"
    )
    assert (
        classify_anglo_section(
            MeetingItem(category="pendiente", description="Responder RFI de ingeniería.")
        )
        == "Ingeniería"
    )
    assert (
        classify_anglo_section(
            MeetingItem(category="acuerdo", description="Coordinar próxima reunión.")
        )
        == "Otros/General"
    )
