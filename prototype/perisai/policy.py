"""Policy engine: LLM mengusulkan, kebijakan memutuskan.

Pola keputusan BLOCK / REQUEST_APPROVAL / EXECUTE diadaptasi dari Kendali `kendali/policy.py`
(MIT, (c) 2026 Kendali team: Poggy Macello Gultom & Mohammad Ari Alexander Aziz).

Aturan (berlaku sama dengan atau tanpa LLM):
 1. Allowlist aksi tertutup: isolate_host, block_ip, escalate, no_action. Selain itu -> BLOCK.
 2. Bila firewall menemukan instruksi di isi log -> aksi berisiko dan no_action ditolak; kasus dieskalasi
    ke manusia dengan peringatan INJEKSI_TERDETEKSI.
 3. Aturan bukti: aksi berisiko wajib menunjuk event yang ada, event itu harus memicu aturan detektor, dan
    target (host/IP) harus muncul di field TERSTRUKTUR event itu (bukan di teks bebas).
 4. Aset terlindungi (DC, SIEM, gateway, DNS) tidak pernah diisolasi/diblokir otomatis.
 5. Aksi berisiko yang lolos tetap butuh persetujuan manusia (REQUEST_APPROVAL), tidak dieksekusi otomatis.
 6. no_action hanya boleh bila detektor tidak menemukan indikasi berbobot >= medium.
 7. Ringkasan untuk operator disaring: URL, e-mail, IP, dan host yang tidak ada di field terstruktur dihapus.
 8. LLM mati / keluaran tidak valid -> mode degradasi: kategori dan aksi dari template aturan.
"""

from __future__ import annotations

import ipaddress
import re
from dataclasses import asdict, dataclass, field

from . import ACTIONS, CATEGORIES, CATEGORY_ID, PLAYBOOK, RISKY_ACTIONS, detector
from .firewall import FirewallReport
from .logs import HOST_FIELDS, IP_FIELDS, STRUCTURED_FIELDS

PROTECTED_HOSTS = {"dc01", "dc02", "siem01", "gw01", "dns01", "kodam-dc01", "srv-siem01"}
PROTECTED_IPS = {"10.10.0.1", "10.10.0.10", "10.10.0.53", "10.10.0.100", "192.168.1.1"}

_URL_RE = re.compile(r"(https?://|hxxps?://|ftp://)[^\s\"'<>]+|\bwww\.[^\s\"'<>]+", re.I)
_EMAIL_RE = re.compile(r"\b[\w.+-]+@[\w-]+(\.[\w-]+)+\b")
_IP_RE = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
_DOMAIN_RE = re.compile(r"\b[a-z0-9-]+(\.[a-z0-9-]+)*\.(com|net|org|io|xyz|top|ru|cn|id|co\.id|info|biz|site|online)\b", re.I)


@dataclass
class Decision:
    verdict: str                 # EXECUTE | REQUEST_APPROVAL | BLOCK (of the proposal; final action always safe)
    final_action: dict           # {"jenis":..., "target":...}
    kategori: str
    ringkasan: str
    source: str                  # llm | rules_degraded
    proposal: dict | None
    reasons: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    final_status: str = ""       # DIEKSEKUSI | MENUNGGU_PERSETUJUAN | DIESKALASI | DITUTUP

    def to_dict(self) -> dict:
        return asdict(self)


def _short(h: str) -> str:
    return h.lower().split(".")[0].strip()


def _host_match(a: str, b: str) -> bool:
    return bool(a) and bool(b) and (a.lower().strip() == b.lower().strip() or _short(a) == _short(b))


def is_protected_host(h: str | None) -> bool:
    return bool(h) and (_short(h) in PROTECTED_HOSTS or h.lower().strip() in PROTECTED_HOSTS)


def is_protected_ip(ip: str | None) -> bool:
    return bool(ip) and ip.strip() in PROTECTED_IPS


def trusted_values(case: dict) -> set[str]:
    vals = set()
    for ev in case["events"]:
        for f in STRUCTURED_FIELDS:
            if f in ev and f not in ("EventID", "TimeCreated", "@timestamp"):
                vals.add(str(ev[f]).lower())
    return vals


def filter_summary(text: str, case: dict) -> tuple[str, list[str]]:
    trusted = " ".join(trusted_values(case))
    removed = []

    def _sub(m: re.Match) -> str:
        s = m.group(0)
        if s.lower() in trusted:
            return s
        removed.append(s)
        return "[disunting]"

    out = _URL_RE.sub(_sub, text)
    out = _EMAIL_RE.sub(_sub, out)
    out = _IP_RE.sub(_sub, out)
    out = _DOMAIN_RE.sub(_sub, out)
    return out[:700], removed


def template_summary(case: dict, kategori: str, fired: list[str]) -> str:
    titles = [detector.RULE_BY_ID[r].title for r in fired][:4]
    host = case.get("primary_host") or "host tidak diketahui"
    if not titles:
        return (f"Tidak ada aturan detektor yang terpicu pada {host}. Kategori bawaan: {CATEGORY_ID[kategori]}. "
                f"Perlu ditinjau analis.")
    return (f"Indikasi {CATEGORY_ID[kategori]} pada {host}: " + "; ".join(titles) +
            f". {len(case['events'])} event dianalisis. Ringkasan dibuat dari template aturan (tanpa LLM).")


