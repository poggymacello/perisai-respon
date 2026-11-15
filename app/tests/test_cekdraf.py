"""Tes cek silang draf AI terhadap kategori aturan (perisai_app/cekdraf.py dan alur /api/kasus/{id}/draf-ai).

LLM asli tidak dipakai: LLM palsu mengembalikan JSON tetap, sehingga alur aplikasi (penjaga draf v1.2.2, cek silang,
audit, tampilan, laporan) diuji secara deterministik.
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

APP = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(APP))

from perisai_app import cekdraf  # noqa: E402
from perisai_app.api import create_app  # noqa: E402

H = {"X-Perisai": "1"}
# Draf asli yang tampil di screenshot 02 (Qwen2.5-1.5B, kasus WS-KEU02 berkategori aturan execution).
DRAF_SS02 = "Pencurian kredensial melalui PowerShell unduh-jalankan, dengan instruksi terdeteksi dalam log."


# ------------------------------------------------------------------ fungsi murni
def test_mismatch_flagged():
    r = cekdraf.check_text(DRAF_SS02, "execution", {"execution"}, ["EX01"])
    assert r["status"] == "BERTENTANGAN" and r["label"] == "Bertentangan dengan temuan aturan"
    assert [b["kategori"] for b in r["bertentangan"]] == ["credential_access"]
    assert r["bertentangan"][0]["attack"] == "TA0006"
    assert "EX01" in r["alasan"] and "TA0002 Execution" in r["alasan"] and "tetap dari aturan" in r["alasan"]
    # istilah Inggris, kunci mesin, dan ID ATT&CK juga dikenali
    for t in ("Possible lateral movement to the file server.", "Kategori: credential_access.",
              "Aktivitas ini cocok dengan TA0010 dan eksfiltrasi data."):
        assert cekdraf.check_text(t, "execution", {"execution"})["status"] == "BERTENTANGAN", t


def test_match_not_flagged():
    r = cekdraf.check_text("Eksekusi kode lewat PowerShell terenkode pada WS-KEU02.", "execution", {"execution"})
    assert r["status"] == "SESUAI" and not r["bertentangan"]
    # kategori kedua yang didukung aturan lain yang terpicu di kasus yang sama tidak dianggap bertentangan
    r = cekdraf.check_text("Pencurian kredensial dari LSASS lalu pergerakan lateral lewat PsExec.",
                           "credential_access", {"credential_access", "lateral_movement"})
    assert r["status"] == "SESUAI"


def test_no_category_not_flagged():
    for t in ("PowerShell terenkode dijalankan dari WINWORD.EXE pada WS-KEU02.",
              "Kasus dieskalasi ke analis untuk ditinjau.",  # "eskalasi" = eskalasi ke analis, bukan taktik
              ""):
        r = cekdraf.check_text(t, "execution", {"execution"})
        assert r["status"] == "TANPA_KATEGORI" and r["label"] == "Tidak menyebut kategori", t


def test_negated_or_preventive_mention_not_flagged():
    for t in ("Tidak ada tanda pergerakan lateral dari host ini.", "Pergerakan lateral tidak terdeteksi.",
              "Belum terlihat indikasi pencurian kredensial.", "Isolasi perlu ditimbang untuk mencegah eksfiltrasi."):
        r = cekdraf.check_text(t, "execution", {"execution"})
        assert r["status"] == "TANPA_KATEGORI" and r["diabaikan_negasi"], t
    # negasi di klausa lain tidak menyelamatkan klaim di klausa berikutnya
    r = cekdraf.check_text("Tidak ada log yang dihapus, namun terjadi pencurian kredensial.", "execution", {"execution"})
    assert r["status"] == "BERTENTANGAN"


# ------------------------------------------------------------------ alur aplikasi dengan LLM palsu
class FakeLLM:
    def __init__(self, ringkasan: str):
        self.ringkasan = ringkasan

    def complete(self, system: str, user: str):
        out = {"kategori": "credential_access", "ringkasan": self.ringkasan,
               "aksi": {"jenis": "escalate", "target": None}, "bukti": ["E1"], "keyakinan": 0.7}
        return json.dumps(out), {"seconds": 0.01, "prompt_tokens": 10, "completion_tokens": 10}


@pytest.fixture()
def llm_client(tmp_path, monkeypatch):
    monkeypatch.setenv("PERISAI_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("PERISAI_MODEL", str(tmp_path / "tidak-ada.gguf"))
    app = create_app(mode="desktop", root=tmp_path)
    svc = app.state.llm
    orig = svc.status
    monkeypatch.setattr(svc, "status", lambda: orig() | {"tersedia": True, "alasan": None})
    holder = {"text": DRAF_SS02}
    monkeypatch.setattr(svc, "get_llm", lambda stage=None: FakeLLM(holder["text"]))
    with TestClient(app, base_url="http://127.0.0.1") as c:
        c.root, c.holder = tmp_path, holder
        assert c.post("/api/sampel", headers=H).status_code == 200
        yield c


def _keu02(c) -> dict:
    return next(k for k in c.get("/api/kasus").json()["kasus"] if k["host"].startswith("WS-KEU02"))


def _make_draft(c, kid: str) -> dict:
    job = c.post(f"/api/kasus/{kid}/draf-ai", headers=H).json()
    for _ in range(200):
        j = c.get(f"/api/tugas/{job['id']}").json()
        if j["status"] in ("selesai", "gagal"):
            break
        time.sleep(0.05)
    assert j["status"] == "selesai", j
    return c.get(f"/api/kasus/{kid}").json()


def _audit(c) -> list[dict]:
    sid = c.get("/api/status").json()["sesi"]["id"]
    return [json.loads(x) for x in (c.root / "sesi" / sid / "audit.jsonl").read_text(encoding="utf-8").splitlines()]


def test_api_flags_contradicting_draft_and_writes_audit(llm_client):
    k = _keu02(llm_client)
    assert k["kategori"] == "execution"
    d = _make_draft(llm_client, k["id"])
    assert d["draf"]["draf_ai"].startswith("Pencurian kredensial")  # draf tetap terlihat, tidak disembunyikan
    cek = d["draf"]["cek_silang"]
    assert cek["status"] == "BERTENTANGAN" and cek["label"] == "Bertentangan dengan temuan aturan"
    assert cek["kategori_aturan"] == "execution" and cek["bertentangan"][0]["kategori"] == "credential_access"
    # kategori dan aksi tetap dari aturan
    assert d["keputusan"]["kategori"] == "execution" and d["keputusan"]["aksi_akhir"]["jenis"] == "escalate"
    assert d["ringkas"]["attack"]["id"] == "TA0002"
    assert "DRAF_AI_BERTENTANGAN" in d["ringkas"]["peringatan"] and d["ringkas"]["cek_draf"] == "BERTENTANGAN"
    # entri audit: sesudah keputusan_v12 draf ini, rantai tetap utuh
    ents = [e for e in _audit(llm_client) if e["case_id"] == d["kasus"]["case_id"]]
    kinds = [e["kind"] for e in ents]
    assert kinds[-2:] == ["keputusan_v12", "cek_silang_draf"]
    p = ents[-1]["payload"]
    assert p["status"] == "BERTENTANGAN" and p["bertentangan"] == ["credential_access"]
    assert p["keputusan_berubah"] is False and "tetap dari aturan" in p["alasan"]
    assert cek["audit_seq"] == ents[-1]["seq"]
    assert any(e["kind"] == "cek_silang_draf" for e in d["audit"])
    assert llm_client.post("/api/audit/verifikasi", headers=H).json()["ok"]
    md = llm_client.get("/api/laporan").json()["markdown"]
    assert "DITANDAI: bertentangan dengan temuan aturan" in md


def test_api_matching_draft_not_flagged(llm_client):
    llm_client.holder["text"] = "Eksekusi kode lewat PowerShell terenkode yang dijalankan dari WINWORD.EXE."
    k = _keu02(llm_client)
    d = _make_draft(llm_client, k["id"])
    assert d["draf"]["draf_ai"], d["draf"]
    assert d["draf"]["cek_silang"]["status"] == "SESUAI"
    assert "DRAF_AI_BERTENTANGAN" not in d["ringkas"]["peringatan"]
    last = [e for e in _audit(llm_client) if e["kind"] == "cek_silang_draf"][-1]
    assert last["payload"]["status"] == "SESUAI"
    assert "DITANDAI" not in llm_client.get("/api/laporan").json()["markdown"]


def test_api_no_category_draft_not_flagged(llm_client):
    llm_client.holder["text"] = "PowerShell terenkode dijalankan dari WINWORD.EXE pada host ini."
    d = _make_draft(llm_client, _keu02(llm_client)["id"])
    assert d["draf"]["cek_silang"]["status"] == "TANPA_KATEGORI"
    assert "DRAF_AI_BERTENTANGAN" not in d["ringkas"]["peringatan"]
