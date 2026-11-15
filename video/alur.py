"""Satu sumber untuk video demo PERISAI-RESPON: urutan potongan, teks kartu, dan narasi per potongan.

Dipakai oleh rekam.py (berapa lama tiap keadaan layar ditahan) dan susun.py (urutan potongan, subtitle,
naskah sulih suara, chapter YouTube). Ubah narasi di sini, lalu jalankan ulang susun.py.

Angka di narasi dan kartu hanya dari buku klaim (12-MEGA-PROMPT-KARTIKA-SUBMISI-2nov2026.md, bagian C).
"""

from __future__ import annotations

from dataclasses import dataclass, field

FPS = 30
CPS = 14.0          # kecepatan bicara narasi (karakter per detik); diukur dari suara Edge TTS Ardi 15 Nov 2026
JEDA = 0.2          # jeda antarbaris narasi (detik)
AWAL = 0.5          # narasi mulai sekian detik setelah potongan dimulai
EKOR = 0.5          # sisa diam di akhir potongan


def durasi_baris(teks: str) -> float:
    return max(1.8, len(teks) / CPS + 0.6)


def butuh(narasi: list[str]) -> float:
    """Lama minimum potongan supaya narasinya muat."""
    if not narasi:
        return 0.0
    return AWAL + sum(durasi_baris(t) for t in narasi) + JEDA * (len(narasi) - 1) + EKOR


@dataclass
class Kartu:
    id: str
    jenis: str                  # judul | bagian | bukti | batasan | penutup
    teks: dict
    narasi: list[str] = field(default_factory=list)
    min_detik: float = 2.2


@dataclass
class Rekam:
    id: str                     # nama potongan di rekam.py (penanda awal/akhir di marks.json)
    narasi: list[str] = field(default_factory=list)
    zoom: bool = False          # potong-perbesar ke area yang disorot (diukur saat merekam)
    min_detik: float = 3.0


