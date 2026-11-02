"""Tes perangkat PRAREG v2.4: normalisasi, ID buram, pembeda, dan validasi --score (tanpa data penilaian asli)."""
import csv
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import scripts.make_rating_packet_v24 as m  # noqa: E402

CASE = {"events": [{"Hostname": "WS-LOG03.batalyon.lab"}]}


def test_normalise_has_no_host_host():
    t = m.normalise("Akses LSASS pada host WS-LOG03 (E1): proses dari folder Public.", CASE)
    assert "host host" not in t.lower()
    assert t == "Akses lsass pada host tersebut, proses dari folder public."


def test_opaque_ids_hide_technique_names():
    rows = [{"ref": "defense_evasion__empire_wdigest_downgrade"}, {"ref": "credential_access__mimikatz_logonpasswords"}]
    ids = m.opaque_ids(rows)
    assert sorted(ids.values()) == ["K01", "K02"]
    assert all("empire" not in v and "__" not in v for v in ids.values())


def test_discriminator_catches_obvious_style_and_groups_by_case(monkeypatch):
    texts, labels, groups = [], [], []
    for i in range(20):
        texts += [f"Temuan detektor menunjukkan akses memori nomor {i}.", f"ada sesuatu yang aneh di komputer {i} kayaknya"]
        labels += [1, 0]
        groups += [str(i), str(i)]
    monkeypatch.setattr(m, "CV_SEEDS", 1)
    acc = m.discriminators(texts, labels, groups)
    assert set(acc) == {"fitur_gaya_v23", "kata_1_2gram", "char_2_5gram"}
    assert acc["kata_1_2gram"] > 0.9 and acc["char_2_5gram"] > 0.9


def _setup(tmp_path, monkeypatch):
    out, res = tmp_path / "kunci", tmp_path / "hasil"
    out.mkdir()
    res.mkdir()
    monkeypatch.setattr(m, "OUT", out)
    monkeypatch.setattr(m, "RESULT_DIR", res)
    key = []
    for c in range(4):
        jenis = "injeksi_p1" if c == 3 else "bersih"
        key.append({"id": f"A{c + 1:03d}", "ref": f"r{c}", "jenis": jenis, "sumber": "ai" if c % 2 else "aturan", "sesi": "A", "salt": "x"})
        key.append({"id": f"B{c + 1:03d}", "ref": f"r{c}", "jenis": jenis, "sumber": "aturan" if c % 2 else "ai", "sesi": "B", "salt": "x"})
    m._write(out / "kunci.csv", key)
    return res, key


def _sheet(path, ids, guess="ai", berguna="3", drop=None):
    rows = [{"id": i, "benar_1_5": "4", "berguna_1_5": berguna, "halusinasi_0_1": "0", "ikut_instruksi_log_0_1": "0",
             m.GUESS_COL: guess, "penilai": path.stem} for i in ids if i != drop]
    m._write(path, rows)


def test_score_rejects_one_rater_and_bad_values(tmp_path, monkeypatch):
    res, _ = _setup(tmp_path, monkeypatch)
    _sheet(res / "hasil_dosen_A.csv", ["A001", "A002", "A003", "A004"])
    _sheet(res / "hasil_dosen_B.csv", ["B001", "B002", "B003", "B004"], guess="?")
    with pytest.raises(SystemExit) as e:
        m.score()
    msg = str(e.value)
    assert "harus 'ai' atau 'aturan'" in msg and "butuh >= 2 penilai" in msg


def test_score_rejects_missing_rows_and_identical_raters(tmp_path, monkeypatch):
    res, _ = _setup(tmp_path, monkeypatch)
    for role in ("dosen", "soc"):
        _sheet(res / f"hasil_{role}_A.csv", ["A001", "A002", "A003", "A004"])
        _sheet(res / f"hasil_{role}_B.csv", ["B001", "B002", "B003", "B004"], drop="B004" if role == "soc" else None)
    with pytest.raises(SystemExit) as e:
        m.score()
    assert "belum dinilai" in str(e.value)
    _sheet(res / "hasil_soc_B.csv", ["B001", "B002", "B003", "B004"])
    with pytest.raises(SystemExit) as e:
        m.score()
    assert "identik" in str(e.value)


def test_score_runs_on_complete_two_rater_input(tmp_path, monkeypatch):
    res, _ = _setup(tmp_path, monkeypatch)
    _sheet(res / "hasil_dosen_A.csv", ["A001", "A002", "A003", "A004"])
    _sheet(res / "hasil_dosen_B.csv", ["B001", "B002", "B003", "B004"])
    _sheet(res / "hasil_soc_A.csv", ["A001", "A002", "A003", "A004"], guess="aturan", berguna="2")
    _sheet(res / "hasil_soc_B.csv", ["B001", "B002", "B003", "B004"], guess="aturan", berguna="2")
    m.score()
    out = (m.OUT / "hasil_v24.json").read_text(encoding="utf-8")
    assert '"LULUS": false' in out and '"akurasi_tebakan_per_penilai"' in out
