from __future__ import annotations

import getpass
import hashlib
import json
import platform
import re
import sqlite3
import unicodedata
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

from src.catalog_models import (
    AuditEvent,
    ClientRecord,
    ContactRecord,
    OrganizationRecord,
    TemplateManifest,
    TemplateValidation,
)
from src.models import Attendee, MeetingMetadata, MinuteAnalysis
from src.release_identity import APP_VERSION
from src.runtime_paths import database_path

CURRENT_SCHEMA_VERSION = 8


def _inserted_id(cursor: sqlite3.Cursor) -> int:
    if cursor.lastrowid is None:
        raise RuntimeError("SQLite no devolvió el identificador insertado.")
    return int(cursor.lastrowid)


def normalize_name(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value or "")
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
    return re.sub(r"\s+", " ", ascii_text.casefold()).strip()


def _sha256_file(path: str | Path) -> str | None:
    candidate = Path(path)
    if not candidate.is_file():
        return None
    digest = hashlib.sha256()
    try:
        with candidate.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
    except OSError:
        return None
    return digest.hexdigest()


class AppDatabase:
    """Repositorio SQLite local con migraciones incrementales."""

    def __init__(self, path: Path | None = None) -> None:
        self.path = path or database_path()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.path, timeout=5.0)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys=ON")
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("PRAGMA synchronous=NORMAL")
        connection.execute("PRAGMA busy_timeout=5000")
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def _backup_before_migration(self, from_version: int) -> Path | None:
        if not self.path.exists() or self.path.stat().st_size == 0:
            return None
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        destination = self.path.with_name(
            f"{self.path.stem}_backup_schema_{from_version}_{timestamp}{self.path.suffix}"
        )
        source = sqlite3.connect(self.path)
        target = sqlite3.connect(destination)
        try:
            source.backup(target)
            target.commit()
        finally:
            target.close()
            source.close()
        return destination

    @staticmethod
    def _table_exists(db: sqlite3.Connection, table: str) -> bool:
        row = db.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
            (table,),
        ).fetchone()
        return row is not None

    @staticmethod
    def _column_exists(db: sqlite3.Connection, table: str, column: str) -> bool:
        return any(row[1] == column for row in db.execute(f"PRAGMA table_info({table})"))

    def _detect_schema_version(self, db: sqlite3.Connection) -> int:
        db.execute(
            """
            CREATE TABLE IF NOT EXISTS app_schema (
                id INTEGER PRIMARY KEY CHECK(id = 1),
                version INTEGER NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        row = db.execute("SELECT version FROM app_schema WHERE id=1").fetchone()
        if row:
            return int(row[0])
        # Una base de la versión 5.0.0 ya contiene contacts/meetings pero no
        # app_schema. Se reconoce como esquema 1 para migrarla sin perder datos.
        legacy = self._table_exists(db, "contacts") or self._table_exists(db, "meetings")
        version = 1 if legacy else 0
        db.execute(
            "INSERT OR REPLACE INTO app_schema(id, version, updated_at) VALUES(1, ?, ?)",
            (version, datetime.now().isoformat(timespec="seconds")),
        )
        return version

    def _set_schema_version(self, db: sqlite3.Connection, version: int) -> None:
        db.execute(
            "INSERT OR REPLACE INTO app_schema(id, version, updated_at) VALUES(1, ?, ?)",
            (version, datetime.now().isoformat(timespec="seconds")),
        )

    def _migration_1(self, db: sqlite3.Connection) -> None:
        db.executescript(
            """
            CREATE TABLE IF NOT EXISTS contacts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                normalized_name TEXT NOT NULL UNIQUE,
                name TEXT NOT NULL,
                initials TEXT,
                email TEXT,
                role TEXT,
                organization TEXT,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS projects (
                code TEXT PRIMARY KEY,
                description TEXT,
                client TEXT,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS meetings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                minute_number TEXT,
                meeting_date TEXT,
                project_code TEXT NOT NULL DEFAULT '',
                matter TEXT,
                client TEXT,
                source_vtt TEXT,
                output_dir TEXT,
                docx_path TEXT,
                json_path TEXT,
                status TEXT NOT NULL,
                model TEXT,
                metadata_json TEXT NOT NULL,
                analysis_json TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_meetings_date
                ON meetings(meeting_date DESC, id DESC);
            CREATE INDEX IF NOT EXISTS idx_meetings_project
                ON meetings(project_code, meeting_date DESC);
            """
        )

    def _migration_2(self, db: sqlite3.Connection) -> None:
        additions = {
            "app_version": "TEXT",
            "document_provider": "TEXT",
            "source_sha256": "TEXT",
            "last_error": "TEXT",
        }
        for name, data_type in additions.items():
            if not self._column_exists(db, "meetings", name):
                db.execute(f"ALTER TABLE meetings ADD COLUMN {name} {data_type}")
        db.execute("CREATE INDEX IF NOT EXISTS idx_meetings_number ON meetings(minute_number)")

    def _migration_3(self, db: sqlite3.Connection) -> None:
        additions = {
            "processing_provider": "TEXT",
            "processing_provider_name": "TEXT",
        }
        for name, data_type in additions.items():
            if not self._column_exists(db, "meetings", name):
                db.execute(f"ALTER TABLE meetings ADD COLUMN {name} {data_type}")
        db.execute(
            "CREATE INDEX IF NOT EXISTS idx_meetings_provider ON meetings(processing_provider)"
        )

    def _migration_4(self, db: sqlite3.Connection) -> None:
        db.execute(
            """
            CREATE TABLE IF NOT EXISTS projects (
                code TEXT PRIMARY KEY,
                description TEXT,
                client TEXT,
                updated_at TEXT NOT NULL DEFAULT ''
            )
            """
        )
        project_additions = {
            "project_manager": "TEXT",
            "approver": "TEXT",
            "default_minute_taker": "TEXT",
            "default_location": "TEXT",
            "document_type": "TEXT",
            "discipline": "TEXT",
        }
        for name, data_type in project_additions.items():
            if not self._column_exists(db, "projects", name):
                db.execute(f"ALTER TABLE projects ADD COLUMN {name} {data_type}")
        db.executescript(
            """
            CREATE TABLE IF NOT EXISTS project_members (
                project_code TEXT NOT NULL,
                normalized_name TEXT NOT NULL,
                display_name TEXT NOT NULL,
                sort_order INTEGER NOT NULL DEFAULT 0,
                PRIMARY KEY(project_code, normalized_name),
                FOREIGN KEY(project_code) REFERENCES projects(code) ON DELETE CASCADE
            );
            CREATE INDEX IF NOT EXISTS idx_project_members_project
                ON project_members(project_code, sort_order, display_name);
            """
        )

    def _migration_5(self, db: sqlite3.Connection) -> None:
        contact_additions = {
            "phone": "TEXT",
            "active": "INTEGER NOT NULL DEFAULT 1",
            "notes": "TEXT",
            "organization_id": "INTEGER",
            "client_id": "INTEGER",
        }
        for name, data_type in contact_additions.items():
            if not self._column_exists(db, "contacts", name):
                db.execute(f"ALTER TABLE contacts ADD COLUMN {name} {data_type}")

        project_additions = {
            "client_id": "INTEGER",
            "template_version_id": "INTEGER",
            "folder_path": "TEXT",
            "active": "INTEGER NOT NULL DEFAULT 1",
        }
        for name, data_type in project_additions.items():
            if not self._column_exists(db, "projects", name):
                db.execute(f"ALTER TABLE projects ADD COLUMN {name} {data_type}")

        meeting_additions = {
            "template_version_id": "INTEGER",
            "template_key": "TEXT",
            "template_version_label": "TEXT",
        }
        for name, data_type in meeting_additions.items():
            if not self._column_exists(db, "meetings", name):
                db.execute(f"ALTER TABLE meetings ADD COLUMN {name} {data_type}")

        db.executescript(
            """
            CREATE TABLE IF NOT EXISTS organizations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                normalized_name TEXT NOT NULL UNIQUE,
                legal_name TEXT NOT NULL,
                short_name TEXT,
                tax_id TEXT,
                address TEXT,
                email TEXT,
                phone TEXT,
                active INTEGER NOT NULL DEFAULT 1,
                notes TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS clients (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                organization_id INTEGER,
                normalized_name TEXT NOT NULL UNIQUE,
                legal_name TEXT NOT NULL,
                short_name TEXT,
                tax_id TEXT,
                address TEXT,
                primary_contact_name TEXT,
                primary_contact_email TEXT,
                primary_contact_phone TEXT,
                active INTEGER NOT NULL DEFAULT 1,
                notes TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY(organization_id) REFERENCES organizations(id)
            );

            CREATE TABLE IF NOT EXISTS project_contacts (
                project_code TEXT NOT NULL,
                contact_id INTEGER NOT NULL,
                role_label TEXT,
                sort_order INTEGER NOT NULL DEFAULT 0,
                PRIMARY KEY(project_code, contact_id),
                FOREIGN KEY(project_code) REFERENCES projects(code) ON DELETE CASCADE,
                FOREIGN KEY(contact_id) REFERENCES contacts(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS document_templates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                template_key TEXT NOT NULL UNIQUE,
                display_name TEXT NOT NULL,
                document_type TEXT NOT NULL,
                description TEXT,
                active_version_id INTEGER,
                active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS template_versions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                template_id INTEGER NOT NULL,
                version_label TEXT NOT NULL,
                file_path TEXT NOT NULL,
                sha256 TEXT NOT NULL,
                state TEXT NOT NULL,
                manifest_json TEXT NOT NULL,
                validation_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                activated_at TEXT,
                UNIQUE(template_id, version_label),
                FOREIGN KEY(template_id) REFERENCES document_templates(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS audit_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                windows_user TEXT NOT NULL,
                machine_name TEXT NOT NULL,
                action TEXT NOT NULL,
                entity_type TEXT NOT NULL,
                entity_id TEXT,
                before_json TEXT,
                after_json TEXT,
                app_version TEXT
            );

            CREATE INDEX IF NOT EXISTS idx_clients_name ON clients(normalized_name);
            CREATE INDEX IF NOT EXISTS idx_organizations_name ON organizations(normalized_name);
            CREATE INDEX IF NOT EXISTS idx_template_versions_template ON template_versions(template_id, created_at DESC);
            CREATE INDEX IF NOT EXISTS idx_audit_created ON audit_events(created_at DESC);
            CREATE INDEX IF NOT EXISTS idx_projects_client_id ON projects(client_id);
            """
        )

    def _migration_6(self, db: sqlite3.Connection) -> None:
        """Entradas flexibles, papelera segura y base de aprendizaje local."""

        meeting_additions = {
            "source_type": "TEXT NOT NULL DEFAULT 'vtt'",
            "source_quality": "TEXT NOT NULL DEFAULT 'alta'",
            "is_test": "INTEGER NOT NULL DEFAULT 0",
            "deleted_at": "TEXT",
            "deleted_by": "TEXT",
            "deletion_reason": "TEXT",
            "trash_path": "TEXT",
            "original_output_dir": "TEXT",
            "original_status": "TEXT",
        }
        for name, data_type in meeting_additions.items():
            if not self._column_exists(db, "meetings", name):
                db.execute(f"ALTER TABLE meetings ADD COLUMN {name} {data_type}")
        db.execute(
            """
            UPDATE meetings SET source_type = CASE
                WHEN LOWER(COALESCE(source_vtt, '')) LIKE '%.docx' THEN 'docx'
                WHEN LOWER(COALESCE(source_vtt, '')) LIKE '%.txt' THEN 'txt'
                ELSE 'vtt'
            END
            WHERE source_type IS NULL OR source_type=''
            """
        )
        db.executescript(
            """
            CREATE INDEX IF NOT EXISTS idx_meetings_deleted
                ON meetings(deleted_at, is_test, updated_at DESC);
            CREATE INDEX IF NOT EXISTS idx_meetings_source_type
                ON meetings(source_type, source_quality);

            CREATE TABLE IF NOT EXISTS technical_terms (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                normalized_term TEXT NOT NULL,
                canonical_term TEXT NOT NULL,
                variants_json TEXT NOT NULL DEFAULT '[]',
                category TEXT,
                project_code TEXT,
                active INTEGER NOT NULL DEFAULT 1,
                notes TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                UNIQUE(normalized_term, project_code)
            );

            CREATE TABLE IF NOT EXISTS correction_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                meeting_id INTEGER,
                item_index INTEGER,
                correction_type TEXT NOT NULL,
                before_json TEXT,
                after_json TEXT,
                approved_for_learning INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                created_by TEXT NOT NULL,
                FOREIGN KEY(meeting_id) REFERENCES meetings(id) ON DELETE SET NULL
            );

            CREATE TABLE IF NOT EXISTS learning_samples (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                meeting_id INTEGER,
                source_sha256 TEXT,
                source_type TEXT NOT NULL,
                meeting_type TEXT,
                project_code TEXT,
                approved INTEGER NOT NULL DEFAULT 0,
                anonymized INTEGER NOT NULL DEFAULT 0,
                approved_by TEXT,
                approved_at TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY(meeting_id) REFERENCES meetings(id) ON DELETE SET NULL
            );
            CREATE INDEX IF NOT EXISTS idx_learning_samples_approved
                ON learning_samples(approved, meeting_type, project_code);
            """
        )

    def _migration_7(self, db: sqlite3.Connection) -> None:
        """Aislamiento de aprendizaje por cliente y exclusión explícita."""

        additions = {
            "client_scope": "TEXT NOT NULL DEFAULT ''",
            "excluded_reason": "TEXT",
        }
        for name, data_type in additions.items():
            if not self._column_exists(db, "learning_samples", name):
                db.execute(f"ALTER TABLE learning_samples ADD COLUMN {name} {data_type}")
        db.execute(
            """
            UPDATE learning_samples
            SET client_scope=UPPER(TRIM(COALESCE((
                SELECT client FROM meetings WHERE meetings.id=learning_samples.meeting_id
            ), '')))
            WHERE client_scope IS NULL OR client_scope=''
            """
        )
        db.execute(
            """CREATE INDEX IF NOT EXISTS idx_learning_samples_client
               ON learning_samples(approved, client_scope, project_code, meeting_type)"""
        )

    def _migration_8(self, db: sqlite3.Connection) -> None:
        """Persistencia del PDF emitido junto al documento Word."""

        if not self._column_exists(db, "meetings", "pdf_path"):
            db.execute("ALTER TABLE meetings ADD COLUMN pdf_path TEXT")

    def _initialize(self) -> None:
        with self.connect() as db:
            version = self._detect_schema_version(db)
        if version > CURRENT_SCHEMA_VERSION:
            raise RuntimeError(
                "La base local fue creada por una versión más reciente de Minutas ASH."
            )
        if version < CURRENT_SCHEMA_VERSION:
            self._backup_before_migration(version)
        with self.connect() as db:
            version = self._detect_schema_version(db)
            migrations = {
                1: self._migration_1,
                2: self._migration_2,
                3: self._migration_3,
                4: self._migration_4,
                5: self._migration_5,
                6: self._migration_6,
                7: self._migration_7,
                8: self._migration_8,
            }
            while version < CURRENT_SCHEMA_VERSION:
                target = version + 1
                migration = migrations[target]
                migration(db)
                self._set_schema_version(db, target)
                version = target

    def get_schema_version(self) -> int:
        with self.connect() as db:
            row = db.execute("SELECT version FROM app_schema WHERE id=1").fetchone()
        return int(row[0]) if row else 0

    def upsert_contact(self, attendee: Attendee) -> None:
        key = normalize_name(attendee.name)
        if not key:
            return
        now = datetime.now().isoformat(timespec="seconds")
        with self.connect() as db:
            db.execute(
                """
                INSERT INTO contacts (
                    normalized_name, name, initials, email, role, organization, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(normalized_name) DO UPDATE SET
                    name=excluded.name,
                    initials=COALESCE(excluded.initials, contacts.initials),
                    email=COALESCE(excluded.email, contacts.email),
                    role=COALESCE(excluded.role, contacts.role),
                    organization=COALESCE(excluded.organization, contacts.organization),
                    updated_at=excluded.updated_at
                """,
                (
                    key,
                    attendee.name,
                    attendee.initials,
                    attendee.email,
                    attendee.role,
                    attendee.organization,
                    now,
                ),
            )

    def list_contacts(self) -> list[Attendee]:
        with self.connect() as db:
            rows = db.execute(
                "SELECT * FROM contacts WHERE COALESCE(active, 1)=1 ORDER BY name COLLATE NOCASE"
            ).fetchall()
        return [
            Attendee(
                id=row["id"],
                initials=row["initials"],
                name=row["name"],
                email=row["email"],
                role=row["role"],
                organization=row["organization"],
            )
            for row in rows
        ]

    def find_contact(self, name: str) -> Attendee | None:
        key = normalize_name(name)
        if not key:
            return None
        with self.connect() as db:
            row = db.execute(
                "SELECT * FROM contacts WHERE normalized_name=?",
                (key,),
            ).fetchone()
        if not row:
            return None
        return Attendee(
            id=row["id"],
            initials=row["initials"],
            name=row["name"],
            email=row["email"],
            role=row["role"],
            organization=row["organization"],
        )

    def upsert_project(self, code: str, description: str | None, client: str | None) -> None:
        code = (code or "").strip().upper()
        if not code:
            return
        now = datetime.now().isoformat(timespec="seconds")
        with self.connect() as db:
            db.execute(
                """
                INSERT INTO projects(code, description, client, updated_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(code) DO UPDATE SET
                    description=excluded.description,
                    client=excluded.client,
                    updated_at=excluded.updated_at
                """,
                (code, description, client, now),
            )

    def list_projects(self) -> list[dict]:
        with self.connect() as db:
            rows = db.execute(
                """
                SELECT code, description, client, client_id, project_manager, approver,
                       default_minute_taker, default_location, document_type, discipline,
                       template_version_id, folder_path, COALESCE(active,1) AS active
                FROM projects
                ORDER BY code COLLATE NOCASE
                """
            ).fetchall()
        return [dict(row) for row in rows]

    def get_project(self, code: str) -> dict | None:
        code = (code or "").strip().upper()
        if not code:
            return None
        with self.connect() as db:
            row = db.execute("SELECT * FROM projects WHERE code=?", (code,)).fetchone()
        return dict(row) if row else None

    def upsert_project_profile(self, profile: dict) -> None:
        code = str(profile.get("code") or "").strip().upper()
        if not code:
            raise ValueError("El perfil de proyecto requiere un código.")
        now = datetime.now().isoformat(timespec="seconds")
        values = (
            code,
            profile.get("description"),
            profile.get("client"),
            profile.get("client_id"),
            profile.get("project_manager"),
            profile.get("approver"),
            profile.get("default_minute_taker"),
            profile.get("default_location") or "Microsoft Teams",
            profile.get("document_type") or "MRE",
            profile.get("discipline") or "PR",
            profile.get("template_version_id"),
            profile.get("folder_path"),
            int(bool(profile.get("active", True))),
            now,
        )
        with self.connect() as db:
            db.execute(
                """
                INSERT INTO projects(
                    code, description, client, client_id, project_manager, approver,
                    default_minute_taker, default_location, document_type, discipline,
                    template_version_id, folder_path, active, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(code) DO UPDATE SET
                    description=excluded.description,
                    client=excluded.client,
                    client_id=excluded.client_id,
                    project_manager=excluded.project_manager,
                    approver=excluded.approver,
                    default_minute_taker=excluded.default_minute_taker,
                    default_location=excluded.default_location,
                    document_type=excluded.document_type,
                    discipline=excluded.discipline,
                    template_version_id=excluded.template_version_id,
                    folder_path=excluded.folder_path,
                    active=excluded.active,
                    updated_at=excluded.updated_at
                """,
                values,
            )

    def set_project_members(self, project_code: str, names: list[str]) -> None:
        project_code = (project_code or "").strip().upper()
        if not project_code:
            return
        unique: list[str] = []
        seen: set[str] = set()
        for name in names:
            display = " ".join((name or "").split())
            key = normalize_name(display)
            if display and key not in seen:
                seen.add(key)
                unique.append(display)
        with self.connect() as db:
            db.execute("DELETE FROM project_members WHERE project_code=?", (project_code,))
            db.executemany(
                """
                INSERT INTO project_members(
                    project_code, normalized_name, display_name, sort_order
                ) VALUES (?, ?, ?, ?)
                """,
                [
                    (project_code, normalize_name(name), name, index)
                    for index, name in enumerate(unique, start=1)
                ],
            )

    def list_project_members(self, project_code: str) -> list[Attendee]:
        project_code = (project_code or "").strip().upper()
        if not project_code:
            return []
        with self.connect() as db:
            rows = db.execute(
                """
                SELECT pm.display_name, c.id, c.initials, c.email, c.role, c.organization
                FROM project_members pm
                LEFT JOIN contacts c ON c.normalized_name=pm.normalized_name
                WHERE pm.project_code=?
                ORDER BY pm.sort_order, pm.display_name COLLATE NOCASE
                """,
                (project_code,),
            ).fetchall()
        return [
            Attendee(
                id=row["id"],
                initials=row["initials"],
                name=row["display_name"],
                email=row["email"],
                role=row["role"],
                organization=row["organization"],
            )
            for row in rows
        ]

    # ------------------------------------------------------------------
    # Catálogos corporativos
    # ------------------------------------------------------------------
    def upsert_organization(self, record: OrganizationRecord | dict) -> int:
        item = (
            record
            if isinstance(record, OrganizationRecord)
            else OrganizationRecord.model_validate(record)
        )
        key = normalize_name(item.legal_name)
        now = datetime.now().isoformat(timespec="seconds")
        before = self.get_organization(item.id) if item.id else None
        with self.connect() as db:
            if item.id:
                db.execute(
                    """
                    UPDATE organizations SET normalized_name=?, legal_name=?, short_name=?,
                        tax_id=?, address=?, email=?, phone=?, active=?, notes=?, updated_at=?
                    WHERE id=?
                    """,
                    (
                        key,
                        item.legal_name,
                        item.short_name,
                        item.tax_id,
                        item.address,
                        item.email,
                        item.phone,
                        int(item.active),
                        item.notes,
                        now,
                        item.id,
                    ),
                )
                result = int(item.id)
            else:
                cursor = db.execute(
                    """
                    INSERT INTO organizations(
                        normalized_name, legal_name, short_name, tax_id, address,
                        email, phone, active, notes, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(normalized_name) DO UPDATE SET
                        legal_name=excluded.legal_name,
                        short_name=excluded.short_name,
                        tax_id=excluded.tax_id,
                        address=excluded.address,
                        email=excluded.email,
                        phone=excluded.phone,
                        active=excluded.active,
                        notes=excluded.notes,
                        updated_at=excluded.updated_at
                    """,
                    (
                        key,
                        item.legal_name,
                        item.short_name,
                        item.tax_id,
                        item.address,
                        item.email,
                        item.phone,
                        int(item.active),
                        item.notes,
                        now,
                        now,
                    ),
                )
                row = db.execute(
                    "SELECT id FROM organizations WHERE normalized_name=?", (key,)
                ).fetchone()
                result_value = row[0] if row else cursor.lastrowid
                if result_value is None:
                    raise RuntimeError("SQLite no devolvió el identificador de organización.")
                result = int(result_value)
        self.log_audit("upsert", "organization", str(result), before, self.get_organization(result))
        return result

    def list_organizations(self, include_inactive: bool = False) -> list[dict]:
        where = "" if include_inactive else "WHERE active=1"
        with self.connect() as db:
            rows = db.execute(
                f"SELECT * FROM organizations {where} ORDER BY COALESCE(short_name, legal_name) COLLATE NOCASE"
            ).fetchall()
        return [dict(row) for row in rows]

    def get_organization(self, organization_id: int | None) -> dict | None:
        if not organization_id:
            return None
        with self.connect() as db:
            row = db.execute(
                "SELECT * FROM organizations WHERE id=?", (organization_id,)
            ).fetchone()
        return dict(row) if row else None

    def upsert_client(self, record: ClientRecord | dict) -> int:
        item = record if isinstance(record, ClientRecord) else ClientRecord.model_validate(record)
        key = normalize_name(item.legal_name)
        now = datetime.now().isoformat(timespec="seconds")
        before = self.get_client(item.id) if item.id else None
        with self.connect() as db:
            if item.id:
                db.execute(
                    """
                    UPDATE clients SET organization_id=?, normalized_name=?, legal_name=?,
                        short_name=?, tax_id=?, address=?, primary_contact_name=?,
                        primary_contact_email=?, primary_contact_phone=?, active=?, notes=?,
                        updated_at=? WHERE id=?
                    """,
                    (
                        item.organization_id,
                        key,
                        item.legal_name,
                        item.short_name,
                        item.tax_id,
                        item.address,
                        item.primary_contact_name,
                        item.primary_contact_email,
                        item.primary_contact_phone,
                        int(item.active),
                        item.notes,
                        now,
                        item.id,
                    ),
                )
                result = int(item.id)
            else:
                db.execute(
                    """
                    INSERT INTO clients(
                        organization_id, normalized_name, legal_name, short_name, tax_id,
                        address, primary_contact_name, primary_contact_email,
                        primary_contact_phone, active, notes, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(normalized_name) DO UPDATE SET
                        organization_id=excluded.organization_id,
                        legal_name=excluded.legal_name,
                        short_name=excluded.short_name,
                        tax_id=excluded.tax_id,
                        address=excluded.address,
                        primary_contact_name=excluded.primary_contact_name,
                        primary_contact_email=excluded.primary_contact_email,
                        primary_contact_phone=excluded.primary_contact_phone,
                        active=excluded.active,
                        notes=excluded.notes,
                        updated_at=excluded.updated_at
                    """,
                    (
                        item.organization_id,
                        key,
                        item.legal_name,
                        item.short_name,
                        item.tax_id,
                        item.address,
                        item.primary_contact_name,
                        item.primary_contact_email,
                        item.primary_contact_phone,
                        int(item.active),
                        item.notes,
                        now,
                        now,
                    ),
                )
                row = db.execute(
                    "SELECT id FROM clients WHERE normalized_name=?", (key,)
                ).fetchone()
                result = int(row[0])
        self.log_audit("upsert", "client", str(result), before, self.get_client(result))
        return result

    def list_clients(self, include_inactive: bool = False) -> list[dict]:
        where = "" if include_inactive else "WHERE c.active=1"
        with self.connect() as db:
            rows = db.execute(
                f"""
                SELECT c.*, o.legal_name AS organization_name
                FROM clients c
                LEFT JOIN organizations o ON o.id=c.organization_id
                {where}
                ORDER BY COALESCE(c.short_name, c.legal_name) COLLATE NOCASE
                """
            ).fetchall()
        return [dict(row) for row in rows]

    def get_client(self, client_id: int | None) -> dict | None:
        if not client_id:
            return None
        with self.connect() as db:
            row = db.execute("SELECT * FROM clients WHERE id=?", (client_id,)).fetchone()
        return dict(row) if row else None

    def upsert_contact_record(self, record: ContactRecord | dict) -> int:
        item = record if isinstance(record, ContactRecord) else ContactRecord.model_validate(record)
        key = normalize_name(item.name)
        now = datetime.now().isoformat(timespec="seconds")
        before = None
        if item.id:
            with self.connect() as db:
                row = db.execute("SELECT * FROM contacts WHERE id=?", (item.id,)).fetchone()
                before = dict(row) if row else None
        with self.connect() as db:
            if item.id:
                db.execute(
                    """
                    UPDATE contacts SET normalized_name=?, name=?, initials=?, email=?, role=?,
                        organization=?, phone=?, active=?, notes=?, organization_id=?, client_id=?,
                        updated_at=? WHERE id=?
                    """,
                    (
                        key,
                        item.name,
                        item.initials,
                        item.email,
                        item.role,
                        item.organization,
                        item.phone,
                        int(item.active),
                        item.notes,
                        item.organization_id,
                        item.client_id,
                        now,
                        item.id,
                    ),
                )
                result = int(item.id)
            else:
                db.execute(
                    """
                    INSERT INTO contacts(
                        normalized_name, name, initials, email, role, organization,
                        phone, active, notes, organization_id, client_id, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(normalized_name) DO UPDATE SET
                        name=excluded.name,
                        initials=COALESCE(excluded.initials, contacts.initials),
                        email=COALESCE(excluded.email, contacts.email),
                        role=COALESCE(excluded.role, contacts.role),
                        organization=COALESCE(excluded.organization, contacts.organization),
                        phone=COALESCE(excluded.phone, contacts.phone),
                        active=excluded.active,
                        notes=COALESCE(excluded.notes, contacts.notes),
                        organization_id=COALESCE(excluded.organization_id, contacts.organization_id),
                        client_id=COALESCE(excluded.client_id, contacts.client_id),
                        updated_at=excluded.updated_at
                    """,
                    (
                        key,
                        item.name,
                        item.initials,
                        item.email,
                        item.role,
                        item.organization,
                        item.phone,
                        int(item.active),
                        item.notes,
                        item.organization_id,
                        item.client_id,
                        now,
                    ),
                )
                row = db.execute(
                    "SELECT id FROM contacts WHERE normalized_name=?", (key,)
                ).fetchone()
                result = int(row[0])
        self.log_audit("upsert", "contact", str(result), before, self.get_contact_record(result))
        return result

    def get_contact_record(self, contact_id: int | None) -> dict | None:
        if not contact_id:
            return None
        with self.connect() as db:
            row = db.execute("SELECT * FROM contacts WHERE id=?", (contact_id,)).fetchone()
        return dict(row) if row else None

    def list_contact_records(self, include_inactive: bool = False) -> list[dict]:
        where = "" if include_inactive else "WHERE COALESCE(c.active, 1)=1"
        with self.connect() as db:
            rows = db.execute(
                f"""
                SELECT c.*, cl.legal_name AS client_name, o.legal_name AS organization_name
                FROM contacts c
                LEFT JOIN clients cl ON cl.id=c.client_id
                LEFT JOIN organizations o ON o.id=c.organization_id
                {where}
                ORDER BY c.name COLLATE NOCASE
                """
            ).fetchall()
        return [dict(row) for row in rows]

    def set_record_active(self, table: str, record_id: int | str, active: bool) -> None:
        allowed = {"contacts": "id", "clients": "id", "organizations": "id", "projects": "code"}
        if table not in allowed:
            raise ValueError("Catálogo no permitido.")
        key = allowed[table]
        with self.connect() as db:
            cursor = db.execute(
                f"UPDATE {table} SET active=? WHERE {key}=?",
                (int(active), record_id),
            )
            if cursor.rowcount == 0:
                raise ValueError("El registro seleccionado ya no existe.")
        action = "activate" if active else "deactivate"
        self.log_audit(action, table.rstrip("s"), str(record_id), None, {"active": bool(active)})

    def deactivate_record(self, table: str, record_id: int | str) -> None:
        self.set_record_active(table, record_id, False)

    # ------------------------------------------------------------------
    # Plantillas documentales
    # ------------------------------------------------------------------
    def register_template_version(
        self,
        manifest: TemplateManifest,
        validation: TemplateValidation,
        file_path: str,
        sha256: str,
        state: str = "draft",
    ) -> int:
        now = datetime.now().isoformat(timespec="seconds")
        with self.connect() as db:
            db.execute(
                """
                INSERT INTO document_templates(
                    template_key, display_name, document_type, description,
                    active, created_at, updated_at
                ) VALUES (?, ?, ?, ?, 1, ?, ?)
                ON CONFLICT(template_key) DO UPDATE SET
                    display_name=excluded.display_name,
                    document_type=excluded.document_type,
                    description=excluded.description,
                    active=1,
                    updated_at=excluded.updated_at
                """,
                (
                    manifest.template_key,
                    manifest.display_name,
                    manifest.document_type,
                    manifest.notes,
                    now,
                    now,
                ),
            )
            template_row = db.execute(
                "SELECT id FROM document_templates WHERE template_key=?",
                (manifest.template_key,),
            ).fetchone()
            template_id = int(template_row[0])
            db.execute(
                """
                INSERT INTO template_versions(
                    template_id, version_label, file_path, sha256, state,
                    manifest_json, validation_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(template_id, version_label) DO UPDATE SET
                    file_path=excluded.file_path,
                    sha256=excluded.sha256,
                    state=excluded.state,
                    manifest_json=excluded.manifest_json,
                    validation_json=excluded.validation_json
                """,
                (
                    template_id,
                    manifest.version_label,
                    file_path,
                    sha256,
                    state,
                    manifest.model_dump_json(),
                    validation.model_dump_json(),
                    now,
                ),
            )
            row = db.execute(
                "SELECT id FROM template_versions WHERE template_id=? AND version_label=?",
                (template_id, manifest.version_label),
            ).fetchone()
            result = int(row[0])
        self.log_audit("install", "template_version", str(result), None, manifest.model_dump())
        return result

    def list_template_versions(self, include_retired: bool = True) -> list[dict]:
        where = "" if include_retired else "WHERE tv.state<>'retired'"
        with self.connect() as db:
            rows = db.execute(
                f"""
                SELECT tv.*, dt.template_key, dt.display_name, dt.document_type,
                       CASE WHEN dt.active_version_id=tv.id THEN 1 ELSE 0 END AS is_active
                FROM template_versions tv
                JOIN document_templates dt ON dt.id=tv.template_id
                {where}
                ORDER BY dt.display_name COLLATE NOCASE, tv.created_at DESC
                """
            ).fetchall()
        return [dict(row) for row in rows]

    def get_template_version(self, version_id: int | None) -> dict | None:
        if not version_id:
            return None
        with self.connect() as db:
            row = db.execute(
                """
                SELECT tv.*, dt.template_key, dt.display_name, dt.document_type,
                       CASE WHEN dt.active_version_id=tv.id THEN 1 ELSE 0 END AS is_active
                FROM template_versions tv
                JOIN document_templates dt ON dt.id=tv.template_id
                WHERE tv.id=?
                """,
                (version_id,),
            ).fetchone()
        return dict(row) if row else None

    def activate_template_version(self, version_id: int) -> None:
        before = self.get_template_version(version_id)
        if not before:
            raise ValueError("No se encontró la versión de plantilla.")
        now = datetime.now().isoformat(timespec="seconds")
        with self.connect() as db:
            db.execute(
                "UPDATE template_versions SET state='retired' WHERE template_id=? AND state='active'",
                (before["template_id"],),
            )
            db.execute(
                "UPDATE template_versions SET state='active', activated_at=? WHERE id=?",
                (now, version_id),
            )
            db.execute(
                "UPDATE document_templates SET active_version_id=?, updated_at=? WHERE id=?",
                (version_id, now, before["template_id"]),
            )
        self.log_audit(
            "activate",
            "template_version",
            str(version_id),
            before,
            self.get_template_version(version_id),
        )

    def set_template_state(self, version_id: int, state: str) -> None:
        if state not in {"draft", "testing", "active", "retired"}:
            raise ValueError("Estado de plantilla no válido.")
        if state == "active":
            self.activate_template_version(version_id)
            return
        before = self.get_template_version(version_id)
        with self.connect() as db:
            db.execute("UPDATE template_versions SET state=? WHERE id=?", (state, version_id))
        self.log_audit(
            "state",
            "template_version",
            str(version_id),
            before,
            self.get_template_version(version_id),
        )

    def resolve_template_version(
        self,
        project_code: str | None = None,
        meeting_type: str | None = None,
        default_template_key: str | None = None,
    ) -> dict | None:
        if project_code:
            project = self.get_project(project_code)
            if project and project.get("template_version_id"):
                result = self.get_template_version(int(project["template_version_id"]))
                if result and result.get("state") != "retired":
                    return result
        with self.connect() as db:
            if default_template_key:
                row = db.execute(
                    """
                    SELECT tv.*, dt.template_key, dt.display_name, dt.document_type, 1 AS is_active
                    FROM document_templates dt JOIN template_versions tv ON tv.id=dt.active_version_id
                    WHERE dt.template_key=? AND dt.active=1
                    """,
                    (default_template_key,),
                ).fetchone()
                if row:
                    return dict(row)
            if meeting_type:
                row = db.execute(
                    """
                    SELECT tv.*, dt.template_key, dt.display_name, dt.document_type, 1 AS is_active
                    FROM document_templates dt JOIN template_versions tv ON tv.id=dt.active_version_id
                    WHERE dt.document_type IN (?, 'meeting_minutes') AND dt.active=1
                    ORDER BY CASE WHEN dt.document_type=? THEN 0 ELSE 1 END, dt.updated_at DESC
                    LIMIT 1
                    """,
                    (meeting_type, meeting_type),
                ).fetchone()
                if row:
                    return dict(row)
        return None

    # ------------------------------------------------------------------
    # Auditoría, integridad y respaldo
    # ------------------------------------------------------------------
    def log_audit(
        self,
        action: str,
        entity_type: str,
        entity_id: str | None,
        before: dict | None,
        after: dict | None,
        app_version: str | None = None,
    ) -> None:
        event = AuditEvent(
            windows_user=getpass.getuser() or "unknown",
            machine_name=platform.node() or "unknown",
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            before=before,
            after=after,
            app_version=app_version or APP_VERSION,
        )
        with self.connect() as db:
            db.execute(
                """
                INSERT INTO audit_events(
                    created_at, windows_user, machine_name, action, entity_type,
                    entity_id, before_json, after_json, app_version
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event.created_at,
                    event.windows_user,
                    event.machine_name,
                    event.action,
                    event.entity_type,
                    event.entity_id,
                    json.dumps(event.before, ensure_ascii=False)
                    if event.before is not None
                    else None,
                    json.dumps(event.after, ensure_ascii=False)
                    if event.after is not None
                    else None,
                    event.app_version,
                ),
            )

    def list_audit_events(self, limit: int = 500) -> list[dict]:
        safe_limit = max(1, min(int(limit), 5000))
        with self.connect() as db:
            rows = db.execute(
                "SELECT * FROM audit_events ORDER BY id DESC LIMIT ?", (safe_limit,)
            ).fetchall()
        return [dict(row) for row in rows]

    def integrity_check(self) -> tuple[bool, str]:
        with self.connect() as db:
            row = db.execute("PRAGMA integrity_check").fetchone()
        message = str(row[0] if row else "unknown")
        return message.casefold() == "ok", message

    def backup_to(self, destination: str | Path) -> Path:
        target_path = Path(destination)
        target_path.parent.mkdir(parents=True, exist_ok=True)
        source = sqlite3.connect(self.path)
        target = sqlite3.connect(target_path)
        try:
            source.backup(target)
            target.commit()
        finally:
            target.close()
            source.close()
        return target_path

    def list_minute_numbers(self, project_code: str) -> list[str]:
        project_code = (project_code or "").strip().upper()
        with self.connect() as db:
            rows = db.execute(
                """
                SELECT minute_number FROM meetings
                WHERE UPPER(COALESCE(project_code, ''))=?
                  AND minute_number IS NOT NULL
                  AND deleted_at IS NULL
                  AND COALESCE(is_test, 0)=0
                """,
                (project_code,),
            ).fetchall()
        return [str(row[0]) for row in rows if row[0]]

    def find_meeting_by_source_sha256(self, sha256: str) -> dict | None:
        value = (sha256 or "").strip().lower()
        if not value:
            return None
        with self.connect() as db:
            row = db.execute(
                """
                SELECT * FROM meetings
                WHERE source_sha256=? AND deleted_at IS NULL
                ORDER BY id DESC
                LIMIT 1
                """,
                (value,),
            ).fetchone()
        return dict(row) if row else None

    def dashboard_stats(self) -> dict[str, int]:
        with self.connect() as db:
            row = db.execute(
                """
                SELECT
                    COUNT(*) AS total,
                    SUM(CASE WHEN status='procesada' THEN 1 ELSE 0 END) AS pending_review,
                    SUM(CASE WHEN status='generada' THEN 1 ELSE 0 END) AS generated
                FROM meetings
                WHERE deleted_at IS NULL AND COALESCE(is_test, 0)=0
                """
            ).fetchone()
        return {
            "total": int(row["total"] or 0),
            "pending_review": int(row["pending_review"] or 0),
            "generated": int(row["generated"] or 0),
        }

    def save_meeting(
        self,
        metadata: MeetingMetadata,
        analysis: MinuteAnalysis | None,
        source_vtt: str,
        output_dir: str,
        model: str,
        status: str,
        docx_path: str | None = None,
        json_path: str | None = None,
        pdf_path: str | None = None,
        meeting_id: int | None = None,
        app_version: str | None = None,
        document_provider: str | None = None,
        processing_provider: str | None = None,
        processing_provider_name: str | None = None,
        last_error: str | None = None,
        source_type: str | None = None,
        source_quality: str | None = None,
        is_test: bool = False,
        template_version_id: int | None = None,
        template_key: str | None = None,
        template_version_label: str | None = None,
    ) -> int:
        now = datetime.now().isoformat(timespec="seconds")
        values = (
            metadata.minute_number,
            metadata.meeting_date,
            metadata.project_code or "",
            metadata.matter,
            metadata.client,
            source_vtt,
            output_dir,
            docx_path,
            json_path,
            pdf_path,
            status,
            model,
            metadata.model_dump_json(),
            analysis.model_dump_json() if analysis else None,
            app_version,
            document_provider,
            _sha256_file(source_vtt),
            processing_provider,
            processing_provider_name,
            last_error,
            source_type or metadata.source_type,
            source_quality or metadata.source_quality,
            int(is_test),
            template_version_id or metadata.template_version_id,
            template_key or metadata.template_key,
            template_version_label or metadata.template_version,
            now,
        )
        with self.connect() as db:
            if meeting_id:
                db.execute(
                    """
                    UPDATE meetings SET
                        minute_number=?, meeting_date=?, project_code=?, matter=?, client=?,
                        source_vtt=?, output_dir=?, docx_path=?, json_path=?, pdf_path=?, status=?, model=?,
                        metadata_json=?, analysis_json=?, app_version=?, document_provider=?,
                        source_sha256=?, processing_provider=?, processing_provider_name=?,
                        last_error=?, source_type=?, source_quality=?, is_test=?,
                        template_version_id=?, template_key=?,
                        template_version_label=?, updated_at=?
                    WHERE id=?
                    """,
                    values + (meeting_id,),
                )
                return meeting_id
            cursor = db.execute(
                """
                INSERT INTO meetings (
                    minute_number, meeting_date, project_code, matter, client,
                    source_vtt, output_dir, docx_path, json_path, pdf_path, status, model,
                    metadata_json, analysis_json, app_version, document_provider,
                    source_sha256, processing_provider, processing_provider_name,
                    last_error, source_type, source_quality, is_test,
                    template_version_id, template_key, template_version_label,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                values[:-1] + (now, now),
            )
            return _inserted_id(cursor)

    def list_meetings(self, limit: int = 200, view: str = "active") -> list[dict]:
        safe_limit = max(1, min(int(limit), 5000))
        views = {
            "active": "deleted_at IS NULL",
            "operational": "deleted_at IS NULL AND COALESCE(is_test, 0)=0",
            "tests": "deleted_at IS NULL AND COALESCE(is_test, 0)=1",
            "trash": "deleted_at IS NOT NULL",
            "all": "1=1",
        }
        where = views.get(view, views["active"])
        with self.connect() as db:
            rows = db.execute(
                f"""
                SELECT id, minute_number, meeting_date, project_code, matter, client,
                       source_vtt, output_dir, docx_path, pdf_path, status, model, updated_at,
                       source_type, source_quality, COALESCE(is_test, 0) AS is_test,
                       deleted_at, deleted_by, deletion_reason, trash_path
                FROM meetings
                WHERE {where}
                ORDER BY COALESCE(meeting_date, '') DESC, id DESC
                LIMIT ?
                """,
                (safe_limit,),
            ).fetchall()
        return [dict(row) for row in rows]

    def set_meeting_test(self, meeting_id: int, is_test: bool) -> None:
        before = self.get_meeting(meeting_id)
        with self.connect() as db:
            cursor = db.execute(
                "UPDATE meetings SET is_test=?, updated_at=? WHERE id=? AND deleted_at IS NULL",
                (int(is_test), datetime.now().isoformat(timespec="seconds"), meeting_id),
            )
            if cursor.rowcount == 0:
                raise ValueError("La minuta no existe o está en la papelera.")
        self.log_audit(
            "mark_test" if is_test else "mark_operational",
            "meeting",
            str(meeting_id),
            before,
            self.get_meeting(meeting_id),
        )

    def move_meeting_to_trash(
        self,
        meeting_id: int,
        reason: str,
        trash_path: str | None = None,
        original_output_dir: str | None = None,
    ) -> None:
        before = self.get_meeting(meeting_id)
        if not before:
            raise ValueError("No se encontró la minuta.")
        now = datetime.now().isoformat(timespec="seconds")
        user = getpass.getuser()
        with self.connect() as db:
            db.execute(
                """
                UPDATE meetings SET deleted_at=?, deleted_by=?, deletion_reason=?,
                    trash_path=?, original_output_dir=COALESCE(?, output_dir),
                    original_status=COALESCE(original_status, status), status='papelera', updated_at=?
                WHERE id=?
                """,
                (now, user, reason, trash_path, original_output_dir, now, meeting_id),
            )
        self.log_audit("trash", "meeting", str(meeting_id), before, self.get_meeting(meeting_id))

    def restore_meeting_from_trash(
        self,
        meeting_id: int,
        output_dir: str | None = None,
        restored_status: str = "procesada",
    ) -> None:
        before = self.get_meeting(meeting_id)
        if not before or not before.get("deleted_at"):
            raise ValueError("La minuta no está en la papelera.")
        now = datetime.now().isoformat(timespec="seconds")
        with self.connect() as db:
            db.execute(
                """
                UPDATE meetings SET deleted_at=NULL, deleted_by=NULL,
                    deletion_reason=NULL, trash_path=NULL,
                    output_dir=COALESCE(?, original_output_dir, output_dir),
                    status=COALESCE(original_status, ?), original_status=NULL, updated_at=? WHERE id=?
                """,
                (output_dir, restored_status, now, meeting_id),
            )
        self.log_audit("restore", "meeting", str(meeting_id), before, self.get_meeting(meeting_id))

    def delete_meeting_permanently(self, meeting_id: int) -> None:
        before = self.get_meeting(meeting_id)
        if not before or not before.get("deleted_at"):
            raise ValueError("Solo se pueden eliminar definitivamente elementos de la papelera.")
        self.log_audit("purge", "meeting", str(meeting_id), before, None)
        with self.connect() as db:
            db.execute("DELETE FROM meetings WHERE id=?", (meeting_id,))

    def list_cleanup_candidates(self, limit: int = 200) -> list[dict]:
        with self.connect() as db:
            rows = db.execute(
                """
                SELECT id, minute_number, meeting_date, project_code, matter, status,
                       source_vtt, docx_path, updated_at, COALESCE(is_test, 0) AS is_test
                FROM meetings
                WHERE deleted_at IS NULL AND (
                    COALESCE(is_test, 0)=1 OR
                    minute_number IS NULL OR TRIM(minute_number)='' OR
                    status IN ('error', 'cancelada') OR
                    (status='procesada' AND (analysis_json IS NULL OR TRIM(analysis_json)=''))
                )
                ORDER BY id DESC LIMIT ?
                """,
                (max(1, min(int(limit), 1000)),),
            ).fetchall()
        return [dict(row) for row in rows]

    def add_technical_term(
        self,
        canonical_term: str,
        variants: list[str] | None = None,
        category: str | None = None,
        project_code: str | None = None,
        notes: str | None = None,
    ) -> int:
        canonical = " ".join((canonical_term or "").split()).strip()
        if not canonical:
            raise ValueError("El término canónico no puede estar vacío.")
        now = datetime.now().isoformat(timespec="seconds")
        key = normalize_name(canonical)
        with self.connect() as db:
            db.execute(
                """
                INSERT INTO technical_terms(
                    normalized_term, canonical_term, variants_json, category,
                    project_code, active, notes, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, 1, ?, ?, ?)
                ON CONFLICT(normalized_term, project_code) DO UPDATE SET
                    canonical_term=excluded.canonical_term,
                    variants_json=excluded.variants_json,
                    category=excluded.category,
                    active=1,
                    notes=excluded.notes,
                    updated_at=excluded.updated_at
                """,
                (
                    key,
                    canonical,
                    json.dumps(variants or [], ensure_ascii=False),
                    category,
                    (project_code or "").strip().upper(),
                    notes,
                    now,
                    now,
                ),
            )
            row = db.execute(
                "SELECT id FROM technical_terms WHERE normalized_term=? AND project_code=?",
                (key, (project_code or "").strip().upper()),
            ).fetchone()
        return int(row[0])

    def list_technical_terms(self, project_code: str | None = None) -> list[dict]:
        with self.connect() as db:
            rows = db.execute(
                """
                SELECT * FROM technical_terms
                WHERE active=1 AND (project_code IS NULL OR project_code='' OR project_code=?)
                ORDER BY CASE WHEN project_code=? THEN 0 ELSE 1 END, canonical_term COLLATE NOCASE
                """,
                ((project_code or "").strip().upper(), (project_code or "").strip().upper()),
            ).fetchall()
        return [dict(row) for row in rows]

    def set_technical_term_active(self, term_id: int, active: bool) -> None:
        with self.connect() as db:
            cursor = db.execute(
                "UPDATE technical_terms SET active=?, updated_at=? WHERE id=?",
                (int(active), datetime.now().isoformat(timespec="seconds"), term_id),
            )
            if cursor.rowcount == 0:
                raise ValueError("No se encontró el término técnico.")

    def list_all_technical_terms(self) -> list[dict]:
        with self.connect() as db:
            rows = db.execute(
                "SELECT * FROM technical_terms ORDER BY active DESC, canonical_term COLLATE NOCASE"
            ).fetchall()
        return [dict(row) for row in rows]

    def record_correction_event(
        self,
        meeting_id: int | None,
        item_index: int | None,
        correction_type: str,
        before: dict | None,
        after: dict | None,
        approved_for_learning: bool = False,
    ) -> int:
        kind = (correction_type or "edicion").strip() or "edicion"
        now = datetime.now().isoformat(timespec="seconds")
        with self.connect() as db:
            cursor = db.execute(
                """
                INSERT INTO correction_events(
                    meeting_id, item_index, correction_type, before_json, after_json,
                    approved_for_learning, created_at, created_by
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    meeting_id,
                    item_index,
                    kind,
                    json.dumps(before, ensure_ascii=False, default=str)
                    if before is not None
                    else None,
                    json.dumps(after, ensure_ascii=False, default=str)
                    if after is not None
                    else None,
                    int(approved_for_learning),
                    now,
                    getpass.getuser(),
                ),
            )
            return _inserted_id(cursor)

    def list_correction_events(
        self,
        *,
        approved_only: bool = False,
        limit: int = 1000,
    ) -> list[dict]:
        safe_limit = max(1, min(int(limit), 10000))
        where = "WHERE approved_for_learning=1" if approved_only else ""
        with self.connect() as db:
            rows = db.execute(
                f"""SELECT * FROM correction_events {where}
                    ORDER BY created_at DESC, id DESC LIMIT ?""",
                (safe_limit,),
            ).fetchall()
        return [dict(row) for row in rows]

    def list_learning_examples(
        self,
        project_code: str | None = None,
        meeting_type: str | None = None,
        limit: int = 3,
        client: str | None = None,
        query_text: str | None = None,
    ) -> list[dict]:
        """Devuelve ejemplos aprobados, aislados por cliente y ordenados por similitud."""

        safe_limit = max(1, min(int(limit), 10))
        project = (project_code or "").strip().upper()
        kind = (meeting_type or "").strip().casefold()
        client_key = normalize_name(client or "")
        query_tokens = set(normalize_name(query_text or "").split())
        with self.connect() as db:
            rows = db.execute(
                """
                SELECT m.id, m.project_code, m.analysis_json, m.metadata_json, m.matter,
                       m.client, ls.meeting_type, ls.approved_at, ls.client_scope,
                       ls.anonymized, ls.id AS learning_sample_id
                FROM learning_samples ls
                JOIN meetings m ON m.id=ls.meeting_id
                WHERE ls.approved=1
                  AND m.deleted_at IS NULL
                  AND m.analysis_json IS NOT NULL
                ORDER BY ls.approved_at DESC, ls.id DESC
                LIMIT 200
                """
            ).fetchall()
        candidates = [dict(row) for row in rows]
        if client_key:
            candidates = [
                row
                for row in candidates
                if normalize_name(str(row.get("client_scope") or row.get("client") or ""))
                == client_key
            ]

        def similarity(row: dict) -> float:
            if not query_tokens:
                return 0.0
            text = " ".join(
                str(row.get(key) or "") for key in ("matter", "metadata_json", "analysis_json")
            )
            tokens = set(normalize_name(text).split())
            return len(query_tokens & tokens) / max(len(query_tokens | tokens), 1)

        candidates.sort(
            key=lambda row: (
                int(bool(project) and str(row.get("project_code") or "").upper() == project),
                int(bool(kind) and str(row.get("meeting_type") or "").casefold() == kind),
                similarity(row),
                str(row.get("approved_at") or ""),
            ),
            reverse=True,
        )
        return candidates[:safe_limit]

    def list_learning_samples(
        self,
        *,
        include_excluded: bool = True,
        client: str | None = None,
    ) -> list[dict]:
        clauses = ["m.deleted_at IS NULL", "m.is_test=0"]
        parameters: list[object] = []
        if not include_excluded:
            clauses.append("ls.approved=1")
        client_key = normalize_name(client or "")
        with self.connect() as db:
            rows = db.execute(
                f"""
                SELECT ls.*, m.minute_number, m.client, m.matter, m.source_vtt,
                       m.analysis_json, m.metadata_json
                FROM learning_samples ls
                JOIN meetings m ON m.id=ls.meeting_id
                WHERE {" AND ".join(clauses)}
                ORDER BY ls.approved_at DESC, ls.id DESC
                """,
                parameters,
            ).fetchall()
        result = [dict(row) for row in rows]
        if client_key:
            result = [
                row
                for row in result
                if normalize_name(str(row.get("client_scope") or row.get("client") or ""))
                == client_key
            ]
        return result

    def set_learning_sample_approved(
        self,
        meeting_id: int,
        approved: bool,
        reason: str | None = None,
    ) -> None:
        now = datetime.now().isoformat(timespec="seconds")
        with self.connect() as db:
            cursor = db.execute(
                """
                UPDATE learning_samples
                SET approved=?, excluded_reason=?, approved_at=?, approved_by=?
                WHERE meeting_id=?
                """,
                (
                    int(approved),
                    None if approved else (reason or "Excluido manualmente"),
                    now if approved else None,
                    getpass.getuser(),
                    meeting_id,
                ),
            )
            if cursor.rowcount == 0:
                raise ValueError("No se encontró el ejemplo de aprendizaje.")

    def register_learning_sample(
        self,
        meeting_id: int,
        approved: bool = True,
        anonymized: bool = False,
        approved_by: str | None = None,
    ) -> int:
        row = self.get_meeting(meeting_id)
        if not row:
            raise ValueError("No se encontró la reunión para registrar el ejemplo.")
        if row.get("deleted_at") or row.get("is_test"):
            raise ValueError(
                "Las minutas de prueba o en papelera no pueden alimentar el aprendizaje."
            )
        metadata = json.loads(row.get("metadata_json") or "{}")
        now = datetime.now().isoformat(timespec="seconds")
        client_scope = normalize_name(
            str(row.get("client") or metadata.get("client") or "")
        ).upper()
        with self.connect() as db:
            existing = db.execute(
                "SELECT id FROM learning_samples WHERE meeting_id=? ORDER BY id DESC LIMIT 1",
                (meeting_id,),
            ).fetchone()
            values = (
                row.get("source_sha256"),
                row.get("source_type") or "vtt",
                metadata.get("meeting_type"),
                row.get("project_code"),
                client_scope,
                int(approved),
                int(anonymized),
                approved_by or getpass.getuser(),
                now if approved else None,
                None if approved else "Excluido al registrar",
                now,
            )
            if existing:
                db.execute(
                    """UPDATE learning_samples SET source_sha256=?, source_type=?, meeting_type=?,
                       project_code=?, client_scope=?, approved=?, anonymized=?, approved_by=?,
                       approved_at=?, excluded_reason=?, created_at=? WHERE id=?""",
                    values + (int(existing[0]),),
                )
                return int(existing[0])
            cursor = db.execute(
                """
                INSERT INTO learning_samples(
                    meeting_id, source_sha256, source_type, meeting_type, project_code,
                    client_scope, approved, anonymized, approved_by, approved_at,
                    excluded_reason, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (meeting_id,) + values,
            )
            return _inserted_id(cursor)

    def learning_summary(self) -> dict[str, int]:
        with self.connect() as db:
            samples = db.execute(
                """SELECT COUNT(*) total,
                          SUM(CASE WHEN approved=1 THEN 1 ELSE 0 END) approved,
                          SUM(CASE WHEN anonymized=1 THEN 1 ELSE 0 END) anonymized
                   FROM learning_samples"""
            ).fetchone()
            corrections = db.execute(
                """SELECT COUNT(*) total,
                          SUM(CASE WHEN approved_for_learning=1 THEN 1 ELSE 0 END) approved
                   FROM correction_events"""
            ).fetchone()
            terms = db.execute("SELECT COUNT(*) FROM technical_terms WHERE active=1").fetchone()
        return {
            "samples": int(samples["total"] or 0),
            "approved_samples": int(samples["approved"] or 0),
            "anonymized_samples": int(samples["anonymized"] or 0),
            "corrections": int(corrections["total"] or 0),
            "approved_corrections": int(corrections["approved"] or 0),
            "technical_terms": int(terms[0] or 0),
        }

    def get_meeting(self, meeting_id: int) -> dict | None:
        with self.connect() as db:
            row = db.execute("SELECT * FROM meetings WHERE id=?", (meeting_id,)).fetchone()
        return dict(row) if row else None
