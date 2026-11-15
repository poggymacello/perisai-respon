"""Penjaga aset OT di jalur IT (lapisan aplikasi).

Celah yang ditutup: daftar aset terlindungi di jalur IT (`perisai/policy.py`) berisi nama host tetap (DC, SIEM,
DNS, gateway), sedangkan awalan OT (`hmi-`, `plc-`, ...) hanya dipakai di jalur OT (`perisai/ot.py`). Host
bernama HMI-POMPA01 di log Windows biasa bisa mendapat usulan `isolate_host` (menunggu persetujuan). Kode mesin
di-hash dan tidak diubah, jadi penjagaan ditambahkan di sini, sesudah `decide_v12`.

Aturan: aksi yang memutus host (`isolate_host`) ke host berawalan OT, atau ke host di daftar terlindungi satuan,
diganti eskalasi dengan alasan "aset OT terlindungi: eskalasi ke insinyur proses". Tidak ada aksi lain yang diubah.

Daftar satuan (opsional): berkas teks `aset_terlindungi.txt` di folder data aplikasi, satu nama per baris.
Baris yang diakhiri `*` atau `-` dianggap awalan (mis. `POMPA-*`); baris kosong dan baris `#` diabaikan.
"""

from __future__ import annotations

from pathlib import Path

from . import engine as _engine  # memastikan perisai bisa diimpor

from perisai.ot import OT_PREFIXES  # noqa: E402

PREFIXES = tuple(dict.fromkeys(tuple(p.lower() for p in OT_PREFIXES) + ("hmi-", "plc-", "scada-", "rtu-", "ews-")))
REASON = "aset OT terlindungi: eskalasi ke insinyur proses"
HOST_ACTIONS = {"isolate_host"}  # aksi yang memutus host dari jaringan
UNIT_FILE = "aset_terlindungi.txt"


def unit_list(folder: Path | None = None) -> tuple[set[str], tuple[str, ...]]:
    """(nama persis, awalan) dari daftar satuan. Huruf kecil."""
    if folder is None:
        from .paths import data_dir
        folder = data_dir()
    p = folder / UNIT_FILE
    names, prefixes = set(), []
    if p.is_file():
        for line in p.read_text(encoding="utf-8", errors="replace").splitlines():
            s = line.split("#", 1)[0].strip().lower()
            if not s:
                continue
            if s.endswith("*"):
                prefixes.append(s.rstrip("*"))
            elif s.endswith("-"):
                prefixes.append(s)
            else:
                names.add(s)
    return names, tuple(x for x in prefixes if x)


def match(host: str | None, folder: Path | None = None) -> str | None:
    """Alasan pencocokan bila host termasuk aset OT/terlindungi satuan, selain itu None."""
    if not host:
        return None
    h = str(host).strip().lower()
    short = h.split(".", 1)[0]
    for pre in PREFIXES:
        if h.startswith(pre):
            return f"awalan OT '{pre.upper()}'"
    names, prefixes = unit_list(folder)
    if h in names or short in names:
        return f"daftar satuan ({UNIT_FILE})"
    for pre in prefixes:
        if h.startswith(pre):
            return f"awalan di daftar satuan '{pre.upper()}*'"
    return None


def guard_decision(case: dict, d: dict, folder: Path | None = None) -> dict | None:
    """Ubah keputusan di tempat bila aksinya memutus aset OT. Mengembalikan isi entri audit, atau None."""
    fa = d.get("final_action") or {}
    if fa.get("jenis") not in HOST_ACTIONS:
        return None
    target = fa.get("target") or case.get("primary_host")
    why = match(target, folder)
    if why is None:
        return None
    before = dict(fa)
    d["final_action"] = {"jenis": "escalate", "target": None}
    d["verdict"], d["final_status"] = "EXECUTE", "DIESKALASI"
    d["reasons"] = list(d.get("reasons", [])) + [f"{REASON} ({target}: {why})"]
    d["penjaga_aset_ot"] = {"aksi_sebelum": before, "host": target, "cocok": why}
    return {"alasan": REASON, "host": target, "cocok": why, "aksi_sebelum": before,
            "aksi_sesudah": d["final_action"], "final_status": d["final_status"], "lapisan": "aplikasi (asetot.py)"}


def guard_proposal(jenis: str, target: str | None, case: dict, folder: Path | None = None) -> str | None:
    """Untuk simulasi usulan: alasan penolakan bila usulan memutus aset OT, selain itu None."""
    if jenis not in HOST_ACTIONS:
        return None
    t = target or case.get("primary_host")
    why = match(t, folder)
    return f"{REASON} ({t}: {why})" if why else None


__all__ = ["PREFIXES", "REASON", "UNIT_FILE", "guard_decision", "guard_proposal", "match", "unit_list"]
