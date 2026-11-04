"""Lokasi berkas: sumber daya (frontend, sampel), folder data lokal, model, dan mesin `perisai`.

Tidak ada path absolut milik mesin pengembang. Semua lokasi diturunkan dari lokasi berkas ini, dari folder
PyInstaller (sys._MEIPASS), atau dari variabel lingkungan:
  PERISAI_DATA_DIR   folder data (bawaan Windows: %LOCALAPPDATA%\\PERISAI-RESPON)
  PERISAI_MODEL      path berkas model GGUF (opsional)
  PERISAI_ENGINE_DIR folder yang berisi paket `perisai` (bawaan dev: ../prototype)
  PERISAI_MODE       "desktop" (bawaan) atau "demo" (server publik, data contoh saja)
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

FROZEN = bool(getattr(sys, "frozen", False))
PKG_DIR = Path(__file__).resolve().parent
APP_ROOT = PKG_DIR.parent  # folder app/ saat dev
MODEL_NAME = "qwen2.5-1.5b-instruct-q3_k_m.gguf"


def bundle_dir() -> Path:
    """Folder sumber daya: _internal/ di build PyInstaller, app/ saat dev."""
    return Path(getattr(sys, "_MEIPASS", APP_ROOT))


def exe_dir() -> Path:
    return Path(sys.executable).resolve().parent if FROZEN else APP_ROOT


def frontend_dir() -> Path:
    env = os.environ.get("PERISAI_FRONTEND_DIR")
    return Path(env) if env else bundle_dir() / "frontend"


def sample_dir() -> Path:
    return PKG_DIR / "sampel"


def engine_meta_dir() -> Path:
    """Salinan berkas hash beku (prototype/frozen/*.sha256) untuk cek integritas mesin."""
    return PKG_DIR / "engine_meta"


def ensure_engine_importable() -> None:
    """Saat dev/Docker, paket `perisai` ada di ../prototype; di build PyInstaller sudah dibundel."""
    try:
        import perisai  # noqa: F401
        return
    except ImportError:
        pass
    env = os.environ.get("PERISAI_ENGINE_DIR")
    cand = [Path(env)] if env else []
    cand.append(APP_ROOT.parent / "prototype")
    for c in cand:
        if (c / "perisai" / "__init__.py").exists():
            sys.path.insert(0, str(c))
            return
    raise ImportError("paket mesin `perisai` tidak ditemukan; set PERISAI_ENGINE_DIR ke folder prototype")


def engine_source_dir() -> Path | None:
    """Folder berkas .py mesin bila tersedia (dev/Docker). Di build PyInstaller None (kode ada di arsip PYZ)."""
    import perisai

    p = Path(perisai.__file__).resolve().parent
    return p if (p / "v12.py").exists() else None


def app_mode() -> str:
    m = os.environ.get("PERISAI_MODE", "desktop").strip().lower()
    return "demo" if m == "demo" else "desktop"


def data_dir() -> Path:
    env = os.environ.get("PERISAI_DATA_DIR")
    if env:
        p = Path(env)
    elif app_mode() == "demo":
        p = Path(os.environ.get("TMPDIR", "/tmp")) / "perisai-demo"
    elif os.name == "nt":
        p = Path(os.environ.get("LOCALAPPDATA") or Path.home() / "AppData" / "Local") / "PERISAI-RESPON"
    else:
        p = Path(os.environ.get("XDG_DATA_HOME") or Path.home() / ".local" / "share") / "perisai-respon"
    p.mkdir(parents=True, exist_ok=True)
    return p


def display_path(p: Path | str) -> str:
    """Path untuk ditampilkan di UI tanpa nama pengguna (mis. %LOCALAPPDATA%\\PERISAI-RESPON)."""
    s = str(p)
    subs = []
    for var in ("LOCALAPPDATA", "APPDATA", "USERPROFILE", "TMPDIR", "TEMP"):
        v = os.environ.get(var)
        if v and len(v) > 3:
            subs.append((v, f"%{var}%" if os.name == "nt" else f"${var}"))
    home = str(Path.home())
    subs.append((home, "~"))
    for v, name in sorted(subs, key=lambda kv: -len(kv[0])):
        if s.lower().startswith(v.lower()):
            return name + s[len(v):]
    return s


def model_candidates() -> list[tuple[Path, str, str]]:
    """(path, label sumber, path untuk ditampilkan) dalam urutan prioritas."""
    out: list[tuple[Path, str, str]] = []
    env = os.environ.get("PERISAI_MODEL")
    if env:
        out.append((Path(env), "variabel PERISAI_MODEL", display_path(env)))
    p = data_dir() / "models" / MODEL_NAME
    out.append((p, "folder model data aplikasi", display_path(p)))
    out.append((exe_dir() / "models" / MODEL_NAME, "folder models di samping PERISAI-RESPON.exe",
                "<folder aplikasi>" + ("\\" if os.name == "nt" else "/") + "models" + ("\\" if os.name == "nt" else "/") + MODEL_NAME))
    if not FROZEN:
        out.append((APP_ROOT.parent / "prototype" / "models" / MODEL_NAME, "prototype/models (pengembangan)",
                    f"prototype/models/{MODEL_NAME}"))
    return out
