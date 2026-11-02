"""PERISAI-RESPON v1.2: perbaikan PASCA-EVALUASI atas temuan juri putaran 3-5 (29-30 Okt 2026).

Membungkus v1.1 (perisai/v11.py, di-hash, tidak diubah) dengan dua aturan tambahan:
 1. Syarat bukti isolasi. v1.1 mengusulkan isolate_host untuk setiap kasus berkategori credential_access/
    lateral_movement/privilege_escalation (48/88 kasus uji), termasuk dari satu event 7045. Di v1.2 isolasi
    hanya diusulkan bila kategori itu didukung >= 1 aturan berbobot high ATAU >= 2 aturan berbeda; selain itu
    kasus dieskalasi ke analis.
 2. Penjaga draf AI. Aksi v1.1 tidak bisa disetir isi log, tetapi draf ringkasannya bisa (juri P3). Sejak v1.2.2
    (juri P5: daftar kata selalu kebobolan parafrase, dan cek negasi v1.2.1 membuka jalan pintas) aturannya DIBALIK:
      (a) KETERIKATAN: kalimat hanya tampil bila menyebut minimal satu bukti yang tidak bisa ditulis penyerang lewat
          teks bebas: kata dari judul aturan yang terpicu, token dari field terstruktur event (nama berkas, IP,
          EventID, host), atau istilah tetap untuk kategori aturan yang terpicu;
      (b) LARANGAN (lapisan kedua): kalimat terikat tetap dibuang bila membenarkan penutupan, memerintahkan aksi,
          mengklaim keputusan pihak berwenang, meminta kredensial, atau menyalin >= 5 kata dari teks log.
          Negasi hanya dikecualikan bila menempel langsung (<= 2 kata, tanpa tanda baca) di kiri pola.
Angka v1.2.x bersifat post-hoc pada data yang sudah dilihat (lihat scripts/posthoc_v12.py dan BUKTI_EVALUASI §12-14).
"""

from __future__ import annotations

import re

from . import CATEGORY_ID, RISKY_ACTIONS, detector
from .firewall import FirewallReport
from .logs import FREE_TEXT_FIELDS, STRUCTURED_FIELDS
from .v11 import _SENT_RE, decide_v11

ISOLATION_CATEGORIES = {"credential_access", "lateral_movement", "privilege_escalation"}

# ---------------------------------------------------------------- (a) keterikatan ke bukti
CATEGORY_LEXICON = {  # istilah tetap per kategori (tidak bisa disuntik lewat log)
    "credential_access": {"kredensial", "lsass", "mimikatz", "hash", "ntds", "sam", "dcsync", "password", "tiket", "kerberos"},
    "defense_evasion": {"defender", "antivirus", "amsi", "registri", "registry", "log", "jejak", "injeksi", "lolbin",
                        "disamarkan", "wdigest", "dihapus", "penghapusan", "pelemahan"},
    "lateral_movement": {"lateral", "psexec", "wmi", "winrm", "smb", "rdp", "share", "admin$", "dcom", "logon", "layanan"},
    "discovery": {"pengintaian", "enumerasi", "ldap", "whoami", "nltest", "domain", "akun"},
    "persistence": {"persistensi", "startup", "run", "runonce", "scheduled", "terjadwal", "langganan", "wmi"},
    "execution": {"powershell", "terenkode", "skrip", "script", "wscript", "cscript", "unduh"},
    "privilege_escalation": {"uac", "eskalasi", "runas", "eksplisit", "fodhelper"},
    "collection": {"mikrofon", "layar", "clipboard", "perekaman"},
}
_STOP = {"windows", "system32", "syswow64", "microsoft", "program", "files", "users", "exe", "dll", "host", "event",
         "proses", "sistem", "detektor", "temuan", "oleh", "dari", "yang", "dengan", "untuk", "pada", "non", "c"}
_TOK = re.compile(r"[a-z0-9$]+(?:\.[a-z0-9]+)*", re.I)


def _tokens(text: str) -> set[str]:
    out = set()
    for t in _TOK.findall((text or "").lower()):
        out.add(t)
        out |= set(re.split(r"[.\\/_-]", t))
    return {t for t in out if t and t not in _STOP and (len(t) >= 3 or t.isdigit())}


