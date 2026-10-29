"""Detektor / pra-filter gaya Sigma (deterministik, tanpa LLM).

Dua kegunaan:
1. memilih event yang paling mencurigakan dari satu rekaman (pra-filter -> kasus triase),
2. BASELINE template aturan: kategori insiden = kategori aturan dengan bobot terbesar.

Aturan ditulis dari pengetahuan umum deteksi (gaya SigmaHQ) dan dicek hanya di split DEV.
Ini BUKAN port aturan SigmaHQ resmi; nama/logika disederhanakan.
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass
from typing import Callable

from . import CATEGORIES

SEV_W = {"low": 1, "medium": 2, "high": 3}


def _f(ev: dict, *names: str) -> str:
    return " ".join(str(ev.get(n, "")) for n in names).lower()


def _text(ev: dict) -> str:
    return _f(ev, "CommandLine", "ParentCommandLine", "ScriptBlockText", "Payload", "Message", "Details",
              "ImagePath", "ServiceFileName")


def _img(ev: dict) -> str:
    return _f(ev, "Image", "NewProcessName", "ProcessName")


def _rx(pattern: str) -> Callable[[str], bool]:
    r = re.compile(pattern, re.I)
    return lambda s: bool(r.search(s))


@dataclass(frozen=True)
class Rule:
    rid: str
    title: str          # judul Bahasa Indonesia, ditampilkan ke operator dan LLM
    category: str
    severity: str
    match: Callable[[dict], bool]


_SYSTEM_SRC = _rx(r"\\(svchost|wmiprvse|msmpeng|csrss|wininit|services|lsm|taskmgr|vmtoolsd|mrt|sysmon64?|"
                  r"healthservice|monitoringhost|splunkd|winlogbeat|osqueryd)\.exe$")

RULES: list[Rule] = [
    # ---- credential_access
    Rule("CA01", "Akses memori proses LSASS oleh proses non-sistem", "credential_access", "high",
         lambda e: e["EventID"] == 10 and _f(e, "TargetImage").endswith("lsass.exe")
         and not _SYSTEM_SRC(_f(e, "SourceImage"))),
    Rule("CA02", "Kata kunci alat pencuri kredensial (mimikatz/sekurlsa/lsadump)", "credential_access", "high",
         lambda e: _rx(r"mimikatz|sekurlsa|lsadump|kerberos::|logonpasswords|dcsync|invoke-mimikatz|pypykatz|"
                       r"procdump.*lsass|comsvcs.*minidump")(_text(e))),
    Rule("CA03", "Penyalinan basis data AD / shadow copy (ntds.dit)", "credential_access", "high",
         lambda e: _rx(r"ntds\.dit|vssadmin.*create\s+shadow|harddiskvolumeshadowcopy|ntdsutil")(_text(e) + _f(e, "TargetFilename"))),
    Rule("CA04", "Ekspor hive registri SAM/SECURITY/SYSTEM", "credential_access", "high",
         lambda e: _rx(r"reg(\.exe)?\s+save\s+hklm\\(sam|security|system)")(_text(e))),
    Rule("CA05", "Akses rahasia LSA di registri", "credential_access", "high",
         lambda e: _rx(r"\\security\\policy\\secrets")(_f(e, "TargetObject", "ObjectName"))),
    Rule("CA06", "Akses brankas kredensial Windows (Vault/Credential Manager)", "credential_access", "medium",
         lambda e: _rx(r"vaultcmd|passwordvault|get-vaultcredential|credentialmanager|credenumerate")(_text(e))),
    Rule("CA07", "Replikasi direktori (pola DCSync) pada objek domain", "credential_access", "high",
         lambda e: e["EventID"] == 4662 and _rx(r"1131f6aa|1131f6ad|89e95b76")(_text(e) + _f(e, "ObjectName"))),
    # ---- lateral_movement
    Rule("LM01", "Layanan PsExec / layanan jarak jauh dipasang", "lateral_movement", "high",
         lambda e: _rx(r"psexesvc|paexec|remcomsvc")(_img(e) + _text(e) + _f(e, "ServiceName", "TargetFilename"))),
    Rule("LM02", "Pemasangan layanan baru (7045/4697)", "lateral_movement", "medium",
         lambda e: e["EventID"] in (7045, 4697)),
    Rule("LM03", "Akses pipa svcctl/atsvc lewat SMB", "lateral_movement", "high",
         lambda e: e["EventID"] == 5145 and _rx(r"svcctl|atsvc")(_f(e, "RelativeTargetName"))),
    Rule("LM04", "Proses anak dari WMI Provider Host", "lateral_movement", "medium",
         lambda e: e["EventID"] in (1, 4688) and _f(e, "ParentImage", "ParentProcessName").endswith("wmiprvse.exe")),
    Rule("LM05", "Sesi PowerShell Remoting / WinRM (wsmprovhost)", "lateral_movement", "high",
         lambda e: "wsmprovhost.exe" in _img(e) + _f(e, "ParentImage", "SourceImage")),
    Rule("LM06", "Akses share administratif (ADMIN$/C$/IPC$) jarak jauh", "lateral_movement", "medium",
         lambda e: e["EventID"] in (5140, 5145) and _rx(r"\\\\\*\\(admin\$|c\$)")(_f(e, "ShareName"))),
    Rule("LM07", "Aplikasi DCOM (mmc/excel/explorer) memunculkan shell", "lateral_movement", "medium",
         lambda e: e["EventID"] in (1, 4688) and _rx(r"\\(mmc|excel|dllhost)\.exe$")(_f(e, "ParentImage", "ParentProcessName"))
         and _rx(r"\\(cmd|powershell|rundll32|mshta)\.exe$")(_img(e))),
    Rule("LM08", "Logon jaringan (tipe 3) dari alamat jarak jauh", "lateral_movement", "low",
         lambda e: e["EventID"] == 4624 and str(e.get("LogonType")) == "3"
         and _f(e, "IpAddress") not in ("", "-", "::1", "127.0.0.1")),
    Rule("LM09", "Logon RDP (tipe 10)", "lateral_movement", "medium",
         lambda e: e["EventID"] == 4624 and str(e.get("LogonType")) == "10"),
    Rule("LM10", "Autentikasi Netlogon tidak lazim", "lateral_movement", "medium",
         lambda e: e["EventID"] in (5805, 5827, 5828, 5829)),
    # ---- persistence
    Rule("PE01", "Perubahan kunci registri Run/RunOnce", "persistence", "high",
         lambda e: e["EventID"] in (12, 13, 14, 4657) and _rx(r"\\currentversion\\run(once)?(\\|$)")(_f(e, "TargetObject", "ObjectName"))),
    Rule("PE02", "Langganan event WMI (persistensi WMI)", "persistence", "high",
         lambda e: e["EventID"] in (19, 20, 21, 5861)),
    Rule("PE03", "Berkas ditulis ke folder Startup", "persistence", "high",
         lambda e: _rx(r"\\start menu\\programs\\startup\\")(_f(e, "TargetFilename") + _text(e))),
    Rule("PE04", "Pembuatan scheduled task", "persistence", "medium",
         lambda e: e["EventID"] in (4698, 106) or _rx(r"schtasks(\.exe)?\s+/create|register-scheduledtask")(_text(e))),
    # ---- defense_evasion
    Rule("DE01", "CreateRemoteThread ke proses lain (injeksi)", "defense_evasion", "high",
         lambda e: e["EventID"] == 8),
    Rule("DE02", "Biner LOLBin disalahgunakan (mavinject/regsvr32/mshta/bitsadmin/certutil/wmic xsl)", "defense_evasion", "medium",
         lambda e: _rx(r"mavinject|regsvr32.*/i:|mshta(\.exe)?\s|bitsadmin.*/(transfer|addfile)|certutil.*-urlcache|"
                       r"wmic.*/format:|installutil|msbuild\.exe|odbcconf|cmstp|control(\.exe)?\s.*\.cpl")(_text(e))),
    Rule("DE03", "Penghapusan log event", "defense_evasion", "low",
         lambda e: e["EventID"] in (1102, 104) or _rx(r"wevtutil(\.exe)?\s+cl|clear-eventlog")(_text(e))),
    Rule("DE04", "Pelemahan antivirus / AMSI", "defense_evasion", "high",
         lambda e: _rx(r"set-mppreference.*-disable|disableantispyware|amsiinitfailed|amsiutils|disablerealtimemonitoring")(_text(e))),
    Rule("DE05", "Kata kunci injeksi proses (VirtualAllocEx/WriteProcessMemory/PEInjection)", "defense_evasion", "medium",
         lambda e: _rx(r"virtualallocex|writeprocessmemory|createremotethread|reflectivepeinjection|peinjection|psinject|"
                       r"ntqueueapcthread|setthreadcontext")(_text(e))),
    Rule("DE06", "Perubahan registri pengaturan keamanan (WDigest/RDP/LSA)", "defense_evasion", "medium",
         lambda e: e["EventID"] in (12, 13, 14, 4657) and _rx(r"uselogoncredential|fdenytsconnections|disablerestrictedadmin|"
                                                               r"runasppl|\\lsa\\")(_f(e, "TargetObject", "ObjectName"))),
    Rule("DE07", "Proses berjalan dari lokasi sementara / berkas disamarkan", "defense_evasion", "low",
         lambda e: e["EventID"] in (1, 4688) and _rx(r"\\(temp|appdata\\local\\temp|users\\public)\\")(_img(e))),
    # ---- discovery
    Rule("DI01", "Perintah pengintaian akun/domain (net/whoami/nltest)", "discovery", "medium",
         lambda e: _rx(r"\bnet1?(\.exe)?\s+(user|group|localgroup|view|accounts)|whoami|nltest|systeminfo|"
                       r"get-net(user|group|computer|domain)|get-domain|find-localadminaccess|invoke-sharefinder|"
                       r"query\s+user|quser|dsquery|adfind")(_text(e))),
    Rule("DI02", "Enumerasi SAMR/LSARPC lewat SMB", "discovery", "medium",
         lambda e: e["EventID"] == 5145 and _rx(r"samr|lsarpc|srvsvc")(_f(e, "RelativeTargetName"))),
    Rule("DI03", "Kueri LDAP/AD dalam jumlah besar oleh skrip", "discovery", "low",
         lambda e: _rx(r"directorysearcher|\[adsisearcher\]|ldap://")(_text(e))),
    # ---- execution
    Rule("EX01", "PowerShell terenkode / unduh-jalankan", "execution", "low",
         lambda e: _rx(r"powershell.*\s-(e|en|enc|encodedcommand)\s|-nop\s.*-w(indowstyle)?\s+hidden|iex\s*\(|"
                       r"downloadstring|invoke-expression|frombase64string")(_text(e))),
    Rule("EX02", "Script host (wscript/cscript) menjalankan skrip", "execution", "medium",
         lambda e: e["EventID"] in (1, 4688) and _rx(r"\\(wscript|cscript)\.exe$")(_img(e))),
    Rule("EX03", "Pendengar HTTP dibuat dari PowerShell", "execution", "low",
         lambda e: _rx(r"httplistener")(_text(e))),
    # ---- privilege_escalation
    Rule("PR01", "Pola bypass UAC (fodhelper/eventvwr/ms-settings)", "privilege_escalation", "high",
         lambda e: _rx(r"fodhelper|eventvwr|ms-settings\\shell\\open\\command|mscfile\\shell\\open|sdclt|computerdefaults")(
             _text(e) + _img(e) + _f(e, "TargetObject"))),
    Rule("PR02", "Logon dengan kredensial eksplisit / RunAs", "privilege_escalation", "medium",
         lambda e: e["EventID"] == 4648 or _rx(r"invoke-runas|runas(\.exe)?\s|createprocesswithlogon")(_text(e))),
    # ---- collection
    Rule("CO01", "Perekaman mikrofon/layar/clipboard", "collection", "medium",
         lambda e: _rx(r"record_mic|soundrecorder|wavein|get-clipboard|screenshot|webcam")(_text(e))),
]

RULE_BY_ID = {r.rid: r for r in RULES}

# Fallback when no rule fires = most frequent label in the DEV split (lateral_movement, 12/33).
FALLBACK_CATEGORY = "lateral_movement"
SALIENT_EIDS = {1, 3, 7, 8, 10, 11, 12, 13, 4104, 4624, 4648, 4662, 4688, 4697, 5140, 5145, 7045, 800, 4103}


def rule_hits(ev: dict) -> list[Rule]:
    hits = []
    for r in RULES:
        try:
            if r.match(ev):
                hits.append(r)
        except Exception:  # a malformed event must never crash the detector
            continue
    return hits


def event_score(ev: dict) -> int:
    return max((SEV_W[r.severity] for r in rule_hits(ev)), default=0)


def _dedup_key(ev: dict) -> tuple:
    return (ev.get("EventID"), _img(ev), _f(ev, "TargetImage", "SourceImage", "TargetObject"),
            _text(ev)[:120])


def select_indices(events: list[dict], k: int = 8) -> list[int]:
    """Pre-filter: highest rule severity first, then rarity of (EventID, Image) inside the recording,
    then original order. Near-duplicates removed. Label-blind. Returns positions in `events`."""
    freq = Counter((e.get("EventID"), _img(e)) for e in events)
    scored = []
    for i, e in enumerate(events):
        s = event_score(e)
        if s == 0 and e.get("EventID") not in SALIENT_EIDS:
            continue
        scored.append((-s, freq[(e.get("EventID"), _img(e))], i))
    scored.sort()
    out, seen = [], set()
    for _, _, i in scored:
        key = _dedup_key(events[i])
        if key in seen:
            continue
        seen.add(key)
        out.append(i)
        if len(out) >= k:
            break
    return out


def select_events(events: list[dict], k: int = 8) -> list[dict]:
    return [events[i] for i in select_indices(events, k)]


def classify(events: list[dict]) -> tuple[str, dict, list[str]]:
    """Baseline template-rule categoriser. Returns (category, weights, rule ids fired)."""
    # Each rule counts once per case (a noisy rule firing on many events must not dominate).
    w = {c: 0 for c in CATEGORIES}
    fired = sorted({r.rid for e in events for r in rule_hits(e)})
    for rid in fired:
        r = RULE_BY_ID[rid]
        w[r.category] += SEV_W[r.severity]
    if not fired:
        return FALLBACK_CATEGORY, w, []
    best = max(CATEGORIES, key=lambda c: (w[c], -CATEGORIES.index(c)))
    return best, w, fired


def max_severity(events: list[dict]) -> int:
    return max((event_score(e) for e in events), default=0)
