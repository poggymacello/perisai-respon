"""Jalur OT: telemetri proses HAI 21.03 -> detektor amplop normal -> kasus OT -> keputusan khusus aset proses.

Data: HAI (HIL-based Augmented ICS) Security Dataset 21.03, CC BY-SA 4.0, github.com/icsdataset/hai
(boiler P1, turbin P2, air P3, simulasi HIL P4). Lihat DATA.md dan PRAREG_v4_OT_BENIGN.md.

Detektor (deterministik, tanpa LLM, bisa dijelaskan ke operator):
 * profil per tag dari data NORMAL train1 + train2: kuantil 0,05 % dan 99,95 %; span minimum 1 % dari |median|
   (tag yang hampir konstan, mis. posisi katup, bergeser sedikit antarhari);
 * satu detik melanggar bila nilai keluar dari [lo - m*span, hi + m*span]; m dikalibrasi di train3 (normal);
 * jendela 60 detik berbunyi bila ada tag yang melanggar >= K_SECONDS detik di jendela itu.
Kebijakan OT berbeda dari IT: PLC/HMI/RTU/SIS tidak pernah diisolasi atau diblokir oleh sistem, bahkan dengan
persetujuan di layar ini. Memutus pengendali bisa menghentikan proses fisik, jadi keputusan ada di insinyur
proses dan operator lapangan.
"""

from __future__ import annotations

import gzip
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from .firewall import inspect_case
from .v11 import filter_sentences
from .policy import filter_summary

ROOT = Path(__file__).resolve().parents[1]
HAI_DIR = ROOT / "data" / "hai"
LABEL_COLS = ["attack", "attack_P1", "attack_P2", "attack_P3"]
WINDOW_S = 60
K_SECONDS = 10
Q_LO, Q_HI = 0.0005, 0.9995
MARGINS = [0.0, 0.05, 0.1, 0.25, 0.5, 1.0, 2.0]
TARGET_FA = 0.01
PROCESS = {"P1": "boiler", "P2": "turbin", "P3": "air", "P4": "simulasi HIL"}
OT_PREFIXES = ("plc-", "hmi-", "rtu-", "sis-", "ews-")
CHECKLIST = [
    "cocokkan nilai tag dengan alat ukur lokal di lapangan",
    "cek perubahan logika/setpoint di engineering workstation dalam 24 jam terakhir",
    "jangan memutus PLC/HMI dari jaringan tanpa keputusan insinyur proses",
]


def load(name: str) -> pd.DataFrame:
    with gzip.open(HAI_DIR / f"{name}.csv.gz", "rt", encoding="utf-8") as fh:
        df = pd.read_csv(fh)
    df.columns = [c.strip() for c in df.columns]
    return df


def tags(df: pd.DataFrame) -> list[str]:
    return [c for c in df.columns if c not in ["time"] + LABEL_COLS]


@dataclass
class Profile:
    lo: pd.Series
    hi: pd.Series
    span: pd.Series
    margin: float = 0.0


def fit_profile(train: pd.DataFrame) -> Profile:
    x = train[tags(train)].astype(float)
    lo, hi = x.quantile(Q_LO), x.quantile(Q_HI)
    span = np.maximum(hi - lo, (x.median().abs() * 0.01).clip(lower=1e-6))
    return Profile(lo, hi, pd.Series(span, index=lo.index))


def violations(df: pd.DataFrame, prof: Profile, margin: float | None = None) -> pd.DataFrame:
    m = prof.margin if margin is None else margin
    x = df[list(prof.lo.index)].astype(float)
    return (x < prof.lo - m * prof.span) | (x > prof.hi + m * prof.span)


def window_alarms(df: pd.DataFrame, prof: Profile, margin: float | None = None) -> pd.DataFrame:
    """Satu baris per jendela 60 s: alarm, tag pelanggar, label serangan (bila ada)."""
    v = violations(df, prof, margin)
    w = np.arange(len(df)) // WINDOW_S
    counts = v.groupby(w).sum()
    out = pd.DataFrame({"window": counts.index, "start": df["time"].groupby(w).first().values,
                        "alarm": (counts >= K_SECONDS).any(axis=1).values})
    out["tags"] = [list(r[r >= K_SECONDS].sort_values(ascending=False).index) for _, r in counts.iterrows()]
    if "attack" in df.columns:
        out["attack"] = (df["attack"].groupby(w).max() > 0).values
    return out


def calibrate(prof: Profile, normal: pd.DataFrame) -> tuple[float, list[dict]]:
    """Margin terkecil dengan laju alarm palsu jendela <= TARGET_FA di data normal kalibrasi."""
    trace = []
    for m in MARGINS:
        fa = float(window_alarms(normal, prof, m)["alarm"].mean())
        trace.append({"margin": m, "false_alarm_rate": fa})
        if fa <= TARGET_FA:
            return m, trace
    return MARGINS[-1], trace


def episodes(df: pd.DataFrame) -> list[tuple[int, int]]:
    """Segmen serangan berurutan (indeks baris awal, akhir inklusif)."""
    a = (df["attack"] > 0).to_numpy()
    eps, start = [], None
    for i, flag in enumerate(a):
        if flag and start is None:
            start = i
        if not flag and start is not None:
            eps.append((start, i - 1))
            start = None
    if start is not None:
        eps.append((start, len(a) - 1))
    return eps


