"""Jembatan ke mesin `perisai` (v1.2.2). Hanya memanggil fungsi mesin; tidak ada logika keputusan di sini.

Alur impor sama dengan `prototype/triase.py:triage` (tes paritas di app/tests/test_api.py):
  importer.read_file -> importer.to_cases -> buang kelompok tanpa temuan (kecuali ada injeksi)
  -> pipeline.run_guarded (firewall + usulan LLM/None + policy v1, dicatat ke audit)
  -> v12.decide_v12 -> audit 'keputusan_v12'.
"""

from __future__ import annotations

import hashlib
import re
import statistics
import time
from datetime import datetime, timezone
from pathlib import Path

from .paths import ensure_engine_importable, engine_meta_dir, engine_source_dir

ensure_engine_importable()

from perisai import ACTIONS, CATEGORY_ID, RISKY_ACTIONS, detector, firewall, importer, laporan, policy  # noqa: E402
from perisai.audit import AuditLog  # noqa: E402
from perisai.firewall import FirewallReport  # noqa: E402
from perisai.logs import FREE_TEXT_FIELDS, STRUCTURED_FIELDS  # noqa: E402
from perisai.pipeline import run_guarded  # noqa: E402
from perisai.v12 import decide_v12  # noqa: E402

V12_KEYS = ("verdict", "final_action", "kategori", "warnings", "final_status", "draf_ai")

# Kategori mesin -> taktik MITRE ATT&CK (Enterprise).
ATTACK_TACTIC = {
    "credential_access": ("TA0006", "Credential Access"),
    "defense_evasion": ("TA0005", "Defense Evasion"),
    "lateral_movement": ("TA0008", "Lateral Movement"),
    "discovery": ("TA0007", "Discovery"),
    "persistence": ("TA0003", "Persistence"),
    "execution": ("TA0002", "Execution"),
    "privilege_escalation": ("TA0004", "Privilege Escalation"),
    "collection": ("TA0009", "Collection"),
}
SEVERITY_NAME = {3: "tinggi", 2: "sedang", 1: "rendah", 0: "info"}
ACTION_LABEL = {"isolate_host": "Isolasi host", "block_ip": "Blokir IP", "escalate": "Eskalasi ke analis",
                "no_action": "Tanpa aksi (tutup)"}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _fw_dump(fw: FirewallReport) -> dict:
    return {"injeksi": fw.injection, "kode": fw.codes(), "obfuscation": list(fw.obfuscation),
            "temuan": [{"event": f.event_id, "field": f.field, "kode": list(f.codes), "cuplikan": f.snippet}
                       for f in fw.flagged]}


def decide_case(case: dict, audit: AuditLog, llm=None) -> tuple[dict, dict, dict]:
    """Satu kasus lewat jalur triase.py. Mengembalikan (keputusan v1.2.2, hasil run_guarded, laporan firewall)."""
    r = run_guarded(case, llm, audit)
    p = r.get("proposal")
    fw = firewall.inspect_case(case)
    # triase.py memakai "LLM dimatikan" juga saat LLM jalan tetapi keluarannya tidak valid; di sini dibedakan
    # (alasan yang sama dengan yang diberikan run_guarded ke policy v1).
    no_prop = r.get("error") or ("keluaran LLM tidak valid" if llm is not None else "LLM dimatikan")
    d = decide_v12(case, p, fw, None if p else no_prop)
    audit.append(case["case_id"], "keputusan_v12", {k: d[k] for k in V12_KEYS}, now_iso())
    return d, r, _fw_dump(fw)


def parse_files(paths: list[Path], source: str, window: int = 15) -> tuple[list[dict], list[dict], int]:
    """(events, kasus, n_kelompok_tanpa_temuan) persis seperti triase.triage."""
    events = [e for p in paths for e in importer.read_file(p)]
    groups = importer.to_cases(events, window_minutes=window, source=source)
    cases = [c for c in groups if not c["tanpa_temuan"] or firewall.inspect_case(c).injection]
    return events, cases, len(groups) - len(cases)


