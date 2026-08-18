# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path
from PyInstaller.utils.hooks import collect_all

root = Path(SPECPATH)

dnd_datas, dnd_binaries, dnd_hiddenimports = collect_all("tkinterdnd2")
reportlab_datas, reportlab_binaries, reportlab_hiddenimports = collect_all("reportlab")
msal_datas, msal_binaries, msal_hiddenimports = collect_all("msal")

a = Analysis(
    [str(root / "src" / "gui.py")],
    pathex=[str(root)],
    binaries=dnd_binaries + reportlab_binaries + msal_binaries,
    datas=[
        (str(root / "assets" / "logo_ash.png"), "assets"),
        (str(root / "assets" / "ash.ico"), "assets"),
        (str(root / "config.json"), "."),
        (str(root / "docs"), "docs"),
        (str(root / "plantillas"), "plantillas"),
    ] + dnd_datas + reportlab_datas + msal_datas,
    hiddenimports=[
        "docx",
        "docx.oxml",
        "lxml.etree",
        "pydantic",
        "requests",
        "src.appearance",
        "src.experience",
        "src.preferences",
        "src.legacy_gui",
        "src.document_numbering",
        "src.project_profiles",
        "src.review_quality",
        "src.release_identity",
        "src.secret_store",
        "src.teams_graph",
        "src.updater",
        "src.providers.ollama_local",
        "src.providers.openai_responses",
        "src.providers.azure_openai_responses",
        "src.providers.anthropic_messages",
        "src.providers.gemini_generate",
        "src.providers.openai_compatible",
        "src.administration",
        "src.backup_service",
        "src.catalog_io",
        "src.catalog_models",
        "src.help_center",
        "src.template_engine",
        "src.template_service",
        "src.documents.managed_template",
        "openpyxl",
        "pypdf",
        "openpyxl.styles",
    ] + dnd_hiddenimports + reportlab_hiddenimports + msal_hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["pytest", "unittest.mock"],
    noarchive=False,
    optimize=1,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="MinutasASH",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(root / "assets" / "ash.ico"),
    version=str(root / "assets" / "version_info.txt"),
    manifest=str(root / "assets" / "application.manifest"),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="MinutasASH",
)
