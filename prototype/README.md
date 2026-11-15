# PERISAI-RESPON (prototipe, Kartika Cyber Hackathon 2026)

Asisten triase insiden yang berjalan **offline** di laptop. LLM lokal **mengusulkan** ringkasan triase berbahasa Indonesia dan satu aksi dari daftar tertutup. **Policy engine yang memutuskan**, dan manusia menyetujui aksi berisiko. Semua langkah dicatat di log audit berantai hash. Produk ini **hanya defensif**: datanya log publik berlabel, injeksi berupa string uji di sistem sendiri, dan tidak ada sistem nyata yang disentuh.

## Mana yang berlaku
Folder ini menyimpan semua rencana uji (prareg), termasuk yang dibatalkan, karena berkas yang sudah di-hash tidak diubah atau dihapus. Status resmi setiap prareg ada di [`PRAREG_STATUS.md`](PRAREG_STATUS.md). Ringkasnya:

| Berkas | Status | Isi |
|---|---|---|
| `PRAREG.md` (v1) | **Berlaku.** Dikunci SHA-256 dan dijalankan 29 Okt 2026. P1 lulus, P2 gagal | angka utama di README dan `docs/BUKTI_EVALUASI.md` |
| `PRAREG_v3_HELDOUT.md` | **Berlaku.** Dijalankan 29 Okt. Deteksi pola 0 %, H-P1 v1 gagal | injeksi keluarga tertahan |
| `PRAREG_v4_OT_BENIGN.md` | **Berlaku.** Dijalankan 29 Okt. 10/10 episode, tanda palsu 0/260.351 | jalur OT dan tanda palsu firewall |
| `PRAREG_v24_DRAF_AI.md`, `PROKTOR_v24.md`, `PANDUAN_PENULIS_v24.md` | **Dibekukan 2 Nov, belum dijalankan.** Butuh penulis ringkasan manusia dan penilai dari luar tim | rancangan penilaian buta nilai draf AI |
| `PRAREG_v2_DRAF_AI.md`, `PRAREG_v21_DRAF_AI.md`, `PRAREG_v22_DRAF_AI.md`, `PRAREG_v23_DRAF_AI.md`, `PROKTOR_v23.md` | **Batal, tidak pernah dijalankan.** Rancangannya tidak buta. Jangan dipakai | arsip saja. Hash dokumen v2.1 sampai v2.3 gagal karena catatan status ditulis sesudah pembekuan (diungkap) |

Berkas pendukung:
- `results/rating/` dan `results/rating_v21/` sampai `results/rating_v23/`: lembar penilaian buta untuk prareg v2 sampai v2.3 yang batal. Kolom nilainya kosong karena penilaian tidak pernah dilakukan. Kunci pembukanya (`kunci.csv`, berisi salt) sengaja tidak ikut git.
- `results/rating_v24/tulis_ringkasan_aturan.csv`: lembar kosong untuk penulis ringkasan manusia v2.4. Lembar ini di-hash dalam keadaan kosong.
- `scripts/make_rating_packet*.py`: pembuat lembar di atas, satu skrip per versi prareg.
- `frozen/`: split dev/uji, manifes hash kasus uji, dan hash kode (`CODE_*.sha256`) yang dibuat sebelum run. Salinan tiga hash kode ada di `app/perisai_app/engine_meta/`, dan `app/tools/build.py` mencocokkan mesin dengan hash itu sebelum membangun exe.
- Prareg dan hash yang dibekukan masih menyebut "juri P#" (mis. "juri P5 N21"). Artinya reviewer internal (simulasi) putaran 5, temuan no. 21: tinjauan kritis yang diadakan tim sendiri sebelum submisi, bukan penilaian juri lomba.

```
log (OTRF, JSON) -> pembaca/normalisasi -> detektor gaya Sigma (pra-filter 8 event + temuan aturan)
   -> firewall masukan (sanitasi, dekode, pola injeksi EN/ID, redaksi, spotlighting «DATA»)
   -> LLM lokal Qwen2.5-1.5B q3_k_m (usulan JSON: kategori, ringkasan, aksi, bukti)
   -> policy engine (allowlist aksi, aturan bukti, aset terlindungi, persetujuan manusia, saring ringkasan)
   -> audit log hash-chain (SHA-256)
LLM mati / keluaran rusak -> mode degradasi: kategori + aksi dari template aturan (tetap aman)
```

