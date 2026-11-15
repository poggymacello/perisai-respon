# PENERAPAN_SATUAN: rencana penerapan PERISAI-RESPON di satuan
### Tim PERISAI Siber Ganesha · 15 Nov 2026 · melengkapi `PROPOSAL.md` §5 dan §6

Dokumen ini menjawab dua pertanyaan: kebutuhan satuan yang mana yang dijawab PERISAI, dan bagaimana alat ini dipasang, dipakai, dan diukur di satuan.

**Aturan baca:**
- Angka tentang PERISAI hanya diambil dari `docs/BUKTI_EVALUASI.md` dan `app/README.md`. Angka di bagian pilot adalah **target usulan**, bukan hasil.
- Kami tidak punya data internal TNI AD dan tidak mengklaim bahwa TNI AD memakai atau meminta alat ini. Semua pernyataan tentang lingkungan satuan diberi label `[ASUMSI]`.
- Webinar 2 (5 Nov 2026) sudah lewat, dan belum ada konfirmasi tentang lingkungan satuan yang tercatat. Setiap `[ASUMSI]` di bawah disertai hal yang bisa mengonfirmasinya.

---

## 1. Peta kebutuhan satuan
Kebutuhan diturunkan dari rujukan publik (daftar lengkap di §5). Kolom "Bukti" menunjuk berkas dan angka yang bisa diperiksa ulang. Kolom "Celah" adalah hal yang belum dijawab.

