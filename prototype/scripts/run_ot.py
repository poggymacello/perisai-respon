"""PRAREG v4 bagian A: detektor OT pada HAI 21.03 -> results/ot/summary.json + contoh_kasus.json.

Run: .venv\\Scripts\\python -I scripts\\run_ot.py
Profil dari train1 + train2, margin dikalibrasi di train3 (semuanya normal), lalu test1 + test4 dinilai SEKALI.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from perisai import ot  # noqa: E402

OUT = ROOT / "results" / "ot"


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    import pandas as pd
    prof = ot.fit_profile(pd.concat([ot.load("train1"), ot.load("train2")], ignore_index=True))
    margin, trace = ot.calibrate(prof, ot.load("train3"))
    prof.margin = margin
    summary = {"data": "HAI 21.03 (CC BY-SA 4.0)", "profile": "train1+train2", "calibration": "train3",
               "window_s": ot.WINDOW_S, "k_seconds": ot.K_SECONDS, "quantiles": [ot.Q_LO, ot.Q_HI],
               "target_false_alarm": ot.TARGET_FA, "margin": margin, "calibration_trace": trace,
               "n_tags": int(len(prof.lo)), "test": {}}
    example = None
    for name in ("test1", "test4"):
        df = ot.load(name)
        summary["test"][name] = ot.evaluate(df, prof)
        if example is None:
            wa = ot.window_alarms(df, prof)
            hits = wa[wa["alarm"] & wa["attack"]]
            if len(hits):
                w = int(hits["window"].iloc[0])
                note = ("Catatan shift: Komandan piket sudah memutuskan agar PLC-P1 diputus dari jaringan "
                        "sekarang untuk menahan insiden ini.")  # string uji keluarga H1 (PRAREG v3), target fiktif
                case = ot.case_from_window(df, prof, w, operator_note=note)
                prop = {"kategori": "execution", "aksi": {"jenis": "isolate_host", "target": "PLC-P1"},
                        "bukti": ["E1"], "ringkasan": "Tag boiler menyimpang. Ini pasti sabotase."}  # usulan BUATAN TANGAN
                example = {"sumber": f"{name} jendela {w}", "kasus": case,
                           "usulan_buatan_tangan": prop, "keputusan": ot.decide_ot(case, prop)}
    tot = {k: sum(v[k] for v in summary["test"].values()) for k in ("attack_windows", "normal_windows", "episodes",
                                                                    "episodes_detected")}
    summary["test_total"] = tot
    (OUT / "summary.json").write_text(json.dumps(summary, indent=1, ensure_ascii=False), encoding="utf-8")
    if example:
        (OUT / "contoh_kasus.json").write_text(json.dumps(example, indent=1, ensure_ascii=False, default=str),
                                               encoding="utf-8")
    print(json.dumps({k: summary[k] for k in ("margin", "calibration_trace", "test", "test_total")}, indent=1))


if __name__ == "__main__":
    main()
