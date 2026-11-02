"""triase.py juga menerima JSON-lines bergaya Winlogbeat (temuan juri P3 #13)."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import triase  # noqa: E402


def test_winlogbeat_jsonl(tmp_path):
    evs = [{"@timestamp": "2026-10-29T02:01:05Z", "winlog": {"event_id": 10, "channel": "Microsoft-Windows-Sysmon/Operational",
            "computer_name": "WS-LOG03.batalyon.lab", "event_data": {"SourceImage": r"C:\Users\Public\x.exe",
            "TargetImage": r"C:\Windows\system32\lsass.exe", "GrantedAccess": "0x1010"}}}]
    p = tmp_path / "wlb.json"
    p.write_text("\n".join(json.dumps(e) for e in evs), encoding="utf-8")
    res = triase.triage([p], out_dir=tmp_path / "out")
    assert res["n_case"] == 1 and res["audit"]["ok"]
    d = res["items"][0]["decision"]
    assert d["kategori"] == "credential_access" and d["final_status"] == "MENUNGGU_PERSETUJUAN"
