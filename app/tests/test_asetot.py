"""Tes penjaga aset OT di jalur IT (perisai_app/asetot.py).

Skenario dari temuan reviewer internal: WS-OPS07 di log contoh diganti nama menjadi HMI-POMPA01. Mesin v1.2.2
(tanpa penjaga aplikasi) mengusulkan isolate_host ke HMI itu; aplikasi harus mengeskalasi ke insinyur proses.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

APP = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(APP))

from perisai_app import asetot, engine  # noqa: E402
from perisai_app.api import create_app  # noqa: E402
from perisai_app.paths import sample_dir  # noqa: E402

H = {"X-Perisai": "1"}


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("PERISAI_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("PERISAI_MODEL", str(tmp_path / "tidak-ada.gguf"))
    app = create_app(mode="desktop", root=tmp_path)
    with TestClient(app, base_url="http://127.0.0.1") as c:
        c.root = tmp_path
        yield c


def _hmi_log() -> bytes:
    return (sample_dir() / "contoh_batalyon.xml").read_bytes().replace(b"WS-OPS07", b"HMI-POMPA01")


def _upload(c, data: bytes, name: str = "batalyon_hmi.xml") -> None:
    r = c.post("/api/impor", files=[("berkas", (name, data, "application/xml"))], headers=H)
    assert r.status_code == 200, r.text


def _audit(c) -> list[dict]:
    sid = c.get("/api/status").json()["sesi"]["id"]
    return [json.loads(x) for x in (c.root / "sesi" / sid / "audit.jsonl").read_text(encoding="utf-8").splitlines()]


def test_prefix_match():
    for h in ("HMI-POMPA01", "plc-genset02.batalyon.lab", "SCADA-01", "Rtu-7", "EWS-ENG01", "SIS-01"):
        assert asetot.match(h), h
    for h in ("WS-OPS07.batalyon.lab", "SRV-FILE01", "HMIX-01", "", None):
        assert asetot.match(h) is None, h


def test_engine_gap_before_and_app_guard_after(client, tmp_path):
    """Sebelum: mesin saja -> isolate_host ke HMI. Sesudah: aplikasi -> eskalasi + entri audit."""
    p = tmp_path / "hmi.xml"
    p.write_bytes(_hmi_log())
    _, cases, _ = engine.parse_files([p], "hmi.xml")
    hmi = next(c for c in cases if c["primary_host"].startswith("HMI-POMPA01"))
    before = engine.decide_v12(hmi, None, engine.firewall.inspect_case(hmi), "LLM dimatikan")
    assert before["final_action"]["jenis"] == "isolate_host"  # celah di jalur IT mesin (tidak diubah)

    _upload(client, _hmi_log())
    row = next(k for k in client.get("/api/kasus").json()["kasus"] if k["host"].startswith("HMI-POMPA01"))
    assert row["aksi"] == {"jenis": "escalate", "target": None} and row["status_mesin"] == "DIESKALASI"
    assert row["aset_terlindungi"] is True
    d = client.get(f"/api/kasus/{row['id']}").json()
    assert any(r.startswith(asetot.REASON) for r in d["keputusan"]["alasan"])
    assert {o["keputusan"] for o in d["opsi_tinjauan"]} == {"tutup", "catatan"}  # tidak ada aksi untuk disetujui
    ents = [e for e in _audit(client) if e["case_id"] == hmi["case_id"]]
    assert [e["kind"] for e in ents][-2:] == ["keputusan_v12", "penjaga_aset_ot"]
    g = ents[-1]["payload"]
    assert g["alasan"] == "aset OT terlindungi: eskalasi ke insinyur proses"
    assert g["aksi_sebelum"]["jenis"] == "isolate_host" and g["aksi_sesudah"]["jenis"] == "escalate"
    assert client.post("/api/audit/verifikasi", headers=H).json()["ok"]
    # simulasi: usulan isolasi ke HMI ditolak walau detektor pola dimatikan
    s = client.post(f"/api/kasus/{row['id']}/simulasi", json={"jenis": "isolate_host", "target": "HMI-POMPA01",
                                                              "bukti": ["E1"], "detektor_aktif": False}, headers=H).json()
    assert s["putusan_usulan"] == "BLOCK" and asetot.REASON in s["alasan_usulan"][-1]
    assert s["aksi_akhir"]["jenis"] == "escalate"


def test_normal_workstation_not_blocked(client):
    client.post("/api/sampel", headers=H)
    row = next(k for k in client.get("/api/kasus").json()["kasus"]
               if k["host"].startswith("WS-OPS07") and k["status_mesin"] == "MENUNGGU_PERSETUJUAN")
    assert row["aksi"] == {"jenis": "isolate_host", "target": "WS-OPS07.batalyon.lab"}
    assert not row["aset_terlindungi"]
    assert not any(e["kind"] == "penjaga_aset_ot" for e in _audit(client))


def test_unit_list_protects_named_host(client):
    (client.root / asetot.UNIT_FILE).write_text("# daftar aset satuan\nWS-OPS07\nPOMPA-*\n", encoding="utf-8")
    assert asetot.match("pompa-utara.batalyon.lab")
    client.post("/api/sampel", headers=H)
    rows = [k for k in client.get("/api/kasus").json()["kasus"] if k["host"].startswith("WS-OPS07")]
    assert rows and all(k["aksi"]["jenis"] != "isolate_host" for k in rows)
    g = [e for e in _audit(client) if e["kind"] == "penjaga_aset_ot"]
    assert g and "daftar satuan" in g[0]["payload"]["cocok"]
