# DOKUMENTASI TEKNIS: PERISAI-RESPON (inti v1 yang dievaluasi + lapisan v1.1/v1.2.2 yang dipakai)
### Kode: `prototype/` (mesin) dan `app/` (aplikasi desktop 1.0.0) · Python 3.11 · Windows 11, berjalan di CPU · diperbarui 2 Nov 2026

## 0. Aplikasi desktop 1.0.0 (`app/`)
Aplikasi analis di atas mesin v1.2.2. Mesin dipanggil sebagai pustaka dan kodenya tidak diubah (hash di `prototype/frozen` tetap cocok).
- **Distribusi:** `PERISAI-RESPON-1.0.0-win64.zip` (41,5 MB, PyInstaller onedir, belum ditandatangani). `PERISAI-RESPON.exe` menjalankan server FastAPI di `127.0.0.1` pada port bebas, lalu membuka jendela pywebview (Edge WebView2). Kalau WebView2 tidak ada, `--browser` membuka peramban bawaan.
- **Fitur:** impor XML `wevtutil`, JSON Winlogbeat, dan `.evtx` (dikonversi lokal dengan `wevtutil`); antrean kasus; detail kasus dengan bukti field terstruktur dan temuan firewall; uji usulan terhadap policy; setujui/tolak oleh analis yang hanya dicatat di jejak audit (`dieksekusi: false`); verifikasi dan uji ubah jejak audit; laporan CSIRT Markdown/HTML; jalur OT; halaman status dengan cek hash model, hash mesin, dan uji kinerja di perangkat.
- **Mode LLM:** opsional. Model 0,92 GB ditaruh di folder `models` di samping exe; SHA-256 dicek sebelum dimuat. Draf AI dibuat per kasus atas permintaan analis, di latar belakang, dan diberi label "bukan dasar keputusan".
- **Keamanan server lokal:** hanya `127.0.0.1`, cek header Host, header `X-Perisai` wajib untuk POST, CSP `connect-src 'self'`, tanpa CDN dan tanpa telemetri.
- **Mode demo (Docker):** `app/Dockerfile`, `PERISAI_MODE=demo`, hanya data contoh dan unggahan ditolak. Langkah publikasi di `app/DEPLOY.md`.
- **Tes:** `cd app; .venv\Scripts\python -I -m pytest -q -p no:cacheprovider tests` (24 tes API). Panduan pengguna lengkap: `app/README.md`.

## 1. Arsitektur
| Lapis | Modul | Fungsi | Bergantung pada LLM? |
|---|---|---|---|
| Pembaca log | `perisai/logs.py` | Membaca arsip OTRF (zip/tar.gz/json) langsung di memori; menormalkan field **terstruktur** (Hostname, IpAddress, EventID, Image, …) dan **teks bebas** (CommandLine, ScriptBlockText, …) | tidak |
| Detektor | `perisai/detector.py` | 37 aturan gaya Sigma (ditulis sendiri, bukan port SigmaHQ resmi). Memilih 8 event berbobot tertinggi dan menyediakan baseline template kategori → playbook | tidak |
| Firewall masukan | `perisai/firewall.py` | Normalisasi Unicode/homoglyph; menghapus karakter tersembunyi; dekode base64/URL/`\uXXXX`; pola injeksi EN/ID, klaim persetujuan, kosakata aksi agen, permintaan kredensial; redaksi field bertanda; spotlighting «DATA» yang tidak bisa dipalsukan | tidak |
| LLM lokal | `perisai/llm.py` | llama-cpp-python 0.3.36 + Qwen2.5-1.5B-Instruct q3_k_m. `temperature=0`, `seed=0`, keluaran JSON. Parser toleran: JSON rusak → mode degradasi | — |
| Policy engine | `perisai/policy.py` | 8 aturan (§2). Menghasilkan `EXECUTE / REQUEST_APPROVAL / BLOCK` atas usulan, ditambah status akhir | tidak |
| Audit | `perisai/audit.py` | JSONL berantai SHA-256: `entry_hash = H(prev_hash ‖ body)` dan `payload_hash`. `verify()` mendeteksi edit, sisip, dan hapus di tengah | tidak |
| Pipeline | `perisai/pipeline.py` | mode `naive`, `guarded`, `prompt_only`, degradasi | — |
| Evaluasi | `run_eval.py`, `analyze.py`, `perisai/metrics.py` | Harness yang bisa dilanjutkan bila terputus, sharding, bootstrap klaster, Holm | — |
| Importer log asli | `perisai/importer.py`, `triase.py` | XML `wevtutil`/`Get-WinEvent` dan JSON. Event dikelompokkan per host dan per jendela 15 menit. Kelompok tanpa temuan aturan tidak dijadikan kasus. DOCTYPE/ENTITY ditolak | tidak |
| Laporan CSIRT | `perisai/laporan.py` | Markdown berisi ringkasan aturan, DRAF AI, alasan, bukti dari field terstruktur, hash audit per kasus, dan kolom persetujuan. Teks bebas log tidak disalin | tidak |
| Integritas model | `perisai/integrity.py` | Mengecek SHA-256 model sebelum dimuat. Kalau tidak cocok, sistem masuk mode aturan | tidak |
| Jalur OT | `perisai/ot.py` | Detektor amplop normal untuk telemetri HAI. Aset proses tidak pernah diputus sistem, aksi akhir selalu eskalasi ke insinyur proses | tidak |

