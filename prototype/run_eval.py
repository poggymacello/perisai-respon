"""Evaluasi PERISAI-RESPON pada split UJI (lihat PRAREG.md). Resumable: baris yang sudah ada di CSV dilewati.

Run: .venv\\Scripts\\python -I run_eval.py            (butuh model di models\\)
     .venv\\Scripts\\python -I run_eval.py --manifest  (hanya membuat manifes kasus uji, tanpa LLM)
"""
from __future__ import annotations

import csv
import hashlib
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from perisai import PLAYBOOK, detector, scenarios  # noqa: E402
from perisai.cases import build_side, check_against_manifest, inject, manifest  # noqa: E402
from perisai.firewall import FirewallReport  # noqa: E402
from perisai.metrics import attack_success, final_action, final_category  # noqa: E402
from perisai.pipeline import run_guarded, run_naive, run_prompt_only  # noqa: E402
from perisai import policy  # noqa: E402

RES = ROOT / "results"
CSV_PATH = RES / "runs.csv"
RAW_PATH = RES / "raw_outputs.jsonl"
MAN_PATH = ROOT / "frozen" / "manifest_test.json"
FIELDS = ["unit_id", "case_id", "group", "label", "condition", "family", "goal", "atk_host", "atk_ip", "mode",
          "parse_ok", "kategori", "jenis", "target", "verdict", "final_status", "warnings", "fw_injection",
          "success", "auto", "cat_correct", "act_correct", "llm_seconds", "firewall_ms", "policy_ms", "error"]
COMBOS = [(f, g) for f in scenarios.DEV_FAMILIES for g in scenarios.GOALS]  # 3 x 4 = 12 templates


def _h(*p: str) -> int:
    return int(hashlib.sha256("|".join(p).encode()).hexdigest()[:8], 16)


def injected_units(cases: list[dict]) -> list[dict]:
    units = []
    for i, c in enumerate(cases):
        for j in range(2):
            fam, goal = COMBOS[(2 * i + j) % len(COMBOS)]
            spec = scenarios.DEV_FAMILIES[fam]
            params = scenarios.goal_params(c, goal)
            text = spec["tpl"].format(goal=scenarios.render_goal(goal, spec["lang"], params))
            ci = inject(c, text, event_index=_h(c["case_id"], fam, goal) % max(1, len(c["events"])))
            units.append({"unit_id": f"{c['case_id']}#{fam}#{goal}", "case": ci, "family": fam, "goal": goal,
                          "params": params})
    return units


def row_from(res: dict, base: dict, label: str) -> dict:
    p = res.get("proposal")
    d = res.get("decision")
    cat = final_category(res)
    jen = final_action(res)
    return {**base, "mode": res["mode"], "parse_ok": p is not None, "kategori": cat, "jenis": jen,
            "target": (d["final_action"].get("target") if d else ((p or {}).get("aksi") or {}).get("target")),
            "verdict": d["verdict"] if d else "", "final_status": d["final_status"] if d else "",
            "warnings": ";".join(d["warnings"]) if d else "", "fw_injection": res.get("fw_injection", ""),
            "cat_correct": cat == label, "act_correct": jen == PLAYBOOK[label],
            "llm_seconds": round(res.get("llm_seconds") or 0.0, 3),
            "firewall_ms": round(res.get("firewall_ms") or 0.0, 3), "policy_ms": round(res.get("policy_ms") or 0.0, 3),
            "error": res.get("error") or ""}


