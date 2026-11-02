"""Triase log Windows asli dari baris perintah -> laporan CSIRT + audit berantai hash.

    .venv\\Scripts\\python -I triase.py --input security.xml [--input sysmon.xml] [--llm] [--window 15]
    .venv\\Scripts\\python -I triase.py --verify results\\triase\\<waktu>\\audit.jsonl

Ekspor log (PowerShell, di PC sendiri):
    wevtutil qe Security /c:500 /rd:true /f:xml > security.xml
    wevtutil qe Microsoft-Windows-Sysmon/Operational /c:500 /rd:true /f:xml > sysmon.xml
Tanpa --llm (bawaan): mode aturan, < 1 detik. Dengan --llm: model dicek hash-nya dulu; hash salah -> mode aturan.
Keputusan memakai v1.2: kategori/aksi dari aturan (isolasi butuh bukti cukup), LLM hanya DRAF AI yang dijaga, aksi berisiko
menunggu persetujuan.
Keluaran ditulis ke results\\triase\\<waktu>\\ (laporan.md, audit.jsonl, kasus.json); folder ini tidak masuk git.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from perisai import firewall, importer, laporan  # noqa: E402
from perisai.audit import AuditLog  # noqa: E402
from perisai.pipeline import run_guarded  # noqa: E402
from perisai.v12 import decide_v12  # noqa: E402


def _args(flag: str) -> list[str]:
    return [sys.argv[i + 1] for i, a in enumerate(sys.argv[:-1]) if a == flag]


def _rel(p: Path) -> str:
    try:
        return str(p.resolve().relative_to(ROOT))
    except ValueError:
        return str(p)


def triage(paths: list[Path], use_llm: bool = False, window: int = 15, out_dir: Path | None = None,
           llm=None) -> dict:
    now = datetime.now(timezone.utc)
    out_dir = out_dir or ROOT / "results" / "triase" / now.strftime("%Y%m%dT%H%M%SZ")
    out_dir.mkdir(parents=True, exist_ok=True)
    events = [e for p in paths for e in importer.read_file(p)]
    groups = importer.to_cases(events, window_minutes=window, source=", ".join(p.name for p in paths))
    # Kelompok tanpa temuan aturan bukan insiden: tidak dibuat kasus (v1.1 akan memberi kategori bawaan dan
    # mengusulkan isolasi). Pengecualian: ada instruksi di teks log, karena itu sendiri mencurigakan.
    cases = [c for c in groups if not c["tanpa_temuan"] or firewall.inspect_case(c).injection]
    check = {"status": "tidak dipakai (mode aturan)"}
    if use_llm and llm is None:
        from perisai.integrity import load_checked_llm
        llm, check = load_checked_llm()
    elif llm is not None:
        check = {"status": "LLM diberikan pemanggil (tes)"}
    audit = AuditLog(out_dir / "audit.jsonl")
    items = []
    for c in cases:
        r = run_guarded(c, llm, audit)
        p = r.get("proposal")
        d = decide_v12(c, p, firewall.inspect_case(c), None if p else (r.get("error") or "LLM dimatikan"))
        ts = datetime.now(timezone.utc).isoformat(timespec="seconds")
        audit.append(c["case_id"], "keputusan_v12", {k: d[k] for k in ("verdict", "final_action", "kategori",
                                                                        "warnings", "final_status", "draf_ai")}, ts)
        items.append({"case": c, "decision": d})
    v = audit.verify()
    run = {"waktu": now.isoformat(timespec="seconds"), "sumber": ", ".join(_rel(p) for p in paths),
           "n_event": len(events), "llm": "Qwen2.5-1.5B lokal" if llm else "mati (mode aturan)",
           "model_check": check["status"], "audit_path": _rel(out_dir / "audit.jsonl"),
           "n_tanpa_temuan": len(groups) - len(cases)}
    md = laporan.render(run, items, v, audit.entries())
    (out_dir / "laporan.md").write_text(md, encoding="utf-8")
    (out_dir / "kasus.json").write_text(json.dumps([{"case_id": i["case"]["case_id"], "sha256": i["case"]["sha256"],
                                                     "keputusan": i["decision"]} for i in items],
                                                   ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    return {"out_dir": out_dir, "n_event": len(events), "n_case": len(cases), "n_tanpa_temuan": run["n_tanpa_temuan"],
            "audit": v, "items": items}


def main() -> None:
    if "--verify" in sys.argv:
        v = AuditLog(Path(_args("--verify")[0])).verify()
        print(f"audit {v['entries']} entri, utuh={v['ok']}, head={v['head']}")
        for p in v["problems"][:10]:
            print("  masalah:", p)
        raise SystemExit(0 if v["ok"] else 1)
    paths = [Path(p) for p in _args("--input")]
    if not paths:
        raise SystemExit(__doc__)
    window = int((_args("--window") or ["15"])[0])
    res = triage(paths, use_llm="--llm" in sys.argv, window=window)
    print(f"{res['n_event']} event -> {res['n_case']} kasus (+{res['n_tanpa_temuan']} kelompok tanpa temuan aturan); "
          f"audit utuh={res['audit']['ok']}")
    for it in res["items"]:
        d = it["decision"]
        print(f"  {it['case']['case_id'][:60]:<60} {d['kategori']:<22} {d['final_action']['jenis']:<12} {d['final_status']}")
    print("laporan:", res["out_dir"] / "laporan.md")


if __name__ == "__main__":
    main()