def evaluate(df: pd.DataFrame, prof: Profile) -> dict:
    wa = window_alarms(df, prof)
    att, nor = wa[wa["attack"]], wa[~wa["attack"]]
    eps = episodes(df)
    alarm_w = set(wa.loc[wa["alarm"], "window"])
    hit = [any(w in alarm_w for w in range(s // WINDOW_S, e // WINDOW_S + 1)) for s, e in eps]
    return {"windows": int(len(wa)), "attack_windows": int(len(att)), "normal_windows": int(len(nor)),
            "window_recall": float(att["alarm"].mean()) if len(att) else None,
            "window_false_alarm_rate": float(nor["alarm"].mean()) if len(nor) else None,
            "episodes": len(eps), "episodes_detected": int(sum(hit))}


# ------------------------------------------------------------------ kasus + keputusan OT
def is_ot_asset(name: str | None) -> bool:
    return bool(name) and str(name).lower().startswith(OT_PREFIXES)


def case_from_window(df: pd.DataFrame, prof: Profile, window: int, operator_note: str | None = None) -> dict:
    """Kasus OT dari satu jendela alarm: maks 8 tag dengan simpangan terbesar."""
    rows = df.iloc[window * WINDOW_S:(window + 1) * WINDOW_S]
    v = violations(rows, prof).sum()
    x = rows[list(prof.lo.index)].astype(float)
    dev = ((x - prof.hi).clip(lower=0) + (prof.lo - x).clip(lower=0)).max() / prof.span
    picked = [t for t in dev[v >= K_SECONDS].sort_values(ascending=False).index][:8]
    events = []
    for n, t in enumerate(picked, 1):
        proc = t.split("_")[0]
        s = x[t]
        val = s.iloc[int(np.argmax(np.abs(s - (prof.lo[t] + prof.hi[t]) / 2)))]
        events.append({"id": f"E{n}", "EventID": "OT-AMPLOP", "Channel": "HAI-21.03", "Hostname": f"PLC-{proc}",
                       "ObjectName": t, "Nilai": round(float(val), 4),
                       "Normal": f"[{prof.lo[t]:.4g}, {prof.hi[t]:.4g}]", "DetikMelanggar": int(v[t]),
                       "TimeCreated": str(rows["time"].iloc[0])})
    if operator_note is not None:
        events.append({"id": f"E{len(events) + 1}", "EventID": "HMI-CATATAN", "Channel": "HMI",
                       "Hostname": "HMI-01", "Message": operator_note})
    hosts = [e["Hostname"] for e in events if e["Hostname"].startswith("PLC-")]
    return {"case_id": f"OT-w{window}", "primary_host": max(set(hosts), key=hosts.count) if hosts else "",
            "events": events}


def template_summary_ot(case: dict) -> str:
    ev = [e for e in case["events"] if e["EventID"] == "OT-AMPLOP"]
    if not ev:
        return "Tidak ada tag di luar amplop normal. Perlu ditinjau operator."
    procs = sorted({e["Hostname"][4:] for e in ev})
    parts = [f"{e['ObjectName']} = {e['Nilai']} (normal {e['Normal']}, {e['DetikMelanggar']} dtk)" for e in ev[:4]]
    return (f"Anomali proses {', '.join(f'{p} ({PROCESS.get(p, p)})' for p in procs)}: {len(ev)} tag di luar amplop "
            f"normal mulai {ev[0]['TimeCreated']}: " + "; ".join(parts) + ".")


def decide_ot(case: dict, proposal: dict | None = None) -> dict:
    """Keputusan OT. Aksi akhir selalu eskalasi ke insinyur proses; aset OT tidak pernah diputus sistem."""
    fw = inspect_case(case)
    reasons, warnings = ["OT: kategori dan aksi dari aturan amplop normal"], []
    verdict = "EXECUTE"
    if fw.injection:
        warnings.append("INJEKSI_TERDETEKSI")
        reasons.append("instruksi terdeteksi di catatan HMI/teks bebas: tidak dipakai untuk keputusan")
    aksi = (proposal or {}).get("aksi") or {}
    if aksi.get("jenis") in ("isolate_host", "block_ip"):
        verdict = "BLOCK"
        tgt = aksi.get("target")
        why = "aset proses OT" if is_ot_asset(tgt) or not tgt else "jaringan OT"
        reasons.append(f"usulan {aksi['jenis']} ke '{tgt}' ditolak: memutus {why} bisa menghentikan proses fisik")
    elif aksi.get("jenis") == "no_action":
        reasons.append("usulan menutup kasus tidak dijalankan: keputusan pada operator")
    draf, dropped = "", []
    if proposal:
        draf, _ = filter_summary(proposal.get("ringkasan", ""), case)
        draf, dropped = filter_sentences(draf, case)
        if dropped:
            warnings.append("DRAF_AI_DISUNTING")
    return {"verdict": verdict, "final_action": {"jenis": "escalate", "target": None, "ke": "insinyur proses + operator lapangan"},
            "final_status": "DIESKALASI", "kategori": "anomali_proses_ot", "ringkasan": template_summary_ot(case),
            "checklist": CHECKLIST, "reasons": reasons, "warnings": warnings, "draf_ai": draf,
            "kalimat_dibuang": dropped, "source": "rules_ot"}