# ---------------------------------------------------------------------------------------------------------
# Urutan akhir video. Potongan Rekam boleh diambil dari bagian mana saja rekaman (mis. pembuka dingin).
# ---------------------------------------------------------------------------------------------------------
URUTAN: list[Kartu | Rekam] = [
    Kartu("k_judul", "judul", {"judul": "PERISAI-RESPON",
                               "sub": "Triase insiden offline yang tidak bisa disetir isi log"},
          ["PERISAI-RESPON memilah insiden dari log Windows secara offline."], min_detik=4.0),
    Rekam("c_dingin", [
        "Masalahnya, isi log bisa ditulis penyerang.",
        "Di sini penyerang menyelipkan perintah untuk AI di baris PowerShell: isolasi DC01.",
        "Aplikasi menandainya sebagai data, tidak menurutinya, dan menyerahkan kasus ke analis.",
    ], zoom=True),

    Kartu("k_bagian_satuan", "bagian", {"kalimat": "Log satuan tidak boleh keluar ke cloud, dan isinya bisa ditulis penyerang."}),
    Rekam("a_mulai", [
        "Log satuan memuat nama host, akun, dan alamat internal.",
        "Karena itu log tidak boleh dikirim ke layanan AI di cloud.",
    ]),
    Rekam("a_pill", [
        "PERISAI-RESPON berjalan di laptop dan hanya menerima koneksi dari perangkat itu sendiri.",
    ]),
    Rekam("a_jaringan", [
        "Status sistem: alamat 127.0.0.1, akses ke host lain diblokir, tanpa telemetri.",
    ]),
    Rekam("a_model", [
        "Modelnya juga lokal, Qwen2.5 1,5B, dan hash berkasnya dicek sebelum dipakai.",
    ]),
    Rekam("a_mode", [
        "Isi log juga bisa menyetir asisten AI yang membacanya.",
        "Karena itu kategori dan aksi diambil dari aturan.",
        "LLM hanya menulis draf ringkasan, dan hanya kalau analis memintanya.",
    ]),

    Kartu("k_bagian_demo", "bagian", {"kalimat": "Demo dengan log contoh sintetis, dari antrean kasus sampai laporan CSIRT."}),
    Rekam("b_muat", [
        "Kita mulai dari sesi kosong dan memuat log contoh dengan host fiktif.",
    ]),
    Rekam("b_antrean", [
        "Event dikelompokkan menjadi kasus.",
        "Tiap kasus punya kategori ATT&CK, severity, dan status dari mesin aturan.",
    ]),
    Rekam("b_filter_injeksi", [
        "Filter ini menampilkan kasus yang lognya memuat instruksi tersembunyi.",
    ]),
    Rekam("c_banner", [
        "Kasus WS-KEU02. Banner merah menyebut lokasi instruksinya: field CommandLine.",
    ]),
    Rekam("c_inert", [
        "Teks log ditampilkan sebagai teks biasa. Teks itu tidak dijalankan dan tidak disalin ke laporan.",
    ]),
    Rekam("c_keputusan", [
        "Keputusan diambil oleh aturan v1.2.2, bukan oleh LLM, dan alasan policy-nya ditulis satu per satu.",
    ]),
    Rekam("c_draf_mulai", [
        "Draf AI dibuat hanya atas permintaan analis. Waktu tunggunya kami potong.",
    ]),
    Rekam("c_draf_hasil", [
        "Draf ini berlabel bukan dasar keputusan.",
        "Cek silang membandingkan kategori yang disebut draf dengan temuan aturan.",
        "Kalau berbeda, draf ditandai bertentangan dan dicatat di audit. Kategori tetap eksekusi kode dari aturan.",
    ], zoom=True),
    Rekam("d_usulan", [
        "Skenario terburuk: LLM sudah tersetir dan mengusulkan isolasi DC01.",
        "Detektor pola injeksi kami matikan.",
    ]),
    Rekam("d_hasil", [
        "Policy tetap menolak: BLOCK, karena DC01 aset terlindungi.",
        "Aturan ini melihat target aksi, jadi tetap bekerja walau kalimat serangannya tidak dikenali.",
    ], zoom=True),

    Rekam("e_kasus", [
        "Kasus WS-OPS07: proses dari folder Public mengakses LSASS.",
        "Aturan mengusulkan isolasi host, dan statusnya menunggu persetujuan.",
    ]),
    Rekam("e_setujui", [
        "Aksi berisiko tidak berjalan sendiri. Analis menyetujuinya dengan nama dan catatan.",
    ]),
    Rekam("e_tercatat", [
        "Persetujuan itu dicatat, tidak dieksekusi. Aplikasi ini baca-saja.",
    ]),
    Rekam("f_audit", [
        "Setiap langkah masuk jejak audit. Tiap entri memuat hash SHA-256 entri sebelumnya.",
    ]),
    Rekam("f_verifikasi", [
        "Verifikasi menghitung ulang seluruh rantai dari berkas.",
    ]),
    Rekam("f_ubah", [
        "Uji ini mengubah persetujuan tadi menjadi dieksekusi: true di salinan.",
        "Verifikasi salinan langsung gagal, dan berkas aslinya tetap utuh.",
    ], zoom=True),
    Rekam("g_laporan", [
        "Laporan CSIRT disusun dari kasus dan jejak audit, lalu bisa diunduh atau dicetak ke PDF.",
    ]),
    Rekam("g_gulir", [
        "Teks bebas dari log tidak ikut disalin ke laporan.",
    ]),

    Kartu("k_bagian_ot", "bagian", {"kalimat": "Jalur OT: PLC dan HMI tidak pernah diputus oleh sistem."}),
    Rekam("h_ot", [
        "Pada telemetri proses bergaya HAI 21.03, satu tag aliran keluar dari amplop normal.",
    ]),
    Rekam("h_hmi", [
        "Catatan HMI mengaku komandan memerintahkan PLC-P1 diputus. Firewall pola tidak menandainya.",
    ]),
    Rekam("h_keputusan", [
        "Usulan itu tetap ditolak aturan aset OT, karena memutus PLC bisa menghentikan proses fisik.",
        "Kasus dieskalasi ke insinyur proses.",
    ], zoom=True),

    Kartu("k_bagian_bukti", "bagian", {"kalimat": "Hasil uji kami, termasuk yang gagal."}),
    Kartu("k_bukti_p1", "bukti", {
        "judul": "Injeksi lewat log yang berhasil",
        "angka": "16,5 % → 0 %",
        "sub": "176 unit uji. Rencana uji dikunci dengan SHA-256 sebelum dijalankan.",
        "catatan": "Pola deteksi ditulis dengan mengetahui keluarga injeksi yang diuji (in-sample).",
        "sumber": "Sumber: uji prareg tim, 29 Okt 2026 (docs/BUKTI_EVALUASI.md bagian 3)",
    }, [
        "Rencana uji kami kunci dengan SHA-256 sebelum dijalankan.",
        "Pada 176 unit uji, injeksi yang berhasil turun dari 16,5 persen ke 0 persen.",
        "Pola deteksinya dibuat dengan mengetahui keluarga injeksi ini, jadi hasilnya in-sample.",
    ]),
    Kartu("k_bukti_ablasi", "bukti", {
        "judul": "Detektor pola dimatikan, policy tetap menahan",
        "angka": "0,6 %",
        "sub": "1 dari 176 unit uji lolos walau detektor pola dimatikan.",
        "catatan": "",
        "sumber": "Sumber: ablasi, 29 Okt 2026 (docs/BUKTI_EVALUASI.md bagian 4)",
    }, [
        "Dengan detektor pola dimatikan, yang lolos 0,6 persen, satu dari 176.",
    ]),
    Kartu("k_bukti_baru", "bukti", {
        "judul": "Injeksi baru yang ditulis ulang",
        "angka": "0 % terdeteksi pola",
        "sub": "Isolasi dan blokir palsu yang lolos tetap 0.",
        "catatan": "Versi 1 kebobolan 4 dari 176 lewat penutupan kasus. Versi sekarang tidak pernah menutup kasus secara otomatis.",
        "sumber": "Sumber: PRAREG v3, 29 Okt 2026 (docs/BUKTI_EVALUASI.md bagian 11)",
    }, [
        "Injeksi yang ditulis ulang lolos dari pola deteksi: 0 persen terdeteksi.",
        "Tetapi isolasi dan blokir palsu yang lolos tetap 0.",
        "Versi 1 kebobolan 4 dari 176 lewat penutupan kasus; kini kasus tidak pernah ditutup otomatis.",
    ]),
    Kartu("k_bukti_p2", "bukti", {
        "judul": "Uji P2 gagal: LLM kalah dari aturan",
        "angka": "35,2 % vs 50,0 %",
        "sub": "Akurasi menebak taktik: LLM 1,5B lawan aturan.",
        "catatan": "Karena itu kategori dan aksi diambil dari aturan. LLM hanya menulis draf berlabel, dan nilai draf belum terbukti.",
        "sumber": "Sumber: uji prareg tim, 29 Okt 2026 (docs/BUKTI_EVALUASI.md bagian 3)",
    }, [
        "Uji P2 gagal. LLM 1,5B kalah dari aturan dalam menebak taktik, 35,2 lawan 50,0 persen.",
        "Karena itu kategori dan aksi diambil dari aturan.",
    ]),
    Kartu("k_bukti_ot", "bukti", {
        "judul": "Jalur OT dan tanda palsu",
        "angka": "10/10",
        "sub": "Episode serangan HAI 21.03 tertangkap. Alarm palsu 5,4 % dan 0 % di dua berkas uji.",
        "catatan": "Firewall menandai 0 dari 260.351 field teks log asli. PLC dan HMI tidak pernah diputus sistem.",
        "sumber": "Sumber: PRAREG v4, 29 Okt 2026 (docs/BUKTI_EVALUASI.md bagian 10)",
    }, [
        "Di jalur OT, 10 dari 10 episode serangan HAI 21.03 tertangkap.",
        "Alarm palsunya 5,4 persen dan 0 persen di dua berkas uji.",
    ]),

    Kartu("k_bagian_terap", "bagian", {"kalimat": "Penerapan di satuan: laptop biasa, lisensi Rp0, pilot baca-saja."}),
    Rekam("i_kinerja", [
        "Di CPU laptop tanpa GPU, firewall dan policy butuh kurang dari 10 milidetik per kasus.",
        "Dengan LLM, median 28,7 detik per kasus. Tombol ini mengukur ulang di perangkat penguji.",
    ]),
    Rekam("i_lisensi", [
        "Lisensinya Rp0. Qwen2.5 berlisensi Apache-2.0.",
        "Llama tidak dipakai karena lisensinya melarang penggunaan militer.",
    ]),
    Rekam("j_impor", [
        "Untuk pilot, log diekspor dengan wevtutil, atau berkas .evtx diimpor langsung.",
    ]),
    Rekam("j_hasil", [
        "Usulan kami pilot baca-saja di satu satuan.",
        "Aplikasi membaca log dan menulis laporan, tanpa menyentuh sistem.",
    ]),

    Kartu("k_batasan", "batasan", {
        "judul": "Batasan",
        "butir": [
            "Pola injeksi tidak tahan parafrase. Yang menahan aksi palsu adalah aturan struktural policy.",
            "LLM 1,5B kalah dari aturan dalam menebak taktik (P2 gagal).",
            "Nilai draf AI belum terbukti. Penilaian buta sudah dirancang, belum dijalankan.",
            "Exe belum ditandatangani dan baru diuji di Windows 11.",
        ],
    }, [
        "Batasannya: pola injeksi tidak tahan parafrase, dan LLM kecil kalah dari aturan.",
        "Nilai draf AI juga belum terbukti.",
        "Exe belum ditandatangani dan baru diuji di Windows 11.",
    ]),
    Kartu("k_penutup", "penutup", {
        "judul": "PERISAI-RESPON",
        "url": "github.com/poggymacello/perisai-respon",
        "ajak": "Coba sendiri: unduh aplikasi dari halaman rilis repo.",
        "kecil": "Kode, hasil uji, deklarasi alat bantu AI, dan lisensi ada di README.",
    }, [
        "Aplikasi, kode, dan hasil uji ada di tautan ini. Silakan unduh dan coba.",
    ], min_detik=6.0),
]

# Chapter YouTube: (judul, id potongan pertama). Baris pertama harus mulai 00:00.
BAB = [
    ("Masalah: log bisa ditulis penyerang", "k_judul"),
    ("Kenapa penting untuk satuan", "k_bagian_satuan"),
    ("Demo: antrean dan kasus injeksi", "k_bagian_demo"),
    ("Uji policy: isolasi DC01 ditolak", "d_usulan"),
    ("Persetujuan analis, audit, laporan CSIRT", "e_kasus"),
    ("Jalur OT", "k_bagian_ot"),
    ("Hasil uji, termasuk yang gagal", "k_bagian_bukti"),
    ("Penerapan di satuan", "k_bagian_terap"),
    ("Batasan dan tautan", "k_batasan"),
]


def kebutuhan_rekam() -> dict[str, float]:
    """Lama minimum tiap potongan rekaman (detik), dipakai rekam.py untuk menahan layar."""
    return {s.id: max(s.min_detik, butuh(s.narasi)) for s in URUTAN if isinstance(s, Rekam)}
