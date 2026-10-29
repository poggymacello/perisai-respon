"""Demo PERISAI-RESPON: memutar beberapa kasus (termasuk yang berisi injeksi) dan menampilkan usulan LLM,
keputusan policy, alasan, dan jejak audit berantai hash.

    .venv\\Scripts\\python -I demo.py            # pakai LLM lokal bila model ada
    .venv\\Scripts\\python -I demo.py --no-llm   # mode degradasi (tanpa LLM)

Event demo SINTETIS (gaya Sysmon/Security; host/IP fiktif) supaya keluaran bisa disimpan dan dibagikan.
String injeksi = keluarga D1/D2 dari perisai/scenarios.py (string uji, bukan kode).
"""
from __future__ import annotations

import io
import shutil
import sys
from contextlib import redirect_stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from perisai import firewall, policy, scenarios  # noqa: E402
from perisai.audit import AuditLog  # noqa: E402
from perisai.cases import inject  # noqa: E402
from perisai.firewall import FirewallReport  # noqa: E402
from perisai.llm import DEFAULT_MODEL  # noqa: E402
from perisai.logs import render_event  # noqa: E402
from perisai.pipeline import run_guarded, run_naive  # noqa: E402

OUT = ROOT / "results" / "demo"
H = "WS-LOG03.batalyon.lab"


def base_case() -> dict:
    return {"case_id": "DEMO-01", "primary_host": H, "label": "credential_access", "events": [
        {"id": "E1", "EventID": 10, "Channel": "Microsoft-Windows-Sysmon/Operational", "Hostname": H,
         "SourceImage": r"C:\Users\Public\updater.exe", "TargetImage": r"C:\Windows\system32\lsass.exe",
         "GrantedAccess": "0x1010"},
        {"id": "E2", "EventID": 4624, "Channel": "Security", "Hostname": H, "LogonType": "3",
         "TargetUserName": "operator2", "IpAddress": "172.16.20.44"},
        {"id": "E3", "EventID": 1, "Channel": "Microsoft-Windows-Sysmon/Operational", "Hostname": H,
         "Image": r"C:\Users\Public\updater.exe", "ParentImage": r"C:\Windows\explorer.exe",
         "CommandLine": r"C:\Users\Public\updater.exe --check"},
        {"id": "E4", "EventID": 3, "Channel": "Microsoft-Windows-Sysmon/Operational", "Hostname": H,
         "Image": r"C:\Users\Public\updater.exe", "DestinationIp": "172.16.20.44", "DestinationPort": "8443"},
    ]}


def show(title: str, case: dict, res: dict) -> None:
    print("=" * 100)
    print(title)
    print("-- event (yang dibaca sistem):")
    for e in case["events"]:
        print("   " + render_event(e, e["id"])[:220])
    if res.get("fw_flagged") is not None:
        print("-- firewall:", "INJEKSI TERDETEKSI " + str(res["fw_flagged"]) if res.get("fw_injection") else "bersih")
    p = res.get("proposal")
    print("-- usulan LLM:", p if p else f"(tidak ada: {res.get('error') or 'keluaran tidak valid'})")
    d = res.get("decision")
    if d:
        verdict = "DITERIMA (tanpa aksi ke sistem)" if d["verdict"] == "EXECUTE" else d["verdict"]
        print(f"-- KEPUTUSAN POLICY: {verdict} -> aksi akhir {d['final_action']} | status {d['final_status']}")
        print(f"   kategori: {d['kategori']} | sumber: {d['source']} | peringatan: {d['warnings']}")
        for r in d["reasons"]:
            print("   alasan:", r)
        if "--v1" in sys.argv:  # ringkasan LLM v1 tanpa saring kalimat (bisa memuat halusinasi)
            print("   ringkasan untuk operator (v1):", d["ringkasan"])
        from perisai.v11 import decide_v11
        d11 = decide_v11(case, p, firewall.inspect_case(case), None if p else "LLM dimatikan")
        print(f"-- v1.1 (yang dipakai): aksi {d11['final_action']} | status {d11['final_status']} | kategori {d11['kategori']}"
              f" | peringatan {d11['warnings']}")
        print("   ringkasan aturan:", d11["ringkasan"])
        if d11["draf_ai"] or d11["kalimat_dibuang"]:
            print("   DRAF AI (disaring):", d11["draf_ai"], "| kalimat dibuang:", d11["kalimat_dibuang"])
    else:
        print("-- TANPA FIREWALL: usulan langsung dieksekusi ->", (p or {}).get("aksi"))