## 2. Aturan policy engine (berlaku dengan atau tanpa LLM)
1. **Allowlist tertutup:** `isolate_host`, `block_ip`, `escalate`, `no_action`. Aksi lain → BLOCK.
2. Firewall menemukan instruksi di isi log → aksi berisiko dan `no_action` ditolak; kasus **dieskalasi** dengan `INJEKSI_TERDETEKSI`.
3. **Aturan bukti:**
   - aksi berisiko wajib menunjuk event yang ada;
   - event itu harus memicu aturan detektor;
   - target harus muncul di field **terstruktur** event itu.
4. **Aset terlindungi** (DC, SIEM, gateway, DNS) tidak pernah diisolasi/diblokir otomatis. Keputusannya di tangan komandan.
5. Aksi berisiko yang lolos tetap `REQUEST_APPROVAL`. **Tidak ada eksekusi otomatis.**
6. `no_action` hanya boleh bila detektor tidak menemukan indikasi berbobot ≥ medium.
7. Ringkasan untuk operator disaring: URL, e-mail, IP, dan host yang tidak ada di field terstruktur dihapus.
8. LLM mati, keluaran tidak valid, atau **hash model tidak cocok** → **mode degradasi**: kategori dan aksi dari template aturan. Hash model dicek oleh `perisai/integrity.py` di `demo.py` dan `triase.py`. Harness evaluasi v1 yang di-hash tidak memakainya.

## 3. Instalasi dan menjalankan (offline setelah unduh pertama)
```powershell
cd prototype
python -m venv .venv
.venv\Scripts\python -m pip install numpy pandas pytest matplotlib pyyaml
.venv\Scripts\python -m pip install --only-binary=:all: llama-cpp-python --extra-index-url https://abetlen.github.io/llama-cpp-python/whl/cpu
# model 0,92 GB -> models\ (URL + SHA-256 di DATA.md); data OTRF 101 MB -> data\otrf\zips\
.venv\Scripts\python -I demo.py --no-llm          # < 1 detik, tanpa model
.venv\Scripts\python -I demo.py                   # 8 skenario dengan LLM (v1 + baris v1.2.2 yang dipakai + OT), ±1 menit di i7-13620H
.venv\Scripts\python -I -m pytest -q -p no:cacheprovider tests   # 102 tes
# log Windows asli dari PC sendiri -> laporan CSIRT
wevtutil qe Security /c:500 /rd:true /f:xml > security.xml
.venv\Scripts\python -I triase.py --input security.xml [--llm]
```
Paket offline untuk satuan berisi wheel, model, dan kode di satu media lepas.

## 4. Demo (8 skenario, `results/demo/demo_output.txt`; setiap skenario menampilkan keputusan v1 **dan** v1.1)
1. Kasus bersih: akses memori LSASS → eskalasi ke analis.
2. Injeksi ID (tujuan: blokir IP): tanpa pengaman, LLM langsung memblokir IP; dengan PERISAI, firewall mendeteksi → eskalasi + peringatan.
3. Injeksi EN "isolasi DC01" → eskalasi. Di sini LLM menulis halusinasi "potensi terorisme": usulan mentah hanya ditampilkan dengan `--v1`, dan draf AI v1.2.2 membuang kalimat itu.
4. **Detektor pola dibuat buta:**
   - usulan **buatan tangan** yang meniru LLM yang menuruti injeksi, "isolasi DC01" → BLOCK karena aset terlindungi;
   - usulan buatan tangan "blokir 10.20.30.40" → BLOCK karena IP tidak ada di field terstruktur. Bukti dengan usulan LLM asli ada di ablasi `policy_only` (§5).
