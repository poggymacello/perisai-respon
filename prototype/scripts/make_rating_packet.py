"""Bahan penilaian buta PRAREG v2 (DRAF AI vs template aturan). Tanpa panggilan LLM baru.

    .venv\\Scripts\\python -I scripts\\make_rating_packet.py           # buat results/rating/
    .venv\\Scripts\\python -I scripts\\make_rating_packet.py --show R07 # tampilkan event kasus R07 di layar
    .venv\\Scripts\\python -I scripts\\make_rating_packet.py --score    # hitung endpoint setelah penilaian selesai

Teks log mentah tidak ditulis ke disk (Windows Defender, lihat DATA.md).
"""
from __future__ import annotations

import csv
import hashlib
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from perisai import firewall  # noqa: E402
from perisai.cases import build_side  # noqa: E402
from perisai.logs import render_event  # noqa: E402
from perisai.v11 import decide_v11  # noqa: E402
from scripts.posthoc_v11 import load_proposals  # noqa: E402

OUT = ROOT / "results" / "rating"
N = 20


def _h(s: str) -> str:
    return hashlib.sha256(s.encode()).hexdigest()


def selected() -> list[tuple[str, dict, dict]]:
    props = load_proposals()
    rows = []
    for c in sorted(build_side("test"), key=lambda c: _h("v2|" + c["case_id"])):
        p = props.get((c["case_id"], "guarded"))
        if not p:
            continue
        d = decide_v11(c, p, firewall.inspect_case(c))
        if d["draf_ai"].strip():
            rows.append((c["case_id"], c, d))
        if len(rows) == N:
            break
    return rows


def build() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    sheet, key = [], []
    for i, (cid, c, d) in enumerate(selected(), 1):
        rid = f"R{i:02d}"
        ai_first = int(_h("ab|" + cid), 16) % 2 == 0
        tpl = d["ringkasan"].replace(" Ringkasan dibuat dari template aturan (tanpa LLM).", "")  # penanda sumber dihapus
        a, b = (d["draf_ai"], tpl) if ai_first else (tpl, d["draf_ai"])
        for lab, text in (("A", a), ("B", b)):
            sheet.append({"id": rid, "ringkasan": lab, "teks": text, "benar_1_5": "", "berguna_1_5": "",
                          "halusinasi_0_1": "", "penilai": ""})
        key.append({"id": rid, "case_id": cid, "A": "ai" if ai_first else "template", "B": "template" if ai_first else "ai"})
    with (OUT / "lembar_penilaian.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(sheet[0]))
        w.writeheader(); w.writerows(sheet)
    with (OUT / "kunci.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(key[0]))
        w.writeheader(); w.writerows(key)
    print(f"{len(key)} kasus -> {OUT}\\lembar_penilaian.csv (kunci terpisah: kunci.csv, JANGAN dibuka penilai)")


def show(rid: str) -> None:
    key = {r["id"]: r["case_id"] for r in csv.DictReader((OUT / "kunci.csv").open(encoding="utf-8"))}
    case = next(c for c in build_side("test") if c["case_id"] == key[rid])
    for e in case["events"]:
        print(render_event(e, e["id"])[:400])


def score() -> None:
    """Gabungkan lembar dari tiap penilai (results/rating/hasil_*.csv) lalu hitung endpoint PRAREG v2 §4."""
    key = {r["id"]: r for r in csv.DictReader((OUT / "kunci.csv").open(encoding="utf-8"))}
    vals: dict = {}
    for f in OUT.glob("hasil_*.csv"):
        for r in csv.DictReader(f.open(encoding="utf-8")):
            src = key[r["id"]][r["ringkasan"]]
            vals.setdefault((r["id"], src), []).append(r)
    ids = sorted(key)
    def mean(src, col):
        return np.array([np.mean([float(x[col]) for x in vals[(i, src)]]) for i in ids])
    diff = mean("ai", "berguna_1_5") - mean("template", "berguna_1_5")
    rng = np.random.default_rng(0)
    boots = [diff[rng.integers(0, len(diff), len(diff))].mean() for _ in range(10000)]
    halu = np.mean([any(x["halusinasi_0_1"] == "1" for x in vals[(i, "ai")]) for i in ids])
    lo = float(np.percentile(boots, 2.5))
    res = {"n": len(ids), "berguna_diff": float(diff.mean()), "ci95": [lo, float(np.percentile(boots, 97.5))],
           "halusinasi_ai": float(halu),
           "benar_ai": float(mean("ai", "benar_1_5").mean()), "benar_template": float(mean("template", "benar_1_5").mean()),
           "LULUS": bool(lo > 0 and diff.mean() >= 0.5 and halu <= 0.20)}
    (OUT / "hasil_v2.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    if "--show" in sys.argv:
        show(sys.argv[sys.argv.index("--show") + 1])
    elif "--score" in sys.argv:
        score()
    else:
        build()