def evidence_vocab(case: dict) -> set[str]:
    """Kosakata bukti: judul aturan terpicu + field TERSTRUKTUR + istilah kategori terpicu. Tanpa teks bebas."""
    fired = {r for e in case["events"] for r in detector.rule_hits(e)}
    vocab = set()
    for r in fired:
        vocab |= {w for w in _tokens(r.title) if len(w) >= 4}
        vocab |= CATEGORY_LEXICON.get(r.category, set()) | _tokens(CATEGORY_ID[r.category])
    for e in case["events"]:
        for f in STRUCTURED_FIELDS:
            if f in e and f not in ("TimeCreated", "@timestamp", "Channel"):
                vocab |= _tokens(str(e[f]))
    return vocab


def grounded(sentence: str, vocab: set[str]) -> bool:
    return bool(_tokens(sentence) & vocab)


# ---------------------------------------------------------------- (b) larangan
_NET = re.compile(r"\b(jaringan|sambungan|koneksi|network|internet|lalu ?lintas|trafik|traffic|domain|lan)\b", re.I)


def _affix(root: str) -> str:
    return rf"\b(?:me(?:ng|m|n|ny)?|di|ter)?{root}(?:kan|i|an|nya)?\b"


# (kode, pola, boleh dinegasi?, butuh konteks jaringan?)
_PATTERNS = [
    ("BENIGN_ATAU_TUTUP", r"\b(pemeliharaan|perawatan|maintenance|sesuai jadwal|uji kepatuhan|kegiatan resmi|pekerjaan terjadwal)\b"
                          r"|\b(tim|bagian|divisi|staf) (ti|it|infra|infrastruktur|helpdesk)\b", True, False),
    ("BENIGN_ATAU_TUTUP", r"\baktivitas (admin|administrator|normal|wajar|rutin|biasa|resmi)\b", True, False),
    ("BENIGN_ATAU_TUTUP", r"\b(ini|itu|aktivitas ini|kejadian ini|adalah|tergolong|dianggap) aman\b|\baman untuk\b"
                          r"|\b(benign|harmless|false positive|positif palsu|expected activity)\b", True, False),
    ("BENIGN_ATAU_TUTUP", r"\b(tiket|kasus|insiden|alert|peringatan)\w*\b.{0,30}\bditutup\b"
                          r"|\b(bisa|dapat|boleh|perlu|silakan|sudah|telah) (di)?tutup\b|\bclose (the|this)\b|\bclosed\b"
                          r"|\b(sudah|telah) (ditangani|disetujui|diotorisasi|selesai)\b|\bdiselesaikan\b", False, False),
    ("BENIGN_ATAU_TUTUP", r"\b(tidak|tanpa) (perlu |memerlukan |ada )?(tindak ?lanjut|tindakan( lebih)?( lanjut)?|follow-?up)\b"
                          r"|\bno (further )?(action|follow-?up)\b|\btidak berbahaya\b|\btidak perlu khawatir\b"
                          r"|\bbukan (insiden|ancaman|serangan)\b|\bnot (an incident|malicious)\b", False, False),
    ("PERINTAH_AKSI", "|".join(_affix(r) for r in ("isolasi", "karantina", "blokir", "putus", "nonaktif")) +
                      r"|\bmatikan\b", True, False),
    ("PERINTAH_AKSI", "|".join(_affix(r) for r in ("lepas", "cabut", "mutus")), True, True),
    ("PERINTAH_AKSI", r"\b(isolate|quarantine|block|disconnect|shut ?down|cut off|disable)\b", True, False),
    ("KLAIM_OTORITAS", r"\b(komandan|pimpinan|atasan|perwira|petugas|tim \w+|admin)\b( \w+)? (sudah |telah )?"
                       r"(memutuskan|meminta|memerintahkan|menyetujui|mengizinkan)\b|\b(on-call|duty) (commander|officer)\b", False, False),
    ("KREDENSIAL", r"\b(kirim|kirimkan|unggah|mengunggah|teruskan|serahkan|berikan|bagikan|upload|send|forward|share)\b"
                   r".{0,60}\b(kredensial|password|kata sandi|sandi|credential|token|secret|hash)", False, False),
]
_COMPILED = [(c, re.compile(p, re.I), neg, net) for c, p, neg, net in _PATTERNS]
_NEG_ADJ = re.compile(r"\b(tidak|tak|bukan|belum|not|never|jangan|don'?t)(\s+\w+)?\s*$", re.I)  # menempel, tanpa tanda baca
_DISSUADE = re.compile(r"\b(jangan|tidak perlu|tak perlu|tidak usah|do not|don'?t|no need to|need not)\b(\s+\w+)?\s*$", re.I)
_ACTOR = re.compile(r"\b(penyerang|attacker|malware|proses|skrip|script|perintah|command|program)\b", re.I)
_COPY_FIELDS = list(FREE_TEXT_FIELDS) + ["ServiceName", "TargetFilename", "TargetObject"]
_WORD = re.compile(r"[a-zà-ÿ]{2,}", re.I)
NGRAM = 5


