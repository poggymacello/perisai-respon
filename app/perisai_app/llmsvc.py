"""LLM lokal (opsional) dan antrean tugas latar belakang.

Mode LLM aktif hanya bila: berkas model ada, SHA-256-nya cocok dengan acuan mesin (perisai.integrity), dan
llama_cpp bisa diimpor. Selain itu aplikasi jalan di mode aturan. Model dimuat sekali, saat draf AI pertama
diminta. Satu pekerja saja: inferensi di CPU memakai semua inti, jadi tugas diantre, tidak paralel.
"""

from __future__ import annotations

import importlib.util
import json
import os
import secrets
import threading
import time
import traceback
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from . import engine
from .paths import data_dir, model_candidates

_ = engine  # memastikan perisai bisa diimpor sebelum modul di bawah
from perisai.integrity import EXPECTED_SHA256, check_model, load_checked_llm  # noqa: E402


def llama_importable() -> bool:
    try:
        return importlib.util.find_spec("llama_cpp") is not None
    except (ImportError, ValueError):
        return False


class Jobs:
    def __init__(self) -> None:
        self._jobs: dict[str, dict] = {}
        self._lock = threading.Lock()
        self.pool = ThreadPoolExecutor(max_workers=1, thread_name_prefix="perisai-llm")

    def submit(self, kind: str, owner: str, fn, **meta) -> dict:
        jid = secrets.token_hex(8)
        job = {"id": jid, "jenis": kind, "pemilik": owner, "status": "antre", "tahap": "menunggu giliran",
               "dibuat": time.time(), "mulai": None, "selesai": None, "hasil": None, "galat": None, **meta}
        with self._lock:
            self._jobs[jid] = job

        def run():
            job["status"], job["mulai"] = "berjalan", time.time()
            try:
                job["hasil"] = fn(lambda stage: job.__setitem__("tahap", stage))
                job["status"], job["tahap"] = "selesai", "selesai"
            except Exception as exc:  # galat dilaporkan ke UI, bukan dilempar ke thread
                job["status"], job["galat"] = "gagal", f"{type(exc).__name__}: {str(exc)[:300]}"
                job["jejak"] = traceback.format_exc()[-2000:]
            finally:
                job["selesai"] = time.time()

        self.pool.submit(run)
        return self.view(job)

    def get(self, jid: str) -> dict | None:
        return self._jobs.get(jid)

    def active_for(self, owner: str, kasus: str | None = None) -> dict | None:
        for j in self._jobs.values():
            if j["pemilik"] == owner and j["status"] in ("antre", "berjalan") and (kasus is None or j.get("kasus") == kasus):
                return j
        return None

    @staticmethod
    def view(job: dict) -> dict:
        now = time.time()
        el = (job["selesai"] or now) - (job["mulai"] or now) if job["mulai"] else 0.0
        return {k: v for k, v in job.items() if k not in ("jejak", "pemilik")} | {"detik_berjalan": round(el, 1)}


class LLMService:
    def __init__(self, enabled: bool = True):
        self.enabled = enabled
        self._llm = None
        self._load_lock = threading.Lock()
        self._check: dict | None = None
        self._checking = False
        self.load_seconds: float | None = None
        self.last_case_seconds: float | None = None
        self.n_threads = max(1, min(8, (os.cpu_count() or 4)))
        self.jobs = Jobs()

    # ------------------------------------------------------------ model
    def model_path(self) -> tuple[Path | None, str | None]:
        for p, label, _ in model_candidates():
            if p.is_file():
                return p, label
        return None, None

    def _cache_file(self) -> Path:
        return data_dir() / "cache" / "cek_model.json"

    def check(self, force: bool = False) -> dict:
        """Hasil cek SHA-256 model (di-cache berdasarkan path+ukuran+waktu ubah)."""
        p, label = self.model_path()
        if p is None:
            return {"ok": False, "status": "model tidak ada", "sha256": None}
        st = p.stat()
        key = {"path": str(p), "size": st.st_size, "mtime": int(st.st_mtime)}
        cf = self._cache_file()
        if not force and cf.exists():
            try:
                c = json.loads(cf.read_text(encoding="utf-8"))
                if c.get("key") == key:
                    return c["hasil"]
            except (OSError, ValueError, KeyError):
                pass
        res = check_model(p)
        res = {k: v for k, v in res.items() if k != "path"}
        cf.parent.mkdir(parents=True, exist_ok=True)
        cf.write_text(json.dumps({"key": key, "hasil": res}), encoding="utf-8")
        return res

    def check_async(self) -> None:
        if not self.enabled or self._checking:
            return
        self._checking = True

        def run():
            try:
                self._check = self.check()
            finally:
                self._checking = False

        threading.Thread(target=run, daemon=True, name="perisai-cek-model").start()

    def status(self) -> dict:
        p, label = self.model_path()
        chk = self._check
        if p is not None and chk is None and not self._checking:
            self.check_async()
        llama = llama_importable()
        if not self.enabled:
            reason = "dinonaktifkan di mode demo publik"
        elif p is None:
            reason = "berkas model tidak ditemukan"
        elif self._checking or chk is None:
            reason = "sedang memeriksa SHA-256 model"
        elif not chk["ok"]:
            reason = chk["status"]
        elif not llama:
            reason = "pustaka llama_cpp tidak tersedia di build ini"
        else:
            reason = None
        return {"tersedia": reason is None, "alasan": reason, "dimuat": self._llm is not None,
                "llama_cpp": llama, "memeriksa": self._checking,
                "model": {"nama": p.name if p else None, "sumber": label, "ukuran": p.stat().st_size if p else None,
                          "cek": chk, "sha256_acuan": EXPECTED_SHA256.get(p.name) if p else None},
                "lokasi_model": [{"lokasi": disp, "keterangan": lab, "ada": c.is_file()} for c, lab, disp in model_candidates()],
                "thread": self.n_threads, "detik_muat": self.load_seconds, "detik_kasus_terakhir": self.last_case_seconds}

    def get_llm(self, stage=lambda s: None):
        with self._load_lock:
            if self._llm is not None:
                return self._llm
            st = self.status()
            if not st["tersedia"]:
                raise RuntimeError(f"LLM tidak tersedia: {st['alasan']}")
            p, _ = self.model_path()
            stage("memeriksa SHA-256 dan memuat model ke memori")
            t0 = time.perf_counter()
            llm, chk = load_checked_llm(p, n_threads=self.n_threads)
            if llm is None:
                raise RuntimeError(f"model tidak dimuat: {chk['status']}")
            self.load_seconds = round(time.perf_counter() - t0, 1)
            self._llm = llm
            return llm
