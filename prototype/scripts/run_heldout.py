"""PRAREG v3: injeksi keluarga TERTAHAN pada 88 kasus uji. Resumable (baris yang sudah ada dilewati).

Run: .venv\\Scripts\\python -I scripts\\run_heldout.py --shard 0/2 --threads 6   (+ jendela kedua --shard 1/2)
     .venv\\Scripts\\python -I scripts\\run_heldout.py --dry-run                 (LLM palsu, 4 unit DEV, cek kode)
Mode per unit: naive, guarded (v1), policy_only (usulan naive + laporan firewall kosong), v11 (usulan guarded
lewat decide_v11). Hanya naive dan guarded yang memanggil LLM.
"""
from __future__ import annotations

import csv
import hashlib
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from perisai import firewall, policy, scenarios  # noqa: E402
from perisai.cases import build_side, check_against_manifest, inject  # noqa: E402
from perisai.firewall import FirewallReport  # noqa: E402
from perisai.metrics import attack_success  # noqa: E402
from perisai.pipeline import run_guarded, run_naive  # noqa: E402
from perisai.scenarios_heldout import HELDOUT_FAMILIES, render  # noqa: E402
from perisai.v11 import decide_v11  # noqa: E402

OUT = ROOT / "results" / "heldout"
FIELDS = ["unit_id", "case_id", "group", "label", "family", "goal", "atk_host", "atk_ip", "mode", "parse_ok",
          "jenis", "target", "verdict", "final_status", "warnings", "fw_injection", "success", "auto",
          "llm_seconds", "error"]
COMBOS = [(f, g) for f in HELDOUT_FAMILIES for g in scenarios.GOALS]  # 4 x 4 = 16 template


def _h(*p: str) -> int:
    return int(hashlib.sha256("|".join(p).encode()).hexdigest()[:8], 16)


def units_for(cases: list[dict]) -> list[dict]:
    units = []
    for i, c in enumerate(cases):
        for j in range(2):
            fam, goal = COMBOS[(2 * i + j) % len(COMBOS)]
            params = scenarios.goal_params(c, goal)
            ci = inject(c, render(fam, goal, params),
                        event_index=_h(c["case_id"], fam, goal, "heldout") % max(1, len(c["events"])))
            units.append({"unit_id": f"{c['case_id']}#{fam}#{goal}", "case": ci, "family": fam, "goal": goal,
                          "params": params, "base": c})
    return units


def v11_success(goal: str, params: dict, d: dict) -> dict:
    """Seperti metrics.attack_success mode guarded, tetapi untuk G4 teks yang dilihat operator = ringkasan
    aturan + DRAF AI."""
    res = {"mode": "guarded", "decision": {**d, "ringkasan": d["ringkasan"] + " " + (d.get("draf_ai") or "")}}
    return attack_success(goal, params, res, scenarios.G4_MARKERS)


class _FakeLLM:  # dry-run only
    def complete(self, system, user):
        return ('{"kategori": "execution", "ringkasan": "uji", "aksi": {"jenis": "escalate", "target": null}, '
                '"bukti": ["E1"], "keyakinan": 0.5}'), {"seconds": 0.0}


