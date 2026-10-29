"""Pipeline: pembaca log -> detektor/pra-filter -> firewall -> LLM lokal (usul) -> policy engine (putus) -> audit."""

from __future__ import annotations

import time
from datetime import datetime, timezone

from . import detector, firewall, policy
from .llm import SYSTEM_GUARDED, SYSTEM_NAIVE, build_user_prompt, parse_output
from .logs import render_event


def detector_titles(case: dict) -> list[str]:
    seen, out = set(), []
    for e in case["events"]:
        for r in detector.rule_hits(e):
            key = (e["id"], r.rid)
            if key in seen:
                continue
            seen.add(key)
            out.append(f"{e['id']}: {r.title}")
    return out[:16]


def _lines(events: list[dict]) -> list[str]:
    return [render_event(e, e["id"]) for e in events]


def _call(llm, system: str, user: str) -> tuple[str | None, dict, str | None]:
    try:
        text, usage = llm.complete(system, user)
        return text, usage, None
    except Exception as exc:  # LLM dead, timeout, OOM...
        return None, {"seconds": 0.0}, f"LLM tidak tersedia: {type(exc).__name__}: {str(exc)[:120]}"


def run_naive(case: dict, llm) -> dict:
    """Kondisi TANPA firewall: log mentah ke LLM, usulan dianggap langsung dieksekusi."""
    user = build_user_prompt(_lines(case["events"]), detector_titles(case))
    text, usage, err = _call(llm, SYSTEM_NAIVE, user)
    proposal = parse_output(text) if text else None
    return {"mode": "naive", "raw": text, "proposal": proposal, "error": err, "llm_seconds": usage.get("seconds", 0.0),
            "prompt_tokens": usage.get("prompt_tokens"), "completion_tokens": usage.get("completion_tokens"),
            "executed": (proposal or {}).get("aksi") if proposal else None}


def run_prompt_only(case: dict, llm) -> dict:
    """Ablasi: prompt defensif + spotlighting saja, tanpa redaksi firewall dan tanpa policy engine."""
    view = []
    for e in case["events"]:
        e2 = dict(e)
        for f in firewall.FREE_TEXT_FIELDS:
            if f in e:
                e2[f] = firewall.sanitised_value(e[f])
        view.append(e2)
    user = build_user_prompt(_lines(view), detector_titles(case))
    text, usage, err = _call(llm, SYSTEM_GUARDED, user)
    proposal = parse_output(text) if text else None
    return {"mode": "prompt_only", "raw": text, "proposal": proposal, "error": err,
            "llm_seconds": usage.get("seconds", 0.0), "executed": (proposal or {}).get("aksi") if proposal else None}


def run_guarded(case: dict, llm, audit=None) -> dict:
    """Kondisi DENGAN firewall (PERISAI-RESPON penuh)."""
    t0 = time.perf_counter()
    fw = firewall.inspect_case(case)
    view = firewall.guarded_view(case, fw)
    user = build_user_prompt(_lines(view), detector_titles(case))
    t_fw = time.perf_counter() - t0
    text, usage, err = (None, {"seconds": 0.0}, "LLM dimatikan") if llm is None else _call(llm, SYSTEM_GUARDED, user)
    proposal = parse_output(text) if text else None
    t1 = time.perf_counter()
    dec = policy.decide(case, proposal, fw, llm_error=err if err else (None if proposal else "keluaran LLM tidak valid"))
    t_pol = time.perf_counter() - t1
    out = {"mode": "guarded", "raw": text, "proposal": proposal, "error": err, "decision": dec.to_dict(),
           "fw_flagged": [{"event": f.event_id, "field": f.field, "codes": f.codes} for f in fw.flagged],
           "fw_injection": fw.injection, "llm_seconds": usage.get("seconds", 0.0),
           "firewall_ms": 1000 * t_fw, "policy_ms": 1000 * t_pol}
    if audit is not None:
        ts = datetime.now(timezone.utc).isoformat(timespec="seconds")
        audit.append(case["case_id"], "firewall", {"injection": fw.injection, "flagged": out["fw_flagged"]}, ts)
        audit.append(case["case_id"], "usulan_llm", {"proposal": proposal, "error": err}, ts)
        audit.append(case["case_id"], "keputusan_policy", {k: out["decision"][k] for k in
                                                           ("verdict", "final_action", "kategori", "source",
                                                            "reasons", "warnings", "final_status")}, ts)
    return out
