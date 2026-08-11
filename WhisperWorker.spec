# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path
from PyInstaller.utils.hooks import collect_all

root = Path(SPECPATH)
fw_datas, fw_binaries, fw_hiddenimports = collect_all("faster_whisper")
ct_datas, ct_binaries, ct_hiddenimports = collect_all("ctranslate2")

a = Analysis(
    [str(root / "src" / "whisper_worker.py")],
    pathex=[str(root)],
    binaries=fw_binaries + ct_binaries,
    datas=fw_datas + ct_datas,
    hiddenimports=fw_hiddenimports + ct_hiddenimports,
    excludes=["pytest", "tkinter"],
    optimize=1,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz, a.scripts, a.binaries, a.datas, [],
    name="WhisperWorker", console=True, debug=False, strip=False, upx=False,
)
