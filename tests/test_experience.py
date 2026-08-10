from __future__ import annotations

import unittest

from src.experience import (
    attendee_display_columns,
    attendee_readiness,
    interface_mode_label,
    meeting_readiness,
    meeting_type_from_label,
    meeting_type_label,
    normalize_interface_mode,
    parse_drop_paths,
    review_display_columns,
    suggested_matter,
)
from src.models import Attendee, MeetingMetadata


class ExperienceTests(unittest.TestCase):
    def test_interface_modes_are_normalized(self):
        self.assertEqual(normalize_interface_mode("advanced"), "advanced")
        self.assertEqual(normalize_interface_mode("anything"), "essential")
        self.assertEqual(interface_mode_label("essential"), "Vista esencial")

    def test_meeting_type_labels_roundtrip(self):
        self.assertEqual(meeting_type_from_label("KOM / inicio de proyecto"), "kom")
        self.assertEqual(meeting_type_label("seguimiento"), "Seguimiento técnico")
        self.assertIn("inicio", suggested_matter("kom").lower())

    def test_attendee_readiness_flags_missing_organization(self):
        attendee = Attendee(name="Carlos Pérez", initials="ML", organization="Por confirmar")
        readiness = attendee_readiness(attendee)
        self.assertFalse(readiness.complete)
        self.assertIn("organización", readiness.missing)

    def test_meeting_readiness_counts_essential_fields(self):
        metadata = MeetingMetadata(
            project_code="P3261",
            matter="Coordinación",
            meeting_date="2026-07-31",
            document_date="2026-07-31",
            minute_taker="Carlos Pérez",
        )
        readiness = meeting_readiness(metadata, has_vtt=True)
        self.assertTrue(readiness.ready)
        self.assertEqual(readiness.completed, readiness.total)

    def test_display_columns_depend_on_mode(self):
        self.assertEqual(attendee_display_columns("essential"), ("name", "organization", "status"))
        self.assertIn("email", attendee_display_columns("advanced"))
        self.assertEqual(review_display_columns("essential"), ("status", "project", "description", "responsible", "date"))
        self.assertIn("quality", review_display_columns("advanced"))

    def test_drop_parser_supports_windows_paths_with_spaces(self):
        data = r"{C:\Users\mleon\Downloads\Reunión prueba.vtt} C:\temp\otra.vtt"
        self.assertEqual(
            parse_drop_paths(data),
            [r"C:\Users\mleon\Downloads\Reunión prueba.vtt", r"C:\temp\otra.vtt"],
        )


if __name__ == "__main__":
    unittest.main()
