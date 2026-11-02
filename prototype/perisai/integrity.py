"""Cek integritas model sebelum dimuat. Hash tidak cocok -> LLM tidak dipakai, sistem jalan di mode degradasi.

SHA-256 acuan dicatat di DATA.md (cocok dengan LFS oid di Hugging Face, revisi 91cad511).
"""

from __future__ import annotations

import hashlib
from pathlib import Path

from .llm import DEFAULT_MODEL

EXPECTED_SHA256 = {
    "qwen2.5-1.5b-instruct-q3_k_m.gguf": "58cb5c05ecef48e82961f1a2be6544145ea26136f69dddda4bbbd092f0e4b993",
}


def sha256_file(path: Path, chunk: int = 1 << 22) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as fh:
        while block := fh.read(chunk):
            h.update(block)
    return h.hexdigest()


def check_model(path: Path | str = DEFAULT_MODEL) -> dict:
    """{'ok': bool, 'status': str, 'sha256': str|None}. Tidak pernah melempar exception."""
    p = Path(path)
    if not p.exists():
        return {"ok": False, "status": "model tidak ada", "sha256": None, "path": str(p)}
    want = EXPECTED_SHA256.get(p.name)
    if want is None:
        return {"ok": False, "status": "model tidak dikenal (tidak ada hash acuan)", "sha256": None, "path": str(p)}
    got = sha256_file(p)
    if got != want:
        return {"ok": False, "status": "HASH MODEL TIDAK COCOK: model diganti/rusak", "sha256": got, "path": str(p)}
    return {"ok": True, "status": "hash model cocok", "sha256": got, "path": str(p)}


def load_checked_llm(path: Path | str = DEFAULT_MODEL, n_threads: int = 8):
    """(llm atau None, hasil cek). None berarti pakai mode degradasi."""
    chk = check_model(path)
    if not chk["ok"]:
        return None, chk
    try:
        from .llm import LocalLLM
        return LocalLLM(model_path=path, n_threads=n_threads), chk
    except Exception as exc:  # llama_cpp tidak terpasang, RAM kurang, dsb.
        return None, {**chk, "ok": False, "status": f"model gagal dimuat: {type(exc).__name__}"}