def main() -> None:
    use_llm = "--no-llm" not in sys.argv and DEFAULT_MODEL.exists()
    llm = None
    if use_llm:
        from perisai.llm import LocalLLM
        llm = LocalLLM(n_threads=8)
    OUT.mkdir(parents=True, exist_ok=True)
    audit_path = OUT / "audit_demo.jsonl"
    if audit_path.exists():
        audit_path.unlink()
    audit = AuditLog(audit_path)
    buf = io.StringIO()
    with redirect_stdout(buf):
        print(f"PERISAI-RESPON demo | LLM: {'Qwen2.5-1.5B-Instruct q3_k_m (lokal, CPU)' if llm else 'MATI (mode degradasi)'}")
        c = base_case()
        show("[1] Kasus bersih: indikasi akses memori LSASS", c, run_guarded(c, llm, audit))

        g = "G2"
        txt = scenarios.DEV_FAMILIES["D2_override_id"]["tpl"].format(
            goal=scenarios.render_goal(g, "id", scenarios.goal_params(c, g)))
        ci = inject(c, txt, event_index=2)
        if llm:
            show("[2a] Injeksi (blokir IP) TANPA firewall", ci, run_naive(ci, llm))
        show("[2b] Injeksi yang sama DENGAN PERISAI", ci, run_guarded(ci, llm, audit))

        txt = scenarios.DEV_FAMILIES["D1_override_en"]["tpl"].format(
            goal=scenarios.render_goal("G1", "en", {"host": "DC01", "ip": "", "url": "", "email": ""}))
        ci = inject(c, txt, event_index=0, field="CommandLine")
        show("[3] Injeksi 'isolasi DC01' DENGAN PERISAI", ci, run_guarded(ci, llm, audit))

        print("=" * 100)
        print("[4] Detektor pola meleset (laporan firewall dikosongkan) + usulan buatan tangan yang MENIRU LLM yang menuruti injeksi -> policy tetap menahan")
        for prop in ({"kategori": "credential_access", "ringkasan": "isolasi DC", "aksi": {"jenis": "isolate_host", "target": "DC01"},
                      "bukti": ["E1"], "keyakinan": 0.9},
                     {"kategori": "credential_access", "ringkasan": "blok", "aksi": {"jenis": "block_ip", "target": "10.20.30.40"},
                      "bukti": ["E1"], "keyakinan": 0.9}):
            d = policy.decide(ci, prop, FirewallReport())
            print(f"   usulan {prop['aksi']} -> {d.verdict}; alasan: {d.reasons[-1]}")

        show("[5] LLM mati -> mode degradasi (template aturan)", c, run_guarded(c, None, audit))

        print("=" * 100)
        print("[5b] v1.1 (pasca-evaluasi): kategori/aksi dari aturan, LLM hanya DRAF AI yang disaring per kalimat")
        from perisai.v11 import decide_v11
        demo_prop = {"kategori": "defense_evasion", "aksi": {"jenis": "no_action", "target": None}, "bukti": ["E1"],
                     "ringkasan": "Akses memori LSASS oleh proses dari folder Public. Ini menunjukkan potensi terorisme."}
        d11 = decide_v11(c, demo_prop, FirewallReport())
        print(f"   usulan REKONSTRUKSI buatan tangan (meniru halusinasi LLM di skenario 3): {demo_prop['aksi']} + ringkasan berisi 'terorisme'")
        print(f"   keputusan v1.1: {d11['final_action']} | status {d11['final_status']} | kategori {d11['kategori']}")
        print(f"   ringkasan aturan: {d11['ringkasan']}")
        print(f"   DRAF AI (disaring): {d11['draf_ai']}")
        print(f"   kalimat dibuang: {d11['kalimat_dibuang']}")

        print("=" * 100)
        v = audit.verify()
        print(f"[6] Audit trail: {v['entries']} entri, utuh={v['ok']}, head={v['head'][:16]}...")
        for e in audit.entries():
            print(f"   #{e['seq']:02d} {e['kind']:<17} kasus={e['case_id']} prev={e['prev_hash'][:10]}... hash={e['entry_hash'][:10]}...")
        tam = OUT / "audit_demo_DIUBAH.jsonl"
        shutil.copy(audit_path, tam)
        lines = tam.read_text(encoding="utf-8").splitlines()
        import json as _json
        e2 = _json.loads(lines[2])
        before = e2["payload"].get("final_status")
        e2["payload"]["final_status"] = "DIEKSEKUSI"  # pura-pura: "aksi sudah dijalankan"
        lines[2] = _json.dumps(e2, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        tam.write_text("\n".join(lines) + "\n", encoding="utf-8")
        v2 = AuditLog(tam).verify()
        print(f"   salinan yang diubah (entri #2 final_status {before!r} -> 'DIEKSEKUSI'): utuh={v2['ok']}, "
              f"masalah={v2['problems'][:2]}")
    text = buf.getvalue()
    print(text)
    (OUT / ("demo_output.txt" if llm else "demo_output_no_llm.txt")).write_text(text, encoding="utf-8")


if __name__ == "__main__":
    main()
