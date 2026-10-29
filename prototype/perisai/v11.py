"""PERISAI-RESPON v1.1: perubahan PASCA-EVALUASI (dibuat 29 Okt 2026 sesudah hasil P1/P2 dilihat).

Kode v1 (policy.py, firewall.py, detector.py) TIDAK diubah karena di-hash di frozen/. Modul ini membungkus
policy.decide dengan tiga perubahan yang dipicu hasil uji (lihat 05_BUKTI.md):
 1. Kategori dan aksi diambil dari template aturan, karena P2 gagal: LLM 35 % vs aturan 50 %.
    LLM hanya menulis DRAF ringkasan.
 2. no_action tidak pernah menutup kasus otomatis. Penutupan butuh persetujuan manusia
    (v1 menutup 3/88 rekaman serangan).
 3. Draf ringkasan LLM disaring per kalimat. Kalimat yang memuat istilah eskalatif yang tidak ada
    di log dibuang (contoh nyata: "potensi terorisme").
Belum divalidasi di data baru, jadi angka v1.1 bersifat post-hoc.
"""

from __future__ import annotations

import re

from . import PLAYBOOK, RISKY_ACTIONS, detector
from .firewall import FirewallReport
from .logs import STRUCTURED_FIELDS
from .policy import Decision, decide, filter_summary, is_protected_host, template_summary

# Istilah yang menuduh/membesar-besarkan. Kalimat yang memuatnya dibuang kecuali istilahnya ada di teks log.
UNSUPPORTED_TERMS = [
    "teroris", "terorisme", "spionase", "mata-mata", "negara asing", "intelijen asing", "sabotase", "makar",
    "pengkhianat", "apt", "state-sponsored", "disponsori negara", "ransomware", "perang siber", "serangan nasional",
    "kebocoran rahasia negara", "pasti", "dipastikan", "terbukti",
]
_SENT_RE = re.compile(r"(?<=[.!?])\s+")


def _case_text(case: dict) -> str:
    # Hanya field TERSTRUKTUR: teks bebas (CommandLine, dll.) bisa ditulis penyerang untuk "membenarkan" klaim.
    return " ".join(str(e[f]) for e in case["events"] for f in STRUCTURED_FIELDS if f in e).lower()


def _has_word(term: str, text: str) -> bool:
    return re.search(rf"\b{re.escape(term)}\b", text) is not None


def filter_sentences(text: str, case: dict) -> tuple[str, list[str]]:
    """Buang kalimat yang memuat istilah di UNSUPPORTED_TERMS yang tidak muncul di log kasus."""
    log = _case_text(case)
    kept, dropped = [], []
    for s in _SENT_RE.split((text or "").strip()):
        if not s:
            continue
        low = s.lower()
        bad = [t for t in UNSUPPORTED_TERMS if _has_word(t, low) and not _has_word(t, log)]
        (dropped if bad else kept).append(s)
    return " ".join(kept), dropped


def decide_v11(case: dict, proposal: dict | None, fw: FirewallReport, llm_error: str | None = None) -> dict:
    """Keputusan v1.1. Mengembalikan dict Decision + 'draf_ai' dan 'kalimat_dibuang'."""
    v1 = decide(case, proposal, fw, llm_error)  # firewall/allowlist/bukti tetap dijalankan untuk alasan & peringatan
    kategori, _, fired = detector.classify(case["events"])
    jenis = PLAYBOOK[kategori]
    target = case.get("primary_host") or None
    reasons = [f"v1.1: kategori dan aksi dari template aturan ({', '.join(fired) or 'tanpa aturan, bawaan'})"]
    warnings = [w for w in v1.warnings if w != "MODE_DEGRADASI"]
    if fw.injection:
        if "INJEKSI_TERDETEKSI" not in warnings:
            warnings.append("INJEKSI_TERDETEKSI")
        reasons.append("instruksi terdeteksi di isi log: aksi berisiko tidak diusulkan, kasus dieskalasi")
        jenis, target = "escalate", None
    if jenis == "isolate_host" and (not target or is_protected_host(target)):
        jenis, target = "escalate", None
        reasons.append("host kosong/terlindungi: dieskalasi")
    if jenis in RISKY_ACTIONS:
        verdict, status = "REQUEST_APPROVAL", "MENUNGGU_PERSETUJUAN"
    else:
        verdict, status, target = "EXECUTE", "DIESKALASI", None
    # usulan LLM untuk menutup kasus tidak pernah dijalankan otomatis
    if proposal and ((proposal.get("aksi") or {}).get("jenis") == "no_action"):
        reasons.append("LLM mengusulkan menutup kasus: tidak dijalankan, keputusan pada analis")

    draf, dropped = "", []
    if proposal:
        draf, _ = filter_summary(proposal.get("ringkasan", ""), case)
        draf, dropped = filter_sentences(draf, case)
        if dropped:
            warnings.append("DRAF_AI_DISUNTING")
            reasons.append(f"{len(dropped)} kalimat draf AI memuat klaim yang tidak didukung log: dibuang")
    d = Decision(verdict, {"jenis": jenis, "target": target}, kategori, template_summary(case, kategori, fired),
                 "rules_v11", proposal, v1.reasons + reasons, warnings, status).to_dict()
    d["draf_ai"] = draf
    d["kalimat_dibuang"] = dropped
    d["v1_verdict"] = v1.verdict
    return d
