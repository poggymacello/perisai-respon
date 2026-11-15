"""Tes API PERISAI-RESPON (aplikasi). Jalankan dari folder app/:

    .venv\\Scripts\\python -I -m pytest -q -p no:cacheprovider tests
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

APP = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(APP))

from perisai_app import engine  # noqa: E402,F401  (memastikan perisai bisa diimpor)
from perisai_app.api import create_app  # noqa: E402
from perisai_app.paths import sample_dir  # noqa: E402

H = {"X-Perisai": "1"}
FIXTURE = APP.parent / "prototype" / "tests" / "fixtures" / "contoh_wevtutil.xml"


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("PERISAI_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("PERISAI_MODEL", str(tmp_path / "tidak-ada.gguf"))
    app = create_app(mode="desktop", root=tmp_path)
    with TestClient(app, base_url="http://127.0.0.1") as c:
        c.root = tmp_path
        yield c


@pytest.fixture()
def loaded(client):
    r = client.post("/api/sampel", headers=H)
    assert r.status_code == 200, r.text
    return client


def _case_by_host(client, host_prefix, status=None):
    for k in client.get("/api/kasus").json()["kasus"]:
        if k["host"].startswith(host_prefix) and (status is None or k["status_mesin"] == status):
            return k
    raise AssertionError(host_prefix)


def _audit_file(client) -> Path:
    sid = client.get("/api/status").json()["sesi"]["id"]
    return client.root / "sesi" / sid / "audit.jsonl"


# ------------------------------------------------------------------ impor + daftar
def test_import_sample_and_list(loaded):
    d = loaded.get("/api/kasus").json()
    assert d["hitung"]["total"] == 10
    assert d["hitung"]["injeksi"] == 3
    assert d["hitung"]["menunggu"] == 2
    assert d["impor"][0]["n_event"] == 22 and d["impor"][0]["n_kelompok_tanpa_temuan"] == 1
    dc = _case_by_host(loaded, "DC01")
    assert dc["aset_terlindungi"] and dc["aksi"]["jenis"] == "escalate"
    ops = _case_by_host(loaded, "WS-OPS07", "MENUNGGU_PERSETUJUAN")
    assert ops["aksi"] == {"jenis": "isolate_host", "target": "WS-OPS07.batalyon.lab"}
    assert ops["attack"]["id"] == "TA0006"


def test_case_detail_marks_injection(loaded):
    k = _case_by_host(loaded, "WS-KEU02")
    d = loaded.get(f"/api/kasus/{k['id']}").json()
    assert d["firewall"]["injeksi"]
    e1 = next(e for e in d["event"] if e["id"] == "E1")
    assert e1["ditandai"][0]["field"] == "CommandLine"
    assert "INJEKSI_TERDETEKSI" in d["keputusan"]["peringatan"]
    assert d["keputusan"]["aksi_akhir"]["jenis"] == "escalate"
    assert {o["keputusan"] for o in d["opsi_tinjauan"]} == {"tutup", "catatan"}
    assert loaded.get("/api/kasus/K-9999").status_code == 404


def test_upload_wevtutil_xml(client):
    with FIXTURE.open("rb") as fh:
        r = client.post("/api/impor", files=[("berkas", ("contoh_wevtutil.xml", fh, "application/xml"))],
                        data={"jendela": "15"}, headers=H)
    assert r.status_code == 200, r.text
    d = r.json()
    assert (d["n_event"], d["n_kasus"], d["n_kelompok_tanpa_temuan"]) == (5, 2, 1)
    assert d["berkas"][0]["sha256"] and d["berkas"][0]["nama"] == "contoh_wevtutil.xml"
    # berkas unggahan tidak disimpan
    assert not any((client.root / "tmp").glob("*/*")) if (client.root / "tmp").exists() else True


def test_upload_winlogbeat_json(client):
    p = sample_dir() / "contoh_winlogbeat.json"
    r = client.post("/api/impor", files=[("berkas", (p.name, p.read_bytes(), "application/json"))], headers=H)
    assert r.status_code == 200, r.text
    assert r.json()["n_event"] == 2 and r.json()["n_kasus"] == 1


def test_upload_rejections(client):
    bad = b'<?xml version="1.0"?><!DOCTYPE x [<!ENTITY a "b">]><Event></Event>'
    r = client.post("/api/impor", files=[("berkas", ("x.xml", bad, "application/xml"))], headers=H)
    assert r.status_code == 422 and "DOCTYPE" in r.json()["detail"]
    r = client.post("/api/impor", files=[("berkas", ("x.exe", b"MZ", "application/octet-stream"))], headers=H)
    assert r.status_code == 415
    r = client.post("/api/impor", files=[("berkas", ("kosong.xml", b"", "application/xml"))], headers=H)
    assert r.status_code == 422


def test_parity_with_triase_cli(client, tmp_path):
    """Keputusan aplikasi = keputusan prototype/triase.py untuk berkas yang sama."""
    sys.path.insert(0, str(APP.parent / "prototype"))
    import triase
    res = triase.triage([FIXTURE], out_dir=tmp_path / "cli")
    cli = {it["case"]["case_id"]: it["decision"] for it in res["items"]}
    with FIXTURE.open("rb") as fh:
        client.post("/api/impor", files=[("berkas", ("contoh_wevtutil.xml", fh, "application/xml"))], headers=H)
    rows = client.get("/api/kasus").json()["kasus"]
    assert {r["case_id"] for r in rows} == set(cli)
    for r in rows:
        d = client.get(f"/api/kasus/{r['id']}").json()["keputusan"]
        c = cli[r["case_id"]]
        assert d["aksi_akhir"] == c["final_action"]
        assert d["status"] == c["final_status"]
        assert d["kategori"] == c["kategori"]
        assert d["peringatan"] == c["warnings"]
        assert d["alasan_asli"] == c["reasons"]  # teks asli mesin tetap tersedia


# ------------------------------------------------------------------ persetujuan analis
def test_approve_writes_audit_and_is_not_executed(loaded):
    k = _case_by_host(loaded, "WS-OPS07", "MENUNGGU_PERSETUJUAN")
    r = loaded.post(f"/api/kasus/{k['id']}/tinjauan", json={"keputusan": "setujui", "analis": "Lettu A. Pratama",
                                                            "catatan": "cek hash di sandbox lokal"}, headers=H)
    assert r.status_code == 200, r.text
    assert r.json()["dieksekusi"] is False
    ents = [json.loads(x) for x in _audit_file(loaded).read_text(encoding="utf-8").splitlines()]
    last = ents[-1]
    assert last["kind"] == "tindakan_analis" and last["payload"]["keputusan"] == "setujui"
    assert last["payload"]["dieksekusi"] is False and last["payload"]["analis"] == "Lettu A. Pratama"
    assert last["payload"]["aksi_diusulkan"] == {"jenis": "isolate_host", "target": "WS-OPS07.batalyon.lab"}
    assert loaded.post("/api/audit/verifikasi", headers=H).json()["ok"]
    # sudah diputus: tidak bisa disetujui/ditolak lagi, catatan tetap boleh
    again = loaded.post(f"/api/kasus/{k['id']}/tinjauan", json={"keputusan": "tolak", "analis": "Lettu A. Pratama",
                                                                "catatan": "ganti keputusan"}, headers=H)
    assert again.status_code == 409
    note = loaded.post(f"/api/kasus/{k['id']}/tinjauan", json={"keputusan": "catatan", "analis": "Serka B",
                                                               "catatan": "operator sudah dihubungi"}, headers=H)
    assert note.status_code == 200
    assert _case_by_host(loaded, "WS-OPS07", "MENUNGGU_PERSETUJUAN")["status_tinjauan"] == "DISETUJUI"


def test_reject_and_close_rules(loaded):
    k = _case_by_host(loaded, "SRV-FILE01")
    r = loaded.post(f"/api/kasus/{k['id']}/tinjauan", json={"keputusan": "tolak", "analis": "Kapten C",
                                                            "catatan": "jadwal pencadangan resmi"}, headers=H)
    assert r.status_code == 200 and r.json()["tinjauan"]["status"] == "DITOLAK"
    esc = _case_by_host(loaded, "WS-KEU02")
    bad = loaded.post(f"/api/kasus/{esc['id']}/tinjauan", json={"keputusan": "setujui", "analis": "Kapten C",
                                                                "catatan": "x x x"}, headers=H)
    assert bad.status_code == 409  # tidak ada aksi berisiko untuk disetujui
    ok = loaded.post(f"/api/kasus/{esc['id']}/tinjauan", json={"keputusan": "tutup", "analis": "Kapten C",
                                                               "catatan": "instruksi uji internal"}, headers=H)
    assert ok.status_code == 200 and ok.json()["tinjauan"]["status"] == "DITUTUP_ANALIS"
    kinds = [json.loads(x)["kind"] for x in _audit_file(loaded).read_text(encoding="utf-8").splitlines()]
    assert kinds.count("tindakan_analis") == 2


def test_review_validation(loaded):
    k = _case_by_host(loaded, "WS-OPS07", "MENUNGGU_PERSETUJUAN")
    r = loaded.post(f"/api/kasus/{k['id']}/tinjauan", json={"keputusan": "setujui", "analis": "", "catatan": "ok ok"}, headers=H)
    assert r.status_code == 422
    r = loaded.post(f"/api/kasus/{k['id']}/tinjauan", json={"keputusan": "eksekusi", "analis": "AB", "catatan": "ok ok"}, headers=H)
    assert r.status_code == 422


# ------------------------------------------------------------------ audit
def test_audit_verify_detects_tampering(loaded):
    k = _case_by_host(loaded, "WS-OPS07", "MENUNGGU_PERSETUJUAN")
    loaded.post(f"/api/kasus/{k['id']}/tinjauan", json={"keputusan": "setujui", "analis": "AB", "catatan": "abc"}, headers=H)
    assert loaded.post("/api/audit/verifikasi", headers=H).json()["ok"]
    # uji perubahan pada SALINAN: salinan rusak, berkas asli tetap utuh
    t = loaded.post("/api/audit/uji-perubahan", headers=H).json()
    assert t["hasil"]["ok"] is False and t["asli"]["ok"] is True
    # ubah berkas ASLI: verifikasi gagal
    f = _audit_file(loaded)
    lines = f.read_text(encoding="utf-8").splitlines()
    e = json.loads(lines[-1])
    e["payload"]["keputusan"] = "tolak"
    lines[-1] = json.dumps(e, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    f.write_text("\n".join(lines) + "\n", encoding="utf-8")
    v = loaded.post("/api/audit/verifikasi", headers=H).json()
    assert v["ok"] is False and any("hash" in p for p in v["problems"])
    # hapus satu entri di tengah: juga terdeteksi
    lines = lines[:3] + lines[4:]
    f.write_text("\n".join(lines) + "\n", encoding="utf-8")
    assert loaded.post("/api/audit/verifikasi", headers=H).json()["ok"] is False


def test_audit_list_and_export(loaded):
    d = loaded.get("/api/audit").json()
    assert d["verifikasi"]["ok"] and d["jumlah"] == len(d["entri"]) == 41
    assert d["entri"][0]["kind"] == "impor_log"
    r = loaded.get("/api/audit/ekspor")
    assert r.status_code == 200 and "attachment" in r.headers["content-disposition"]
    assert len(r.text.splitlines()) == 41


# ------------------------------------------------------------------ laporan
def test_report_download(loaded):
    k = _case_by_host(loaded, "WS-OPS07", "MENUNGGU_PERSETUJUAN")
    loaded.post(f"/api/kasus/{k['id']}/tinjauan", json={"keputusan": "setujui", "analis": "Lettu D", "catatan": "ok lanjut"}, headers=H)
    md = loaded.get("/api/laporan/unduh?format=md")
    assert md.status_code == 200 and md.headers["content-disposition"].endswith('.md"')
    assert md.text.startswith("# Laporan Insiden PERISAI-RESPON")
    assert "Tindakan analis" in md.text and "Lettu D" in md.text
    assert "Ignore all previous" not in md.text and "Abaikan semua" not in md.text  # teks bebas log tidak disalin
    html = loaded.get("/api/laporan/unduh?format=html")
    assert html.status_code == 200 and "<table>" in html.text and "<script" not in html.text.lower()
    assert loaded.get("/api/laporan").json()["html"].startswith("<h1>")


def test_engine_no_llm_reason_is_mapped_not_hidden(loaded):
    """Jalur v1 menulis "LLM dimatikan"; di aplikasi kalimat itu dipetakan, teks aslinya tetap ada."""
    from perisai_app.engine import REASON_RULES_LLM_OFF, REASON_RULES_LLM_ON, REPORT_RULES_LLM_OFF
    k = _case_by_host(loaded, "WS-KEU02")
    d = loaded.get(f"/api/kasus/{k['id']}").json()["keputusan"]
    assert d["alasan_asli"][0] == "LLM dimatikan"
    assert d["alasan"][0] == REASON_RULES_LLM_OFF  # fixture client: model tidak ada -> LLM tidak aktif
    assert "LLM dimatikan" not in d["alasan"]
    assert d["alasan"][1:] == d["alasan_asli"][1:]  # alasan lain tidak disentuh
    md = loaded.get("/api/laporan").json()["markdown"]
    assert f'{REPORT_RULES_LLM_OFF} (teks asli mesin: "LLM dimatikan")' in md
    assert "- LLM dimatikan" not in md
    ents = [json.loads(x) for x in _audit_file(loaded).read_text(encoding="utf-8").splitlines()]
    assert any(e["kind"] == "keputusan_policy" and e["payload"]["reasons"][0] == "LLM dimatikan" for e in ents)
    from perisai_app import engine as eng
    assert eng.reason_text("LLM dimatikan", True) == REASON_RULES_LLM_ON
    assert eng.reason_text("kategori dari template aturan (EX01)", True) == "kategori dari template aturan (EX01)"


def test_report_requires_cases(client):
    assert client.get("/api/laporan").status_code == 409


# ------------------------------------------------------------------ policy, OT, status
def test_simulation_policy_blocks_protected_host(loaded):
    k = _case_by_host(loaded, "WS-KEU02")
    r = loaded.post(f"/api/kasus/{k['id']}/simulasi", json={"jenis": "isolate_host", "target": "DC01", "bukti": ["E1"],
                                                            "detektor_aktif": False}, headers=H).json()
    assert r["putusan_usulan"] == "BLOCK" and "terlindungi" in r["alasan_usulan"][-1]
    r = loaded.post(f"/api/kasus/{k['id']}/simulasi", json={"jenis": "hapus_berkas", "bukti": []}, headers=H).json()
    assert r["putusan_usulan"] == "BLOCK"
    before = loaded.get(f"/api/kasus/{k['id']}").json()["keputusan"]
    assert before["aksi_akhir"]["jenis"] == "escalate"  # simulasi tidak mengubah kasus


def test_ot_rejects_plc_isolation(client):
    d = client.get("/api/ot").json()
    assert d["keputusan"]["verdict"] == "BLOCK"
    assert d["keputusan"]["final_action"]["jenis"] == "escalate"
    assert d["tag"][0]["tag"] == "P1_FT01" and d["tag"][0]["normal"] == [180.0, 350.0]
    assert d["firewall"]["injeksi"] is False  # catatan HMI lolos pola; aturan aset OT yang menolak


def test_status_rules_mode_and_integrity(client):
    s = client.get("/api/status").json()
    assert s["aplikasi"]["versi"] == "1.0.0" and s["mesin"]["versi"] == "1.2.2"
    assert s["mesin"]["integritas"]["ok"] is True
    assert s["mode_analisis"] == "aturan" and s["llm"]["tersedia"] is False
    assert s["jaringan"]["lokal_saja"] is True
    r = client.post(f"/api/kasus/K-0001/draf-ai", headers=H)
    assert r.status_code == 404
    client.post("/api/sampel", headers=H)
    r = client.post("/api/kasus/K-0001/draf-ai", headers=H)
    assert r.status_code == 409 and "LLM" in r.json()["detail"]


def test_bench_rules(loaded):
    r = loaded.post("/api/uji-kinerja", headers=H).json()
    assert r["n"] == 300 and r["median_ms"] > 0


def test_new_session_keeps_old(loaded):
    old = loaded.get("/api/status").json()["sesi"]["id"]
    loaded.post("/api/sesi/baru", headers=H)
    new = loaded.get("/api/status").json()["sesi"]
    assert new["id"] != old and new["n_kasus"] == 0
    assert (loaded.root / "sesi" / old / "audit.jsonl").exists()


# ------------------------------------------------------------------ keamanan server lokal
def test_mutation_requires_header(client):
    r = client.post("/api/sampel")
    assert r.status_code == 403


def test_foreign_host_rejected(client):
    assert client.get("/api/status", headers={"host": "perisai.attacker.example"}).status_code == 400


def test_frontend_served_with_csp(client):
    r = client.get("/")
    assert r.status_code == 200 and "PERISAI-RESPON" in r.text
    assert "connect-src 'self'" in r.headers["content-security-policy"]
    js = client.get("/js/app.js")
    assert js.status_code == 200 and "javascript" in js.headers["content-type"]
    assert "http://" not in r.text and "https://" not in r.text  # tidak ada CDN


def test_demo_mode_rejects_upload(tmp_path, monkeypatch):
    monkeypatch.setenv("PERISAI_DATA_DIR", str(tmp_path))
    app = create_app(mode="demo", root=tmp_path, bind="0.0.0.0")
    with TestClient(app, base_url="https://demo.example") as c:
        d = c.get("/api/kasus").json()  # pengunjung baru: data contoh dimuat otomatis
        assert d["hitung"]["total"] == 10
        assert "perisai_demo" in c.cookies
        with FIXTURE.open("rb") as fh:
            r = c.post("/api/impor", files=[("berkas", ("a.xml", fh, "application/xml"))], headers=H)
        assert r.status_code == 403 and "demo" in r.json()["detail"].lower()
        st = c.get("/api/status").json()
        assert st["mode"] == "demo" and st["kemampuan"]["unggah"] is False and st["llm"]["tersedia"] is False
        assert c.post("/api/kasus/K-0001/draf-ai", headers=H).status_code == 409
        assert c.post("/api/keluar", headers=H).status_code == 409
    # pengunjung lain mendapat sesi terpisah
    with TestClient(app, base_url="https://demo.example") as c2:
        c2.get("/api/kasus")
        k = c2.get("/api/kasus").json()["kasus"][0]
        assert k["status_tinjauan"] is None


@pytest.mark.skipif(os.name != "nt", reason="wevtutil hanya ada di Windows")
def test_evtx_conversion(client, tmp_path):
    from perisai_app import evtx
    src = tmp_path / "app.evtx"
    q = subprocess.run(["wevtutil", "epl", "Application", str(src), "/q:*[System[TimeCreated[timediff(@SystemTime) <= 604800000]]]"],
                       capture_output=True)
    if q.returncode != 0 or not src.exists():
        pytest.skip("tidak bisa mengekspor .evtx contoh di mesin ini")
    out = tmp_path / "app.xml"
    evtx.evtx_to_xml(src, out)
    text = out.read_text(encoding="utf-8").lstrip()
    if not text:
        pytest.skip("log Application 7 hari terakhir kosong")
    assert text.startswith("<Event")
    r = client.post("/api/impor", files=[("berkas", ("app.evtx", src.read_bytes(), "application/octet-stream"))], headers=H)
    assert r.status_code in (200, 422), r.text  # log Application biasanya tanpa temuan aturan
    if r.status_code == 200:
        assert r.json()["n_event"] >= 1

def test_sample_load_is_idempotent(loaded):
    n = len(loaded.get("/api/kasus").json()["kasus"])
    r = loaded.post("/api/sampel", headers=H)
    assert r.status_code == 200, r.text
    assert len(loaded.get("/api/kasus").json()["kasus"]) == n == 10


def test_demo_sample_click_does_not_duplicate(tmp_path, monkeypatch):
    monkeypatch.setenv("PERISAI_DATA_DIR", str(tmp_path))
    app = create_app(mode="demo", root=tmp_path, bind="0.0.0.0")
    with TestClient(app, base_url="https://demo.example") as c:
        assert len(c.get("/api/kasus").json()["kasus"]) == 10
        assert c.post("/api/sampel", headers=H).status_code == 200
        assert len(c.get("/api/kasus").json()["kasus"]) == 10