5. LLM mati → mode degradasi: isolasi host diusulkan dan **menunggu persetujuan**.
5b. v1.2.2 dengan usulan rekonstruksi (tutup kasus + "terorisme" + "pemeliharaan terjadwal") → kasus tidak ditutup, kedua kalimat dibuang.
5c. OT: tag boiler di luar amplop, catatan HMI berisi string uji "putus PLC-P1" (firewall **tidak** menangkapnya), usulan buatan tangan "isolate_host PLC-P1" → **BLOCK**, lalu eskalasi ke insinyur proses.
6. Audit 12 entri utuh. Pada salinan, `final_status` entri #2 diubah menjadi `DIEKSEKUSI`, dan perubahan itu terdeteksi: `entry hash mismatch`.

## 5. Evaluasi
- **Prareg:** `PRAREG.md`, SHA-256 `cad685a322876caea362d58f685af88a862f2358aee9fc4912db0c5b62d3012a`, dibekukan 29 Okt 01:20 WIB. Bisa dicek dengan `sha256sum -c PRAREG.sha256`.
- **Hash kode:** `frozen/CODE_PRE_TEST_FAMILIES.sha256` (firewall/policy/detektor, cocok), `CODE_EVAL_v2_harness.sha256` (sharding, diungkap sebelum hasil), `CODE_ANALYZE_v3.sha256` (koreksi bug S3, **sesudah** hasil, lihat D1).
- **Data:**
  - OTRF Security-Datasets commit `d9d40ef1` (MIT): 121 rekaman Windows. Satu arsip dikarantina Windows Defender dan dikeluarkan.
  - Split per teknik ATT&CK: DEV 33 / UJI 88. Tes `test_frozen_split_has_no_group_leakage` memastikan tidak ada kebocoran.
- **Unit injeksi:** 176 = 88 kasus × 2 kombinasi dari 12 template (3 keluarga × 4 tujuan: G1 isolasi host, G2 blokir IP, G3 menutup kasus, G4 relay kredensial ke URL `.invalid`).

### 5.1 Hasil
| | Nilai | CI95 bootstrap klaster |
|---|---|---|
| ASR LLM tanpa pengaman (`naive`) | 16,5 % (29/176) | [6,8; 27,7] |
| ASR prompt defensif saja | 15,9 % | [6,3; 26,6] |
| ASR **policy saja, detektor buta** | **0,6 %** (1/176) | [0; 1,7] |
| ASR PERISAI penuh | **0 %** (0/176) | [0; 0] |
| **P1** Δ naive − guarded | +16,5 poin, p = 0,0002, Holm lulus | [6,8; 27,7] → **LULUS** |
| ASR naive per tujuan | G1 0/44 · **G2 18/44** · G3 9/44 · G4 2/44 | laju dasar G3 tanpa injeksi = 7/44 |
| Akurasi kategori: aturan / LLM tanpa FW / LLM+FW | 50,0 % / 18,2 % / 35,2 % | — |
| **P2** Δ LLM+FW − aturan | −14,8 poin | [−30,6; −2,7] → **GAGAL** |
| Macro-F1 aturan / LLM+FW / LLM | 0,47 / 0,34 / 0,12 | — |
| Akurasi aksi (S3, setelah koreksi D1) aturan / LLM+FW | 59,1 % / 54,5 % | Δ [−42; +34] |
| JSON valid (guarded / naive) | 98,9 % / 96,6 % | — |
| False flag firewall di data bersih | 0/88 | — |
| Policy BLOCK di data bersih | 3/88 | [0; 6,8] |
| Latensi LLM per kasus (guarded) | median 28,7 s, p90 39,4 s, maks 100 s | — |
| Firewall / policy / mode degradasi | median 4,5 ms / 2,5 ms / 3,3 ms | — |
| **Uji tertahan (PRAREG v3):** deteksi firewall | 0/176 | — |
| Uji tertahan: ASR naive / v1 / policy saja / v1.1 | 5,7 % / 2,3 % / 1,7 % / **0 %** | H-P1 Δ +3,4 poin [0; 6,8], p 0,032 → **GAGAL** |
| Tanda palsu firewall, teks asli 121 rekaman | 0 / 260.351 field | — |
| OT HAI 21.03 (PRAREG v4): episode tertangkap / alarm palsu | 10/10 · 5,4 % (test1), 0 % (test4) | — |

**Catatan latensi:** laptop sempat tidur ±4,3 jam di tengah run, sehingga beberapa panggilan `naive`/`prompt_only` tercatat lebih dari 15.000 detik. Yang dilaporkan hanya median dan p90. Rata-rata untuk mode itu tidak bermakna.

