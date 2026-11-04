"""Sesi kerja analis di folder data lokal. Tidak ada yang dikirim keluar mesin.

Satu sesi = satu folder:
  audit.jsonl     rantai audit SHA-256 (perisai.audit.AuditLog), hanya ditambah, tidak pernah ditulis ulang
  kasus.json.gz   kasus terpilih + keputusan + tindakan analis (dikompres; log serangan asli bisa memuat string
                  yang ditandai antivirus bila ditulis polos, lihat prototype/perisai/cases.py)
Berkas log yang diunggah tidak disimpan: hanya nama, ukuran, dan SHA-256-nya yang dicatat.
"""

from __future__ import annotations

import gzip
import json
import os
import re
import secrets
import shutil
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

from . import engine
from .engine import AuditLog

_ID_RE = re.compile(r"^[A-Za-z0-9_-]{4,64}$")

REVIEW = {  # keputusan analis -> (label, status tinjauan, berlaku untuk status mesin)
    "setujui": ("Aksi disetujui", "DISETUJUI", {"MENUNGGU_PERSETUJUAN"}),
    "tolak": ("Aksi ditolak", "DITOLAK", {"MENUNGGU_PERSETUJUAN"}),
    "tutup": ("Kasus ditutup analis", "DITUTUP_ANALIS", {"DIESKALASI"}),
    "catatan": ("Catatan analis", None, {"MENUNGGU_PERSETUJUAN", "DIESKALASI"}),
}
FINAL_REVIEW = {"DISETUJUI", "DITOLAK", "DITUTUP_ANALIS"}


class ReviewError(ValueError):
    pass


