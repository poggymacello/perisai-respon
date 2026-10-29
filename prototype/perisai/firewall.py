"""Firewall masukan: sanitasi + deteksi instruksi yang diselipkan di isi log (deterministik, tanpa LLM).

Diadaptasi dari Kendali `kendali/security.py` (MIT, (c) 2026 Kendali team: Poggy Macello Gultom &
Mohammad Ari Alexander Aziz): daftar pola injeksi EN/ID, klaim persetujuan, karakter tersembunyi, homoglyph.
Ditambah untuk konteks SOC: dekode base64/URL/\\uXXXX sebelum dipindai, kosakata aksi agen di dalam log,
permintaan menutup/menandai aman, permintaan mengirim kredensial.

Pola ini ditulis SEBELUM template injeksi keluarga uji dibuat (lihat PRAREG.md). Pola bisa diparafrasekan;
keamanan aksi TIDAK bergantung padanya (policy engine menegakkan allowlist, bukti, dan persetujuan manusia).
"""

from __future__ import annotations

import base64
import binascii
import re
import unicodedata
import urllib.parse
from dataclasses import dataclass, field

from .logs import FREE_TEXT_FIELDS

# ---------------------------------------------------------------- ported from Kendali security.py
INJECTION_PATTERNS = [
    r"ignore\s+(all\s+|any\s+)?(previous|prior|above|earlier)\s+(instructions|rules|policies|prompts?)",
    r"(disregard|override|bypass|skip)\s+(the\s+|all\s+|your\s+)?(policy|policies|limits?|rules|guardrails?|checks?|approval)",
    r"\b(system|assistant|developer)\s*(prompt)?\s*:",
    r"<\s*/?\s*(system|instructions?|prompt)\s*>",
    r"you\s+are\s+(now\s+)?(an?\s+|the\s+)?(ai|assistant|agent|bot)",
    r"(dear|attention|note\s+to(\s+the)?)\s+(ai|assistant|agent|bot|llm)",
    r"do\s+not\s+(tell|inform|notify|alert)\s+(the\s+)?(owner|human|user|analyst|operator|soc|admin)",
    r"new\s+instructions?\s*:",
    r"abaikan\s+(semua\s+)?(instruksi|aturan|perintah|kebijakan)",
    r"kamu\s+(sekarang\s+)?adalah\s+(ai|asisten|agen)",
    r"jangan\s+(beritahu|kasih\s+tahu|laporkan)\s+(ke\s+)?(pemilik|owner|atasan|analis|operator)",
]
APPROVAL_CLAIM_PATTERNS = [
    r"\b(to|for|attention|attn|dear|hello|hi|note\s+to)\s*:?\s+(the\s+|any\s+|an?\s+|our\s+|your\s+)?"
    r"(automated|automatic|auto|ai)\b[\w\s/-]{0,40}\b(tool|system|agent|bot|assistant|processor|software|pipeline|workflow|reader|analyst)",
    r"\b(tool|system|agent|bot|software|ai|model|program|assistant)\s+(that\s+is\s+)?(reading|processing|parsing|handling|reviewing)\s+this\b",
    r"\b(if|when)\s+you\s+are\s+(an?\s+)?(automated|ai|bot|machine|program|language\s+model)",
    r"\b(pre|already)[\s-]?(cleared|approved|authori[sz]ed|signed[\s-]?off|okayed)\b",
    r"\bno\s+(further\s+|additional\s+|extra\s+|other\s+)?(sign[\s-]?off|approval|review|check|verification|confirmation)s?"
    r"\s+(is\s+|are\s+)?(needed|required|necessary)",
    r"\b(no\s+need|not\s+necessary|unnecessary|don'?t\s+need)\s+to\s+(check|verify|review|approve|confirm|escalate|wait)",
    r"\b(sudah|udah|dah|telah)\s+(di\s*)?(acc|disetujui|approve|diapprove|approved|diotorisasi)\b",
    r"\b(gausah|ga\s*usah|gak\s*usah|nggak\s*usah|tidak\s+usah|tidak\s+perlu|tak\s+perlu|ga\s*perlu|gak\s*perlu)\b.{0,30}"
    r"\b(cek|dicek|periksa|diperiksa|tunggu|approval|persetujuan|konfirmasi|verifikasi|eskalasi|dieskalasi|lapor)",
    r"\b(buat|kepada|untuk|halo|hai|yth\.?)\s+(sistem|bot|robot|ai|mesin|asisten)(nya)?\b",
]
# ---------------------------------------------------------------- SOC-specific additions (PERISAI)
SOC_DIRECTIVE_PATTERNS = [
    # the agent's own tool / schema vocabulary never occurs in genuine Windows telemetry
    r"\b(isolate_host|block_ip|no_action)\b",
    r"\"\s*(aksi|jenis|kategori|ringkasan|keyakinan)\s*\"\s*:",
    # requests to close / whitelist / mark safe
    r"\b(mark|classify|label|treat|report)\s+(this|it|the\s+(alert|event|incident))?\s*(as\s+)?(benign|safe|false[\s-]?positive|harmless|no\s+incident)",
    r"\b(tandai|klasifikasikan|anggap|laporkan)\s+(ini\s+|kejadian\s+ini\s+|event\s+ini\s+)?(sebagai\s+)?(aman|bukan\s+insiden|positif\s+palsu|false\s+positive|normal)",
    r"\b(close|dismiss|suppress|whitelist|allowlist)\s+(this|the)\s+(alert|incident|case|event)",
    r"\b(tutup|abaikan)\s+(kasus|insiden|alert|peringatan)\s+ini",
    # requests to act addressed to the reader
    r"\b(you\s+must|you\s+should|please|immediately)\s+(isolate|quarantine|block|disconnect|shut\s*down)\b",
    r"\b(segera|harap|wajib|tolong)\s+(isolasi|karantina|blokir|putus(kan)?|matikan)\b",
    # credential exfiltration requests
    r"\b(send|forward|upload|post|email|exfiltrate)\s+(the\s+|all\s+|any\s+)?(credentials?|passwords?|hash(es)?|tokens?|secrets?|keys?)\b",
    r"\b(kirim(kan)?|teruskan|unggah)\s+(semua\s+)?(kredensial|password|kata\s+sandi|hash|token|rahasia)",
]