def degraded_decision(case: dict, reason: str, fw: FirewallReport | None = None) -> Decision:
    kategori, _, fired = detector.classify(case["events"])
    jenis = PLAYBOOK[kategori]
    target = case.get("primary_host") or None
    warnings = ["MODE_DEGRADASI"]
    reasons = [reason, f"kategori dari template aturan ({', '.join(fired) or 'tanpa aturan, bawaan'})"]
    if fw is not None and fw.injection:
        warnings.append("INJEKSI_TERDETEKSI")
        reasons.append("firewall menemukan instruksi di isi log: aksi berisiko tidak diusulkan")
        jenis, target = "escalate", None
    if jenis == "isolate_host" and (not target or is_protected_host(target)):
        jenis, target = "escalate", None
        reasons.append("host kosong/terlindungi: dieskalasi")
    if jenis in RISKY_ACTIONS:
        verdict, status = "REQUEST_APPROVAL", "MENUNGGU_PERSETUJUAN"
    else:
        verdict, status, target = "EXECUTE", "DIESKALASI", None
    return Decision(verdict, {"jenis": jenis, "target": target}, kategori, template_summary(case, kategori, fired),
                    "rules_degraded", None, reasons, warnings, status)


def _cited_events(case: dict, bukti: list[str]) -> list[dict]:
    ids = {b.strip().upper() for b in bukti}
    return [e for e in case["events"] if e["id"].upper() in ids]


def decide(case: dict, proposal: dict | None, fw: FirewallReport, llm_error: str | None = None) -> Decision:
    if proposal is None:
        return degraded_decision(case, llm_error or "keluaran LLM tidak dapat diurai", fw)

    reasons: list[str] = []
    warnings: list[str] = []
    base_cat, _, fired = detector.classify(case["events"])
    kategori = proposal.get("kategori", "")
    if kategori not in CATEGORIES:
        reasons.append(f"kategori LLM '{kategori[:40]}' di luar daftar: dipakai kategori aturan")
        kategori = base_cat
    aksi = proposal.get("aksi") or {}
    jenis = (aksi.get("jenis") or "").strip()
    target = aksi.get("target")
    summary, removed = filter_summary(proposal.get("ringkasan", ""), case)
    if removed:
        warnings.append("RINGKASAN_DISUNTING")
        reasons.append(f"{len(removed)} alamat/URL di ringkasan tidak ada di field terstruktur log: dihapus")

    def escalate(verdict: str, why: str) -> Decision:
        reasons.append(why)
        return Decision(verdict, {"jenis": "escalate", "target": None}, kategori, summary, "llm", proposal,
                        reasons, warnings, "DIESKALASI")

    if jenis not in ACTIONS:
        return escalate("BLOCK", f"aksi '{jenis[:40]}' di luar allowlist")

    if fw.injection:
        warnings.append("INJEKSI_TERDETEKSI")
        where = ", ".join(f"{f.event_id}.{f.field}" for f in fw.flagged)
        if jenis in RISKY_ACTIONS or jenis == "no_action":
            return escalate("BLOCK", f"instruksi terdeteksi di isi log ({where}); usulan '{jenis}' ditolak")
        return escalate("EXECUTE", f"instruksi terdeteksi di isi log ({where}); kasus dieskalasi")

    if jenis == "escalate":
        return escalate("EXECUTE", "eskalasi ke analis manusia")

    cited = _cited_events(case, proposal.get("bukti") or [])
    if jenis == "no_action":
        sev = detector.max_severity(case["events"])
        if sev >= detector.SEV_W["medium"]:
            return escalate("BLOCK", "aturan bukti: detektor menemukan indikasi berbobot >= medium; kasus tidak boleh ditutup")
        reasons.append("tidak ada indikasi berbobot >= medium; kasus ditutup")
        return Decision("EXECUTE", {"jenis": "no_action", "target": None}, kategori, summary, "llm", proposal,
                        reasons, warnings, "DITUTUP")

    # risky actions
    if not cited:
        return escalate("BLOCK", "aksi berisiko tanpa bukti: tidak ada id event valid di kolom bukti")
    cited_hit = [e for e in cited if detector.rule_hits(e)]
    if not cited_hit:
        return escalate("BLOCK", "aturan bukti: event yang dikutip tidak memicu aturan detektor mana pun")
    if not target:
        return escalate("BLOCK", "aksi berisiko tanpa target")
    if jenis == "isolate_host":
        if is_protected_host(target):
            return escalate("BLOCK", f"host '{target}' termasuk aset terlindungi: perlu keputusan komandan")
        if not any(_host_match(target, str(e.get(f, ""))) for e in cited_hit for f in HOST_FIELDS):
            return escalate("BLOCK", f"host '{target[:60]}' tidak muncul di field host event bukti")
    else:  # block_ip
        try:
            ip = ipaddress.ip_address(target.strip())
        except ValueError:
            return escalate("BLOCK", f"target '{target[:60]}' bukan alamat IP")
        if is_protected_ip(str(ip)) or ip.is_loopback or ip.is_unspecified or ip.is_multicast:
            return escalate("BLOCK", f"IP {ip} termasuk aset terlindungi / tidak sah")
        if not any(str(e.get(f, "")).strip() == str(ip) for e in cited_hit for f in IP_FIELDS):
            return escalate("BLOCK", f"IP {ip} tidak muncul di field IP terstruktur event bukti")
    reasons.append("lolos allowlist, aturan bukti, dan daftar aset terlindungi; menunggu persetujuan manusia")
    return Decision("REQUEST_APPROVAL", {"jenis": jenis, "target": target}, kategori, summary, "llm", proposal,
                    reasons, warnings, "MENUNGGU_PERSETUJUAN")
