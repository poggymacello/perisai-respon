"""Dev-only sanity run (NOT the evaluation): a few DEV cases, clean + DEV injection families."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from perisai import scenarios  # noqa: E402
from perisai.cases import build_side, inject  # noqa: E402
from perisai.llm import LocalLLM  # noqa: E402
from perisai.metrics import attack_success  # noqa: E402
from perisai.pipeline import run_guarded, run_naive  # noqa: E402

N = int(sys.argv[1]) if len(sys.argv) > 1 else 4


def main() -> None:
    cases = build_side("dev")[:: max(1, len(build_side("dev")) // N)][:N]
    llm = LocalLLM(n_threads=8)
    out = []
    for c in cases:
        for mode, fn in (("naive", run_naive), ("guarded", run_guarded)):
            r = fn(c, llm)
            out.append({"case": c["case_id"], "label": c["label"], "inj": None, **{k: r.get(k) for k in
                        ("mode", "proposal", "decision", "fw_injection", "llm_seconds")}})
            print(c["case_id"][:40], mode, (r.get("proposal") or {}).get("kategori"), (r.get("proposal") or {}).get("aksi"),
                  r.get("decision", {}).get("final_status") if r.get("decision") else "", flush=True)
        for j, (fam, spec) in enumerate(scenarios.DEV_FAMILIES.items()):
            goal = scenarios.GOALS[(j + cases.index(c)) % 4]
            params = scenarios.goal_params(c, goal)
            text = spec["tpl"].format(goal=scenarios.render_goal(goal, spec["lang"], params))
            ci = inject(c, text, event_index=j)
            for mode, fn in (("naive", run_naive), ("guarded", run_guarded)):
                r = fn(ci, llm)
                s = attack_success(goal, params, r, scenarios.G4_MARKERS)
                out.append({"case": c["case_id"], "inj": fam, "goal": goal, "success": s, **{k: r.get(k) for k in
                            ("mode", "proposal", "decision", "fw_injection", "llm_seconds")}})
                print("  ", fam, goal, mode, s, (r.get("proposal") or {}).get("aksi"), r.get("fw_injection"), flush=True)
    p = ROOT / "results" / "dev_sanity" / "dev_sanity.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(out, indent=1, ensure_ascii=False, default=str), encoding="utf-8")


if __name__ == "__main__":
    main()
