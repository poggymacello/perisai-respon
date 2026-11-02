# DATA.md: aset yang diunduh (29 Okt 2026)

Semua aset publik, tanpa login, dan masing-masing di bawah 1 GB. Folder `models/` dan `data/` tidak masuk git (`.gitignore`).

## Model
| | |
|---|---|
| Nama | Qwen2.5-1.5B-Instruct GGUF, kuantisasi **q3_k_m** |
| Repo resmi | https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct-GGUF (tidak di-gate; `gated: false` menurut API HF) |
| Revisi | `91cad51170dc346986eccefdc2dd33a9da36ead9` |
| URL berkas | https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct-GGUF/resolve/91cad51170dc346986eccefdc2dd33a9da36ead9/qwen2.5-1.5b-instruct-q3_k_m.gguf |
| Lokal | `models/qwen2.5-1.5b-instruct-q3_k_m.gguf` |
| Ukuran | 924.455.968 byte (0,92 GB) |
| SHA-256 | `58cb5c05ecef48e82961f1a2be6544145ea26136f69dddda4bbbd092f0e4b993` (cocok dengan LFS oid di API HF) |
| Lisensi | Apache-2.0 (`models/LICENSE.qwen`, diunduh dari revisi yang sama). Llama dan Gemma **tidak** dipakai |

## Runtime
`llama-cpp-python` 0.3.36, wheel CPU prebuilt `llama_cpp_python-0.3.36-py3-none-win_amd64.whl` (7,8 MB) dari index `https://abetlen.github.io/llama-cpp-python/whl/cpu`. Wheel terpasang tanpa build (`--only-binary=:all:`). Lisensi MIT. Versi paket lain: `requirements-lock.txt`.

## Log berlabel
| | |
|---|---|
| Nama | OTRF Security-Datasets (Mordor) |
| Sumber | https://github.com/OTRF/Security-Datasets, commit `d9d40ef123d2c87d5d3df28c96bcab4f0faccc87` (20 Sep 2023) |
| Lisensi | MIT ("Copyright (c) 2021 Open Threat Research Forge") |
| Subset | semua `datasets/atomic/windows/<taktik>/host/*` (122 arsip zip/tar.gz/json) + 100 metadata `datasets/atomic/_metadata/SDWIN-*.yaml` |
| Ukuran | ±101 MB di disk (`data/otrf/zips/`). Daftar berkas + ukuran + git-sha: `data/otrf/filelist.txt`. Pohon repo: `data/otrf/tree_master.json` |
| Label | folder taktik ATT&CK dari OTRF, per rekaman |

**Windows Defender:** arsip `discovery__empire_shell_net_local_users.zip` dikarantina Defender (VirTool:PowerShell/Empire) dua kali, pada 00:50 dan 00:52, sehingga **dikeluarkan**. Total yang dipakai: 121 rekaman. File teks kasus yang sempat ditulis polos (`frozen/cases_dev.jsonl`, berisi command line Mimikatz/Empire dari log) juga dikarantina (HackTool:Win32/Mikatz). Karena itu kasus sekarang dibangun di memori dari arsip asli, dan yang dibekukan hanya manifes SHA-256 (`frozen/manifest_test.json`). Pengaturan Defender **tidak** diubah dan tidak ada pengecualian yang ditambahkan.

## Telemetri OT (ditambahkan 29 Okt 2026, PRAREG v4)
| | |
|---|---|
| Nama | HAI (HIL-based Augmented ICS) Security Dataset, versi **21.03** (boiler P1, turbin P2, air P3, simulasi HIL P4) |
| Sumber | https://github.com/icsdataset/hai, commit `2a814cebc9a66b06c9e5cd545e2d72e65d383737`, folder `hai-21.03/` (berkas `.csv.gz` biasa, bukan LFS) |
| Lisensi | **CC BY-SA 4.0** (README repo, bagian License; salinan `data/hai/README.hai.md`). Atribusi: Shin, Lee, Yun, Min (The Affiliated Institute of ETRI), "Two ICS Security Datasets and Anomaly Detection Contest on the HIL-Based Augmented ICS Testbed", 2021 |
| Berkas | `train1` 30,7 MB · `train2` 31,4 MB · `train3` 68,0 MB (normal) · `test1` 6,1 MB · `test4` 5,6 MB (berlabel serangan). Total ±142 MB di `data/hai/` |
| SHA-256 | tercantum di `PRAREG_v4_OT_BENIGN.sha256` |

## Log benign Windows: dicari, tidak dipakai
- COMISET (Zenodo 15375146, CC BY 4.0): 4,9 GB + 31,7 GB, di atas batas 1 GB.
- arniki/atomic-evtx (punya folder benign): repo tidak berlisensi.
- Pengganti: semua teks bebas asli di 121 rekaman OTRF dipindai firewall (`scripts/benign_firewall.py`) + data normal HAI.

## Skenario injeksi
Dibuat sendiri (`perisai/scenarios.py`): 3 keluarga string teks (override EN, override ID, tag sistem palsu) × 4 tujuan. Isinya hanya string uji di field log sistem kita sendiri. Host dan IP fiktif, domain memakai TLD cadangan `.invalid` (RFC 2606), dan tidak ada kode maupun target nyata. Keluarga uji yang ditahan **tidak dibuat** untuk PRAREG v1 (lihat `PRAREG.md` §0). Keluarga tertahan dibuat kemudian untuk PRAREG v3 (`perisai/scenarios_heldout.py`: 4 pembungkus bergaya log × 4 tujuan dalam bahasa alami, target sama, domain `.invalid`).
