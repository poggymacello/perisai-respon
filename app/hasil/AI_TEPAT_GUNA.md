# AI tepat guna di PERISAI-RESPON

Prinsip: LLM dipakai untuk bahasa, aturan untuk keputusan, statistik untuk sensor OT, dan penjaga deterministik untuk memeriksa keluaran AI. Setiap baris di bawah punya bukti berupa berkas dan angka yang bisa diulang. Angka evaluasi lama diambil dari `docs/BUKTI_EVALUASI.md`; angka baru berasal dari `app/tools/ukur_konsistensi_draf.py` dan tes `app/tests/`.

| Tugas | Alat | Alasan | Bukti (berkas, angka) |
|---|---|---|---|
| Menentukan kategori insiden dan aksi | Aturan (template detektor + playbook) | LLM 1,5B lebih buruk dari aturan dalam menebak kategori | `docs/BUKTI_EVALUASI.md` §3, P2: LLM+firewall 35,2 % vs aturan 50,0 % (selisih −14,8 pp [−30,6; −2,7]) |
| Menahan injeksi perintah di isi log | Penjaga: firewall pola + policy engine | Isi log bisa ditulis penyerang; aksi tidak boleh bisa disetir teks | `docs/BUKTI_EVALUASI.md` §3, P1: keberhasilan injeksi 16,5 % → 0,0 %; ablasi policy saja 0,57 % (1/176); §11 held-out: firewall pola menangkap 0/176, jadi yang menahan adalah aturan struktural |
| Menulis ringkasan kasus dalam Bahasa Indonesia | LLM lokal Qwen2.5-1.5B (offline, CPU) | Tugas bahasa; tidak dipakai untuk kategori atau aksi | `docs/BUKTI_EVALUASI.md` §3: median 28,7 dtk per kasus di CPU; nilai kegunaan draf bagi analis belum menjadi angka final |
| Menyaring kalimat draf AI | Penjaga `guard_draft` v1.2.2 (deterministik) | Draf bisa disetir isi log; kalimat harus terikat ke bukti terstruktur | `prototype/results/posthoc_v12.json`: kasus bersih 3/103 kalimat dibuang, gema injeksi held-out 0/176 (ukuran dibuat penulis yang sama, sebagian menurut konstruksi) |
| Memeriksa kategori yang disebut draf AI | Penjaga baru `app/perisai_app/cekdraf.py` (deterministik) | Draf yang menamai kategori lain dari aturan bisa menyesatkan analis | `app/hasil/konsistensi_draf.md`: 175 dari 421 draf tersimpan (41,6 %) menamai kategori yang tidak didukung aturan dan kini ditandai; uji petik 10/10 penandaan tepat dan 10/10 tidak-ditandai tepat (dibaca asisten AI generatif, belum oleh peninjau independen) |
| Mendeteksi anomali sensor OT | Statistik: amplop normal per tag (79 tag) | Data proses numerik; tidak perlu LLM | `docs/BUKTI_EVALUASI.md` §10.2 (HAI 21.03): recall jendela 92,9 % (test1) dan 95,7 % (test4); alarm palsu 5,4 % (test1) dan 0,0 % (test4) |
| Melindungi aset OT yang muncul di log IT | Penjaga baru `app/perisai_app/asetot.py` (awalan HMI-/PLC-/SCADA-/RTU-/EWS-/SIS- + daftar satuan) | Daftar aset terlindungi mesin di jalur IT hanya berisi nama host tetap | `app/tests/test_asetot.py`: host HMI-POMPA01 sebelumnya `isolate_host` (menunggu persetujuan), sesudahnya eskalasi ke insinyur proses dengan entri audit `penjaga_aset_ot` |
| Mengurangi beban baca analis | Aturan (pra-filter event + pengelompokan) | Pemilihan event harus bisa dijelaskan dan diulang | `app/hasil/konsistensi_draf.json` (`beban_analis`): 88 rekaman uji OTRF, 693.683 event mentah → 88 kasus dengan 704 event terpilih (±985:1). Semua kasus tetap ditinjau manusia; tidak ada yang ditutup otomatis. Angka ini dari aturan, bukan dari LLM |

## Yang tidak dikerjakan AI

- Tidak memilih aksi. Aksi berisiko (isolasi, blokir IP) selalu menunggu persetujuan analis dan tidak dieksekusi oleh aplikasi.
- Tidak menutup kasus. Usulan LLM untuk menutup kasus dicatat dan diabaikan.
- Tidak menjadi dasar kategori. Bila draf menamai kategori lain, draf diberi label "Bertentangan dengan temuan aturan", alasannya dicatat di jejak audit (`cek_silang_draf`), dan kategori aturan tetap berlaku.

## Cara mengulang

```
app\.venv\Scripts\python -I app\tools\ukur_konsistensi_draf.py
app\.venv\Scripts\python -I -m pytest -q -p no:cacheprovider app\tests
```
