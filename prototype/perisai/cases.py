"""Kasus triase: satu rekaman OTRF -> K event terpilih oleh pra-filter + label kategori (folder taktik OTRF).

Catatan operasional: Windows Defender menandai teks log mentah OTRF (string Mimikatz/Empire di command line)
sebagai ancaman bila ditulis polos ke disk. Karena itu kasus dibangun DI MEMORI dari arsip asli setiap kali,
dan yang dibekukan ke disk hanya manifes: (dataset, posisi event terpilih, SHA-256 isi kasus).
"""

from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

from . import detector
from .logs import FREE_TEXT_FIELDS, host_of, load_events

ROOT = Path(__file__).resolve().parents[1]
K_EVENTS = 8


def canonical(obj) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str)


def case_sha256(case: dict) -> str:
    body = {k: case[k] for k in ("case_id", "dataset", "label", "group", "events")}
    return hashlib.sha256(canonical(body).encode("utf-8")).hexdigest()


def build_case(dataset: str, label: str, group: str, side: str, zips_dir: Path | None = None) -> dict:
    zips_dir = zips_dir or ROOT / "data" / "otrf" / "zips"
    events = load_events(zips_dir / dataset)
    idx = detector.select_indices(events, k=K_EVENTS)
    evs = [{"id": f"E{n}", **events[i]} for n, i in enumerate(idx, 1)]
    hosts = [host_of(e) for e in evs if host_of(e)]
    primary = max(sorted(set(hosts)), key=hosts.count) if hosts else ""
    case = {"case_id": dataset.rsplit(".", 1)[0].replace(".tar", ""), "dataset": dataset, "label": label,
            "group": group, "side": side, "n_events_recording": len(events), "primary_host": primary,
            "positions": idx, "events": evs}
    case["sha256"] = case_sha256(case)
    return case


def build_side(side: str) -> list[dict]:
    rows = json.loads((ROOT / "frozen" / "split.json").read_text(encoding="utf-8"))
    return [build_case(r["dataset"], r["label"], r["group"], r["side"]) for r in rows if r["side"] == side]


def manifest(cases: list[dict]) -> list[dict]:
    return [{k: c[k] for k in ("case_id", "dataset", "label", "group", "side", "n_events_recording",
                               "primary_host", "positions", "sha256")} for c in cases]


def check_against_manifest(cases: list[dict], man: list[dict]) -> list[str]:
    by = {m["case_id"]: m for m in man}
    problems = []
    for c in cases:
        m = by.get(c["case_id"])
        if m is None:
            problems.append(f"{c['case_id']}: not in manifest")
        elif m["sha256"] != c["sha256"]:
            problems.append(f"{c['case_id']}: content hash differs from frozen manifest")
    if len(cases) != len(man):
        problems.append(f"count {len(cases)} != manifest {len(man)}")
    return problems


def inject(case: dict, text: str, event_index: int, field: str | None = None) -> dict:
    """Return a copy of the case with `text` appended to a free-text field of one event.
    If the event has no free-text field, `field` (default CommandLine) is created."""
    c = copy.deepcopy(case)
    if not c["events"]:
        c["events"].append({"id": "E1", "EventID": 1, "Hostname": c.get("primary_host", "")})
    ev = c["events"][event_index % len(c["events"])]
    target = field
    if target is None:
        target = next((f for f in FREE_TEXT_FIELDS if f in ev), "CommandLine")
    ev[target] = (str(ev.get(target, "")) + " " + text).strip()
    c["injected_event"] = ev["id"]
    c["injected_field"] = target
    return c