| # | Ancaman atau kebutuhan (rujukan) | Fitur PERISAI | Bukti (berkas, angka) | Celah |
|---|---|---|---|---|
| 1 | Membangun kapabilitas tanggap insiden yang efektif dan efisien (Perpres 47/2023 Pasal 9 huruf a). Tanggap insiden dilakukan bertahap oleh Tim Tanggap Insiden Siber (TTIS) organisasi, sektor, lalu nasional (Pasal 21 ayat 2) | Triase di tingkat paling bawah: log diolah di posko, keluarannya laporan yang siap diteruskan ke TTIS di atasnya | Laporan Markdown/HTML/PDF dari menu **Laporan CSIRT** (`app/README.md`); contoh `prototype/results/contoh_laporan/laporan.md` | Alur pelaporan satuan ke CSIRT atasan `[ASUMSI]`. Konfirmasi: bagan alur pelaporan dari panitia atau satuan pilot |
| 2 | Isi minimal laporan insiden: kontak pelapor, deskripsi, kronologi, dampak (Peraturan BSSN 1/2024 Pasal 15 ayat 4). Setiap insiden dilaporkan TTIS organisasi ke TTIS sektoral (Pasal 15 ayat 1) | Laporan memuat ringkasan aturan (deskripsi), tabel bukti dengan `TimeCreated` per event (kronologi), hash audit per kasus, dan kolom persetujuan analis | `perisai/laporan.py`; `docs/DOKUMENTASI_TEKNIS.md` §1 | Sejak 15 Nov 2026, kontak pelapor dan dampak diisi analis di halaman **Laporan CSIRT** dan tercetak di bagian "Data pelaporan (Peraturan BSSN 1/2024 Pasal 15 ayat 4)"; kolom kosong ditandai "belum diisi". Format resmi Kartika CSIRT belum kami terima |
| 3 | Deteksi dan analisis kejadian (NIST SP 800-61r3, fungsi *Detect* dan *Respond*: analisis kejadian, analisis insiden, pelaporan) | 37 aturan gaya Sigma, kategori dipetakan ke taktik MITRE ATT&CK, bukti dari field terstruktur | Akurasi kategori aturan **50,0 %** vs LLM+firewall 35,2 % pada 88 kasus uji (P2, `BUKTI_EVALUASI.md` §3); aturan disetel di DEV 25/33 | Semua data dari satu lab (OTRF). Log satuan belum pernah dipakai (`BUKTI_EVALUASI.md` §6 L2) |
| 4 | Teknik serangan Windows yang umum: pencurian kredensial dari memori LSASS (ATT&CK T1003.001), *pass the ticket* (T1550.003) | Aturan untuk akses memori LSASS, logon jaringan, proses dari lokasi sementara, pemasangan layanan | Demo skenario 1: akses LSASS → eskalasi (`DOKUMENTASI_TEKNIS.md` §4). v1 menutup otomatis 3/88 rekaman serangan, termasuk *pass the ticket* Rubeus; v1.1 0/88 (post-hoc, `BUKTI_EVALUASI.md` §9) | Cakupan per teknik ATT&CK belum diukur. Rekaman yang tidak memicu aturan tetap bisa lolos dari antrean |
| 5 | Penyerang menyelipkan instruksi lewat isi log (OWASP LLM01:2025 *Prompt Injection*) | Firewall masukan + policy engine struktural | Keberhasilan injeksi **16,5 % → 0 %** (P1 lulus); policy saja dengan detektor buta **0,6 %** (1/176); deteksi pola pada injeksi baru **0 %** (`BUKTI_EVALUASI.md` §3, §4, §11) | Pola tidak tahan parafrase. Injeksi uji ditulis tim sendiri; red team luar belum ada |
| 6 | AI diberi wewenang bertindak terlalu besar (OWASP LLM06:2025 *Excessive Agency*) | Allowlist 4 aksi, aturan bukti, aset terlindungi, persetujuan manusia; alat tidak menjalankan aksi (`dieksekusi: false`) | Uji tertahan: isolasi dan blokir palsu 0/88 lolos di mode guarded; v1.1 0/176 menurut konstruksi (`BUKTI_EVALUASI.md` §11) | Karena alat baca-saja, integrasi dengan tindakan respons yang sebenarnya belum diuji |
| 7 | Log satuan tidak boleh keluar dari perangkat `[ASUMSI: sesuai kebijakan klasifikasi satuan; konfirmasi: aturan penanganan data satuan pilot]` | Aplikasi offline, server lokal hanya `127.0.0.1`, CSP `connect-src 'self'`, tanpa telemetri; berkas log yang diunggah tidak disimpan | `app/README.md` bagian "Data dan privasi"; `DOKUMENTASI_TEKNIS.md` §6 | Belum ada uji penetrasi aplikasi oleh pihak luar. Data sesi tidak dienkripsi oleh aplikasi (lihat §3.7) |
| 8 | Akuntabilitas keputusan dan pelestarian bukti (NIST SP 800-61r3, manajemen insiden dan pelaporan) | Jejak audit berantai SHA-256; persetujuan analis dicatat dengan nama, waktu, dan catatan | Uji ubah: satu entri diubah di salinan, verifikasi gagal (`app/README.md` langkah 5; demo skenario 6) | Pemegang perangkat bisa menghitung ulang seluruh rantai. Jangkar harian masih prosedur, belum dikode (`TANYA_JAWAB.md` #12) |
| 9 | OT: memisahkan zona kendali dari jaringan kantor dan mengendalikan conduit di antaranya (ISA/IEC 62443-3-2). Teknik ICS seperti *Modify Parameter* (T0836) dan *Manipulation of Control* (T0831) di ATT&CK for ICS | Jalur OT: pengecekan batas normal tiap sensor (operating envelope); PLC/HMI/RTU/SIS/EWS tidak pernah diputus sistem, aksi akhir eskalasi ke insinyur proses | HAI 21.03: **10/10** episode serangan tertangkap, alarm palsu **5,4 %** (test1) dan **0 %** (test4) (`BUKTI_EVALUASI.md` §10.2) | Halaman **Jalur OT** di aplikasi 1.0.0 hanya kasus contoh; impor telemetri sensor belum ada di aplikasi. **Host HMI berbasis Windows yang masuk lewat jalur IT belum dilindungi** (lihat catatan di bawah tabel). Penggunaan SCADA berjaringan di satuan `[ASUMSI]` |
| 10 | Peningkatan kapabilitas, kapasitas, dan kualitas SDM (Perpres 47/2023 Pasal 6 huruf f). Personel siber di satuan terbatas `[ASUMSI: konfirmasi lewat data personel satuan pilot]` | Antarmuka berbahasa Indonesia, alasan setiap keputusan ditampilkan, mode aturan tanpa LLM, pelatihan 1 hari | Belum ada ukuran. Pelatihan ±8 jam adalah estimasi (`PROPOSAL.md` §6) | Belum ada uji dengan operator nyata (`BUKTI_EVALUASI.md` §7 butir 5) |
| 11 | Alat keamanan tidak boleh menjadi celah rantai pasok | SHA-256 model dicek sebelum dimuat; hash kode mesin dibandingkan dengan hash beku di **Status sistem** | `perisai/integrity.py`, tes `test_model_hash_mismatch_means_no_llm`; cek model 1,8 detik untuk 0,92 GB (`BUKTI_EVALUASI.md` §10.1) | Exe belum ditandatangani sertifikat penerbit (`app/README.md` bagian "Batasan") |

**Catatan baris 9, diperiksa 15 Nov 2026.** Daftar aset terlindungi di jalur IT berisi nama host tetap (`dc01`, `siem01`, `gw01`, `dns01`, dan beberapa lainnya di `prototype/perisai/policy.py`). Awalan `plc-`/`hmi-` hanya dipakai jalur OT (`perisai/ot.py`). Kami mengganti nama host WS-OPS07 di log contoh `app/perisai_app/sampel/contoh_batalyon.xml` menjadi HMI-POMPA01, lalu menjalankan `triase.py` dengan direktori keluaran sementara. Hasilnya, kasus `credential_access` di HMI-POMPA01 mendapat usulan `isolate_host` berstatus `MENUNGGU_PERSETUJUAN`, sama seperti sebelum nama diganti. Usulan itu tidak dijalankan alat dan tetap menunggu analis. Meski begitu, untuk satuan yang punya HMI berbasis Windows, ini celah nyata. Celah ini sudah ditutup di aplikasi desktop dan demo web sejak 15 Nov 2026 (`app/perisai_app/asetot.py`, tes `app/tests/test_asetot.py`). Usulan isolasi untuk host berawalan HMI-, PLC-, SCADA-, RTU-, EWS-, SIS-, atau yang tercantum di `aset_terlindungi.txt`, sekarang menjadi eskalasi "aset OT terlindungi: eskalasi ke insinyur proses". Dengan nama HMI-POMPA01, usulan `isolate_host` berubah menjadi `escalate` (DIESKALASI). CLI `prototype/triase.py` belum memakai penjaga ini. Selama pilot, daftar host OT dan host kritis satuan tetap ditempel di posko dan dimasukkan ke `aset_terlindungi.txt`.

Cara mengulang (PowerShell, dari akar repo):
```powershell
(Get-Content app\perisai_app\sampel\contoh_batalyon.xml) -replace 'WS-OPS07','HMI-POMPA01' | Set-Content -Encoding utf8 $env:TEMP\hmi.xml
prototype\.venv\Scripts\python -I prototype\triase.py --input $env:TEMP\hmi.xml
```

---

## 2. Skenario operasional: satu hari di posko siber satuan
**Latar `[ASUMSI]`:** posko siber sebuah satuan setingkat batalyon/pangkalan. Ada PC kantor berbasis Windows dan satu PC HMI berbasis Windows untuk pompa air dan genset pangkalan. Posko punya satu laptop khusus yang tidak tersambung ke jaringan mana pun. Personel: satu operator dan satu analis per sif. Konfirmasi: survei perangkat dan personel di satuan pilot.

| Waktu | Kegiatan | Layar aplikasi | Yang terlihat dan dicatat |
|---|---|---|---|
| 07.30 | Serah terima sif. Admin menyalakan laptop offline, memeriksa jejak audit hari sebelumnya, dan mencatat hash terakhir (head) di buku jaga | **Jejak audit** → **Verifikasi integritas**; **Status sistem** | Rantai utuh atau gagal. Status hash model dan hash kode mesin |
| 08.00 | Operator mengekspor log dari PC kantor dan PC HMI ke media lepas khusus: `wevtutil qe Security /c:500 /rd:true /f:xml > security.xml`, dan bila Sysmon terpasang `wevtutil qe Microsoft-Windows-Sysmon/Operational /c:500 /rd:true /f:xml > sysmon.xml`. Media dibawa ke laptop offline | (di luar aplikasi) | Nama berkas memuat nama host dan tanggal, misalnya `WS-ADM01_20261116_security.xml` |
| 08.30 | Operator mengimpor berkas | **Impor log** | Jumlah event, jumlah kasus, kelompok tanpa temuan, SHA-256 tiap berkas. Isi log tidak disimpan; yang masuk audit hanya nama, ukuran, dan hash berkas |
| 09.00 | Analis membuka antrean dan mengurutkan menurut severity. Kasus berlabel **Injeksi terdeteksi** dibaca lebih dulu | **Antrean kasus** | Kategori ATT&CK, severity, status (`DIESKALASI`, `MENUNGGU_PERSETUJUAN`), tanda injeksi |
| 09.15 | Analis membuka satu kasus: bukti field terstruktur, aturan yang terpicu, temuan firewall, dan alasan keputusan | Detail kasus | Teks log yang mencurigakan tampil sebagai teks biasa dan ditandai, tidak dijalankan |
| 09.30 | Kasus di PC kantor meminta isolasi. Analis memeriksa bukti, lalu **Setujui aksi** atau **Tolak aksi** dengan nama dan catatan. Isolasi dijalankan manusia lewat prosedur satuan yang berlaku | Detail kasus → kartu persetujuan | Entri `tindakan_analis` di audit dengan `dieksekusi: false` |
| 10.00 | Kasus di PC HMI pompa/genset meminta isolasi (celah §1 baris 9). Analis **menolak** dengan catatan "host OT, eskalasi ke teknisi", lalu menghubungi teknisi genset. Kalau ada keraguan, analis bisa menguji usulan lain terhadap policy | Detail kasus → **Uji usulan terhadap policy**; **Jalur OT** untuk acuan kebijakan dan daftar periksa | Penolakan tercatat di audit. Daftar periksa OT: cocokkan dengan alat ukur lokal, cek perubahan di engineering workstation, jangan memutus PLC/HMI tanpa keputusan insinyur |
| 11.00 | Opsional, hanya bila model terpasang: analis meminta **Buat draf AI** untuk kasus yang rumit, untuk membantu menulis narasi | Detail kasus | Draf diberi label "bukan dasar keputusan" dan disaring per kalimat. Kategori dan aksi tidak berubah |
| 13.00 | Kasus tanpa ancaman nyata ditutup analis dengan catatan berawalan `FP:` (positif palsu) supaya bisa dihitung di pilot | Detail kasus → tutup kasus | Entri `tindakan_analis` dengan keputusan `tutup` |
| 14.00 | Analis membuat laporan, melengkapi kontak pelapor dan dampak secara manual, lalu menandatanganinya | **Laporan CSIRT** → unduh Markdown/HTML atau **Cetak / simpan PDF** | Laporan berisi ringkasan aturan, bukti, hash audit per kasus, dan kolom persetujuan |
| 15.00 | Laporan diteruskan ke CSIRT atasan lewat kanal resmi satuan `[ASUMSI]`. Jejak audit diekspor ke media arsip | **Jejak audit** → ekspor `audit.jsonl` | Head hash dicatat lagi di buku jaga sebagai jangkar harian |

Jalur log seluruhnya satu arah: dari PC sumber ke media, lalu ke laptop offline. Laptop tidak pernah tersambung ke jaringan satuan maupun internet.

---

## 3. Paket penerapan satuan
### 3.1 Isi paket
| Komponen | Ukuran | Sumber |
|---|---|---|
| `PERISAI-RESPON-1.0.0-win64.zip` + berkas `.sha256` | 41,5 MB | `app/README.md` |
| Model `qwen2.5-1.5b-instruct-q3_k_m.gguf` (opsional) | 0,92 GB, SHA-256 `58cb5c05…b993` | `app/README.md`, `prototype/DATA.md` |
| Microsoft Edge WebView2 Runtime, installer offline (hanya untuk Windows 10 yang belum memilikinya) | dari Microsoft | rencana, belum diuji |
| Dokumen: panduan pengguna (`app/README.md`), dokumen ini, lembar daftar host kritis satuan, buku jaga jangkar audit | - | - |

### 3.2 Instalasi air-gapped
1. Admin menerima paket di media lepas, ditambah nilai SHA-256 lewat kanal terpisah dari media itu (misalnya tercetak di berita acara serah terima) `[ASUMSI prosedur satuan]`.
2. Di laptop offline: `Get-FileHash -Algorithm SHA256 PERISAI-RESPON-1.0.0-win64.zip`. Nilainya harus sama dengan nilai yang diterima. Kalau berbeda, paket tidak dipasang.
3. Ekstrak seluruh isi zip ke satu folder, misalnya `C:\PERISAI\`. Jangan jalankan dari dalam zip.
4. Kalau model dipakai, salin berkas model ke `C:\PERISAI\models\`. Aplikasi mengecek SHA-256 model sebelum memuatnya. Kalau tidak cocok, aplikasi tetap di mode aturan dan alasannya tampil di **Status sistem**.
5. Jalankan `PERISAI-RESPON.exe`. SmartScreen akan memperingatkan karena exe belum ditandatangani. Admin membuka blokir sesuai kebijakan perangkat satuan.
6. Uji penerimaan: **Muat data contoh** harus menghasilkan 10 kasus dari 22 event; **Verifikasi integritas** harus utuh; **Uji deteksi perubahan** harus gagal pada salinan; **Status sistem** harus menunjukkan hash kode mesin cocok. Lalu klik **Mulai sesi baru** sebelum memakai log asli.

### 3.3 Pembaruan aturan dan model
- **Aturan.** Aturan deteksi ada di dalam kode mesin yang di-hash, jadi pembaruan aturan berarti **rilis zip baru**. Status sistem menampilkan apakah kode mesin cocok dengan hash beku.
- **Model.** Berkas model diganti. Hash acuannya tertanam di aplikasi, jadi model baru juga memerlukan rilis aplikasi baru. Model dengan hash lain tidak akan dimuat.
- **Alur usulan:** tim pemelihara (diusulkan lewat Kartika CSIRT `[ASUMSI]`) membangun zip dengan `app/tools/build.py`, menerbitkan SHA-256, lalu mengirim paket di media dan hash lewat kanal terpisah. Admin satuan mengulang langkah 3.2 butir 1 sampai 6. Sesi lama tidak dihapus.
- **Belum ada:** tanda tangan digital paket (misalnya Authenticode untuk exe), dan paket aturan terpisah dari aplikasi. Keduanya masuk tahap 3 di `PROPOSAL.md` §6. Sampai saat itu, perlindungannya hanya kecocokan hash yang dikirim lewat kanal terpisah.

### 3.4 Peran
Aplikasi 1.0.0 **belum punya login atau pembatasan peran**. Nama analis pada persetujuan diisi bebas. Karena itu, peran di bawah ditegakkan lewat prosedur dan akun Windows terpisah di laptop `[ASUMSI: kebijakan akun perangkat satuan]`.

| Peran | Tugas | Layar |
|---|---|---|
| Operator | Mengekspor log dari PC sumber, membawa media, mengimpor berkas, memeriksa jumlah event | **Impor log**, **Antrean kasus** |
| Analis | Membaca bukti, menyetujui atau menolak usulan, menutup kasus dengan catatan, membuat dan menandatangani laporan | Detail kasus, **Laporan CSIRT**, **Jalur OT** |
| Admin | Memasang dan memperbarui paket, memeriksa hash, mencatat jangkar audit harian, mengarsipkan sesi, menjaga daftar host kritis | **Status sistem**, **Jejak audit** |

### 3.5 Pelatihan satu hari (8 jam, untuk operator dan analis)
| Sesi | Durasi | Isi | Praktik |
|---|---|---|---|
| 1 | 1 jam | Batas alat: yang dikerjakan aturan, LLM, policy, dan manusia. Mengapa log bisa disetir penyerang | Membaca diagram alur `README.md` |
| 2 | 1 jam | Ekspor log Windows dengan `wevtutil`, Sysmon, konversi `.evtx`, penanganan media lepas | Ekspor dari PC latihan |
| 3 | 1 jam | Impor log, antrean kasus, kategori ATT&CK, severity | Data contoh: 10 kasus dari 22 event |
| 4 | 1 jam | Membaca bukti field terstruktur dan temuan firewall. Kasus injeksi | Kasus WS-KEU02 di data contoh |
| 5 | 1 jam | Setujui, tolak, tutup, dan catatan. Kebijakan aset terlindungi dan host OT | Kasus WS-OPS07; uji usulan isolasi DC01 dan PLC-P1 |
| 6 | 1 jam | Jejak audit: verifikasi, uji perubahan, jangkar harian di buku jaga | **Uji deteksi perubahan** |
| 7 | 1 jam | Laporan CSIRT: melengkapi kontak pelapor dan dampak, mencetak, meneruskan | Laporan dari data contoh |
| 8 | 1 jam | Latihan skenario §2 dari awal sampai akhir, lalu evaluasi | Peserta lulus bila menyelesaikan skenario tanpa menyetujui usulan untuk host terlindungi atau host OT |

Admin mendapat tambahan 2 jam untuk instalasi, pembaruan, dan pemeriksaan hash. Durasi ini estimasi dan diuji di pilot.

### 3.6 Pilot 30 hari
**Bentuk:** baca-saja, satu satuan, berjalan di samping prosedur yang sudah ada dan tidak menggantikannya. Mulai setelah izin `[ASUMSI]`.

| Minggu | Kegiatan |
|---|---|
| 0 (sebelum mulai) | Instalasi dan uji penerimaan (§3.2), pelatihan (§3.5), daftar host kritis dan host OT ditetapkan, format laporan disesuaikan dengan format CSIRT bila tersedia |
| 1 | Impor harian dari sebagian kecil PC. Catat semua alarm palsu dengan awalan `FP:` |
| 2 | Tinjauan pertengahan: aturan yang paling sering memberi alarm palsu dicatat sebagai bahan rilis aturan berikutnya. Aturan tidak diubah selama pilot, supaya angka minggu 1 dan 4 bisa dibandingkan |
| 3-4 | Cakupan PC diperluas. Tambahkan PC HMI bila ada |
| Akhir | Laporan pilot: metrik di bawah, wawancara operator dan analis, keputusan lanjut atau berhenti |

**Metrik keberhasilan.** Semua metrik dihitung dari `audit.jsonl` (menu **Jejak audit** → ekspor), kecuali yang ditandai. Target adalah usulan tim dan ditetapkan bersama satuan sebelum pilot dimulai.

| Metrik | Cara mengukur dari jejak audit | Target usulan |
|---|---|---|
| Median waktu triase per kasus | Selisih `ts` entri `tindakan_analis` pertama yang punya `status_tinjauan` dengan `ts` entri `keputusan_v12` untuk `case_id` yang sama. Ini mengukur waktu dari impor sampai keputusan analis | Ditetapkan dari minggu 1; minggu 4 tidak lebih lambat dari minggu 1 |
| Cakupan tinjauan | Persentase kasus yang punya `tindakan_analis` berstatus dalam satu sif | ≥ 90 % |
| Usulan disetujui / ditolak | Di antara kasus `final_status = MENUNGGU_PERSETUJUAN`, jumlah `keputusan = setujui` dan `keputusan = tolak` | Dilaporkan apa adanya; penolakan yang tinggi berarti aturan isolasi perlu ditinjau |
| Laju alarm palsu | Jumlah `keputusan = tutup` dengan catatan berawalan `FP:` dibagi jumlah kasus | Turun dari minggu 1 ke minggu 4 setelah rilis aturan; ambang ditetapkan bersama satuan |
| Usulan untuk host terlindungi atau host OT yang disetujui | Persetujuan pada kasus yang host-nya ada di daftar host kritis satuan | 0 |
| Integritas audit | Hasil **Verifikasi integritas** harian dan kecocokan head hash dengan buku jaga | 30/30 hari utuh |
| Kasus dengan injeksi terdeteksi | Entri `keputusan_v12` dengan peringatan `INJEKSI_TERDETEKSI` | Dilaporkan; setiap kasus ditinjau manual |
| Insiden yang terlewat | **Di luar audit:** insiden yang ditemukan lewat jalur lain (CSIRT, laporan pengguna) pada host yang lognya sudah diimpor | Dilaporkan apa adanya |
| Kegunaan bagi analis | **Di luar audit:** kuesioner singkat di akhir minggu 2 dan 4 | Dilaporkan apa adanya |

Contoh perhitungan di laptop pilot (PowerShell 5.1 bawaan Windows, tanpa instalasi tambahan). Skrip ini sudah kami uji pada jejak audit buatan dengan 7 kasus dan 5 tindakan analis:
```powershell
$e   = Get-Content audit.jsonl -Encoding UTF8 | ForEach-Object { $_ | ConvertFrom-Json }
$kas = $e | Where-Object kind -eq 'keputusan_v12'
$tin = $e | Where-Object { $_.kind -eq 'tindakan_analis' -and $_.payload.status_tinjauan }
$menit = foreach ($k in $kas) { $t = $tin | Where-Object case_id -eq $k.case_id | Select-Object -First 1
  if ($t) { ([datetime]$t.ts - [datetime]$k.ts).TotalMinutes } }
$s = @($menit | Sort-Object); $med = if ($s.Count) { $s[[int][math]::Floor(($s.Count - 1) / 2)] }
$usul   = @($kas | Where-Object { $_.payload.final_status -eq 'MENUNGGU_PERSETUJUAN' }).Count
$setuju = @($tin | Where-Object { $_.payload.keputusan -eq 'setujui' }).Count
$tolak  = @($tin | Where-Object { $_.payload.keputusan -eq 'tolak' }).Count
$fp     = @($tin | Where-Object { $_.payload.keputusan -eq 'tutup' -and $_.payload.catatan -like 'FP:*' }).Count
"kasus=$($kas.Count) ditinjau=$($s.Count) median_menit=$med usulan=$usul setuju=$setuju tolak=$tolak alarm_palsu=$fp"
```

### 3.7 Biaya
| Pos | Biaya | Keterangan |
|---|---|---|
| Lisensi perangkat lunak | **Rp0** | Kode MIT; Qwen2.5 Apache-2.0; llama.cpp MIT. Tidak ada biaya per token |
| Perangkat | Rp0 tambahan `[ASUMSI: satuan punya laptop Windows 10/11 64-bit yang bisa dikhususkan]` | Spesifikasi di §4 |
| Media lepas khusus | sesuai persediaan satuan | Dua media: satu untuk log masuk, satu untuk arsip audit dan laporan |
| Penyiapan dan instalasi | 1 hari-orang (admin) + 1 hari-orang (tim) | Termasuk uji penerimaan |
| Pelatihan | 1 hari × jumlah peserta, ditambah 1 hari-orang pelatih dari tim | Contoh: 4 peserta = 4 hari-orang peserta + 1 hari-orang pelatih |
| Operasi pilot | ±1 jam per hari per sif untuk ekspor, impor, dan triase `[estimasi]`, sekitar 4 hari-orang selama 30 hari untuk satu sif | Diukur ulang dari metrik waktu triase |
| Pendampingan tim | 3 kunjungan (awal, minggu 2, akhir) × 1 hari × 2 orang = 6 hari-orang | Pendampingan jarak jauh tidak memungkinkan karena laptop offline |
| Evaluasi pilot | 2 hari-orang tim | Menghitung metrik, menulis laporan |

Semua jumlah hari-orang adalah estimasi tim dan belum diuji.

### 3.8 Register risiko
| # | Risiko | Dampak | Mitigasi |
|---|---|---|---|
| 1 | Log satuan berbeda dari data lab OTRF, sehingga aturan meleset atau alarm palsu tinggi | Analis kehilangan kepercayaan; insiden terlewat | Pilot baca-saja berjalan di samping prosedur yang ada; alarm palsu dicatat `FP:`; aturan disetel lewat rilis setelah pilot |
| 2 | Usulan isolasi untuk host HMI berbasis Windows atau host kritis yang tidak ada di daftar aset terlindungi (diperiksa, §1 baris 9) | Analis menyetujui isolasi host proses | Daftar host kritis dan host OT ditempel di posko; metrik "persetujuan untuk host terlindungi = 0"; daftar aset per satuan di lapisan aplikasi diusulkan untuk rilis berikutnya |
| 3 | Analis terlalu percaya draf AI | Narasi yang salah masuk laporan | Mode aturan sebagai bawaan; draf AI berlabel dan hanya dibuat atas permintaan; sesi 1 dan 4 pelatihan |
| 4 | Media lepas membawa malware ke laptop offline, atau data keluar lewat media | Laptop terinfeksi; kebocoran log | Media khusus dan diberi tanda; alur satu arah; pemindaian sesuai prosedur satuan `[ASUMSI]`; laptop tidak pernah tersambung ke jaringan |
| 5 | Pemegang laptop menghitung ulang seluruh rantai audit | Catatan keputusan bisa dipalsukan | Jangkar harian: head hash dicatat di buku jaga oleh admin, bukan oleh analis yang bertugas |
| 6 | Paket pembaruan palsu | Aturan atau model disusupi | Hash dikirim lewat kanal terpisah dari media; model dengan hash lain tidak dimuat; tanda tangan digital di tahap 3 |
| 7 | Antivirus mengkarantina exe yang belum ditandatangani atau teks log serangan | Aplikasi tidak bisa jalan; berkas hilang | Hash zip dicek sebelum pengecualian dibuat oleh admin sesuai kebijakan; penandatanganan exe di tahap 3 |

Data sesi (`audit.jsonl`, `kasus.json.gz`, berisi maksimal 8 event terpilih per kasus) tersimpan tanpa enkripsi di `%LOCALAPPDATA%\PERISAI-RESPON\sesi\`. Perlindungan saat laptop hilang bergantung pada enkripsi disk yang diatur satuan `[ASUMSI]`.

---

## 4. Persyaratan sistem
Fakta diambil dari `app/README.md`. Butir yang belum diuji ditulis sebagai rencana uji.

| | Mode aturan (bawaan) | Mode LLM lokal (opsional) | Status |
|---|---|---|---|
| Sistem operasi | Windows 10/11 64-bit dengan Microsoft Edge WebView2 Runtime (bawaan Windows 11) | sama | **Diuji** di Windows 11 build 26200. **Rencana uji:** Windows 10 dan mesin tanpa WebView2 (opsi `--browser` tersedia sebagai jalan keluar) |
| Disk | ±100 MB setelah diekstrak (zip 41,5 MB) | tambah 0,92 GB untuk model | Diuji |
| RAM | proses aplikasi ±170 MB saat diuji | model 0,92 GB dimuat ke RAM; sediakan ≥ 2 GB kosong | Diuji di laptop tim |
| CPU | x64 biasa; firewall + policy < 10 ms per kasus di laptop tim | x64 tanpa GPU; median 28,7 s per kasus di i7-13620H | Diuji di laptop tim (i7-13620H). **Rencana uji:** PC kelas kantor milik satuan, diukur dengan tombol **Uji kinerja di perangkat ini** di **Status sistem** |
| Jaringan | tidak perlu; server lokal hanya `127.0.0.1` | tidak perlu | Diuji |
| Akun dan instalasi | tidak perlu Python, internet, atau akun | `llama_cpp` sudah dibundel | Diuji |
| Format log | XML `wevtutil`/`Get-WinEvent`, JSON Winlogbeat/NXLog, `.evtx` (dikonversi lokal dengan `wevtutil`) | sama | Diuji dengan log contoh dan OTRF. **Rencana uji:** log asli satuan |
| Tanda tangan exe | belum ada; SmartScreen dan sebagian antivirus memberi peringatan | sama | Batasan yang diketahui |

---

## 5. Rujukan publik
1. Peraturan Presiden Republik Indonesia Nomor 47 Tahun 2023 tentang Strategi Keamanan Siber Nasional dan Manajemen Krisis Siber (2023). Pasal 6, 9, dan 21. https://peraturan.bpk.go.id/Details/255542/perpres-no-47-tahun-2023
2. Peraturan Badan Siber dan Sandi Negara Nomor 10 Tahun 2020 tentang Tim Tanggap Insiden Siber (2020), Berita Negara 2020 No. 1488. https://peraturan.go.id/files/bn1488-2020.pdf
3. Peraturan Badan Siber dan Sandi Negara Nomor 1 Tahun 2024 tentang Pengelolaan Insiden Siber (2024). Pasal 15. https://peraturan.go.id/files/peraturan-bssn-no-1-tahun-2024.pdf
4. NIST SP 800-61 Rev. 3, *Incident Response Recommendations and Considerations for Cybersecurity Risk Management: A CSF 2.0 Community Profile* (April 2025). https://doi.org/10.6028/NIST.SP.800-61r3
5. ISA/IEC 62443 *Series of Standards*, terutama ANSI/ISA-62443-3-2-2020 *Security for industrial automation and control systems, Part 3-2: Security risk assessment for system design* (zona dan conduit). https://www.isa.org/standards-and-publications/isa-standards/isa-iec-62443-series-of-standards
6. MITRE ATT&CK (Enterprise): T1003.001 *OS Credential Dumping: LSASS Memory*, T1550.003 *Use Alternate Authentication Material: Pass the Ticket*. https://attack.mitre.org/
7. MITRE ATT&CK for ICS: T0836 *Modify Parameter*, T0831 *Manipulation of Control*. https://attack.mitre.org/matrices/ics/
8. OWASP *Top 10 for LLM Applications 2025*: LLM01:2025 *Prompt Injection*, LLM06:2025 *Excessive Agency*. https://genai.owasp.org/llm-top-10/

Semua tautan diperiksa 15 Nov 2026.
