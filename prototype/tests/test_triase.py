"""Tes importer log asli, laporan CSIRT, cek hash model (fixture sintetis, tanpa LLM)."""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from perisai import importer, integrity  # noqa: E402
from perisai.audit import AuditLog  # noqa: E402
import triase  # noqa: E402

FIX = ROOT / "tests" / "fixtures" / "contoh_wevtutil.xml"


def test_wevtutil_xml_is_parsed_into_normalised_events():
    evs = importer.read_file(FIX)
    assert len(evs) == 5
    assert evs[0]["EventID"] == 10 and evs[0]["Hostname"] == "WS-LOG03.batalyon.lab"
    assert evs[0]["TargetImage"].endswith("lsass.exe") and evs[1]["LogonType"] == "3"


def test_doctype_is_rejected(tmp_path):
    p = tmp_path / "x.xml"
    p.write_text('<!DOCTYPE a [<!ENTITY b "c">]><Event></Event>', encoding="utf-8")
    with pytest.raises(ValueError):
        importer.read_file(p)


def test_events_grouped_per_host_and_window():
    cases = importer.to_cases(importer.read_file(FIX), window_minutes=15)
    assert [c["primary_host"].split(".")[0] for c in cases] == ["WS-LOG03", "SRV-ARSIP02", "WS-ADM01"]
    assert cases[2]["tanpa_temuan"] and not cases[0]["tanpa_temuan"]


def test_triage_report_and_audit(tmp_path):
    res = triase.triage([FIX], out_dir=tmp_path)
    assert res["n_case"] == 2 and res["n_tanpa_temuan"] == 1 and res["audit"]["ok"]
    d0 = res["items"][0]["decision"]
    assert "INJEKSI_TERDETEKSI" in d0["warnings"] and d0["final_action"]["jenis"] == "escalate"
    md = (tmp_path / "laporan.md").read_text(encoding="utf-8")
    assert "Abaikan" not in md, "teks bebas log tidak boleh disalin ke laporan"
    assert "bukti isolasi kurang" in md, "satu event 7045 tidak boleh langsung diusulkan isolasi (v1.2)"
    assert res["items"][1]["decision"]["final_action"]["jenis"] == "escalate" and res["audit"]["head"] in md
    assert AuditLog(tmp_path / "audit.jsonl").verify()["ok"]


def test_model_hash_mismatch_means_no_llm(tmp_path):
    fake = tmp_path / "qwen2.5-1.5b-instruct-q3_k_m.gguf"
    fake.write_bytes(b"bukan model")
    llm, chk = integrity.load_checked_llm(fake)
    assert llm is None and not chk["ok"] and "TIDAK COCOK" in chk["status"]
    assert integrity.check_model(tmp_path / "tidak-ada.gguf")["status"] == "model tidak ada"