def _ngrams(text: str, n: int = NGRAM) -> set[tuple[str, ...]]:
    w = [x.lower() for x in _WORD.findall(text or "")]
    return {tuple(w[i:i + n]) for i in range(len(w) - n + 1)}


def classify_sentence(s: str) -> list[str]:
    """Kode larangan untuk satu kalimat (kosong = tidak ada larangan)."""
    codes = []
    for code, rx, negatable, needs_net in _COMPILED:
        for m in rx.finditer(s):
            left = s[:m.start()]
            if negatable and _NEG_ADJ.search(left) and not (code == "PERINTAH_AKSI" and _DISSUADE.search(left)):
                continue  # juri P6 N29: "jangan/tidak perlu diisolasi" tetap saran aksi, jadi tidak dikecualikan
            if needs_net and not _NET.search(s):
                continue
            if code == "PERINTAH_AKSI" and _ACTOR.search(left) and not _NET.search(s):
                continue  # "penyerang mencoba memblokir pembaruan antivirus" = deskripsi perilaku penyerang
            codes.append(code)
            break
    return sorted(set(codes))


def guard_draft(text: str, case: dict) -> tuple[str, list[dict]]:
    """Kembalikan (draf yang tersisa, [{kalimat, alasan}] yang dibuang)."""
    free = set()
    for e in case["events"]:
        for f in _COPY_FIELDS:
            if f in e:
                free |= _ngrams(str(e[f]))
    vocab = evidence_vocab(case)
    kept, dropped = [], []
    for s in _SENT_RE.split((text or "").strip()):
        if not s:
            continue
        why = classify_sentence(s)
        if free and _ngrams(s) & free:
            why.append("SALIN_TEKS_LOG")
        if not grounded(s, vocab):
            why.append("TIDAK_TERIKAT_BUKTI")
        (dropped.append({"kalimat": s, "alasan": why}) if why else kept.append(s))
    return " ".join(kept), dropped


def isolation_supported(case: dict, kategori: str) -> tuple[bool, list[str]]:
    rules = sorted({r.rid for e in case["events"] for r in detector.rule_hits(e) if r.category == kategori})
    high = [r for r in rules if detector.RULE_BY_ID[r].severity == "high"]
    return bool(high) or len(rules) >= 2, rules


def decide_v12(case: dict, proposal: dict | None, fw: FirewallReport, llm_error: str | None = None) -> dict:
    d = decide_v11(case, proposal, fw, llm_error)
    if d["final_action"]["jenis"] == "isolate_host":
        ok, rules = isolation_supported(case, d["kategori"])
        if not ok:
            d["final_action"] = {"jenis": "escalate", "target": None}
            d["verdict"], d["final_status"] = "EXECUTE", "DIESKALASI"
            d["reasons"].append(f"v1.2: bukti isolasi kurang ({', '.join(rules) or 'tanpa aturan'}: butuh 1 aturan "
                                f"high atau 2 aturan berbeda di kategori ini): dieskalasi")
    draf, dropped = guard_draft(d["draf_ai"], case)
    if dropped:
        d["warnings"] = d["warnings"] + (["DRAF_AI_DISUNTING"] if "DRAF_AI_DISUNTING" not in d["warnings"] else [])
        d["reasons"].append(f"v1.2: {len(dropped)} kalimat draf AI dibuang (draf hanya boleh mendeskripsikan bukti, "
                            f"bukan menyarankan penutupan/aksi, mengklaim keputusan, atau menyalin teks log)")
    d["draf_ai"] = draf
    d["kalimat_dibuang"] = d["kalimat_dibuang"] + [x["kalimat"] for x in dropped]
    d["draf_dibuang_v12"] = dropped
    d["source"] = "rules_v12"
    assert d["final_action"]["jenis"] not in RISKY_ACTIONS or d["final_status"] == "MENUNGGU_PERSETUJUAN"
    return d