Asal-usul: pola "LLM mengusulkan, kebijakan memutuskan", detektor injeksi EN/ID, dan audit berantai hash **diadaptasi dari Kendali** (`TIM/FinTechathon2026/kendali`, MIT, pemilik Poggy Macello Gultom & Mohammad Ari Alexander Aziz). Folder Kendali tidak diubah. Pola evaluasi (prareg ber-hash, bootstrap klaster, Holm) mengikuti DetakPompa (`ITSHackathon2026/prototype`).

## Cara jalan (Windows, PowerShell, dari folder `prototype`)
```powershell
python -m venv .venv
.venv\Scripts\python -m pip install numpy pandas pytest matplotlib pyyaml
.venv\Scripts\python -m pip install --only-binary=:all: llama-cpp-python --extra-index-url https://abetlen.github.io/llama-cpp-python/whl/cpu
# model (0,92 GB, Apache-2.0, tanpa login) -> models\  (URL + SHA-256 di DATA.md)
# data OTRF (MIT) -> data\otrf\zips\  (daftar berkas di DATA.md / data\otrf\filelist.txt)

.venv\Scripts\python -I demo.py              # demo 8 skenario (termasuk OT), ±1 menit dengan LLM
.venv\Scripts\python -I demo.py --no-llm     # demo mode degradasi, < 1 detik
.venv\Scripts\python -I -m pytest -q -p no:cacheprovider tests   # 102 tes (v1, v1.1, v1.2.x, OT, importer, perangkat v2.4), < 2 detik
.venv\Scripts\python -I triase.py --input security.xml           # triase log ASLI -> laporan CSIRT + audit (lihat bawah)
.venv\Scripts\python -I scripts\run_heldout.py --shard 0/2 --threads 6   # PRAREG v3 injeksi tertahan (+ --shard 1/2)
.venv\Scripts\python -I scripts\analyze_heldout.py              # -> results\heldout\summary.json
.venv\Scripts\python -I scripts\run_ot.py                       # PRAREG v4 A: detektor OT HAI -> results\ot\
.venv\Scripts\python -I scripts\benign_firewall.py              # PRAREG v4 B: tanda palsu firewall -> results\benign\
.venv\Scripts\python -I scripts\posthoc_v11.py                  # v1.1 pasca-evaluasi -> results\posthoc_v11.json
.venv\Scripts\python -I scripts\posthoc_v12.py                  # v1.2 pasca-evaluasi -> results\posthoc_v12.json
.venv\Scripts\python -I scripts\make_rating_packet_v24.py --lembar-tulis   # PRAREG v2.4 (rancangan): ringkasan aturan ditulis manusia; v2-v2.3 tidak dipakai
.venv\Scripts\python -I scripts\make_split.py                    # split dev/uji dari metadata
.venv\Scripts\python -I run_eval.py --manifest                   # manifes hash kasus uji
.venv\Scripts\python -I run_eval.py --shard 0/2 --threads 6      # + jendela kedua: --shard 1/2
.venv\Scripts\python -I analyze.py                               # endpoint -> results\summary.json
sha256sum -c PRAREG.sha256                                       # cek prareg (Git Bash)
```
Versi yang dipakai tercatat di `requirements-lock.txt` (Python 3.11.9).

**Catatan Windows Defender:** teks log mentah OTRF berisi string Mimikatz/Empire, sehingga Defender mengkarantina berkas yang memuatnya bila ditulis polos (lihat `DATA.md`). Karena itu kasus dibangun di memori dan tidak ditulis ke disk. Jangan menonaktifkan Defender. Demo memakai event sintetis.

## Kebutuhan hardware dan waktu (diukur di laptop ini)
- CPU Intel i7-13620H (10 core / 16 thread), RAM 32 GB, tanpa GPU. Model + konteks 4096 memakai ±1,5 GB RAM.
- Satu panggilan LLM per kasus (8 event, ±1.000–2.500 token prompt) di CPU: angka median/p90 ada di `results/summary.json` → `S_latency`.
- Firewall + policy: < 10 ms per kasus. Mode degradasi tanpa LLM: < 10 ms.
- Evaluasi penuh (88 kasus uji × 2 + 176 unit injeksi × 3 = 704 panggilan LLM) memakan beberapa jam dengan 2 proses × 6 thread.

