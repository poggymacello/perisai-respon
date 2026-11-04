# -*- mode: python ; coding: utf-8 -*-
# PyInstaller onedir untuk PERISAI-RESPON. Dipanggil oleh app/tools/build.py (jangan jalankan langsung tanpa build.py:
# build.py menulis build/engine_meta/build_manifest.json dan build/perisai.ico lebih dulu).
import os
from pathlib import Path

from PyInstaller.utils.hooks import collect_all, collect_submodules

APP = Path(SPECPATH).resolve().parent
PROTO = APP.parent / "prototype"
BUILD = APP / "build"
WITH_LLM = os.environ.get("PERISAI_BUNDLE_LLM", "1") == "1"

datas = [
    (str(APP / "frontend"), "frontend"),
    (str(APP / "perisai_app" / "sampel"), "perisai_app/sampel"),
    (str(APP / "perisai_app" / "engine_meta"), "perisai_app/engine_meta"),
    (str(BUILD / "engine_meta" / "build_manifest.json"), "perisai_app/engine_meta"),
]
binaries = []
hiddenimports = (collect_submodules("perisai") + collect_submodules("perisai_app") + collect_submodules("uvicorn")
                 + ["multipart", "python_multipart", "webview.platforms.edgechromium", "webview.platforms.winforms"])
if WITH_LLM:
    d, b, h = collect_all("llama_cpp")
    datas += d
    binaries += b
    hiddenimports += h

excludes = ["tkinter", "matplotlib", "PIL", "IPython", "pytest", "_pytest", "playwright", "PyInstaller", "setuptools",
            "pip", "pydoc_data", "test", "httpx"]

a = Analysis(
    [str(APP / "run_desktop.py")],
    pathex=[str(APP), str(PROTO)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    excludes=excludes,
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="PERISAI-RESPON",
    debug=False,
    strip=False,
    upx=False,
    console=False,
    icon=str(BUILD / "perisai.ico"),
    version=str(APP / "packaging" / "version_info.txt"),
)
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name="PERISAI-RESPON")