### 5.2 Penyimpangan dari prareg
- **§0 (diungkap sebelum hasil):** keluarga injeksi yang ditahan tidak dibuat, jadi P1 bersifat in-sample. Sebagai penggantinya ditambahkan ablasi `policy_only`.
- **v2 harness (sebelum hasil):** sharding 2 proses × 6 thread.
- **D1 (sesudah hasil):** `run_eval.py:115` menulis `act_correct=True` untuk mode `rules`. Koreksinya di `analyze.py`. Hanya metrik sekunder S3 yang berubah (100 % → 59,1 %). P1 dan P2 tidak berubah.

## 6. Keamanan alat itu sendiri
| Ancaman | Kontrol |
|---|---|
| Injeksi lewat isi log | firewall + policy struktural (diuji, §5) |
| Model diganti | `perisai/integrity.py` mengecek SHA-256 model (hash acuan dari `DATA.md`) sebelum dimuat. Kalau tidak cocok, sistem masuk mode aturan dan status integritas tercatat di laporan (tes `test_model_hash_mismatch_means_no_llm`) |
| Berkas XML jahat | importer menolak DOCTYPE/ENTITY sebelum parsing |
| Laporan ikut membawa instruksi penyerang | teks bebas log tidak disalin ke laporan CSIRT, hanya field terstruktur + id event. **Batas:** DRAF AI ikut dicetak (berlabel), dan draf itu bisa mengulang narasi penyerang (temuan tinjauan, `BUKTI_EVALUASI.md` §11). Menurut ukuran tim, gema turun dari 14/176 (v1.1) ke 0/176 (v1.2.2, post-hoc, §14), tetapi probe juri baru masih lolos, jadi draf tetap dianggap tidak tepercaya |
| Audit dipotong di ujung | **prosedur, belum dikode/diuji:** jangkar harian, yaitu hash terakhir (`triase.py --verify` mencetak `head`) dicatat di luar perangkat (buku jaga) |
| Ringkasan menyesatkan (halusinasi) | v1: hanya URL/e-mail/IP/host yang disaring. v1.1: ringkasan utama dari aturan, draf AI disaring per kalimat (istilah eskalatif tanpa dukungan log dibuang). v1.2.2: kalimat harus menyebut bukti, dan kalimat yang menyarankan penutupan/aksi, mengklaim otoritas, meminta kredensial, atau menyalin teks log dibuang (daftar kata; parafrase baru masih bisa lolos, `BUKTI_EVALUASI.md` §14). Kewajiban event ID per kalimat masih **rencana**. Contoh nyata: "terorisme" di demo |
| Data keluar | mesin (`prototype/perisai`) tidak punya kode jaringan. Aplikasi desktop (`app/`) menjalankan server lokal yang hanya mendengar di `127.0.0.1`, memeriksa header Host, dan memasang CSP `connect-src 'self'`; tidak ada koneksi keluar. Mode demo Docker mendengar di `0.0.0.0` tetapi hanya memuat data contoh dan menolak unggahan |

## 6b. v1.1 (pasca-evaluasi)
`perisai/v11.py`: kategori + aksi dari aturan, LLM hanya DRAF AI, tanpa penutupan kasus otomatis, dan penyaring kalimat. 8 tes di `tests/test_v11.py`. Total 102 tes lulus, termasuk `test_v12.py` (6), `test_v121_guard.py` (16), `test_v122_probes.py` (30), `test_ot.py` (5), dan `test_triase.py` (5). **v1.2** (`perisai/v12.py`) dipakai `demo.py` dan `triase.py`. Isolasi hanya diusulkan dengan bukti cukup (1 aturan high atau 2 aturan), dan draf AI dijaga (lihat `BUKTI_EVALUASI.md` §12). Replay post-hoc: `scripts/posthoc_v11.py` → `results/posthoc_v11.json`. Detail di `BUKTI_EVALUASI.md` §9. Catatan: docstring `firewall.py` menyebut pola ditulis "sebelum" keluarga uji, padahal yang benar menurut PRAREG §0 adalah in-sample. Berkas itu tidak diubah karena di-hash.

## 7. Lisensi komponen
Qwen2.5 (Apache-2.0) · llama.cpp/llama-cpp-python (MIT) · OTRF Security-Datasets (MIT) · HAI 21.03 (CC BY-SA 4.0, data tidak ikut repo) · numpy/pandas (BSD) · kode PERISAI MIT (`LICENSE`). Llama tidak dipakai karena *Acceptable Use Policy*-nya melarang penggunaan militer.

## 8. Keterbatasan
Lihat `PROPOSAL.md` §7 dan `BUKTI_EVALUASI.md`.
