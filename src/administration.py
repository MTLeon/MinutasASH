from __future__ import annotations

import json
import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import filedialog, messagebox, simpledialog, ttk
from tkinter.scrolledtext import ScrolledText

from pydantic import ValidationError

from src.backup_service import create_backup, restore_backup, verify_backup
from src.catalog_io import create_import_template, export_catalog, import_catalog
from src.catalog_models import ClientRecord, ContactRecord, OrganizationRecord, ProjectCatalogRecord
from src.database import AppDatabase
from src.learning_dataset import export_lora_datasets
from src.runtime_paths import backups_dir, exports_dir, resource_path, templates_dir
from src.template_service import TemplateService
from src.ui_state import configure_resizable_window

CATALOG_LABELS = {
    "contacts": "Contactos",
    "clients": "Clientes",
    "organizations": "Organizaciones",
    "projects": "Proyectos",
}


class RecordDialog(tk.Toplevel):
    def __init__(
        self,
        parent,
        title: str,
        fields: list[tuple[str, str]],
        values: dict | None = None,
        options: dict[str, list[tuple[str, object]]] | None = None,
    ) -> None:
        super().__init__(parent)
        self.title(title)
        configure_resizable_window(self, parent, "catalog_record", "720x600", (560, 420))
        self.result: dict | None = None
        self.values = values or {}
        self.options = options or {}
        self.option_maps: dict[str, dict[str, object]] = {}
        self.variables: dict[str, tk.StringVar] = {}
        frame = ttk.Frame(self, padding=16)
        frame.pack(fill="both", expand=True)
        for row, (key, label) in enumerate(fields):
            ttk.Label(frame, text=label).grid(row=row, column=0, sticky="w", pady=5, padx=(0, 10))
            choices = self.options.get(key)
            if choices:
                label_to_value = {display: value for display, value in choices}
                self.option_maps[key] = label_to_value
                current_value = self.values.get(key)
                current_label = next(
                    (display for display, value in choices if value == current_value),
                    "",
                )
                variable = tk.StringVar(value=current_label)
                widget: ttk.Combobox | ttk.Entry = ttk.Combobox(
                    frame,
                    textvariable=variable,
                    values=[display for display, _value in choices],
                    state="readonly",
                    width=50,
                )
            else:
                variable = tk.StringVar(value=str(self.values.get(key) or ""))
                widget = ttk.Entry(frame, textvariable=variable, width=52)
            self.variables[key] = variable
            widget.grid(row=row, column=1, sticky="ew", pady=5)
        frame.columnconfigure(1, weight=1)
        buttons = ttk.Frame(frame)
        buttons.grid(row=len(fields), column=0, columnspan=2, sticky="e", pady=(14, 0))
        ttk.Button(buttons, text="Cancelar", command=self.destroy).pack(side="left")
        ttk.Button(buttons, text="Guardar", style="Primary.TButton", command=self._save).pack(
            side="left", padx=(8, 0)
        )
        self.bind("<Return>", lambda _event: self._save())
        self.bind("<Escape>", lambda _event: self.destroy())
        self.grab_set()

    def _save(self) -> None:
        result: dict = {}
        for key, variable in self.variables.items():
            text = variable.get().strip()
            if key in self.option_maps:
                result[key] = self.option_maps[key].get(text)
            else:
                result[key] = text or None
        self.result = result
        self.destroy()


class TemplateInstallDialog(tk.Toplevel):
    def __init__(self, parent) -> None:
        super().__init__(parent)
        self.title("Instalar plantilla Word")
        configure_resizable_window(self, parent, "template_install", "780x560", (620, 440))
        self.result: dict | None = None
        self.vars = {
            "source": tk.StringVar(),
            "template_key": tk.StringVar(value="minuta_ash"),
            "display_name": tk.StringVar(value="Minuta ASH"),
            "version_label": tk.StringVar(value="1.0"),
            "document_type": tk.StringVar(value="meeting_minutes"),
            "notes": tk.StringVar(),
        }
        frame = ttk.Frame(self, padding=16)
        frame.pack(fill="both", expand=True)
        fields = [
            ("source", "Archivo Word (.docx)"),
            ("template_key", "Identificador"),
            ("display_name", "Nombre visible"),
            ("version_label", "Versión"),
            ("document_type", "Tipo de documento"),
            ("notes", "Descripción"),
        ]
        for row, (key, label) in enumerate(fields):
            ttk.Label(frame, text=label).grid(row=row, column=0, sticky="w", pady=5, padx=(0, 10))
            box = ttk.Frame(frame)
            box.grid(row=row, column=1, sticky="ew", pady=5)
            box.columnconfigure(0, weight=1)
            ttk.Entry(box, textvariable=self.vars[key], width=52).grid(row=0, column=0, sticky="ew")
            if key == "source":
                ttk.Button(box, text="Examinar...", command=self._browse).grid(
                    row=0, column=1, padx=(6, 0)
                )
        frame.columnconfigure(1, weight=1)
        ttk.Label(
            frame,
            text="La plantilla debe incluir los marcadores corporativos y filas {{TABLA_ASISTENTES}} y {{TABLA_ACUERDOS}}.",
            style="Muted.TLabel",
            wraplength=560,
        ).grid(row=len(fields), column=0, columnspan=2, sticky="w", pady=(8, 0))
        buttons = ttk.Frame(frame)
        buttons.grid(row=len(fields) + 1, column=0, columnspan=2, sticky="e", pady=(14, 0))
        ttk.Button(buttons, text="Cancelar", command=self.destroy).pack(side="left")
        ttk.Button(
            buttons, text="Instalar y validar", style="Primary.TButton", command=self._save
        ).pack(side="left", padx=(8, 0))
        self.grab_set()

    def _browse(self) -> None:
        path = filedialog.askopenfilename(parent=self, filetypes=[("Documentos Word", "*.docx")])
        if path:
            self.vars["source"].set(path)

    def _save(self) -> None:
        data = {key: variable.get().strip() for key, variable in self.vars.items()}
        if not Path(data["source"]).is_file():
            messagebox.showwarning("Plantilla", "Seleccione un archivo Word válido.", parent=self)
            return
        if not data["template_key"] or not data["display_name"] or not data["version_label"]:
            messagebox.showwarning(
                "Plantilla", "Complete identificador, nombre y versión.", parent=self
            )
            return
        self.result = data
        self.destroy()


