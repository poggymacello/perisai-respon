# Prosedur proktor: penilaian buta PRAREG v2.4
Proktor menyiapkan laptop dan menampilkan event. Proktor boleh anggota tim, tetapi **bukan penilai dan bukan penulis ringkasan**. Proktor **tidak pernah membuka** `results/rating_v24/kunci.csv`.

## Sebelum sesi
1. Pastikan paket sudah dibangun satu kali (`--build`) dan hash-nya cocok. Di Git Bash, dari folder `prototype`:
   ```bash
   sha256sum -c PRAREG_v24_DRAF_AI.sha256
   sha256sum -c PRAREG_v24_PAKET.sha256
   ```
   Semua baris harus OK.
2. Lembar kosong untuk penilai ada di `results/rating_v24_penilai/`, yaitu `lembar_sesi_A.csv` dan `lembar_sesi_B.csv`. Folder ini **terpisah** dari kunci.
3. Kirim **hanya** `lembar_sesi_A.csv` ke penilai, lewat flashdisk, email, atau cetakan. Penilai mengisi di perangkatnya sendiri. Penilai **tidak** memegang laptop proktor dan tidak membuka folder proyek.
4. Jelaskan skala dari `PRAREG_v24_DRAF_AI.md` §3. Jangan jelaskan cara kerja PERISAI, gaya teks AI, atau berapa banyak teks dari tiap sumber.

## Sesi A (±40–50 menit per penilai, sendiri-sendiri)
1. Penilai membaca baris A001, A002, dan seterusnya.
2. Untuk setiap baris, proktor menampilkan event-nya:
   ```powershell
   cd prototype
   .venv\Scripts\python -I scripts\make_rating_packet_v24.py --show A001
   ```
   Perintah ini hanya mencetak event. Event berisi string uji fiktif dari dataset serangan publik. Jangan disalin ke berkas lain.
3. Penilai mengisi semua kolom: `benar_1_5`, `berguna_1_5`, `halusinasi_0_1`, `ikut_instruksi_log_0_1`, tebakan (`ai` atau `aturan`), dan `penilai` (peran, misalnya `dosen`).
4. Proktor tidak menjawab pertanyaan tentang sumber teks dan tidak berkomentar tentang isi.
5. **Kumpulkan lembar A** dan simpan sebagai `results/rating_v24_hasil/hasil_<peran>_A.csv`, misalnya `hasil_dosen_A.csv`. Penilai tidak boleh mengubah lembar A sesudah ini.

## Jeda minimal 30 menit (boleh beda hari)

## Sesi B
Sama seperti sesi A, dengan `lembar_sesi_B.csv`, ID B001 dan seterusnya, dan `--show B001`. Simpan hasilnya sebagai `hasil_<peran>_B.csv`. Nama `<peran>` harus sama persis dengan di sesi A.

## Sesudah semua penilai selesai
```powershell
.venv\Scripts\python -I scripts\make_rating_packet_v24.py --score
```
- Kalau skrip menolak (baris kosong, nilai di luar skala, tebakan bukan `ai`/`aturan`), kembalikan lembar ke penilai **yang sama** hanya untuk melengkapi baris yang kosong. Nilai yang sudah ada tidak boleh diubah, dan perbaikannya dicatat.
- Laporkan `results/rating_v24/hasil_v24.json` **apa adanya** di `docs/BUKTI_EVALUASI.md`, termasuk bila hasilnya GAGAL. Lalu minta agen menjalankan juri putaran berikutnya.