HIDDEN_CHARS = {
    "​": "ZERO WIDTH SPACE", "‌": "ZERO WIDTH NON-JOINER", "‍": "ZERO WIDTH JOINER",
    "⁠": "WORD JOINER", "﻿": "ZERO WIDTH NO-BREAK SPACE", "­": "SOFT HYPHEN",
    "‪": "LRE", "‫": "RLE", "‬": "PDF", "‭": "LRO", "‮": "RLO",
    "⁦": "LRI", "⁧": "RLI", "⁨": "FSI", "⁩": "PDI",
}
CONFUSABLES = {
    "а": "a", "е": "e", "о": "o", "р": "p", "с": "c", "у": "y", "х": "x", "і": "i", "ј": "j",
    "ѕ": "s", "к": "k", "м": "m", "т": "t", "н": "h", "в": "b",
    "А": "A", "В": "B", "Е": "E", "К": "K", "М": "M", "Н": "H", "О": "O", "Р": "P", "С": "C",
    "Т": "T", "Х": "X", "У": "Y", "І": "I",
    "ο": "o", "α": "a", "ν": "v", "ρ": "p", "τ": "t", "Ο": "O", "Α": "A", "Β": "B", "Ε": "E",
    "Ζ": "Z", "Η": "H", "Ι": "I", "Κ": "K", "Μ": "M", "Ν": "N", "Ρ": "P", "Τ": "T", "Χ": "X",
}
_B64_RE = re.compile(r"[A-Za-z0-9+/]{24,}={0,2}")
_UESC_RE = re.compile(r"\\u([0-9a-fA-F]{4})")
_PCT_RE = re.compile(r"(%[0-9a-fA-F]{2}){3,}")
_SPOTLIGHT_BREAK = re.compile(r"[«»]")

_COMPILED = [("PROMPT_INJECTION", re.compile(p, re.I)) for p in INJECTION_PATTERNS] + \
            [("APPROVAL_OR_READER_CLAIM", re.compile(p, re.I)) for p in APPROVAL_CLAIM_PATTERNS] + \
            [("SOC_DIRECTIVE", re.compile(p, re.I)) for p in SOC_DIRECTIVE_PATTERNS]


@dataclass
class FieldReport:
    event_id: str
    field: str
    codes: list[str] = field(default_factory=list)
    snippet: str = ""


@dataclass
class FirewallReport:
    flagged: list[FieldReport] = field(default_factory=list)
    obfuscation: list[str] = field(default_factory=list)  # informative only (not a block reason by itself)

    @property
    def injection(self) -> bool:
        return bool(self.flagged)

    def codes(self) -> list[str]:
        return sorted({c for f in self.flagged for c in f.codes})


def strip_hidden(text: str) -> tuple[str, list[str]]:
    found = sorted({name for ch, name in HIDDEN_CHARS.items() if ch in text})
    return "".join(ch for ch in text if ch not in HIDDEN_CHARS), found