# Teks alasan dari jalur v1 yang tidak cocok dengan mode aplikasi. Teks asli mesin tetap dikirim ke UI/laporan dan
# tidak diubah di jejak audit.
ENGINE_NO_LLM = "LLM dimatikan"
REASON_RULES_LLM_ON = ("Keputusan diambil dari aturan; LLM tidak dipakai untuk kategori dan aksi "
                       "(draf AI dibuat terpisah atas permintaan analis)")
REASON_RULES_LLM_OFF = ("Keputusan diambil dari aturan; LLM lokal tidak aktif di aplikasi ini, jadi tidak dipakai "
                        "untuk kategori dan aksi")


def reason_text(raw: str, llm_on: bool) -> str:
    if raw == ENGINE_NO_LLM:
        return REASON_RULES_LLM_ON if llm_on else REASON_RULES_LLM_OFF
    return raw


# Versi pendek untuk laporan: perisai.laporan memotong tiap alasan di 120 karakter.
REPORT_RULES_LLM_ON = "Keputusan dari aturan; LLM tidak dipakai untuk kategori dan aksi"
REPORT_RULES_LLM_OFF = "Keputusan dari aturan; LLM lokal tidak aktif"


def reasons_for_report(reasons: list[str], llm_on: bool) -> list[str]:
    out = []
    for r in reasons:
        if r == ENGINE_NO_LLM:
            out.append(f'{REPORT_RULES_LLM_ON if llm_on else REPORT_RULES_LLM_OFF} (teks asli mesin: "{r}")')
        else:
            out.append(r)
    return out


def event_view(ev: dict) -> dict:
    hits = detector.rule_hits(ev)
    return {
        "id": ev.get("id"),
        "terstruktur": {f: ev[f] for f in STRUCTURED_FIELDS if f in ev},
        "teks_bebas": {f: ev[f] for f in FREE_TEXT_FIELDS if f in ev},
        "lain": {k: v for k, v in ev.items() if k not in STRUCTURED_FIELDS and k not in FREE_TEXT_FIELDS and k != "id"},
        "aturan": [{"id": r.rid, "judul": r.title, "kategori": r.category, "severity": r.severity} for r in hits],
    }


def case_meta(case: dict) -> dict:
    kategori, weights, fired = detector.classify(case["events"])
    sev = detector.max_severity(case["events"])
    times = sorted(str(e.get("TimeCreated") or e.get("@timestamp") or "") for e in case["events"]
                   if e.get("TimeCreated") or e.get("@timestamp"))
    return {"aturan_terpicu": [{"id": r, "judul": detector.RULE_BY_ID[r].title, "kategori": detector.RULE_BY_ID[r].category,
                                "severity": detector.RULE_BY_ID[r].severity} for r in fired],
            "severity": SEVERITY_NAME.get(sev, "info"), "severity_skor": sev,
            "waktu_awal": times[0] if times else None, "waktu_akhir": times[-1] if times else None,
            "n_event_terpilih": len(case["events"]), "n_event_rekaman": case.get("n_events_recording")}


def simulate(case: dict, jenis: str, target: str | None, bukti: list[str], detektor_aktif: bool = True) -> dict:
    """Uji usulan buatan analis terhadap policy. Tidak mengubah kasus dan tidak dicatat sebagai keputusan."""
    fw = firewall.inspect_case(case) if detektor_aktif else FirewallReport()
    kategori = detector.classify(case["events"])[0]
    prop = {"kategori": kategori, "ringkasan": "", "aksi": {"jenis": jenis, "target": target or None},
            "bukti": bukti, "keyakinan": 0.9}
    v1 = policy.decide(case, prop, fw)
    d = decide_v12(case, prop, fw)
    return {"usulan": prop["aksi"] | {"bukti": bukti}, "detektor_aktif": detektor_aktif,
            "putusan_usulan": v1.verdict, "alasan_usulan": v1.reasons, "peringatan_usulan": v1.warnings,
            "aksi_akhir": d["final_action"], "status_akhir": d["final_status"], "alasan_akhir": d["reasons"],
            "peringatan_akhir": d["warnings"]}


