from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from src.catalog_models import ClientRecord, ContactRecord, OrganizationRecord, ProjectCatalogRecord
from src.database import CURRENT_SCHEMA_VERSION, AppDatabase


class Catalogs23Tests(unittest.TestCase):
    def test_schema_and_catalog_roundtrip(self) -> None:
        with TemporaryDirectory() as temp:
            db = AppDatabase(Path(temp) / "minutas.db")
            self.assertEqual(db.get_schema_version(), CURRENT_SCHEMA_VERSION)
            organization_id = db.upsert_organization(
                OrganizationRecord(legal_name="ASH Ingeniería y Proyectos", short_name="ASH")
            )
            client_id = db.upsert_client(
                ClientRecord(
                    legal_name="Cliente de Prueba S.A.", short_name="Cliente", organization_id=None
                )
            )
            contact_id = db.upsert_contact_record(
                ContactRecord(
                    name="Persona de Prueba",
                    email="persona@example.com",
                    role="Especialista",
                    organization="Cliente",
                    organization_id=organization_id,
                    client_id=client_id,
                )
            )
            db.upsert_project_profile(
                ProjectCatalogRecord(
                    code="P0001",
                    description="Proyecto piloto",
                    client="Cliente",
                    client_id=client_id,
                    project_manager="Persona de Prueba",
                ).model_dump()
            )
            self.assertEqual(db.get_organization(organization_id)["short_name"], "ASH")
            self.assertEqual(db.get_client(client_id)["short_name"], "Cliente")
            self.assertEqual(db.get_contact_record(contact_id)["email"], "persona@example.com")
            self.assertEqual(db.get_project("P0001")["client_id"], client_id)
            events = db.list_audit_events()
            self.assertGreaterEqual(len(events), 3)
            self.assertTrue(all(event.get("app_version") == "2.3.8" for event in events[:3]))

    def test_deactivation_keeps_historical_record(self) -> None:
        with TemporaryDirectory() as temp:
            db = AppDatabase(Path(temp) / "minutas.db")
            client_id = db.upsert_client(ClientRecord(legal_name="Cliente Inactivo"))
            db.deactivate_record("clients", client_id)
            self.assertIsNotNone(db.get_client(client_id))
            self.assertEqual(db.list_clients(), [])
            self.assertEqual(len(db.list_clients(include_inactive=True)), 1)
            db.set_record_active("clients", client_id, True)
            self.assertEqual(len(db.list_clients()), 1)


if __name__ == "__main__":
    unittest.main()
