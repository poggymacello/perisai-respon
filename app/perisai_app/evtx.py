"""Konversi .evtx -> XML dengan wevtutil bawaan Windows (lokal, tanpa jaringan)."""

from __future__ import annotations

import locale
import os
import subprocess
from pathlib import Path


class EvtxError(ValueError):
    pass


def available() -> bool:
    return os.name == "nt" and _exe().exists()


def _exe() -> Path:
    return Path(os.environ.get("SystemRoot", r"C:\Windows")) / "System32" / "wevtutil.exe"


def evtx_to_xml(src: Path, dst: Path, timeout: int = 300) -> int:
    """Tulis XML hasil `wevtutil qe <src> /lf:true /f:xml` ke dst (UTF-8). Mengembalikan jumlah byte."""
    if not available():
        raise EvtxError("berkas .evtx hanya bisa dikonversi di Windows (wevtutil). Ekspor dulu ke XML: "
                        "wevtutil qe <berkas.evtx> /lf:true /f:xml > log.xml")
    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    try:
        r = subprocess.run([str(_exe()), "qe", str(src), "/lf:true", "/f:xml"], capture_output=True,
                           timeout=timeout, creationflags=flags, stdin=subprocess.DEVNULL)
    except subprocess.TimeoutExpired as exc:
        raise EvtxError(f"wevtutil tidak selesai dalam {timeout} detik") from exc
    if r.returncode != 0:
        msg = (r.stderr or r.stdout or b"").decode(locale.getpreferredencoding(False), errors="replace").strip()
        raise EvtxError(f"wevtutil gagal (kode {r.returncode}): {msg[:200]}")
    raw = r.stdout
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        text = raw.decode("mbcs" if os.name == "nt" else locale.getpreferredencoding(False), errors="replace")
    dst.write_text(text, encoding="utf-8")
    return len(raw)
