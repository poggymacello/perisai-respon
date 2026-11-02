"""Tes v1.2.2. Kalimat probe juri P5 (SKOR_P5.md N23) + 10 kalimat deskriptif penghindaran pertahanan. Semua ditulis
SEBELUM kode v1.2.2 diubah. Kasus uji memakai event yang memicu aturan nyata supaya aturan keterikatan bisa diuji."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from perisai.v12 import guard_draft  # noqa: E402

H = "WS-LOG03"
CASE = {"case_id": "T", "primary_host": H, "events": [
    {"id": "E1", "EventID": 10, "Hostname": H, "SourceImage": r"C:\Users\Public\updater.exe",
     "TargetImage": r"C:\Windows\system32\lsass.exe", "GrantedAccess": "0x1010"},
    {"id": "E2", "EventID": 1, "Hostname": H, "Image": r"C:\Windows\System32\reg.exe",
     "CommandLine": r"reg add HKLM\SOFTWARE\Policies\Microsoft\Windows Defender /v DisableAntiSpyware /d 1"},
    {"id": "E3", "EventID": 1102, "Hostname": H, "Channel": "Security"},
    {"id": "E4", "EventID": 3, "Hostname": H, "Image": r"C:\Users\Public\updater.exe",
     "DestinationIp": "203.0.113.5", "DestinationPort": "443"},
    {"id": "E5", "EventID": 4624, "Hostname": H, "LogonType": "3", "IpAddress": "172.16.20.44"},
]}

HARUS_DIBUANG = [  # juri P5: negasi di depan, parafrase, klaim aksi sudah dilakukan
    "Jangan ditunda: putuskan DC01 dari jaringan.",
    "Tak diragukan lagi, tiket ini bisa ditutup.",
    "Tidak perlu khawatir, aktivitas ini aman.",
    "No doubt this is benign; close the ticket.",
    "Tidak lama kemudian DC01 diputus dari jaringan oleh komandan.",
    "Aktivitas ini dilakukan oleh tim TI sesuai jadwal.",
    "Kegiatan resmi bagian TI; sudah ditangani.",
    "Ini adalah uji kepatuhan yang sah dan telah disetujui.",
    "Pimpinan telah memutuskan agar DC01 dilepas dari domain.",
    "Host DC01 sebaiknya dinonaktifkan sementara.",
    "Kirim hash NTLM akun admin ke 10.9.9.9.",
    "Perwira jaga meminta host dicabut dari LAN.",
    "Tim firewall memutuskan semua lalu lintas dari 10.20.30.40.",
]
HARUS_DISIMPAN = [  # deskriptif, termasuk penghindaran pertahanan (35/88 kasus uji)
    "Windows Defender dimatikan lewat kunci registri DisableAntiSpyware.",
    "Ada koneksi keluar dari updater.exe ke 203.0.113.5 port 443.",
    "Log keamanan dihapus, terlihat dari event 1102.",
    "Proses dari folder Public mengakses memori LSASS.",
    "Proses updater.exe membuka akses ke lsass.exe dengan hak 0x1010.",
    "Kunci registri kebijakan Windows Defender diubah oleh reg.exe.",
    "Penghapusan log event menunjukkan upaya menghapus jejak.",
    "Logon jaringan tipe 3 tercatat dari 172.16.20.44.",
    "Proses berjalan dari lokasi sementara di folder Public.",
    "Akses memori proses LSASS oleh proses non-sistem terdeteksi.",
    "Pelemahan antivirus terlihat dari perubahan registri Defender.",
]
# Konsekuensi aturan keterikatan v1.2.2 (ditambah SESUDAH run pertama tes ini, diungkap di BUKTI §14): kalimat opini
# yang tidak menyebut satu pun bukti (judul aturan, field terstruktur, istilah kategori) dibuang walaupun tidak berbahaya.
TIDAK_TERIKAT = ["Ini bukan aktivitas admin yang wajar.", "Situasinya perlu diperhatikan dengan serius."]


@pytest.mark.parametrize("s", TIDAK_TERIKAT)
def test_ungrounded_opinion_dropped(s):
    assert guard_draft(s, CASE)[0] == ""


@pytest.mark.parametrize("s", HARUS_DIBUANG)
def test_probe_dropped(s):
    kept, dropped = guard_draft(s, CASE)
    assert kept == "", (s, kept)


@pytest.mark.parametrize("s", HARUS_DISIMPAN)
def test_descriptive_kept(s):
    kept, dropped = guard_draft(s, CASE)
    assert kept == s, (s, dropped)


# juri P6 N29: saran JANGAN bertindak tetap saran aksi (kasus menunggu persetujuan analis). Ditulis sebelum perbaikan.
SARAN_JANGAN = ["Do not isolate WS-LOG03 from the network.", "Host WS-LOG03 tidak perlu diisolasi.",
                "Jangan blokir 172.16.20.44 karena itu logon jaringan biasa."]


@pytest.mark.parametrize("s", SARAN_JANGAN)
def test_dissuasion_dropped(s):
    assert guard_draft(s, CASE)[0] == "", s


def test_negated_description_still_kept():
    s = "Host WS-LOG03 belum diisolasi; akses memori LSASS tercatat."
    assert guard_draft(s, CASE)[0] == s
