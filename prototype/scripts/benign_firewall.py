"""PRAREG v4 bagian B: laju tanda palsu firewall pada SEMUA teks bebas asli di 121 rekaman OTRF.

Log OTRF tidak memuat injeksi prompt, jadi setiap field yang ditandai firewall = tanda palsu.
Teks field TIDAK ditulis ke disk (string Mimikatz/Empire memicu Defender); yang disimpan hanya hitungan, kode
pola, nama rekaman, posisi event, dan nama field.
Run: .venv\\Scripts\\python -I scripts\\benign_firewall.py
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from perisai.firewall import scan_text  # noqa: E402
from perisai.logs import FREE_TEXT_FIELDS, load_events  # noqa: E402

OUT = ROOT / "results" / "benign"


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    zips = sorted((ROOT / "data" / "otrf" / "zips").iterdir())
    n_ev = n_ev_text = n_fields = 0
    flagged, codes, by_field = [], Counter(), Counter()
    for z in zips:
        for i, ev in enumerate(load_events(z)):
            n_ev += 1
            fs = [f for f in FREE_TEXT_FIELDS if f in ev]
            if fs:
                n_ev_text += 1
            for f in fs:
                n_fields += 1
                by_field[f] += 1
                c, _, _ = scan_text(str(ev[f]))
                if c:
                    flagged.append({"rekaman": z.name, "posisi": i, "field": f, "kode": c, "panjang": len(str(ev[f]))})
                    codes.update(c)
    ev_flag = len({(r["rekaman"], r["posisi"]) for r in flagged})
    summary = {"rekaman": len(zips), "event": n_ev, "event_dengan_teks_bebas": n_ev_text, "field_teks_bebas": n_fields,
               "field_per_jenis": dict(by_field), "field_ditandai": len(flagged), "event_ditandai": ev_flag,
               "laju_tanda_palsu_field": len(flagged) / n_fields if n_fields else None,
               "laju_tanda_palsu_event": ev_flag / n_ev_text if n_ev_text else None,
               "rekaman_dengan_tanda": len({r["rekaman"] for r in flagged}), "kode": dict(codes), "daftar": flagged}
    (OUT / "summary.json").write_text(json.dumps(summary, indent=1, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({k: v for k, v in summary.items() if k != "daftar"}, indent=1))


if __name__ == "__main__":
    main()
