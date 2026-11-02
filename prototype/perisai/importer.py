"""Importer log Windows ASLI -> kasus triase.

Format yang diterima (diekspor operator di PC/server sendiri, tanpa alat tambahan):
  * XML wevtutil :  wevtutil qe Security /c:500 /rd:true /f:xml > security.xml
                    wevtutil qe Microsoft-Windows-Sysmon/Operational /c:500 /rd:true /f:xml > sysmon.xml
  * XML PowerShell: Get-WinEvent -LogName Security -MaxEvents 500 | ForEach-Object { $_.ToXml() } | Out-File -Encoding utf8 security.xml
  * JSON / JSON-lines bergaya Winlogbeat/NXLog/OTRF (dibaca oleh logs.normalize).
Keluaran wevtutil berupa deretan <Event> tanpa elemen akar, jadi dibungkus dulu. Dokumen yang memuat DOCTYPE/ENTITY
ditolak (mencegah ledakan entitas XML).

Event dikelompokkan per host dan jendela waktu (bawaan 15 menit). Tiap kelompok menjadi satu kasus dengan
8 event terpilih oleh pra-filter detektor yang sama dengan evaluasi.
"""

from __future__ import annotations

import json
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from pathlib import Path

from . import detector
from .cases import K_EVENTS, case_sha256
from .logs import _iter_json_lines, host_of, normalize

_NS = re.compile(r"^\{[^}]*\}")
_XML_DECL = re.compile(r"<\?xml[^>]*\?>")


def _local(tag: str) -> str:
    return _NS.sub("", tag)


def parse_xml(text: str) -> list[dict]:
    if re.search(r"<!(DOCTYPE|ENTITY)", text, re.I):
        raise ValueError("XML berisi DOCTYPE/ENTITY: ditolak")
    body = _XML_DECL.sub("", text.lstrip("﻿"))
    root = ET.fromstring(f"<Events>{body}</Events>")
    out = []
    for ev in root.iter():
        if _local(ev.tag) != "Event":
            continue
        rec: dict = {}
        for child in ev:
            name = _local(child.tag)
            if name == "System":
                for s in child:
                    sn = _local(s.tag)
                    if sn == "TimeCreated":
                        rec["TimeCreated"] = s.get("SystemTime", "")
                    elif sn == "Provider":
                        rec["Provider"] = s.get("Name", "")
                    elif s.text and s.text.strip():
                        rec[sn] = s.text.strip()
            elif name == "EventData":
                for d in child:
                    if d.get("Name"):
                        rec[d.get("Name")] = (d.text or "").strip()
            elif name == "UserData":
                for d in child.iter():
                    if d is not child and len(d) == 0 and d.text and d.text.strip():
                        rec.setdefault(_local(d.tag), d.text.strip())
            elif name == "RenderingInfo":
                msg = next((m.text for m in child if _local(m.tag) == "Message"), None)
                if msg:
                    rec["Message"] = msg.strip()
        out.append(rec)
    return out


def read_file(path: Path) -> list[dict]:
    raw = path.read_bytes()
    for enc in ("utf-8-sig", "utf-16"):
        try:
            text = raw.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    else:
        text = raw.decode("utf-8", errors="replace")
    if text.lstrip("﻿").lstrip().startswith("<"):
        recs = parse_xml(text)
    else:
        recs = list(_iter_json_lines(text.encode("utf-8")))
    return [normalize(r) for r in recs]


def _ts(ev: dict) -> datetime | None:
    v = str(ev.get("TimeCreated") or ev.get("@timestamp") or "")
    if not v:
        return None
    v = v.replace("Z", "+00:00")
    v = re.sub(r"(\.\d{6})\d+", r"\1", v)  # wevtutil memberi 7 digit pecahan detik
    try:
        return datetime.fromisoformat(v)
    except ValueError:
        return None


def to_cases(events: list[dict], window_minutes: int = 15, source: str = "impor") -> list[dict]:
    """Kelompokkan per host + jendela waktu; kelompok tanpa temuan aturan tetap dibuat (ditandai tanpa_temuan)."""
    groups: dict[tuple, list[dict]] = {}
    for ev in events:
        t = _ts(ev)
        slot = None
        if t is not None:
            base = t.replace(second=0, microsecond=0)
            slot = (base - timedelta(minutes=base.minute % window_minutes)).isoformat()
        groups.setdefault((host_of(ev) or "host-tidak-diketahui", slot), []).append(ev)
    cases = []
    for (host, slot), evs in sorted(groups.items(), key=lambda kv: (str(kv[0][1]), kv[0][0])):
        evs = sorted(evs, key=lambda e: str(_ts(e) or ""))
        idx = detector.select_indices(evs, k=K_EVENTS)
        picked = [{"id": f"E{n}", **evs[i]} for n, i in enumerate(idx, 1)]
        cid = f"{host}@{slot or 'tanpa-waktu'}"
        case = {"case_id": cid, "dataset": source, "label": "", "group": "", "side": "impor",
                "n_events_recording": len(evs), "primary_host": host if host != "host-tidak-diketahui" else "",
                "positions": idx, "events": picked,
                "tanpa_temuan": not any(detector.rule_hits(e) for e in picked)}
        case["sha256"] = case_sha256(case)
        cases.append(case)
    return cases


def dump_cases(cases: list[dict]) -> str:
    return json.dumps(cases, ensure_ascii=False, indent=1)