## Triase log Windows asli
```powershell
wevtutil qe Security /c:500 /rd:true /f:xml > security.xml
wevtutil qe Microsoft-Windows-Sysmon/Operational /c:500 /rd:true /f:xml > sysmon.xml
.venv\Scripts\python -I triase.py --input security.xml --input sysmon.xml          # mode aturan, < 1 detik
.venv\Scripts\python -I triase.py --input security.xml --llm                       # + DRAF AI (hash model dicek dulu)
.venv\Scripts\python -I triase.py --verify results\triase\<waktu>\audit.jsonl
```
Keluarannya ada di `results\triase\<waktu>\laporan.md` (tidak masuk git). Contoh dari log sintetis: `results\contoh_laporan\laporan.md`. Log asli satuan jangan di-commit.

## v1.1 (pasca-evaluasi)
`perisai/v11.py`: kategori + aksi dari aturan (P2 gagal), LLM hanya DRAF AI yang disaring per kalimat, tidak ada penutupan kasus otomatis. Kode v1 yang di-hash tidak diubah. Lihat `../docs/BUKTI_EVALUASI.md` §9 dan `PRAREG_v2_DRAF_AI.md` (batal, lihat "Mana yang berlaku").

## Struktur
| Path | Isi |
|---|---|
| `perisai/logs.py` | pembaca arsip OTRF (zip/tar.gz/json, tidak diekstrak ke disk), normalisasi field terstruktur vs teks bebas |
| `perisai/detector.py` | 37 aturan gaya Sigma (bukan port SigmaHQ resmi), pra-filter, baseline template |
| `perisai/firewall.py` | sanitasi, dekode, deteksi pola, redaksi, spotlighting |
| `perisai/policy.py` | policy engine + mode degradasi |
| `perisai/llm.py` | llama.cpp, prompt naif/terjaga, parser JSON |
| `perisai/audit.py` | audit hash-chain |
| `perisai/scenarios.py` | string injeksi uji (3 keluarga × 4 tujuan) |
| `perisai/scenarios_heldout.py` | keluarga injeksi tertahan PRAREG v3 (4 × 4, tujuan dalam bahasa alami) |
| `perisai/importer.py`, `triase.py` | importer XML wevtutil/Get-WinEvent + JSON, CLI triase |
| `perisai/laporan.py` | laporan insiden CSIRT (Markdown) |
| `perisai/integrity.py` | cek SHA-256 model sebelum dimuat |
| `perisai/v12.py` | v1.2: syarat bukti isolasi + penjaga draf AI (pasca-evaluasi) |
| `perisai/ot.py` | jalur OT: detektor amplop HAI, kasus OT, kebijakan aset proses |
| `PRAREG_v2_DRAF_AI.md` (v2–v2.3 tidak buta, digantikan rancangan v2.4), `PRAREG_v3_HELDOUT.md`, `PRAREG_v4_OT_BENIGN.md` | prareg tambahan + `.sha256` |
| `perisai/metrics.py` | definisi sukses serangan, bootstrap klaster, Holm |
| `PRAREG.md` / `PRAREG.sha256` | prareg yang dibekukan sebelum run uji |
| `frozen/` | split, manifes kasus uji, hash kode |
| `results/` | `runs*.csv`, `summary.json`, `endpoints.csv`, `asr_breakdown.csv`, `fig_endpoints.png`, `demo/`, `pytest_output.txt` |

## Batasan utama
Lihat `PRAREG.md` §0 dan §6 serta `../docs/BUKTI_EVALUASI.md`. Singkatnya:
- P1 bersifat **in-sample**. Keluarga tertahan diuji terpisah di PRAREG v3, tetapi ditulis oleh penulis yang sama.
- Semua log Windows berasal dari satu lab.
- Hanya ada satu model kecil.
- Log benign Windows berlabel tidak tersedia.

`sha256sum -c` atas `PRAREG_v4_OT_BENIGN.sha256` dan `PRAREG_v2_DRAF_AI.sha256` akan gagal untuk berkas data (`data/hai/*`, `results/rating/kunci.csv`) di salinan repo, karena berkas itu sengaja tidak ikut git. Berkas kode dan dokumen tetap bisa dicek.
