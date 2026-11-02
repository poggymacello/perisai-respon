# Prosedur proktor: penilaian buta PRAREG v2.3
Proktor adalah orang yang menyiapkan laptop dan menampilkan event. Proktor boleh anggota tim, tetapi **bukan penilai**.

## Sebelum sesi
1. Pastikan `prototype\results\rating_v23\kunci.csv` ada. **Jangan membukanya.** Cek hash-nya dengan `sha256sum -c PRAREG_v23_DRAF_AI.sha256` di Git Bash. Semua baris harus OK.
2. Salin `results\rating_v23\lembar_penilaian.csv` untuk setiap penilai, menjadi `hasil_<peran>.csv` (misalnya `hasil_dosen.csv`, `hasil_soc.csv`) di folder yang sama.
3. Jelaskan skala dari `PRAREG_v23_DRAF_AI.md` §3. Jangan menjelaskan cara kerja PERISAI atau perbedaan gaya teks.

## Selama sesi (per penilai, ±60–90 menit, sendiri-sendiri)
1. Penilai membuka berkas `hasil_<peran>.csv` miliknya dan menilai baris T001, T002, dan seterusnya.
2. Untuk setiap baris, proktor menjalankan perintah ini dan memperlihatkan layar ke penilai:
   ```powershell
   cd prototype
   .venv\Scripts\python -I scripts\make_rating_packet_v23.py --show T001
   ```
   Perintah ini hanya mencetak event, tanpa sumber teks. Event berisi string uji fiktif dari dataset serangan publik. Jangan disalin ke berkas lain.
3. Penilai mengisi semua kolom, **termasuk tebakan sumber**.
4. Proktor tidak menjawab pertanyaan tentang sumber teks dan tidak berkomentar tentang isi.

## Sesudah semua penilai selesai
```powershell
.venv\Scripts\python -I scripts\make_rating_packet_v23.py --score
```
Laporkan `results\rating_v23\hasil_v23.json` apa adanya di `docs\BUKTI_EVALUASI.md`, termasuk bila hasilnya GAGAL.