class Workspace:
    def __init__(self, folder: Path):
        self.dir = folder
        self.dir.mkdir(parents=True, exist_ok=True)
        self.lock = threading.RLock()
        self.audit = AuditLog(self.dir / "audit.jsonl")
        self._state: dict | None = None

    # ---------------------------------------------------------- persistensi
    @property
    def state(self) -> dict:
        if self._state is None:
            p = self.dir / "kasus.json.gz"
            if p.exists():
                with gzip.open(p, "rt", encoding="utf-8") as fh:
                    self._state = json.load(fh)
            else:
                self._state = {"versi": 1, "dibuat": engine.now_iso(), "impor": [], "kasus": [], "seq": 0}
        return self._state

    def save(self) -> None:
        tmp = self.dir / "kasus.json.gz.tmp"
        with gzip.open(tmp, "wt", encoding="utf-8") as fh:
            json.dump(self.state, fh, ensure_ascii=False, default=str)
        os.replace(tmp, self.dir / "kasus.json.gz")

    @property
    def sid(self) -> str:
        return self.dir.name

    # ---------------------------------------------------------- impor
    def import_files(self, files: list[tuple[Path, str, int, str]], window: int = 15, label: str = "impor") -> dict:
        """files: [(path, nama asli, ukuran, sha256)]. Mengembalikan ringkasan parse."""
        t0 = time.perf_counter()
        names = [f[1] for f in files]
        source = ", ".join(names)
        with self.lock:
            events, cases, n_empty = engine.parse_files([f[0] for f in files], source, window)
            imp_id = f"I{len(self.state['impor']) + 1:03d}"
            self.audit.append(imp_id, "impor_log", {"jenis": label, "berkas": [
                {"nama": n, "ukuran": s, "sha256": h} for _, n, s, h in files], "n_event": len(events),
                "n_kasus": len(cases), "n_kelompok_tanpa_temuan": n_empty, "jendela_menit": window}, engine.now_iso())
            new_ids = []
            for c in cases:
                d, r, fw = engine.decide_case(c, self.audit)
                self.state["seq"] += 1
                kid = f"K-{self.state['seq']:04d}"
                new_ids.append(kid)
                self.state["kasus"].append({"id": kid, "impor": imp_id, "ditambahkan": engine.now_iso(), "case": c,
                                            "decision": d, "decision_rules": d, "firewall": fw, "tinjauan": [],
                                            "draf": None})
            summary = {"id": imp_id, "jenis": label, "waktu": engine.now_iso(), "berkas": [
                {"nama": n, "ukuran": s, "sha256": h} for _, n, s, h in files], "n_event": len(events),
                "n_kasus": len(cases), "n_kelompok_tanpa_temuan": n_empty, "jendela_menit": window,
                "kasus": new_ids, "detik": round(time.perf_counter() - t0, 3)}
            self.state["impor"].append(summary)
            self.save()
        return summary

    # ---------------------------------------------------------- akses
    def get(self, kid: str) -> dict | None:
        return next((k for k in self.state["kasus"] if k["id"] == kid), None)

    def review_status(self, k: dict) -> str | None:
        st = None
        for r in k["tinjauan"]:
            if r["status"]:
                st = r["status"]
        return st

    def review(self, kid: str, keputusan: str, analis: str, catatan: str) -> dict:
        with self.lock:
            k = self.get(kid)
            if k is None:
                raise KeyError(kid)
            if keputusan not in REVIEW:
                raise ReviewError("keputusan tidak dikenal")
            label, status, allowed = REVIEW[keputusan]
            engine_status = k["decision"]["final_status"]
            if engine_status not in allowed:
                raise ReviewError(f"'{label}' tidak berlaku untuk kasus berstatus {engine_status}")
            current = self.review_status(k)
            if status and current in FINAL_REVIEW:
                raise ReviewError(f"kasus sudah {current}; tambahkan catatan bila perlu")
            fa = k["decision"]["final_action"]
            payload = {"keputusan": keputusan, "status_tinjauan": status, "label": label,
                       "aksi_diusulkan": fa, "status_mesin": engine_status, "analis": analis, "catatan": catatan,
                       "dieksekusi": False, "keterangan": "dicatat, tidak dieksekusi (pilot baca-saja)"}
            entry = self.audit.append(k["case"]["case_id"], "tindakan_analis", payload, engine.now_iso())
            rec = {"keputusan": keputusan, "label": label, "status": status, "analis": analis, "catatan": catatan,
                   "ts": entry["ts"], "seq": entry["seq"], "hash": entry["entry_hash"]}
            k["tinjauan"].append(rec)
            self.save()
            return rec

    def all_reviews(self) -> list[dict]:
        out = []
        for k in self.state["kasus"]:
            fa = k["decision"]["final_action"]
            aksi = fa["jenis"] + (f" -> {fa['target']}" if fa.get("target") else "")
            for r in k["tinjauan"]:
                out.append({**r, "kasus": k["id"], "case_id": k["case"]["case_id"], "aksi": aksi})
        return sorted(out, key=lambda r: r["seq"])

    def set_draft(self, kid: str, decision: dict, info: dict) -> None:
        with self.lock:
            k = self.get(kid)
            if k is None:
                return
            k["decision"] = decision
            k["draf"] = info
            self.save()

    # ---------------------------------------------------------- audit
    def tamper_test(self, seq: int | None = None) -> dict:
        """Salin rantai, ubah satu entri di SALINAN, verifikasi salinan. Berkas asli tidak disentuh."""
        with self.lock:
            entries = self.audit.entries()
            if not entries:
                raise ReviewError("jejak audit masih kosong")
            idx = seq if seq is not None and 0 <= seq < len(entries) else None
            if idx is None:
                idx = next((e["seq"] for e in reversed(entries) if e["kind"] == "tindakan_analis"), None)
            if idx is None:
                idx = next((e["seq"] for e in entries if e["kind"] == "keputusan_v12"), 0)
            tmpdir = self.dir / f"_uji_{secrets.token_hex(4)}"
            tmpdir.mkdir()
            try:
                copy = tmpdir / "audit_salinan.jsonl"
                shutil.copy(self.audit.path, copy)
                lines = copy.read_text(encoding="utf-8").splitlines()
                e = json.loads(lines[idx])
                field, before, after = _tamper(e)
                lines[idx] = json.dumps(e, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
                copy.write_text("\n".join(lines) + "\n", encoding="utf-8")
                v = AuditLog(copy).verify()
            finally:
                shutil.rmtree(tmpdir, ignore_errors=True)
            return {"seq": idx, "jenis_entri": entries[idx]["kind"], "field": field, "sebelum": before,
                    "sesudah": after, "hasil": v, "asli": self.audit.verify()}


def _tamper(e: dict) -> tuple[str, object, object]:
    p = e["payload"]
    for key, new in (("final_status", "DIEKSEKUSI"), ("keputusan", "setujui"), ("dieksekusi", True),
                     ("n_kasus", 0), ("injection", False)):
        if key in p and p[key] != new:
            before = p[key]
            p[key] = new
            return f"payload.{key}", before, new
    before = e.get("ts")
    e["ts"] = "2026-01-01T00:00:00+00:00"
    return "ts", before, e["ts"]


class Store:
    """Desktop: satu sesi aktif. Demo: satu sesi per pengunjung (cookie), dibatasi jumlahnya."""

    def __init__(self, root: Path, demo: bool = False, max_demo: int = 300):
        self.root = root
        self.demo = demo
        self.max_demo = max_demo
        self.sessions_dir = root / ("pengunjung" if demo else "sesi")
        self.sessions_dir.mkdir(parents=True, exist_ok=True)
        self._ws: dict[str, Workspace] = {}
        self._lock = threading.Lock()

    def _new_id(self) -> str:
        if self.demo:
            return secrets.token_hex(12)
        base = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
        sid, n = base, 1
        while (self.sessions_dir / sid).exists():
            n += 1
            sid = f"{base}-{n}"
        return sid

    def _open(self, sid: str) -> Workspace:
        with self._lock:
            ws = self._ws.get(sid)
            if ws is None:
                ws = Workspace(self.sessions_dir / sid)
                self._ws[sid] = ws
            return ws

    def active(self, visitor: str | None = None) -> tuple[Workspace, bool]:
        """(sesi, baru_dibuat)."""
        if self.demo:
            if visitor and _ID_RE.match(visitor) and (self.sessions_dir / visitor).exists():
                return self._open(visitor), False
            self._prune()
            return self._open(self._new_id()), True
        marker = self.root / "sesi_aktif.txt"
        sid = marker.read_text(encoding="utf-8").strip() if marker.exists() else ""
        if sid and _ID_RE.match(sid) and (self.sessions_dir / sid).exists():
            return self._open(sid), False
        return self.new_session(), True

    def new_session(self, visitor: str | None = None) -> Workspace:
        sid = self._new_id()
        ws = self._open(sid)
        if not self.demo:
            (self.root / "sesi_aktif.txt").write_text(sid, encoding="utf-8")
        return ws

    def list_sessions(self) -> list[dict]:
        out = []
        for d in sorted(self.sessions_dir.iterdir(), reverse=True):
            if d.is_dir() and _ID_RE.match(d.name):
                out.append({"id": d.name, "ada_audit": (d / "audit.jsonl").exists()})
        return out

    def _prune(self) -> None:
        dirs = sorted((d for d in self.sessions_dir.iterdir() if d.is_dir()), key=lambda d: d.stat().st_mtime)
        for d in dirs[: max(0, len(dirs) - self.max_demo + 1)]:
            with self._lock:
                self._ws.pop(d.name, None)
            shutil.rmtree(d, ignore_errors=True)