def main() -> None:
    dry = "--dry-run" in sys.argv
    if dry:
        cases = build_side("dev")[:2]
        out = OUT / "dry_run"
    else:
        cases = build_side("test")
        problems = check_against_manifest(cases, json.loads((ROOT / "frozen" / "manifest_test.json").read_text("utf-8")))
        if problems:
            raise SystemExit("test cases differ from frozen manifest: " + "; ".join(problems[:5]))
        out = OUT
    out.mkdir(parents=True, exist_ok=True)
    shard_k, shard_n, threads = 0, 1, 8
    if "--shard" in sys.argv:
        shard_k, shard_n = map(int, sys.argv[sys.argv.index("--shard") + 1].split("/"))
    if "--threads" in sys.argv:
        threads = int(sys.argv[sys.argv.index("--threads") + 1])
    csv_path = out / f"runs_shard{shard_k}.csv"
    raw_path = out / f"raw_shard{shard_k}.jsonl"
    done = set()
    for f in out.glob("runs_shard*.csv"):
        with f.open(encoding="utf-8") as fh0:
            done |= {(r["unit_id"], r["mode"]) for r in csv.DictReader(fh0)}
    new = not csv_path.exists()
    fh = csv_path.open("a", encoding="utf-8", newline="")
    w = csv.DictWriter(fh, fieldnames=FIELDS)
    if new:
        w.writeheader()
    raw = raw_path.open("a", encoding="utf-8")
    if dry:
        llm = _FakeLLM()
    else:
        from perisai.llm import LocalLLM
        llm = LocalLLM(n_threads=threads)

    t0 = time.time()
    units = units_for(cases)
    for n, u in enumerate(units, 1):
        if ((n - 1) // 2) % shard_n != shard_k:  # kedua unit satu kasus di shard yang sama
            continue
        c = u["case"]
        ub = {"unit_id": u["unit_id"], "case_id": c["case_id"], "group": c["group"], "label": c["label"],
              "family": u["family"], "goal": u["goal"], "atk_host": u["params"]["host"], "atk_ip": u["params"]["ip"]}
        results = {}
        for mode, fn in (("naive", run_naive), ("guarded", run_guarded)):
            if (u["unit_id"], mode) in done:
                continue
            r = fn(c, llm)
            results[mode] = r
            s = attack_success(u["goal"], u["params"], r, scenarios.G4_MARKERS)
            d = r.get("decision")
            p = r.get("proposal")
            fa = d["final_action"] if d else ((p or {}).get("aksi") or {})
            w.writerow({**ub, "mode": mode, "parse_ok": p is not None, "jenis": fa.get("jenis"),
                        "target": fa.get("target"), "verdict": d["verdict"] if d else "",
                        "final_status": d["final_status"] if d else "",
                        "warnings": ";".join(d["warnings"]) if d else "", "fw_injection": r.get("fw_injection", ""),
                        **s, "llm_seconds": round(r.get("llm_seconds") or 0.0, 3), "error": r.get("error") or ""})
            raw.write(json.dumps({"unit_id": u["unit_id"], "mode": mode, "raw": r.get("raw"), "proposal": p,
                                  "decision": d}, ensure_ascii=False, default=str) + "\n")
            if mode == "naive" and (u["unit_id"], "policy_only") not in done:
                dec = policy.decide(c, p, FirewallReport(), llm_error=None if p else "keluaran LLM tidak valid")
                r2 = {"mode": "guarded", "decision": dec.to_dict()}
                s2 = attack_success(u["goal"], u["params"], r2, scenarios.G4_MARKERS)
                w.writerow({**ub, "mode": "policy_only", "parse_ok": p is not None, "jenis": dec.final_action["jenis"],
                            "target": dec.final_action.get("target"), "verdict": dec.verdict,
                            "final_status": dec.final_status, "warnings": ";".join(dec.warnings),
                            "fw_injection": False, **s2})
            if mode == "guarded" and (u["unit_id"], "v11") not in done:
                fw = firewall.inspect_case(c)
                d11 = decide_v11(c, p, fw, None if p else "keluaran LLM tidak valid")
                s3 = v11_success(u["goal"], u["params"], d11)
                w.writerow({**ub, "mode": "v11", "parse_ok": p is not None, "jenis": d11["final_action"]["jenis"],
                            "target": d11["final_action"].get("target"), "verdict": d11["verdict"],
                            "final_status": d11["final_status"], "warnings": ";".join(d11["warnings"]),
                            "fw_injection": fw.injection, **s3})
            fh.flush()
            raw.flush()
        print(f"[{n}/{len(units)}] {u['unit_id'][:70]}  elapsed {time.time() - t0:.0f}s", flush=True)
    fh.close()
    raw.close()
    print("done", round(time.time() - t0))


if __name__ == "__main__":
    main()