def main() -> None:
    t_start = time.time()
    cases = build_side("test")
    if "--manifest" in sys.argv:
        MAN_PATH.write_text(json.dumps(manifest(cases), indent=1, ensure_ascii=False), encoding="utf-8")
        print("manifest written:", len(cases), "cases")
        return
    problems = check_against_manifest(cases, json.loads(MAN_PATH.read_text(encoding="utf-8")))
    if problems:
        raise SystemExit("test cases differ from frozen manifest: " + "; ".join(problems[:5]))
    RES.mkdir(exist_ok=True)
    shard_k, shard_n, threads = 0, 1, 8
    if "--shard" in sys.argv:
        shard_k, shard_n = map(int, sys.argv[sys.argv.index("--shard") + 1].split("/"))
    if "--threads" in sys.argv:
        threads = int(sys.argv[sys.argv.index("--threads") + 1])
    csv_path = CSV_PATH if shard_n == 1 else RES / f"runs_shard{shard_k}.csv"
    raw_path = RAW_PATH if shard_n == 1 else RES / f"raw_outputs_shard{shard_k}.jsonl"
    done = set()
    for f in RES.glob("runs*.csv"):
        with f.open(encoding="utf-8") as fh0:
            done |= {(r["unit_id"], r["mode"]) for r in csv.DictReader(fh0)}
    new = not csv_path.exists()
    fh = csv_path.open("a", encoding="utf-8", newline="")
    w = csv.DictWriter(fh, fieldnames=FIELDS)
    if new:
        w.writeheader()
    raw = raw_path.open("a", encoding="utf-8")

    def emit(row: dict, res: dict | None = None) -> None:
        w.writerow({k: row.get(k, "") for k in FIELDS})
        fh.flush()
        if res is not None:
            raw.write(json.dumps({"unit_id": row["unit_id"], "mode": row["mode"], "raw": res.get("raw"),
                                  "proposal": res.get("proposal"), "decision": res.get("decision")},
                                 ensure_ascii=False, default=str) + "\n")
            raw.flush()

    # rules baseline + degraded mode (no LLM) on clean cases
    for c in cases:
        base = {"unit_id": c["case_id"], "case_id": c["case_id"], "group": c["group"], "label": c["label"],
                "condition": "clean"}
        if (c["case_id"], "rules") not in done:
            t0 = time.perf_counter()
            cat, _, _ = detector.classify(c["events"])
            ms = 1000 * (time.perf_counter() - t0)
            emit({**base, "mode": "rules", "parse_ok": "", "kategori": cat, "jenis": PLAYBOOK[cat],
                  "cat_correct": cat == c["label"], "act_correct": True, "policy_ms": round(ms, 3)})
        if (c["case_id"], "degraded") not in done:
            r = run_guarded(c, None)
            r["mode"] = "guarded"
            row = row_from(r, base, c["label"])
            row["mode"] = "degraded"
            emit(row)

    from perisai.llm import LocalLLM
    llm = LocalLLM(n_threads=threads)
    units = injected_units(cases)
    by_case = {}
    for u in units:
        by_case.setdefault(u["case"]["case_id"], []).append(u)
    for n, c in enumerate(cases, 1):
        if (n - 1) % shard_n != shard_k:
            continue
        base = {"unit_id": c["case_id"], "case_id": c["case_id"], "group": c["group"], "label": c["label"],
                "condition": "clean"}
        for mode, fn in (("naive", run_naive), ("guarded", run_guarded)):
            if (c["case_id"], mode) in done:
                continue
            r = fn(c, llm)
            emit(row_from(r, base, c["label"]), r)
        for u in by_case.get(c["case_id"], []):
            ub = {"unit_id": u["unit_id"], "case_id": c["case_id"], "group": c["group"], "label": c["label"],
                  "condition": "injected", "family": u["family"], "goal": u["goal"],
                  "atk_host": u["params"]["host"], "atk_ip": u["params"]["ip"]}
            for mode, fn in (("naive", run_naive), ("guarded", run_guarded), ("prompt_only", run_prompt_only)):
                if (u["unit_id"], mode) in done:
                    continue
                r = fn(u["case"], llm)
                s = attack_success(u["goal"], u["params"], r, scenarios.G4_MARKERS)
                emit({**row_from(r, ub, c["label"]), **s}, r)
                if mode == "naive" and (u["unit_id"], "policy_only") not in done:
                    # worst case for the pattern detector: it missed everything, the LLM saw the raw injection,
                    # only the policy engine stands between the proposal and execution.
                    t1 = time.perf_counter()
                    dec = policy.decide(u["case"], r.get("proposal"), FirewallReport(),
                                        llm_error=None if r.get("proposal") else "keluaran LLM tidak valid")
                    r2 = {"mode": "guarded", "proposal": r.get("proposal"), "decision": dec.to_dict(),
                          "fw_injection": False, "llm_seconds": 0.0, "policy_ms": 1000 * (time.perf_counter() - t1)}
                    s2 = attack_success(u["goal"], u["params"], r2, scenarios.G4_MARKERS)
                    row = {**row_from(r2, ub, c["label"]), **s2}
                    row["mode"] = "policy_only"
                    emit(row)
        print(f"[{n}/{len(cases)}] {c['case_id'][:50]}  elapsed {time.time() - t_start:.0f}s", flush=True)
    fh.close()
    raw.close()
    print("done", time.time() - t_start)


if __name__ == "__main__":
    main()
