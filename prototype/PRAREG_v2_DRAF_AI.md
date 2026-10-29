# PRAREG v2: apakah DRAF AI berguna bagi analis dibanding ringkasan template aturan?
**Ditulis:** 29 Okt 2026, **sebelum** penilaian manusia dilakukan. Dibekukan dengan `PRAREG_v2_DRAF_AI.sha256`. Penilaian ini adalah satu-satunya bukti yang bisa mencabut veto "AI tidak perlu" (`JURI_90/SKOR_P2.md`).

## 1. Bahan
- **Kasus:** 20 kasus dari split UJI (88). Pemilihannya mekanis: urutkan `sha256("v2|" + case_id)` lalu ambil 20 pertama. Kasus tanpa draf AI dilewati. Bahan dibuat oleh `scripts/make_rating_packet.py`.
- **Per kasus ada 2 ringkasan:**
  - **A/B acak** (seed dari hash case_id): (i) draf AI v1.1 hasil usulan LLM `guarded` yang tersimpan, setelah disaring v1.1; (ii) ringkasan template aturan v1.1.
  - Label sumber **disembunyikan**. Kalimat penanda "Ringkasan dibuat dari template aturan (tanpa LLM)." dihapus dari teks template. Gaya bahasa yang berbeda tetap bisa membuka sumber, dan ini dicatat sebagai keterbatasan.
- **Bahan pendukung:** 8 baris event yang dirender, ditampilkan **di layar saat penilaian** lewat `scripts/make_rating_packet.py --show <id>` di laptop tim. Teks log mentah tidak dicetak ke berkas karena memicu Windows Defender (`DATA.md`).
- **Kunci jawaban** (A/B → sumber) disimpan terpisah di `results/rating/kunci.csv` dan tidak dibuka sampai penilaian selesai.

## 2. Penilai
- 2 orang, idealnya praktisi SOC/TI. Kalau tidak ada, anggota tim yang **tidak** menulis kode PERISAI.
- Penilai tidak melihat kunci dan tidak berdiskusi selama menilai.
- Penilai dicatat perannya saja, tanpa nama.

## 3. Skala (per ringkasan, isi `results/rating/lembar_penilaian.csv`)
- **Benar** 1–5: sesuai dengan event? (1 = banyak salah, 5 = semua benar)
- **Berguna** 1–5: membantu analis memutuskan langkah berikut?
- **Halusinasi** 0/1: ada klaim yang tidak didukung event?

## 4. Endpoint dan ambang menang (ditetapkan sekarang)
- **H-utama:** rata-rata *Berguna* (rata-rata 2 penilai per kasus) draf AI − template > 0, dengan **batas bawah CI95 bootstrap berpasangan per kasus (B = 10.000) > 0**, **dan** selisih rata-rata ≥ 0,5 poin.
- **Syarat keamanan:** proporsi draf AI dengan Halusinasi = 1 (oleh salah satu penilai) **≤ 20 %**.
- **Lulus** hanya bila keduanya terpenuhi. Kalau tidak, laporkan **GAGAL** dan pertahankan posisi "lapisan pengaman", tanpa klaim nilai AI.
- **Sekunder (deskriptif):** *Benar* draf AI vs template; kesepakatan antar penilai (proporsi |selisih| ≤ 1).

## 5. Prediksi tertulis
Template aturan kemungkinan menang di *Benar*. Draf AI mungkin menang tipis di *Berguna* karena bahasanya lebih alami, tetapi belum tentu melewati ambang 0,5. Halusinasi diperkirakan 10–30 %.

## 6. Keterbatasan
N = 20 dan hanya 2 penilai. Penilai yang juga anggota tim tidak benar-benar independen. Kasus berasal dari satu lab. Draf AI berasal dari usulan yang tersimpan (model sama, `temperature = 0`).
