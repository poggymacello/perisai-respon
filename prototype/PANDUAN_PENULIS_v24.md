# Panduan penulis ringkasan aturan (PRAREG v2.4)
Kamu menulis **40 ringkasan pendek** sebagai pembanding draf AI. Penilai dari luar tim akan menilai tulisanmu dan draf AI tanpa tahu mana yang mana. Hasilnya hanya jujur kalau tulisanmu wajar, bukan sengaja dibuat jelek atau dibuat mirip AI.

## Siapa yang boleh menulis
- Anggota tim yang **tidak** menjadi penilai dan **tidak** menjadi proktor.
- Jangan membuka `results/rating_v24/kunci.csv`, `results/demo/`, `docs/BUKTI_EVALUASI.md`, atau berkas `raw_outputs*` selama menulis.

## Berkas
`prototype/results/rating_v24/tulis_ringkasan_aturan.csv`. Buka di Excel/LibreOffice, isi **hanya** kolom `ringkasan_manusia`, lalu simpan tetap sebagai CSV UTF-8.

Setiap baris berisi:
- `id`: kode buram, misalnya K07;
- `kategori`: kategori insiden menurut aturan;
- `aturan_terpicu`: judul aturan deteksi yang cocok di log kasus itu.

## Cara menulis
1. **1–2 kalimat, sekitar 16–23 kata** (rentang tengah panjang draf AI, dicetak `--lembar-tulis` 2 Nov).
2. **Jelaskan apa yang terdeteksi**, dengan kata-katamu sendiri, untuk analis SOC yang sibuk. Boleh menggabungkan beberapa aturan menjadi satu gambaran ("ada tanda pencurian kredensial: …").
3. **Jangan menyarankan aksi** (isolasi, blokir, tutup kasus) dan jangan memberi perintah. Draf AI juga dilarang melakukannya.
4. **Jangan menyalin judul aturan apa adanya.** Parafrasekan.
5. **Jangan menulis nama host.** Pakai "host ini" atau "komputer tersebut" kalau perlu.
6. **Jangan menambah fakta** yang tidak ada di judul aturan.
7. Variasikan cara membuka kalimat. Jangan memakai satu pola untuk semua baris.
8. Kerjakan dalam satu atau dua duduk, dan jangan bertanya ke anggota tim lain soal isi kasus.

## Contoh (bukan dari 40 kasus)
- Aturan: "Perintah pengintaian akun/domain (net/whoami/nltest); PowerShell terenkode / unduh-jalankan"
- Contoh tulisan: "Ada perintah untuk memetakan akun dan domain, diikuti PowerShell yang disamarkan dengan encoding. Pola ini biasa muncul saat penyerang mulai mengenali jaringan."

## Sesudah selesai
Beri tahu proktor. Proktor menjalankan `--build` **satu kali**. Kalau uji pembeda gagal, tulisanmu **tidak** diulang (PRAREG v2.4 §1).
