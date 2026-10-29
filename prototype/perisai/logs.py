"""Pembaca log: arsip OTRF Security-Datasets (zip / tar.gz / json) -> event ternormalisasi.

Event OTRF adalah JSON per baris (Windows Security, Sysmon, PowerShell, dsb. via Winlogbeat/NXLog).
Kita hanya menyimpan subset field yang relevan untuk triase supaya prompt kecil.
"""

from __future__ import annotations

import io
import json
import tarfile
import zipfile
from pathlib import Path
from typing import Iterator

# Field yang dibawa ke kasus. Dibagi dua: TERSTRUKTUR (dibuat sistem/OS, dipakai sebagai bukti oleh
# policy engine) dan TEKS BEBAS (bisa ditulis/dipengaruhi penyerang: command line, script block, pesan).
STRUCTURED_FIELDS = [
    "EventID", "Channel", "Hostname", "Computer", "TimeCreated", "@timestamp",
    "SubjectUserName", "TargetUserName", "User", "LogonType",
    "Image", "ParentImage", "TargetImage", "SourceImage", "GrantedAccess",
    "SourceIp", "DestinationIp", "DestinationPort", "IpAddress", "SourceAddress", "DestAddress",
    "DestinationHostname", "ServiceName", "TargetObject", "TargetFilename", "ObjectName",
    "ShareName", "RelativeTargetName", "ProcessName", "NewProcessName", "ParentProcessName",
]
FREE_TEXT_FIELDS = ["CommandLine", "ParentCommandLine", "ScriptBlockText", "Message", "Details",
                    "Payload", "ImagePath", "ServiceFileName", "UserAgent"]
IP_FIELDS = ["SourceIp", "DestinationIp", "IpAddress", "SourceAddress", "DestAddress"]
HOST_FIELDS = ["Hostname", "Computer"]

MAX_FIELD_CHARS = 400


def _iter_json_lines(raw: bytes) -> Iterator[dict]:
    text = raw.decode("utf-8", errors="replace")
    stripped = text.lstrip()
    if stripped.startswith("["):
        try:
            for obj in json.loads(stripped):
                if isinstance(obj, dict):
                    yield obj
            return
        except json.JSONDecodeError:
            pass
    for line in text.splitlines():
        line = line.strip()
        if not line or not line.startswith("{"):
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict):
            yield obj


def read_archive(path: Path) -> Iterator[dict]:
    """Yield raw event dicts from an OTRF archive. Reads members in memory; never extracts to disk."""
    name = path.name.lower()
    if name.endswith(".zip"):
        with zipfile.ZipFile(path) as zf:
            for info in zf.infolist():
                if info.is_dir() or not info.filename.lower().endswith(".json"):
                    continue
                yield from _iter_json_lines(zf.read(info))
    elif name.endswith(".tar.gz") or name.endswith(".tgz"):
        with tarfile.open(path, "r:gz") as tf:
            for m in tf.getmembers():
                if not m.isfile() or not m.name.lower().endswith(".json"):
                    continue
                fh = tf.extractfile(m)
                if fh is not None:
                    yield from _iter_json_lines(fh.read())
    elif name.endswith(".json"):
        yield from _iter_json_lines(path.read_bytes())


def _flat(ev: dict) -> dict:
    """Some exports nest event data (winlog.event_data). Flatten one level."""
    out = dict(ev)
    for key in ("event_data", "EventData"):
        if isinstance(ev.get(key), dict):
            out.update(ev[key])
    wl = ev.get("winlog")
    if isinstance(wl, dict):
        out.setdefault("EventID", wl.get("event_id"))
        out.setdefault("Channel", wl.get("channel"))
        out.setdefault("Computer", wl.get("computer_name"))
        if isinstance(wl.get("event_data"), dict):
            out.update(wl["event_data"])
    # older winlogbeat schema (event_id / log_name / computer_name / message)
    if "EventID" not in out and "event_id" in ev:
        out["EventID"] = ev.get("event_id")
    if "Channel" not in out and "log_name" in ev:
        out["Channel"] = ev.get("log_name")
    if "Computer" not in out and "computer_name" in ev:
        out["Computer"] = ev.get("computer_name")
    if "Message" not in out and "message" in ev:
        out["Message"] = ev.get("message")
    return out


def normalize(ev: dict) -> dict:
    ev = _flat(ev)
    out: dict = {}
    for f in STRUCTURED_FIELDS + FREE_TEXT_FIELDS:
        v = ev.get(f)
        if v is None or v == "" or v == "-":
            continue
        if isinstance(v, (dict, list)):
            v = json.dumps(v, ensure_ascii=False)
        v = str(v)
        if len(v) > MAX_FIELD_CHARS:
            v = v[:MAX_FIELD_CHARS] + "…"
        out[f] = v
    try:
        out["EventID"] = int(out.get("EventID", -1))
    except (TypeError, ValueError):
        out["EventID"] = -1
    if "Hostname" not in out and "Computer" in out:
        out["Hostname"] = out["Computer"]
    # The rendered Message duplicates structured fields; keep it only for events that have little else.
    informative = [f for f in out if f not in ("EventID", "Channel", "Hostname", "Computer", "TimeCreated",
                                                "@timestamp", "Message")]
    if "Message" in out and len(informative) >= 2:
        del out["Message"]
    return out


def load_events(path: Path, limit: int | None = None) -> list[dict]:
    evs = []
    for i, raw in enumerate(read_archive(path)):
        evs.append(normalize(raw))
        if limit is not None and i + 1 >= limit:
            break
    return evs


def host_of(event: dict) -> str:
    for f in HOST_FIELDS:
        if event.get(f):
            return str(event[f])
    return ""


def render_event(event: dict, eid: str, fields_free: dict | None = None) -> str:
    """One-line-per-field compact rendering used in prompts and the demo."""
    parts = [f"[{eid}]"]
    for f in STRUCTURED_FIELDS + FREE_TEXT_FIELDS:
        if f in ("Computer", "TimeCreated", "@timestamp") or f not in event:
            continue
        v = event[f] if fields_free is None or f not in fields_free else fields_free[f]
        parts.append(f"{f}={v}")
    return " | ".join(parts)
