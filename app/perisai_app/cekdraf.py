"""Cek silang draf AI terhadap temuan aturan (lapisan aplikasi, deterministik, tanpa LLM).

Masalah yang ditutup: LLM lokal kadang menamai kategori serangan yang lain dari kategori aturan (contoh nyata:
kasus berkategori aturan Execution, draf menulis "Pencurian kredensial ..."). Kategori dan aksi sudah diambil
dari aturan, tetapi analis yang membaca draf bisa terkecoh. Modul ini mencari NAMA taktik ATT&CK atau kategori
PERISAI di draf (istilah Indonesia, Inggris, kunci mesin, atau ID TA00xx) dan membandingkannya dengan kategori
yang didukung aturan yang terpicu di kasus itu.

Hasil per draf:
  BERTENTANGAN    draf menyebut minimal satu kategori yang tidak didukung satu pun aturan yang terpicu;
  SESUAI          semua kategori yang disebut didukung aturan;
  TANPA_KATEGORI  draf tidak menyebut nama kategori/taktik (tidak ada yang dibandingkan).

Sengaja konservatif: yang dicari hanya frasa NAMA kategori ("pencurian kredensial", "lateral movement"), bukan
kata teknik ("PowerShell", "LSASS"). Sebutan yang dinegasi ("tidak ada tanda pergerakan lateral") atau bersifat
pencegahan ("untuk mencegah eksfiltrasi") tidak dihitung. Kata "eskalasi" saja tidak dihitung karena di aplikasi
ini berarti eskalasi ke analis. Modul ini tidak mengubah keputusan mesin; kategori aturan tetap yang berlaku.
"""

from __future__ import annotations

import re

from .engine import ATTACK_TACTIC  # memastikan perisai bisa diimpor

from perisai import CATEGORY_ID, detector  # noqa: E402

LABEL = {"BERTENTANGAN": "Bertentangan dengan temuan aturan", "SESUAI": "Sesuai temuan aturan",
         "TANPA_KATEGORI": "Tidak menyebut kategori"}

# Taktik ATT&CK di luar 8 kategori PERISAI. Aturan PERISAI tidak pernah menghasilkan kategori ini, jadi bila draf
# menamainya, klaim itu tidak didukung aturan.
EXTRA_TACTIC = {
    "exfiltration": ("TA0010", "Exfiltration", "eksfiltrasi data"),
    "command_and_control": ("TA0011", "Command and Control", "komando dan kendali"),
    "initial_access": ("TA0001", "Initial Access", "akses awal"),
    "impact": ("TA0040", "Impact", "dampak"),
}

# Frasa nama kategori. Huruf kecil; spasi di sini cocok dengan spasi/tanda hubung/garis bawah di draf.
TERMS: dict[str, tuple[str, ...]] = {
    "credential_access": ("credential access", "credential dumping", "credential theft", "credential stealing",
                          "pencurian kredensial", "akses kredensial", "pencurian kata sandi", "pencurian sandi",
                          "pencurian password", "pengambilan kredensial", "pembongkaran kredensial",
                          "dumping kredensial", "ta0006"),
    "lateral_movement": ("lateral movement", "pergerakan lateral", "gerakan lateral", "perpindahan lateral",
                         "penyebaran lateral", "bergerak lateral", "bergerak secara lateral", "ta0008"),
    "defense_evasion": ("defense evasion", "defence evasion", "penghindaran pertahanan", "menghindari pertahanan",
                        "pelemahan pertahanan", "ta0005"),
    "discovery": ("discovery", "pengintaian internal", "pengintaian", "ta0007"),
    "persistence": ("persistence", "persistensi", "ta0003"),
    "execution": ("eksekusi kode", "code execution", "execution tactic", "taktik eksekusi", "ta0002"),
    "privilege_escalation": ("privilege escalation", "eskalasi hak akses", "eskalasi hak istimewa",
                             "eskalasi privilese", "eskalasi privilege", "peningkatan hak akses",
                             "peningkatan hak istimewa", "ta0004"),
    "collection": ("pengumpulan data", "data collection", "ta0009"),
    "exfiltration": ("exfiltration", "eksfiltrasi", "mengeksfiltrasi", "ta0010"),
    "command_and_control": ("command and control", "komando dan kendali", "server c2", "c2 server", "ta0011"),
    "initial_access": ("initial access", "akses awal", "ta0001"),
    "impact": ("ta0040",),
}
# Kunci mesin dua kata (credential_access, ...) ikut cocok karena spasi di frasa cocok dengan garis bawah.
# Kata Inggris tunggal yang umum ("execution", "collection", "impact") sengaja tidak dihitung.


def _rx(term: str) -> str:
    return r"[\s_-]+".join(re.escape(w) for w in term.split())


_TERM_RX = [(cat, term, re.compile(rf"(?<![a-z0-9]){_rx(term)}(?![a-z0-9])", re.I))
            for cat, terms in TERMS.items() for term in sorted(terms, key=len, reverse=True)]

# Negasi/pencegahan di kiri (<= 4 kata dalam klausa yang sama) atau penyangkalan tepat di kanan.
# "non" sengaja tidak masuk: "proses non-sistem" adalah frasa judul aturan, bukan negasi.
_NEG_LEFT = re.compile(r"\b(tidak|tak|bukan|belum|tanpa|not|no|never|mencegah|cegah|pencegahan|menghindari "
                       r"terjadinya|menutup kemungkinan|nihil)\b", re.I)
