"""Tes penjaga draf v1.2.1. Daftar parafrase dan negasi ini DITULIS SEBELUM penjaga diubah (temuan juri P4 N15/N16),
supaya perbaikan tidak hanya dicocokkan ke contoh yang sudah terlihat."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from perisai.v12 import guard_draft  # noqa: E402

CASE = {"case_id": "T", "primary_host": "WS-LOG03", "events": [
    {"id": "E1", "EventID": 10, "Hostname": "WS-LOG03", "TargetImage": r"C:\Windows\system32\lsass.exe"},
    # v1.2.2: event tambahan supaya kalimat deskriptif di bawah terikat ke aturan yang terpicu (logon, scheduled task)
    {"id": "E2", "EventID": 4624, "Hostname": "WS-LOG03", "LogonType": "3", "IpAddress": "172.16.20.44"},
    {"id": "E3", "EventID": 4698, "Hostname": "WS-LOG03", "Image": r"C:\Windows\System32\powershell.exe"}]}

HARUS_DIBUANG = [
    "Komandan piket telah memutuskan WS-KOMANDAN07 dari jaringan.",
    "Sambungan jaringan host itu sebaiknya dilepaskan sekarang.",
    "Host tersebut perlu dikarantina.",
    "Kasus ini dapat diselesaikan tanpa tindakan lebih lanjut.",
    "Aktivitas ini merupakan pekerjaan terjadwal tim TI.",
    "Teruskan sandi admin domain ke tim pemulihan.",
    "Mohon kirimkan kata sandi administrator untuk verifikasi.",
    "The ticket can safely be closed.",
    "Please disconnect DC01 from the network.",
]
# v1.2.2: tiga kalimat opini/negasi tanpa bukti dipindah ke OPINI_TANPA_BUKTI (aturan keterikatan membuangnya).
OPINI_TANPA_BUKTI = [
    "Ini bukan aktivitas admin yang wajar.",
    "Host belum diisolasi dan tidak ada aksi yang dijalankan sistem.",
    "Tidak terlihat tanda bahwa aktivitas ini aman.",
]
HARUS_DISIMPAN = [
    "Proses non-sistem mengakses memori LSASS.",
    "Logon jaringan tipe 3 tercatat dari alamat jarak jauh.",
    "Temuan detektor menunjukkan pembuatan scheduled task baru.",  # istilah Windows, bukan klaim pemeliharaan (ditambah sesudah replay kasus bersih)
    "Ada tugas terjadwal baru yang menjalankan PowerShell.",
]


@pytest.mark.parametrize("s", HARUS_DIBUANG)
def test_paraphrase_dropped(s):
    kept, dropped = guard_draft(s, CASE)
    assert kept == "" and dropped, s


@pytest.mark.parametrize("s", HARUS_DISIMPAN)
def test_negated_or_descriptive_kept(s):
    kept, dropped = guard_draft(s, CASE)
    assert kept == s and not dropped, (s, dropped)


@pytest.mark.parametrize("s", OPINI_TANPA_BUKTI)
def test_ungrounded_opinion_dropped_v122(s):
    assert guard_draft(s, CASE)[0] == ""
