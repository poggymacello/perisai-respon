# PERISAI-RESPON (prototipe, Kartika Cyber Hackathon 2026)

Asisten triase insiden yang berjalan **offline** di laptop. LLM lokal **mengusulkan** ringkasan triase berbahasa Indonesia dan satu aksi dari daftar tertutup. **Policy engine yang memutuskan**, dan manusia menyetujui aksi berisiko. Semua langkah dicatat di log audit berantai hash. Produk ini **hanya defensif**: datanya log publik berlabel, injeksi berupa string uji di sistem sendiri, dan tidak ada sistem nyata yang disentuh.

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

.venv\Scripts\python -I demo.py              # demo 6 skenario, ±1-2 menit dengan LLM
.venv\Scripts\python -I demo.py --no-llm     # demo mode degradasi, < 1 detik
.venv\Scripts\python -I -m pytest -q -p no:cacheprovider tests   # 33 tes (v1 + v1.1), < 1 detik
.venv\Scripts\python -I scripts\posthoc_v11.py                  # v1.1 pasca-evaluasi -> results\posthoc_v11.json
.venv\Scripts\python -I scripts\make_rating_packet.py           # bahan penilaian buta PRAREG v2
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

## v1.1 (pasca-evaluasi)
`perisai/v11.py`: kategori + aksi dari aturan (P2 gagal), LLM hanya DRAF AI yang disaring per kalimat, tidak ada penutupan kasus otomatis. Kode v1 yang di-hash tidak diubah. Lihat `../05_BUKTI.md` §9 dan `PRAREG_v2_DRAF_AI.md`.

## Struktur
| Path | Isi |
|---|---|
| `perisai/logs.py` | pembaca arsip OTRF (zip/tar.gz/json, tidak diekstrak ke disk), normalisasi field terstruktur vs teks bebas |
| `perisai/detector.py` | 33 aturan gaya Sigma (bukan port SigmaHQ resmi), pra-filter, baseline template |
| `perisai/firewall.py` | sanitasi, dekode, deteksi pola, redaksi, spotlighting |
| `perisai/policy.py` | policy engine + mode degradasi |
| `perisai/llm.py` | llama.cpp, prompt naif/terjaga, parser JSON |
| `perisai/audit.py` | audit hash-chain |
| `perisai/scenarios.py` | string injeksi uji (3 keluarga × 4 tujuan) |
| `perisai/metrics.py` | definisi sukses serangan, bootstrap klaster, Holm |
| `PRAREG.md` / `PRAREG.sha256` | prareg yang dibekukan sebelum run uji |
| `frozen/` | split, manifes kasus uji, hash kode |
| `results/` | `runs*.csv`, `summary.json`, `endpoints.csv`, `asr_breakdown.csv`, `fig_endpoints.png`, `demo/`, `pytest_output.txt` |

## Batasan utama
Lihat `PRAREG.md` §0 dan §6 serta `../05_BUKTI.md`. Singkatnya: keluarga injeksi yang diuji bersifat **in-sample**, semua log berasal dari satu lab, dan satu model kecil.
