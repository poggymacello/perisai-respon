# Laporan Insiden PERISAI-RESPON · 2026-10-30T07:18:07+00:00

> Dibuat otomatis. Semua aksi berisiko **menunggu persetujuan analis**; tidak ada aksi yang dijalankan sistem.

| | |
|---|---|
| Sumber log | tests\fixtures\contoh_wevtutil.xml |
| Jumlah event / kasus | 5 / 2 (+1 kelompok event tanpa temuan aturan, tidak dibuat kasus) |
| LLM | mati (mode aturan) |
| Integritas model | tidak dipakai (mode aturan) |
| Audit | 8 entri, utuh = **True**, head `dbba1495d43068fefbf7b8087c075e03dc26b8917e8eef59768fc8663c38e814` |

## Ringkasan

| # | Kasus | Host | Kategori | Aksi akhir | Status | Peringatan |
|---|---|---|---|---|---|---|
| 1 | WS-LOG03.batalyon.lab@2026-10-29T02:00:00+00:00 | WS-LOG03.batalyon.lab | credential_access | escalate | DIESKALASI | INJEKSI_TERDETEKSI |
| 2 | SRV-ARSIP02.batalyon.lab@2026-10-29T03:30:00+00:00 | SRV-ARSIP02.batalyon.lab | lateral_movement | escalate | DIESKALASI | - |

## 1. WS-LOG03.batalyon.lab@2026-10-29T02:00:00+00:00

**Ringkasan aturan:** Indikasi pencurian kredensial pada WS-LOG03.batalyon.lab: Akses memori proses LSASS oleh proses non-sistem; Proses berjalan dari lokasi sementara / berkas disamarkan; Logon jaringan (tipe 3) dari alamat jarak jauh. 3 event dianalisis. Ringkasan dibuat dari template aturan (tanpa LLM).

**Alasan keputusan:**
- LLM dimatikan
- kategori dari template aturan (CA01, DE07, LM08)
- firewall menemukan instruksi di isi log: aksi berisiko tidak diusulkan
- v1.1: kategori dan aksi dari template aturan (CA01, DE07, LM08)
- instruksi terdeteksi di isi log: aksi berisiko tidak diusulkan, kasus dieskalasi

**Bukti (field terstruktur):**

| id | EventID | Channel | TimeCreated | Hostname | TargetUserName | LogonType | Image | ParentImage | TargetImage | SourceImage | GrantedAccess | IpAddress |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| E1 | 10 | Microsoft-Windows-Sysmon/Operational | 2026-10-29T02:01:05.1234567Z | WS-LOG03.batalyon.lab |  |  |  |  | C:\Windows\system32\lsass.exe | C:\Users\Public\updater.exe | 0x1010 |  |
| E2 | 4624 | Security | 2026-10-29T02:02:11.0000000Z | WS-LOG03.batalyon.lab | operator2 | 3 |  |  |  |  |  | 172.16.20.44 |
| E3 | 1 | Microsoft-Windows-Sysmon/Operational | 2026-10-29T02:03:40.5000000Z | WS-LOG03.batalyon.lab |  |  | C:\Users\Public\updater.exe | C:\Windows\explorer.exe |  |  |  |  |

**Jejak audit:** #0 firewall `b771271e64d6f276`, #1 usulan_llm `4c973a8c5e185eb4`, #2 keputusan_policy `e41398d4e761c7f9`, #3 keputusan_v12 `49c4bef0549213e1`

Persetujuan analis: ☐ setuju ☐ tolak · nama/NRP: `[[...]]` · waktu: `[[...]]`

## 2. SRV-ARSIP02.batalyon.lab@2026-10-29T03:30:00+00:00

**Ringkasan aturan:** Indikasi pergerakan lateral pada SRV-ARSIP02.batalyon.lab: Pemasangan layanan baru (7045/4697). 1 event dianalisis. Ringkasan dibuat dari template aturan (tanpa LLM).

**Alasan keputusan:**
- LLM dimatikan
- kategori dari template aturan (LM02)
- v1.1: kategori dan aksi dari template aturan (LM02)
- v1.2: bukti isolasi kurang (LM02: butuh 1 aturan high atau 2 aturan berbeda di kategori ini): dieskalasi

**Bukti (field terstruktur):**

| id | EventID | Channel | TimeCreated | Hostname | ServiceName |
|---|---|---|---|---|---|
| E1 | 7045 | System | 2026-10-29T03:30:00.0000000Z | SRV-ARSIP02.batalyon.lab | UpdSvc |

**Jejak audit:** #4 firewall `62de706c81277845`, #5 usulan_llm `ba57b7862d295a08`, #6 keputusan_policy `2bd47d781711cae1`, #7 keputusan_v12 `dbba1495d43068fe`

Persetujuan analis: ☐ setuju ☐ tolak · nama/NRP: `[[...]]` · waktu: `[[...]]`

---
Teks bebas log tidak disalin ke laporan. Buka log asli dengan id event di atas. Cek audit: `python -I triase.py --verify results\contoh_laporan\audit.jsonl`
