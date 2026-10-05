from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from src.database import AppDatabase
from src.standard_library import StandardLibraryService, select_document_format


def test_library_copies_reference_and_preserves_project_scope() -> None:
    with TemporaryDirectory() as temp:
        root = Path(temp)
        source = root / "estandar.doc"
        source.write_bytes(b"standard")
        db = AppDatabase(root / "data" / "minutas.db")
        with patch("src.standard_library.references_dir", return_value=root / "references"):
            service = StandardLibraryService(db)
            reference_id = service.install(
                source,
                title="Formato Anglo American",
                reference_type="format",
                project_code="P3165",
                client="Anglo American",
            )
        reference = db.get_standard_reference(reference_id)
        assert reference is not None
        assert Path(reference["file_path"]).is_file()
        assert db.list_standard_references(project_code="P3165")
        db.set_standard_reference_active(reference_id, False)
        assert not db.list_standard_references(include_inactive=False)


def test_select_document_format_prefers_project_and_tolerates_client_legal_suffix() -> None:
    references = [
        {
            "id": 1,
            "reference_type": "format",
            "project_code": None,
            "client": "Anglo American Sur",
            "file_path": "generic.docx",
        },
        {
            "id": 2,
            "reference_type": "format",
            "project_code": "3165",
            "client": "Anglo American Sur",
            "file_path": "3165.docx",
        },
    ]
    selected = select_document_format(references, "3165", "Anglo American Sur S.A.")
    assert selected is not None
    assert selected["id"] == 2
