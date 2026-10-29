"""Split dev/test OTRF datasets by ATT&CK technique (technique-disjoint). Uses ONLY metadata
(file names, metadata YAML), never event contents. Deterministic: sha256(group) mod 100 < 35 -> dev.

Run: .venv\\Scripts\\python -I scripts\\make_split.py
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
ZIPS = ROOT / "data" / "otrf" / "zips"
META = ROOT / "data" / "otrf" / "metadata"
DEV_PCT = 35


def main() -> None:
    link2meta = {}
    for f in sorted(META.glob("*.yaml")):
        d = yaml.safe_load(f.read_text(encoding="utf-8"))
        for fl in d.get("files") or []:
            if fl.get("type") == "Host":
                techs = [str(a.get("technique")) + (("." + str(a["sub-technique"])) if a.get("sub-technique") else "")
                         for a in d.get("attack_mappings") or []]
                link2meta[os.path.basename(fl["link"])] = {"meta_id": d["id"], "techniques": techs,
                                                           "title": d.get("title", "")}
    rows = []
    for z in sorted(os.listdir(ZIPS)):
        tactic, base = z.split("__", 1)
        meta = link2meta.get(base)
        if meta and meta["techniques"]:
            group = meta["techniques"][0]
        else:
            group = "nometa:" + base
        h = int(hashlib.sha256(group.encode()).hexdigest()[:8], 16) % 100
        rows.append({"dataset": z, "label": tactic, "group": group, "meta_id": meta["meta_id"] if meta else None,
                     "title": meta["title"] if meta else None, "side": "dev" if h < DEV_PCT else "test"})
    out = ROOT / "frozen" / "split.json"
    out.write_text(json.dumps(rows, indent=1, ensure_ascii=False), encoding="utf-8")
    from collections import Counter
    print("total", len(rows), Counter(r["side"] for r in rows))
    for side in ("dev", "test"):
        print(side, dict(Counter(r["label"] for r in rows if r["side"] == side)))
    dg = {r["group"] for r in rows if r["side"] == "dev"}
    tg = {r["group"] for r in rows if r["side"] == "test"}
    assert not (dg & tg), "group leakage"
    print("groups dev/test", len(dg), len(tg))


if __name__ == "__main__":
    sys.exit(main())
