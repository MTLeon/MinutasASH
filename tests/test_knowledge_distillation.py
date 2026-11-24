from pathlib import Path

from docx import Document

from src.knowledge_distillation import extract_reference_items


def test_extracts_items_only_from_a_reference_matrix(tmp_path: Path):
    reference = tmp_path / "minuta.docx"
    document = Document()
    table = document.add_table(rows=3, cols=4)
    for cell, value in zip(
        table.rows[0].cells, ("N°", "Descripción", "Acción", "Responsable"), strict=True
    ):
        cell.text = value
    for cell, value in zip(
        table.rows[1].cells,
        ("1", "Emitir planos IFC", "Enviar el viernes", "Ivan Tapia"),
        strict=True,
    ):
        cell.text = value
    for cell, value in zip(
        table.rows[2].cells, ("2", "Estado de acreditación vigente", "", "Informativo"), strict=True
    ):
        cell.text = value
    document.save(reference)

    items, warnings = extract_reference_items(reference)

    assert warnings == []
    assert [item.description for item in items] == [
        "Emitir planos IFC",
        "Estado de acreditación vigente",
    ]
    assert items[0].category == "compromiso"
    assert items[0].responsible == "Ivan Tapia"
    assert items[1].category == "informativo"
    assert items[1].responsible is None