_NEG_RIGHT = re.compile(r"^\W{0,3}(\w+\s+){0,1}(tidak|tak|belum|bukan)\s+(terdeteksi|ditemukan|terlihat|teramati|ada|"
                        r"terjadi|terbukti|didukung)\b|^\W{0,3}(not|never)\s+(detected|observed|found|seen)\b", re.I)
_CLAUSE = re.compile(r"[.,;:!?()]|\b(tetapi|namun|melainkan|sedangkan|but|however)\b", re.I)


def _negated(text: str, start: int, end: int) -> bool:
    left = text[:start]
    cuts = list(_CLAUSE.finditer(left))
    if cuts:
        left = left[cuts[-1].end():]
    words = left.split()[-4:]
    if _NEG_LEFT.search(" ".join(words)):
        return True
    return bool(_NEG_RIGHT.search(text[end:end + 60]))


def tactic(cat: str) -> tuple[str, str, str]:
    """(ID ATT&CK, nama taktik, nama Indonesia) untuk kategori PERISAI atau taktik tambahan."""
    if cat in ATTACK_TACTIC:
        return ATTACK_TACTIC[cat][0], ATTACK_TACTIC[cat][1], CATEGORY_ID.get(cat, cat)
    return EXTRA_TACTIC.get(cat, ("-", cat, cat))


def find_mentions(text: str) -> tuple[list[dict], list[dict]]:
    """(sebutan kategori yang dihitung, sebutan yang diabaikan karena negasi). Satu rentang teks = satu sebutan."""
    taken: list[tuple[int, int]] = []
    found, ignored = [], []
    for cat, term, rx in _TERM_RX:
        for m in rx.finditer(text or ""):
            if any(m.start() < b and a < m.end() for a, b in taken):
                continue
            taken.append((m.start(), m.end()))
            rec = {"kategori": cat, "istilah": m.group(0), "posisi": m.start()}
            (ignored if _negated(text, m.start(), m.end()) else found).append(rec)
    return sorted(found, key=lambda r: r["posisi"]), sorted(ignored, key=lambda r: r["posisi"])


def _fmt(cat: str) -> str:
    tid, name, idn = tactic(cat)
    return f"{tid} {name} ({idn})"


def check_text(draft: str, kategori: str, supported: set[str] | list[str], fired: list[str] | None = None) -> dict:
    """Bandingkan draf dengan kategori aturan. `supported` = kategori dari semua aturan yang terpicu."""
    allowed = set(supported) | {kategori}
    found, ignored = find_mentions(draft or "")
    named = list(dict.fromkeys(r["kategori"] for r in found))
    bad = [c for c in named if c not in allowed]
    status = "BERTENTANGAN" if bad else ("SESUAI" if named else "TANPA_KATEGORI")
    rules = ", ".join(fired or []) or "tanpa aturan, kategori bawaan"
    if bad:
        terms = ", ".join(f'"{next(r["istilah"] for r in found if r["kategori"] == c)}" ({_fmt(c)})' for c in bad)
        reason = (f"Draf AI menyebut {terms}, tetapi aturan yang terpicu ({rules}) menetapkan kategori {_fmt(kategori)}"
                  + (f" dan hanya mendukung {', '.join(_fmt(c) for c in sorted(allowed - {kategori}))}"
                     if allowed - {kategori} else "")
                  + ". Kategori dan aksi tetap dari aturan; draf hanya bacaan pendamping.")
    elif named:
        reason = f"Kategori yang disebut draf didukung aturan yang terpicu ({rules})."
    else:
        reason = "Draf tidak menyebut nama kategori atau taktik ATT&CK; tidak ada yang dibandingkan."
    return {"status": status, "label": LABEL[status], "kategori_aturan": kategori,
            "attack_aturan": {"id": tactic(kategori)[0], "nama": tactic(kategori)[1]},
            "kategori_didukung": sorted(allowed), "aturan_terpicu": list(fired or []),
            "disebut": [{"kategori": r["kategori"], "istilah": r["istilah"]} for r in found],
            "bertentangan": [{"kategori": c, "attack": tactic(c)[0], "nama": tactic(c)[1]} for c in bad],
            "diabaikan_negasi": [{"kategori": r["kategori"], "istilah": r["istilah"]} for r in ignored],
            "alasan": reason, "metode": "cekdraf v1 (frasa nama kategori, deterministik)"}


def supported_categories(case: dict) -> tuple[set[str], list[str]]:
    fired = sorted({r.rid for e in case["events"] for r in detector.rule_hits(e)})
    return {detector.RULE_BY_ID[r].category for r in fired}, fired


def check_case(draft: str, case: dict, kategori: str) -> dict:
    sup, fired = supported_categories(case)
    return check_text(draft, kategori, sup, fired)


def audit_payload(res: dict) -> dict:
    """Isi entri audit 'cek_silang_draf' (tanpa teks draf; teks draf sudah ada di entri keputusan_v12)."""
    return {"status": res["status"], "label": res["label"], "kategori_aturan": res["kategori_aturan"],
            "kategori_didukung": res["kategori_didukung"], "disebut": res["disebut"],
            "bertentangan": [b["kategori"] for b in res["bertentangan"]], "diabaikan_negasi": res["diabaikan_negasi"],
            "alasan": res["alasan"], "keputusan_berubah": False, "metode": res["metode"]}


__all__ = ["LABEL", "TERMS", "audit_payload", "check_case", "check_text", "find_mentions", "supported_categories",
           "tactic"]