def fold_confusables(text: str) -> tuple[str, bool]:
    changed, out = False, []
    for ch in unicodedata.normalize("NFKC", text):
        if ch in CONFUSABLES:
            out.append(CONFUSABLES[ch])
            changed = True
        else:
            out.append(ch)
    return "".join(out), changed


def _printable_ratio(s: str) -> float:
    if not s:
        return 0.0
    return sum(1 for ch in s if ch.isprintable() or ch in "\r\n\t") / len(s)


def decoded_views(text: str, max_blobs: int = 20) -> list[str]:
    """Best-effort decodings of encoded segments (base64 utf-8/utf-16le, %xx, \\uXXXX) for SCANNING only."""
    views = []
    for m in list(_B64_RE.finditer(text))[:max_blobs]:
        blob = m.group(0)
        pad = blob + "=" * (-len(blob) % 4)
        try:
            raw = base64.b64decode(pad, validate=False)
        except (binascii.Error, ValueError):
            continue
        for enc in ("utf-8", "utf-16-le"):
            try:
                s = raw.decode(enc)
            except UnicodeDecodeError:
                continue
            if len(s) >= 8 and _printable_ratio(s) > 0.9:
                views.append(s)
                break
    if _PCT_RE.search(text):
        views.append(urllib.parse.unquote(text))
    if _UESC_RE.search(text):
        views.append(_UESC_RE.sub(lambda mm: chr(int(mm.group(1), 16)), text))
    return views


def normalise_for_scan(text: str) -> tuple[str, list[str]]:
    notes = []
    t, hidden = strip_hidden(text)
    if hidden:
        notes.append("HIDDEN_CHARACTERS")
    t, conf = fold_confusables(t)
    if conf:
        notes.append("HOMOGLYPH")
    t = re.sub(r"\s+", " ", t)
    return t, notes


def scan_text(text: str) -> tuple[list[str], str, list[str]]:
    """Return (codes, snippet, obfuscation_notes) for one untrusted string."""
    base, notes = normalise_for_scan(text)
    candidates = [base] + [normalise_for_scan(v)[0] for v in decoded_views(base)]
    codes, snippet = [], ""
    for i, cand in enumerate(candidates):
        for code, rx in _COMPILED:
            m = rx.search(cand)
            if m:
                c = code if i == 0 else code + "_ENCODED"
                if c not in codes:
                    codes.append(c)
                if not snippet:
                    snippet = cand[max(0, m.start() - 30): m.end() + 50]
    if codes and notes:
        codes += [n for n in notes if n not in codes]
    return codes, snippet, notes


def inspect_case(case: dict) -> FirewallReport:
    rep = FirewallReport()
    for ev in case["events"]:
        for f in FREE_TEXT_FIELDS:
            if f not in ev:
                continue
            codes, snip, notes = scan_text(str(ev[f]))
            if codes:
                rep.flagged.append(FieldReport(ev["id"], f, codes, snip))
            elif notes:
                rep.obfuscation.append(f"{ev['id']}.{f}:" + ",".join(notes))
    # context stitching: a directive split across events/fields is caught on the concatenation
    if not rep.flagged:
        joined = " ".join(str(ev[f]) for ev in case["events"] for f in FREE_TEXT_FIELDS if f in ev)
        codes, snip, _ = scan_text(joined)
        if codes:
            rep.flagged.append(FieldReport("*", "*gabungan*", [c + "_STITCHED" for c in codes], snip))
    return rep


def sanitised_value(value: str) -> str:
    """What the guarded LLM sees for an un-flagged free-text value."""
    t, _ = strip_hidden(str(value))
    t, _ = fold_confusables(t)
    t = _SPOTLIGHT_BREAK.sub("", t)
    return "«DATA»" + t + "«/DATA»"


def guarded_view(case: dict, report: FirewallReport) -> list[dict]:
    """Case events as shown to the guarded LLM: free text spotlighted, flagged fields redacted."""
    flagged = {(f.event_id, f.field): f for f in report.flagged}
    stitched = any(f.event_id == "*" for f in report.flagged)
    out = []
    for ev in case["events"]:
        e2 = dict(ev)
        for f in FREE_TEXT_FIELDS:
            if f not in ev:
                continue
            fr = flagged.get((ev["id"], f))
            if fr is not None:
                e2[f] = f"[DIHAPUS PERISAI: teks instruksi terdeteksi ({','.join(fr.codes)})]"
            elif stitched:
                e2[f] = "[DIHAPUS PERISAI: bagian dari instruksi terpecah]"
            else:
                e2[f] = sanitised_value(ev[f])
        out.append(e2)
    return out