def render_report(run: dict, items: list[dict], audit: AuditLog, reviews: list[dict], llm_on: bool = False) -> str:
    items = [{"case": it["case"], "decision": {**it["decision"],
              "reasons": reasons_for_report(it["decision"]["reasons"], llm_on)}} for it in items]
    md = laporan.render(run, items, audit.verify(), audit.entries())
    if reviews:
        md += "\n## Tindakan analis (tercatat di jejak audit, tidak dieksekusi)\n\n"
        md += "| Waktu (UTC) | Kasus | Tindakan | Aksi yang diusulkan | Analis | Catatan | Audit |\n|---|---|---|---|---|---|---|\n"
        for r in reviews:
            md += (f"| {laporan._cell(r['ts'])} | {laporan._cell(r['case_id'])} | {laporan._cell(r['label'])} | "
                   f"{laporan._cell(r['aksi'])} | {laporan._cell(r['analis'])} | {laporan._cell(r['catatan'])} | "
                   f"#{r['seq']} `{r['hash'][:16]}` |\n")
    return md


# ------------------------------------------------------------------ integritas kode mesin
_CORE = ["__init__.py", "audit.py", "cases.py", "detector.py", "firewall.py", "llm.py", "logs.py", "pipeline.py",
         "policy.py", "v11.py", "v12.py"]


def _expected_hashes() -> dict[str, tuple[str, str]]:
    out: dict[str, tuple[str, str]] = {}
    for fname in ("CODE_EVAL.sha256", "CODE_V11_posthoc.sha256", "CODE_V12_posthoc.sha256"):
        p = engine_meta_dir() / fname
        if not p.exists():
            continue
        for line in p.read_text(encoding="utf-8").splitlines():
            m = re.match(r"^([0-9a-f]{64}) \*perisai/(\S+\.py)$", line.strip())
            if m:
                out[m.group(2)] = (m.group(1), fname)
    return out


def engine_integrity() -> dict:
    """Bandingkan kode mesin yang dipakai dengan hash beku di prototype/frozen."""
    exp = _expected_hashes()
    src = engine_source_dir()
    if src is not None:
        got = {f: hashlib.sha256((src / f).read_bytes()).hexdigest() for f in _CORE if (src / f).exists()}
        how = "dihitung langsung dari berkas .py mesin"
    else:
        import json
        mp = engine_meta_dir() / "build_manifest.json"
        got = json.loads(mp.read_text(encoding="utf-8")) if mp.exists() else {}
        how = "manifes saat build (kode dibundel di dalam aplikasi)"
    rows = []
    for f in _CORE:
        if f not in exp:
            continue
        want, ref = exp[f]
        rows.append({"berkas": f"perisai/{f}", "cocok": got.get(f) == want, "acuan": ref, "sha256": got.get(f)})
    return {"ok": bool(rows) and all(r["cocok"] for r in rows), "cara": how, "berkas": rows}


# ------------------------------------------------------------------ uji kinerja
def bench_rules(cases: list[dict], rounds: int = 30) -> dict:
    """Latensi firewall + detektor + policy v1.2.2 per kasus, tanpa LLM, di perangkat ini."""
    if not cases:
        return {"n": 0}
    samples = []
    for _ in range(rounds):
        for c in cases:
            t0 = time.perf_counter()
            fw = firewall.inspect_case(c)
            decide_v12(c, None, fw, "LLM dimatikan")
            samples.append((time.perf_counter() - t0) * 1000)
    samples.sort()
    return {"n": len(samples), "n_kasus": len(cases), "putaran": rounds,
            "median_ms": round(statistics.median(samples), 3),
            "p95_ms": round(samples[int(0.95 * (len(samples) - 1))], 3), "maks_ms": round(samples[-1], 3)}


__all__ = ["ACTIONS", "ACTION_LABEL", "ATTACK_TACTIC", "AuditLog", "CATEGORY_ID", "RISKY_ACTIONS", "case_meta",
           "decide_case", "engine_integrity", "event_view", "parse_files", "render_report", "simulate", "bench_rules",
           "now_iso"]
