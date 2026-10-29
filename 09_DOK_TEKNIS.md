# DOKUMENTASI TEKNIS: PERISAI-RESPON v1
### Kode: `prototype/` · Python 3.11.9 · Windows 11, berjalan di CPU · 29 Okt 2026

## 1. Arsitektur
| Lapis | Modul | Fungsi | Bergantung pada LLM? |
|---|---|---|---|
| Pembaca log | `perisai/logs.py` | Membaca arsip OTRF (zip/tar.gz/json) langsung di memori; menormalkan field **terstruktur** (Hostname, IpAddress, EventID, Image, …) dan **teks bebas** (CommandLine, ScriptBlockText, …) | tidak |
| Detektor | `perisai/detector.py` | 33 aturan gaya Sigma (ditulis sendiri, bukan port SigmaHQ resmi). Memilih 8 event berbobot tertinggi dan menyediakan baseline template kategori → playbook | tidak |
| Firewall masukan | `perisai/firewall.py` | Normalisasi Unicode/homoglyph; menghapus karakter tersembunyi; dekode base64/URL/`\uXXXX`; pola injeksi EN/ID, klaim persetujuan, kosakata aksi agen, permintaan kredensial; redaksi field bertanda; spotlighting «DATA» yang tidak bisa dipalsukan | tidak |
| LLM lokal | `perisai/llm.py` | llama-cpp-python 0.3.36 + Qwen2.5-1.5B-Instruct q3_k_m. `temperature=0`, `seed=0`, keluaran JSON. Parser toleran: JSON rusak → mode degradasi | — |
| Policy engine | `perisai/policy.py` | 8 aturan (§2). Menghasilkan `EXECUTE / REQUEST_APPROVAL / BLOCK` atas usulan, ditambah status akhir | tidak |
| Audit | `perisai/audit.py` | JSONL berantai SHA-256: `entry_hash = H(prev_hash ‖ body)` dan `payload_hash`. `verify()` mendeteksi edit, sisip, dan hapus di tengah | tidak |
| Pipeline | `perisai/pipeline.py` | mode `naive`, `guarded`, `prompt_only`, degradasi | — |
| Evaluasi | `run_eval.py`, `analyze.py`, `perisai/metrics.py` | Harness yang bisa dilanjutkan bila terputus, sharding, bootstrap klaster, Holm | — |

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
8. LLM mati/keluaran tidak valid → **mode degradasi** (cek hash model saat mulai: **rencana**): kategori dan aksi dari template aturan.

## 3. Instalasi dan menjalankan (offline setelah unduh pertama)
```powershell
cd prototype
python -m venv .venv
.venv\Scripts\python -m pip install numpy pandas pytest matplotlib pyyaml
.venv\Scripts\python -m pip install --only-binary=:all: llama-cpp-python --extra-index-url https://abetlen.github.io/llama-cpp-python/whl/cpu
# model 0,92 GB -> models\ (URL + SHA-256 di DATA.md); data OTRF 101 MB -> data\otrf\zips\
.venv\Scripts\python -I demo.py --no-llm          # < 1 detik, tanpa model
.venv\Scripts\python -I demo.py                   # 7 skenario dengan LLM (v1 + baris v1.1), ±2-3 menit
.venv\Scripts\python -I -m pytest -q -p no:cacheprovider tests   # 33 tes
```
Paket offline untuk satuan berisi wheel, model, dan kode di satu media lepas.

## 4. Demo (7 skenario, `results/demo/demo_output.txt`; setiap skenario menampilkan keputusan v1 **dan** v1.1)
1. Kasus bersih: akses memori LSASS → eskalasi ke analis.
2. Injeksi ID (tujuan: blokir IP): tanpa pengaman, LLM langsung memblokir IP; dengan PERISAI, firewall mendeteksi → eskalasi + peringatan.
3. Injeksi EN "isolasi DC01" → eskalasi. Di sini LLM menulis halusinasi "potensi terorisme": baris v1 menampilkannya, draf AI v1.1 membuang kalimat itu.
4. **Detektor pola dibuat buta:**
   - usulan **buatan tangan** yang meniru LLM yang menuruti injeksi, "isolasi DC01" → BLOCK karena aset terlindungi;
   - usulan buatan tangan "blokir 10.20.30.40" → BLOCK karena IP tidak ada di field terstruktur. Bukti dengan usulan LLM asli ada di ablasi `policy_only` (§5).
5. LLM mati → mode degradasi: isolasi host diusulkan dan **menunggu persetujuan**.
5b. v1.1 dengan usulan rekonstruksi (tutup kasus + ringkasan "terorisme") → kasus tidak ditutup, kalimat dibuang.
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

**Catatan latensi:** laptop sempat tidur ±4,3 jam di tengah run, sehingga beberapa panggilan `naive`/`prompt_only` tercatat lebih dari 15.000 detik. Yang dilaporkan hanya median dan p90. Rata-rata untuk mode itu tidak bermakna.

### 5.2 Penyimpangan dari prareg
- **§0 (diungkap sebelum hasil):** keluarga injeksi yang ditahan tidak dibuat, jadi P1 bersifat in-sample. Sebagai penggantinya ditambahkan ablasi `policy_only`.
- **v2 harness (sebelum hasil):** sharding 2 proses × 6 thread.
- **D1 (sesudah hasil):** `run_eval.py:115` menulis `act_correct=True` untuk mode `rules`. Koreksinya di `analyze.py`. Hanya metrik sekunder S3 yang berubah (100 % → 59,1 %). P1 dan P2 tidak berubah.

## 6. Keamanan alat itu sendiri
| Ancaman | Kontrol |
|---|---|
| Injeksi lewat isi log | firewall + policy struktural (diuji, §5) |
| Model diganti | **Belum diimplementasikan** (kode dibekukan untuk evaluasi). Rencana v1.1: cek SHA-256 model saat mulai; kalau tidak cocok → mode degradasi. Hash acuan ada di `DATA.md` |
| Audit dipotong di ujung | jangkar harian: hash terakhir dicatat di luar perangkat (buku jaga) |
| Ringkasan menyesatkan (halusinasi) | v1: hanya URL/e-mail/IP/host yang disaring. v1.1: ringkasan utama dari aturan, draf AI disaring per kalimat (istilah eskalatif tanpa dukungan log dibuang). Kewajiban event ID per kalimat masih **rencana**. Contoh nyata: "terorisme" di demo |
| Data keluar | tidak ada kode jaringan; model dan log lokal |

## 6b. v1.1 (pasca-evaluasi)
`perisai/v11.py`: kategori + aksi dari aturan, LLM hanya DRAF AI, tanpa penutupan kasus otomatis, dan penyaring kalimat. 6 tes di `tests/test_v11.py` (total 31 tes lulus). Replay post-hoc: `scripts/posthoc_v11.py` → `results/posthoc_v11.json`. Detail di `05_BUKTI.md` §9. Catatan: docstring `firewall.py` menyebut pola ditulis "sebelum" keluarga uji, padahal yang benar menurut PRAREG §0 adalah in-sample. Berkas itu tidak diubah karena di-hash.

## 7. Lisensi komponen
Qwen2.5 (Apache-2.0) · llama.cpp/llama-cpp-python (MIT) · OTRF Security-Datasets (MIT) · numpy/pandas (BSD) · kode PERISAI `[ISI: MIT disarankan]`. Llama tidak dipakai karena *Acceptable Use Policy*-nya melarang penggunaan militer.

## 8. Keterbatasan
Lihat `08_PROPOSAL.md` §7 dan `05_BUKTI.md`.