class AdministrationCenter(tk.Toplevel):
    def __init__(self, parent, database: AppDatabase, config: dict, refresh_callback=None) -> None:
        super().__init__(parent)
        self.title("Administración - Minutas ASH")
        configure_resizable_window(self, parent, "administration_center", "1180x800", (900, 600))
        self.database = database
        self.app_config = config
        self.refresh_callback = refresh_callback
        self.template_service = TemplateService(database)
        self.current_catalog = "contacts"
        self._build()
        self._refresh_all()

    def _build(self) -> None:
        header = ttk.Frame(self, padding=14)
        header.pack(fill="x")
        ttk.Label(header, text="Administración", style="Title.TLabel").pack(side="left")
        ttk.Label(
            header,
            text="Catálogos, plantillas, respaldos y auditoría",
            style="Muted.TLabel",
        ).pack(side="left", padx=14)
        ttk.Button(header, text="Cerrar", command=self.destroy).pack(side="right")

        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True, padx=14, pady=(0, 14))
        self.tab_catalogs = ttk.Frame(self.notebook, padding=12)
        self.tab_templates = ttk.Frame(self.notebook, padding=12)
        self.tab_backup = ttk.Frame(self.notebook, padding=12)
        self.tab_audit = ttk.Frame(self.notebook, padding=12)
        self.tab_learning = ttk.Frame(self.notebook, padding=12)
        self.tab_repository = ttk.Frame(self.notebook, padding=12)
        self.notebook.add(self.tab_catalogs, text="Catálogos")
        self.notebook.add(self.tab_templates, text="Plantillas")
        self.notebook.add(self.tab_backup, text="Respaldo")
        self.notebook.add(self.tab_audit, text="Auditoría")
        self.notebook.add(self.tab_learning, text="Aprendizaje")
        self.notebook.add(self.tab_repository, text="Repositorio")
        self._build_catalogs()
        self._build_templates()
        self._build_backup()
        self._build_audit()
        self._build_learning()
        self._build_repository()

    # ------------------------------------------------------------------
    # Catálogos
    # ------------------------------------------------------------------
    def _build_catalogs(self) -> None:
        tab = self.tab_catalogs
        tab.columnconfigure(0, weight=1)
        tab.rowconfigure(2, weight=1)
        controls = ttk.Frame(tab)
        controls.grid(row=0, column=0, sticky="ew")
        self.catalog_var = tk.StringVar(value="contacts")
        self.catalog_display_var = tk.StringVar(value=CATALOG_LABELS["contacts"])
        self.catalog_search_var = tk.StringVar()
        ttk.Label(controls, text="Catálogo").pack(side="left")
        combo = ttk.Combobox(
            controls,
            textvariable=self.catalog_display_var,
            values=list(CATALOG_LABELS.values()),
            state="readonly",
            width=20,
        )
        combo.pack(side="left", padx=8)
        combo.bind("<<ComboboxSelected>>", lambda _event: self._on_catalog_selected())
        ttk.Button(controls, text="Nuevo", command=self._new_catalog_record).pack(
            side="left", padx=(12, 4)
        )
        ttk.Button(controls, text="Editar", command=self._edit_catalog_record).pack(
            side="left", padx=4
        )
        ttk.Button(controls, text="Activar / desactivar", command=self._toggle_catalog_record).pack(
            side="left", padx=4
        )
        ttk.Button(controls, text="Importar", command=self._import_catalog).pack(
            side="right", padx=4
        )
        ttk.Button(controls, text="Plantilla Excel", command=self._create_catalog_template).pack(
            side="right", padx=4
        )
        ttk.Button(controls, text="Exportar", command=self._export_catalog).pack(
            side="right", padx=4
        )
        ttk.Button(controls, text="Actualizar", command=self._refresh_catalog).pack(
            side="right", padx=4
        )
        search_box = ttk.Entry(controls, textvariable=self.catalog_search_var, width=24)
        search_box.pack(side="right", padx=(12, 4))
        ttk.Label(controls, text="Buscar").pack(side="right")
        self.catalog_search_var.trace_add("write", lambda *_args: self._refresh_catalog())

        ttk.Label(
            tab,
            text="Los registros usados en documentos anteriores se desactivan; no se eliminan físicamente.",
            style="Muted.TLabel",
        ).grid(row=1, column=0, sticky="w", pady=(8, 6))
        self.catalog_tree = ttk.Treeview(tab, show="headings")
        self.catalog_tree.grid(row=2, column=0, sticky="nsew")
        scroll = ttk.Scrollbar(tab, orient="vertical", command=self.catalog_tree.yview)
        scroll.grid(row=2, column=1, sticky="ns")
        self.catalog_tree.configure(yscrollcommand=scroll.set)
        self.catalog_tree.bind("<Double-1>", lambda _event: self._edit_catalog_record())

    def _on_catalog_selected(self) -> None:
        reverse = {label: key for key, label in CATALOG_LABELS.items()}
        self.catalog_var.set(reverse.get(self.catalog_display_var.get(), "contacts"))
        self._refresh_catalog()

    def _catalog_rows(self, catalog: str) -> list[dict]:
        if catalog == "contacts":
            rows = self.database.list_contact_records(include_inactive=True)
        elif catalog == "clients":
            rows = self.database.list_clients(include_inactive=True)
        elif catalog == "organizations":
            rows = self.database.list_organizations(include_inactive=True)
        else:
            rows = self.database.list_projects()
        term = (
            self.catalog_search_var.get().strip().casefold()
            if hasattr(self, "catalog_search_var")
            else ""
        )
        if not term:
            return rows
        return [
            row
            for row in rows
            if term in " ".join(str(value or "") for value in row.values()).casefold()
        ]

    def _catalog_columns(self, catalog: str) -> list[tuple[str, str, int]]:
        return {
            "contacts": [
                ("id", "ID", 50),
                ("name", "Nombre", 230),
                ("email", "Correo", 220),
                ("role", "Cargo", 170),
                ("organization", "Organización", 170),
                ("active", "Activo", 70),
            ],
            "clients": [
                ("id", "ID", 50),
                ("legal_name", "Nombre legal", 250),
                ("short_name", "Nombre corto", 170),
                ("tax_id", "RUT", 120),
                ("primary_contact_name", "Contacto", 180),
                ("active", "Activo", 70),
            ],
            "organizations": [
                ("id", "ID", 50),
                ("legal_name", "Nombre legal", 260),
                ("short_name", "Nombre corto", 180),
                ("tax_id", "RUT", 120),
                ("email", "Correo", 220),
                ("active", "Activo", 70),
            ],
            "projects": [
                ("code", "Código", 100),
                ("description", "Descripción", 300),
                ("client", "Cliente", 190),
                ("project_manager", "Jefe de proyecto", 180),
                ("document_type", "Tipo", 80),
                ("active", "Activo", 70),
            ],
        }[catalog]

    def _refresh_catalog(self) -> None:
        catalog = self.catalog_var.get() or "contacts"
        self.current_catalog = catalog
        columns = self._catalog_columns(catalog)
        self.catalog_tree.configure(columns=[key for key, _label, _width in columns])
        for key, label, width in columns:
            self.catalog_tree.heading(key, text=label)
            self.catalog_tree.column(key, width=width, anchor="w")
        self.catalog_tree.delete(*self.catalog_tree.get_children())
        for row in self._catalog_rows(catalog):
            record_key: object = row.get("code") if catalog == "projects" else row.get("id")
            values = []
            for field, _label, _width in columns:
                value = row.get(field)
                if field == "active":
                    value = "Sí" if bool(value) else "No"
                values.append(value or "")
            self.catalog_tree.insert("", "end", iid=str(record_key or ""), values=values)

    def _selected_catalog_row(self) -> dict | None:
        selection = self.catalog_tree.selection()
        if not selection:
            return None
        key = selection[0]
        for row in self._catalog_rows(self.current_catalog):
            row_key = str(row.get("code") if self.current_catalog == "projects" else row.get("id"))
            if row_key == key:
                return row
        return None

    def _catalog_fields(self, catalog: str) -> list[tuple[str, str]]:
        return {
            "contacts": [
                ("name", "Nombre *"),
                ("initials", "Iniciales"),
                ("email", "Correo"),
                ("role", "Cargo"),
                ("organization_id", "Organización registrada"),
                ("client_id", "Cliente asociado"),
                ("organization", "Organización mostrada"),
                ("phone", "Teléfono"),
                ("notes", "Observaciones"),
            ],
            "clients": [
                ("legal_name", "Nombre legal *"),
                ("short_name", "Nombre corto"),
                ("organization_id", "Organización vinculada"),
                ("tax_id", "RUT"),
                ("address", "Dirección"),
                ("primary_contact_name", "Contacto principal"),
                ("primary_contact_email", "Correo principal"),
                ("primary_contact_phone", "Teléfono principal"),
                ("notes", "Observaciones"),
            ],
            "organizations": [
                ("legal_name", "Nombre legal *"),
                ("short_name", "Nombre corto"),
                ("tax_id", "RUT"),
                ("address", "Dirección"),
                ("email", "Correo"),
                ("phone", "Teléfono"),
                ("notes", "Observaciones"),
            ],
            "projects": [
                ("code", "Código *"),
                ("description", "Descripción"),
                ("client_id", "Cliente registrado"),
                ("client", "Cliente alternativo"),
                ("project_manager", "Jefe de proyecto"),
                ("approver", "Aprobador"),
                ("default_minute_taker", "Redactor habitual"),
                ("default_location", "Lugar habitual"),
                ("document_type", "Tipo documental"),
                ("discipline", "Disciplina"),
                ("template_version_id", "Plantilla predeterminada"),
                ("folder_path", "Carpeta documental"),
            ],
        }[catalog]

    def _catalog_options(self, catalog: str) -> dict[str, list[tuple[str, object]]]:
        organizations = [
            (
                f"{row.get('short_name') or row.get('legal_name')} [ID {row.get('id')}]",
                row.get("id"),
            )
            for row in self.database.list_organizations()
        ]
        clients = [
            (
                f"{row.get('short_name') or row.get('legal_name')} [ID {row.get('id')}]",
                row.get("id"),
            )
            for row in self.database.list_clients()
        ]
        templates = [
            (
                f"{row.get('display_name')} v{row.get('version_label')} [ID {row.get('id')}]",
                row.get("id"),
            )
            for row in self.database.list_template_versions(include_retired=False)
            if row.get("state") == "active"
        ]
        options: dict[str, list[tuple[str, object]]] = {}
        if catalog in {"contacts", "clients"}:
            options["organization_id"] = [("", None), *organizations]
        if catalog in {"contacts", "projects"}:
            options["client_id"] = [("", None), *clients]
        if catalog == "projects":
            options["template_version_id"] = [("", None), *templates]
        return options

    def _new_catalog_record(self) -> None:
        dialog = RecordDialog(
            self,
            f"Nuevo - {CATALOG_LABELS[self.current_catalog]}",
            self._catalog_fields(self.current_catalog),
            options=self._catalog_options(self.current_catalog),
        )
        self.wait_window(dialog)
        if dialog.result:
            self._save_catalog_values(dialog.result)

    def _edit_catalog_record(self) -> None:
        row = self._selected_catalog_row()
        if not row:
            messagebox.showinfo("Catálogos", "Seleccione un registro.", parent=self)
            return
        dialog = RecordDialog(
            self,
            f"Editar - {CATALOG_LABELS[self.current_catalog]}",
            self._catalog_fields(self.current_catalog),
            row,
            options=self._catalog_options(self.current_catalog),
        )
        self.wait_window(dialog)
        if dialog.result:
            dialog.result["id" if self.current_catalog != "projects" else "code"] = row.get(
                "id" if self.current_catalog != "projects" else "code"
            )
            dialog.result["active"] = bool(row.get("active", 1))
            self._save_catalog_values(dialog.result)

    def _save_catalog_values(self, values: dict) -> None:
        try:
            if values.get("organization_id"):
                organization = self.database.get_organization(int(values["organization_id"]))
                if organization and self.current_catalog == "contacts":
                    values["organization"] = organization.get("short_name") or organization.get(
                        "legal_name"
                    )
            if values.get("client_id"):
                client = self.database.get_client(int(values["client_id"]))
                if client:
                    client_name = client.get("short_name") or client.get("legal_name")
                    if self.current_catalog == "projects":
                        values["client"] = client_name
                    elif self.current_catalog == "contacts" and not values.get("organization"):
                        values["organization"] = client_name
            if self.current_catalog == "contacts":
                self.database.upsert_contact_record(ContactRecord.model_validate(values))
            elif self.current_catalog == "clients":
                self.database.upsert_client(ClientRecord.model_validate(values))
            elif self.current_catalog == "organizations":
                self.database.upsert_organization(OrganizationRecord.model_validate(values))
            else:
                self.database.upsert_project_profile(
                    ProjectCatalogRecord.model_validate(values).model_dump()
                )
            self._refresh_catalog()
            if self.refresh_callback:
                self.refresh_callback()
        except (ValidationError, ValueError) as exc:
            messagebox.showerror("Datos inválidos", str(exc), parent=self)

    def _toggle_catalog_record(self) -> None:
        row = self._selected_catalog_row()
        if not row:
            messagebox.showinfo("Catálogos", "Seleccione un registro.", parent=self)
            return
        key = row.get("code") if self.current_catalog == "projects" else row.get("id")
        current = bool(row.get("active", 1))
        target = not current
        verb = "activar" if target else "desactivar"
        detail = (
            "El registro volverá a estar disponible en selecciones nuevas."
            if target
            else "El registro dejará de aparecer en selecciones nuevas, pero se conservará para el historial."
        )
        if key is None:
            return
        if messagebox.askyesno(verb.capitalize(), f"{detail}\n\n¿Desea {verb}lo?", parent=self):
            self.database.set_record_active(self.current_catalog, key, target)
            self._refresh_catalog()
            if self.refresh_callback:
                self.refresh_callback()

    def _create_catalog_template(self) -> None:
        exports_dir().mkdir(parents=True, exist_ok=True)
        path = filedialog.asksaveasfilename(
            parent=self,
            initialdir=exports_dir(),
            initialfile=f"plantilla_{self.current_catalog}.xlsx",
            defaultextension=".xlsx",
            filetypes=[("Excel", "*.xlsx"), ("CSV", "*.csv")],
        )
        if not path:
            return
        try:
            result = create_import_template(self.current_catalog, path)
            messagebox.showinfo(
                "Plantilla de importación",
                f"Archivo creado:\n\n{result}\n\nComplete las filas sin modificar los encabezados.",
                parent=self,
            )
            self._open_path(result)
        except Exception as exc:
            messagebox.showerror("Plantilla de importación", str(exc), parent=self)

    def _import_catalog(self) -> None:
        path = filedialog.askopenfilename(
            parent=self,
            filetypes=[("Excel o CSV", "*.xlsx *.csv"), ("Excel", "*.xlsx"), ("CSV", "*.csv")],
        )
        if not path:
            return
        try:
            summary = import_catalog(
                self.database,
                self.current_catalog,
                path,
                duplicate_policy=str(
                    self.app_config.get("catalog_import_duplicate_policy", "upsert")
                ),
            )
            detail = (
                f"Importados o actualizados: {summary.imported}\n"
                f"Omitidos: {summary.skipped}\n"
                f"Duplicados omitidos: {summary.duplicates}"
            )
            if summary.issues:
                detail += "\n\nPrimeros errores:\n" + "\n".join(
                    f"Fila {issue.row_number}: {issue.message}" for issue in summary.issues[:10]
                )
            messagebox.showinfo("Importación terminada", detail, parent=self)
            self._refresh_catalog()
        except Exception as exc:
            messagebox.showerror("Importación", str(exc), parent=self)

    def _export_catalog(self) -> None:
        exports_dir().mkdir(parents=True, exist_ok=True)
        path = filedialog.asksaveasfilename(
            parent=self,
            initialdir=exports_dir(),
            initialfile=f"{self.current_catalog}_{datetime.now().strftime('%Y%m%d')}.xlsx",
            defaultextension=".xlsx",
            filetypes=[("Excel", "*.xlsx"), ("CSV", "*.csv")],
        )
        if not path:
            return
        try:
            result = export_catalog(self.database, self.current_catalog, path)
            messagebox.showinfo("Exportación", f"Archivo creado:\n\n{result}", parent=self)
        except Exception as exc:
            messagebox.showerror("Exportación", str(exc), parent=self)

    # ------------------------------------------------------------------
    # Plantillas
    # ------------------------------------------------------------------
    def _build_templates(self) -> None:
        tab = self.tab_templates
        tab.columnconfigure(0, weight=1)
        tab.rowconfigure(1, weight=1)
        controls = ttk.Frame(tab)
        controls.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        ttk.Button(controls, text="Cargar plantilla Word", command=self._install_template).pack(
            side="left"
        )
        ttk.Button(controls, text="Abrir ejemplo", command=self._open_template_example).pack(
            side="left", padx=4
        )
        ttk.Button(controls, text="Validar", command=self._validate_template).pack(
            side="left", padx=4
        )
        ttk.Button(controls, text="Documento de prueba", command=self._test_template).pack(
            side="left", padx=4
        )
        ttk.Button(controls, text="Activar", command=self._activate_template).pack(
            side="left", padx=4
        )
        ttk.Button(controls, text="Retirar", command=self._retire_template).pack(
            side="left", padx=4
        )
        ttk.Button(
            controls, text="Abrir carpeta", command=lambda: self._open_path(templates_dir())
        ).pack(side="right")
        columns = ("id", "name", "version", "type", "state", "valid", "active")
        self.template_tree = ttk.Treeview(tab, columns=columns, show="headings")
        for key, label, width in (
            ("id", "ID", 50),
            ("name", "Plantilla", 230),
            ("version", "Versión", 90),
            ("type", "Tipo", 160),
            ("state", "Estado", 90),
            ("valid", "Válida", 80),
            ("active", "Activa", 70),
        ):
            self.template_tree.heading(key, text=label)
            self.template_tree.column(key, width=width, anchor="w")
        self.template_tree.grid(row=1, column=0, sticky="nsew")
        ttk.Label(
            tab,
            text="Una plantilla nueva se instala como Borrador. Al generar el documento de prueba pasa a En prueba y recién entonces puede activarse.",
            style="Muted.TLabel",
        ).grid(row=2, column=0, sticky="w", pady=(8, 0))

    def _refresh_templates(self) -> None:
        if not hasattr(self, "template_tree"):
            return
        self.template_tree.delete(*self.template_tree.get_children())
        for row in self.database.list_template_versions(include_retired=True):
            try:
                validation = json.loads(row.get("validation_json") or "{}")
                valid = bool(validation.get("valid"))
            except json.JSONDecodeError:
                valid = False
            self.template_tree.insert(
                "",
                "end",
                iid=str(row["id"]),
                values=(
                    row["id"],
                    row["display_name"],
                    row["version_label"],
                    row["document_type"],
                    row["state"],
                    "Sí" if valid else "No",
                    "Sí" if row.get("is_active") else "No",
                ),
            )

    def _selected_template_id(self) -> int | None:
        selection = self.template_tree.selection()
        return int(selection[0]) if selection else None

    def _open_template_example(self) -> None:
        path = resource_path("plantillas/Plantilla_Marcadores_ASH_2.3.docx")
        if not path.is_file():
            messagebox.showerror(
                "Plantilla de ejemplo",
                f"No se encontró el archivo de ejemplo:\n\n{path}",
                parent=self,
            )
            return
        self._open_path(path)

    def _install_template(self) -> None:
        dialog = TemplateInstallDialog(self)
        self.wait_window(dialog)
        if not dialog.result:
            return
        try:
            version_id = self.template_service.install(
                dialog.result["source"],
                template_key=dialog.result["template_key"],
                display_name=dialog.result["display_name"],
                version_label=dialog.result["version_label"],
                document_type=dialog.result["document_type"],
                notes=dialog.result.get("notes") or None,
                state="draft",
            )
            self._refresh_templates()
            self.template_tree.selection_set(str(version_id))
            messagebox.showinfo(
                "Plantilla instalada",
                "La plantilla fue validada e instalada como Borrador. Genere y revise el documento de prueba antes de activarla.",
                parent=self,
            )
            if self.refresh_callback:
                self.refresh_callback()
        except Exception as exc:
            messagebox.showerror("Plantilla no válida", str(exc), parent=self)

    def _validate_template(self) -> None:
        version_id = self._selected_template_id()
        if not version_id:
            messagebox.showinfo("Plantillas", "Seleccione una versión.", parent=self)
            return
        result = self.template_service.validate_version(version_id)
        detail = ["Válida: " + ("Sí" if result.valid else "No")]
        if result.missing_required:
            detail.append("Faltan: " + ", ".join(result.missing_required))
        if result.unknown_markers:
            detail.append("Desconocidos: " + ", ".join(result.unknown_markers))
        detail.extend(result.warnings)
        messagebox.showinfo("Validación de plantilla", "\n".join(detail), parent=self)

    def _test_template(self) -> None:
        version_id = self._selected_template_id()
        if not version_id:
            messagebox.showinfo("Plantillas", "Seleccione una versión.", parent=self)
            return
        try:
            path = self.template_service.create_test_document(version_id)
            messagebox.showinfo(
                "Documento de prueba", f"Se creó el documento:\n\n{path}", parent=self
            )
            self._open_path(path)
            self._refresh_templates()
        except Exception as exc:
            messagebox.showerror("Documento de prueba", str(exc), parent=self)

    def _activate_template(self) -> None:
        version_id = self._selected_template_id()
        if not version_id:
            messagebox.showinfo("Plantillas", "Seleccione una versión.", parent=self)
            return
        try:
            self.template_service.activate(version_id)
            self._refresh_templates()
            if self.refresh_callback:
                self.refresh_callback()
            messagebox.showinfo(
                "Plantilla activa",
                "La versión se utilizará en documentos nuevos según las reglas de selección.",
                parent=self,
            )
        except Exception as exc:
            messagebox.showerror("Activación", str(exc), parent=self)

    def _retire_template(self) -> None:
        version_id = self._selected_template_id()
        if not version_id:
            messagebox.showinfo("Plantillas", "Seleccione una versión.", parent=self)
            return
        if messagebox.askyesno(
            "Retirar plantilla",
            "Los documentos históricos no cambiarán. ¿Retirar esta versión?",
            parent=self,
        ):
            self.template_service.retire(version_id)
            self._refresh_templates()

    # ------------------------------------------------------------------
    # Respaldo y auditoría
    # ------------------------------------------------------------------
    def _build_backup(self) -> None:
        tab = self.tab_backup
        ttk.Label(tab, text="Respaldo y restauración", style="Title.TLabel").pack(anchor="w")
        ttk.Label(
            tab,
            text="El respaldo incluye SQLite, configuración, plantillas administradas y un manifiesto SHA-256.",
            style="Muted.TLabel",
            wraplength=820,
        ).pack(anchor="w", pady=(6, 14))
        buttons = ttk.Frame(tab)
        buttons.pack(anchor="w")
        ttk.Button(
            buttons, text="Crear respaldo", style="Primary.TButton", command=self._create_backup
        ).pack(side="left")
        ttk.Button(buttons, text="Verificar respaldo", command=self._verify_backup).pack(
            side="left", padx=8
        )
        ttk.Button(buttons, text="Restaurar respaldo", command=self._restore_backup).pack(
            side="left"
        )
        ttk.Button(
            buttons, text="Abrir carpeta", command=lambda: self._open_path(backups_dir())
        ).pack(side="left", padx=8)
        self.backup_text = ScrolledText(tab, height=18, wrap="word")
        self.backup_text.pack(fill="both", expand=True, pady=(16, 0))
        self._write_backup_text("No se ha ejecutado ninguna operación en esta sesión.")

    def _write_backup_text(self, text: str) -> None:
        self.backup_text.configure(state="normal")
        self.backup_text.delete("1.0", "end")
        self.backup_text.insert("1.0", text)
        self.backup_text.configure(state="disabled")

    def _create_backup(self) -> None:
        try:
            path = create_backup(
                self.database, app_version=str(self.app_config.get("app_version") or "")
            )
            self._write_backup_text(f"Respaldo creado correctamente:\n{path}")
            messagebox.showinfo("Respaldo", f"Respaldo creado:\n\n{path}", parent=self)
        except Exception as exc:
            messagebox.showerror("Respaldo", str(exc), parent=self)

    def _verify_backup(self) -> None:
        path = filedialog.askopenfilename(
            parent=self, initialdir=backups_dir(), filetypes=[("Respaldo Minutas ASH", "*.zip")]
        )
        if not path:
            return
        try:
            manifest = verify_backup(path)
            self._write_backup_text(json.dumps(manifest, ensure_ascii=False, indent=2))
            messagebox.showinfo(
                "Respaldo válido", "El respaldo superó la verificación de integridad.", parent=self
            )
        except Exception as exc:
            messagebox.showerror("Verificación", str(exc), parent=self)

    def _restore_backup(self) -> None:
        path = filedialog.askopenfilename(
            parent=self, initialdir=backups_dir(), filetypes=[("Respaldo Minutas ASH", "*.zip")]
        )
        if not path:
            return
        if not messagebox.askyesno(
            "Restaurar respaldo",
            "Se reemplazarán la base, la configuración y las plantillas actuales. Se creará una copia de seguridad de la base existente. ¿Continuar?",
            parent=self,
        ):
            return
        try:
            manifest = restore_backup(path)
            self._write_backup_text(json.dumps(manifest, ensure_ascii=False, indent=2))
            messagebox.showinfo(
                "Restauración terminada",
                "Reinicie Minutas ASH para cargar los datos restaurados.",
                parent=self,
            )
        except Exception as exc:
            messagebox.showerror("Restauración", str(exc), parent=self)

    def _build_audit(self) -> None:
        tab = self.tab_audit
        tab.columnconfigure(0, weight=1)
        tab.rowconfigure(1, weight=1)
        ttk.Button(tab, text="Actualizar", command=self._refresh_audit).grid(
            row=0, column=0, sticky="e", pady=(0, 8)
        )
        columns = ("date", "user", "action", "entity", "id", "machine")
        self.audit_tree = ttk.Treeview(tab, columns=columns, show="headings")
        for key, label, width in (
            ("date", "Fecha", 160),
            ("user", "Usuario", 140),
            ("action", "Acción", 110),
            ("entity", "Entidad", 150),
            ("id", "ID", 120),
            ("machine", "Equipo", 150),
        ):
            self.audit_tree.heading(key, text=label)
            self.audit_tree.column(key, width=width, anchor="w")
        self.audit_tree.grid(row=1, column=0, sticky="nsew")

    def _refresh_audit(self) -> None:
        if not hasattr(self, "audit_tree"):
            return
        self.audit_tree.delete(*self.audit_tree.get_children())
        for row in self.database.list_audit_events(500):
            self.audit_tree.insert(
                "",
                "end",
                values=(
                    row.get("created_at"),
                    row.get("windows_user"),
                    row.get("action"),
                    row.get("entity_type"),
                    row.get("entity_id") or "",
                    row.get("machine_name"),
                ),
            )

    def _build_learning(self) -> None:
        tab = self.tab_learning
        tab.columnconfigure(0, weight=1)
        tab.rowconfigure(2, weight=1)
        ttk.Label(tab, text="Aprendizaje supervisado local", style="Title.TLabel").grid(
            row=0, column=0, sticky="w"
        )
        self.learning_summary_var = tk.StringVar(value="Sin datos")
        ttk.Label(
            tab,
            textvariable=self.learning_summary_var,
            style="Muted.TLabel",
            wraplength=900,
        ).grid(row=1, column=0, sticky="w", pady=(5, 10))

        columns = ("term", "variants", "category", "project", "active")
        self.learning_terms_tree = ttk.Treeview(
            tab, columns=columns, show="headings", selectmode="browse"
        )
        for key, label, width in (
            ("term", "Término correcto", 220),
            ("variants", "Variantes de transcripción", 360),
            ("category", "Categoría", 140),
            ("project", "Proyecto", 100),
            ("active", "Estado", 80),
        ):
            self.learning_terms_tree.heading(key, text=label)
            self.learning_terms_tree.column(key, width=width, anchor="w")
        self.learning_terms_tree.grid(row=2, column=0, sticky="nsew")
        actions = ttk.Frame(tab)
        actions.grid(row=3, column=0, sticky="ew", pady=(10, 0))
        ttk.Button(actions, text="Agregar término", command=self._add_learning_term).pack(
            side="left"
        )
        ttk.Button(actions, text="Activar / desactivar", command=self._toggle_learning_term).pack(
            side="left", padx=6
        )
        ttk.Button(actions, text="Actualizar", command=self._refresh_learning).pack(side="left")
        ttk.Button(actions, text="Excluir ejemplo", command=self._exclude_learning_sample).pack(
            side="left", padx=(12, 6)
        )
        ttk.Button(
            actions, text="Exportar dataset LoRA", command=self._export_learning_dataset
        ).pack(side="left")
        ttk.Label(
            actions,
            text="Las correcciones aprobadas se almacenan localmente; no modifican automáticamente el modelo.",
            style="Muted.TLabel",
        ).pack(side="right")

    def _add_learning_term(self) -> None:
        canonical = simpledialog.askstring("Diccionario técnico", "Término correcto:", parent=self)
        if not canonical or not canonical.strip():
            return
        variants_text = (
            simpledialog.askstring(
                "Diccionario técnico",
                "Variantes separadas por coma (ej.: PLC next, pese ele next):",
                parent=self,
            )
            or ""
        )
        category = (
            simpledialog.askstring(
                "Diccionario técnico",
                "Categoría (equipo, persona, sigla, documento, etc.):",
                parent=self,
            )
            or ""
        )
        project = (
            simpledialog.askstring(
                "Diccionario técnico",
                "Proyecto específico, o deje vacío para uso general:",
                parent=self,
            )
            or ""
        )
        variants = [item.strip() for item in variants_text.split(",") if item.strip()]
        try:
            self.database.add_technical_term(
                canonical.strip(), variants, category.strip() or None, project.strip() or None
            )
            self._refresh_learning()
        except Exception as exc:
            messagebox.showerror("Diccionario técnico", str(exc), parent=self)

    def _toggle_learning_term(self) -> None:
        selected = (
            self.learning_terms_tree.selection() if hasattr(self, "learning_terms_tree") else ()
        )
        if not selected:
            messagebox.showinfo("Diccionario técnico", "Seleccione un término.", parent=self)
            return
        term_id = int(selected[0])
        rows = {int(row["id"]): row for row in self.database.list_all_technical_terms()}
        row = rows.get(term_id)
        if not row:
            return
        self.database.set_technical_term_active(term_id, not bool(row.get("active")))
        self._refresh_learning()

    def _exclude_learning_sample(self) -> None:
        meeting_id = simpledialog.askinteger(
            "Excluir ejemplo",
            "ID interno de la minuta que no debe usarse para aprendizaje:",
            parent=self,
            minvalue=1,
        )
        if not meeting_id:
            return
        reason = simpledialog.askstring(
            "Excluir ejemplo",
            "Motivo de exclusión:",
            parent=self,
        )
        try:
            self.database.set_learning_sample_approved(meeting_id, False, reason)
            self._refresh_learning()
            messagebox.showinfo(
                "Aprendizaje",
                "El ejemplo quedó excluido. La minuta original no fue eliminada.",
                parent=self,
            )
        except Exception as exc:
            messagebox.showerror("Aprendizaje", str(exc), parent=self)

    def _export_learning_dataset(self) -> None:
        destination = filedialog.askdirectory(
            parent=self,
            title="Carpeta para dataset LoRA",
            initialdir=exports_dir(),
        )
        if not destination:
            return
        client = simpledialog.askstring(
            "Dataset LoRA",
            "Cliente específico (vacío exporta todos en archivos separados):",
            parent=self,
        )
        only_anonymized = messagebox.askyesno(
            "Dataset LoRA",
            "¿Exportar solamente ejemplos marcados como anonimizados?",
            parent=self,
        )
        try:
            manifest = export_lora_datasets(
                self.database,
                destination,
                client=(client or "").strip() or None,
                require_anonymized=only_anonymized,
            )
            records = sum(int(row["records"]) for row in manifest["files"])
            messagebox.showinfo(
                "Dataset LoRA",
                f"Exportación completada: {records} ejemplo(s) en "
                f"{len(manifest['files'])} archivo(s) separados por cliente.",
                parent=self,
            )
        except Exception as exc:
            messagebox.showerror("Dataset LoRA", str(exc), parent=self)

    def _refresh_learning(self) -> None:
        if not hasattr(self, "learning_terms_tree"):
            return
        summary = self.database.learning_summary()
        self.learning_summary_var.set(
            f"Ejemplos aprobados: {summary['approved_samples']} · "
            f"Correcciones registradas: {summary['corrections']} · "
            f"Correcciones autorizadas: {summary['approved_corrections']} · "
            f"Términos técnicos: {summary['technical_terms']}"
        )
        self.learning_terms_tree.delete(*self.learning_terms_tree.get_children())
        for row in self.database.list_all_technical_terms():
            try:
                variants = ", ".join(json.loads(row.get("variants_json") or "[]"))
            except Exception:
                variants = row.get("variants_json") or ""
            self.learning_terms_tree.insert(
                "",
                "end",
                iid=str(row["id"]),
                values=(
                    row.get("canonical_term"),
                    variants,
                    row.get("category") or "",
                    row.get("project_code") or "General",
                    "Activo" if row.get("active") else "Inactivo",
                ),
            )

    def _build_repository(self) -> None:
        tab = self.tab_repository
        ttk.Label(tab, text="Repositorio de datos", style="Title.TLabel").pack(anchor="w")
        ttk.Label(
            tab,
            text="SQLite está operativo y es la opción predeterminada. La interfaz de repositorio corporativo está preparada para una implementación SQL Server posterior.",
            style="Muted.TLabel",
            wraplength=820,
        ).pack(anchor="w", pady=(6, 16))
        table = ttk.Frame(tab)
        table.pack(anchor="w", fill="x")
        for row, (label, value) in enumerate(
            (
                ("Repositorio activo", "SQLite local"),
                ("Esquema detectado", str(self.database.get_schema_version())),
                ("Integridad", self.database.integrity_check()[1]),
                ("SQL Server", "Contrato preparado; activación planificada para la línea 2.4.x"),
            )
        ):
            ttk.Label(table, text=label).grid(row=row, column=0, sticky="w", padx=(0, 18), pady=6)
            ttk.Label(
                table, text=value, style="Section.TLabel" if row == 0 else "Muted.TLabel"
            ).grid(row=row, column=1, sticky="w", pady=6)

    def _refresh_all(self) -> None:
        self._refresh_catalog()
        self._refresh_templates()
        self._refresh_audit()
        self._refresh_learning()

    @staticmethod
    def _open_path(path: Path) -> None:
        import os
        import subprocess
        import sys

        target = str(path)
        if sys.platform.startswith("win"):
            os.startfile(target)
        elif sys.platform == "darwin":
            subprocess.Popen(["open", target])
        else:
            subprocess.Popen(["xdg-open", target])


def open_administration(
    parent, database: AppDatabase, config: dict, refresh_callback=None
) -> AdministrationCenter:
    window = AdministrationCenter(parent, database, config, refresh_callback)
    window.grab_set()
    return window
