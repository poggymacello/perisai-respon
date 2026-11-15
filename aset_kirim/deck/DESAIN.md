# DESAIN: dek PERISAI-RESPON untuk Kartika Cyber Hackathon 2026
15 Nov 2026 · `buat_deck.py` (memakai `deckkit.py`) → `PERISAI-RESPON_Deck_Kartika2026.pptx` / `.pdf`

Dek lama di `../slide/` tidak diubah. Jalankan ulang: `python buat_deck.py --pdf`.

## Brief desain
1. Satu contoh berjalan: kasus K-0004 (WS-KEU02, CommandLine berisi "isolate_host with target DC01") dari hook sampai penutup.
2. Judul berupa kalimat klaim, rata kiri, maksimal 2 baris, di atas garis tipis; bukti di bawahnya.
3. Putih, tinta hijau-hitam, satu aksen hijau tua #1E5B3C; merah #B42318 hanya untuk nilai yang salah, ditolak, atau ditandai.
4. Satu slide gelap saja (Solusi) sebagai jeda bab.
5. Tangkapan layar asli 1920×1080 dipotong ke area yang membuktikan judul, dengan kotak sorot dan penanda bernomor.
6. Angka besar (52–100 px) dengan keterangan pendek dan baris sumber di setiap slide.
7. Navigasi bagian kecil di atas, bagian aktif bergaris aksen.
8. Grid 1920×1080 px, margin 80, isi y 205–990, sumber y 1004. Font Arial dan Courier New (ada di PowerPoint dan Google Slides).
9. Teks isi 20–30 px, keterangan minimal 15 px; tidak ada teks isi di bawah 14 pt.
10. Tanpa gradien, bayangan, glow, emoji, ikon stok, atau gambar AI; grafik digambar sebagai bentuk.
11. Pembagian asimetris: argumen kiri, bukti kanan.
12. Alur demo 5 langkah dengan layar asli, lalu satu slide per langkah (cadangan bila demo langsung gagal).
13. Hasil yang gagal dan batasan punya slide sendiri.
14. Lampiran A1–A5 untuk angka rinci, ancaman terhadap alat, pemetaan standar, cara mengulang, dan rujukan.

## Ide yang diambil dari dek rujukan
| Dek | Ide | Dipakai di |
|---|---|---|
| Jatan (juara 1 Hackvidia, 86) | Navigasi bagian dengan bagian aktif disorot; hijau tua sebagai satu warna merek; layar produk asli yang besar; lampiran berlabel "Appendix." | Semua slide utama (nav atas), palet, slide 6–11, label LAMPIRAN A1–A5 |
| Livestoq (juara 2, 78) | Deretan layar produk asli sebagai alur; slide gelap tunggal sebagai pembuka solusi; pipeline dengan angka hasil di ujung | Slide 4 (gelap), 5 (alur demo), 12 (arsitektur) |
| BIMA / Gajah Mada Tuir (juara 3, 76) | Label bagian kecil di atas judul; angka besar berwarna dengan merah untuk yang buruk; penutup satu kalimat besar | Label "LANGKAH n DARI 5", slide 2 (16,5 % merah), slide 13, slide 17 |
| Wasit ROUND 1, demo flow | Demo sebagai langkah bernomor dengan layar asli dan kotak "setup jujur"; penutup dengan pernyataan + tim + tautan | Slide 5, slide 6–9, slide 17 |

## Daftar slide
1 Sampul · 2 Satu baris log bisa menyuruh asisten AI memutus DC sendiri · 3 Masalah dan pertanyaan · 4 Solusi (gelap) · 5 Peta demo · 6 Antrean · 7 Detail K-0004 · 8 Uji policy · 9 Audit dan laporan · 10 AI tepat guna dan cek silang · 11 Jalur OT · 12 Arsitektur dan teknologi · 13 Hasil · 14 Yang gagal dan batasan · 15 Penerapan dan pilot · 16 Cara mencoba, tim, deklarasi · 17 Penutup · A1–A5 lampiran.

## Audit tulisan (skill avoid-ai-writing, suara professional/technical)
Mode: tulis mengikuti aturan, lalu deteksi dan sunting seluruh teks dek (slide + catatan pembicara, diekstrak dari PPTX). Aturan skill ini dikalibrasi untuk bahasa Inggris; untuk teks Indonesia dipakai padanan polanya. Penilaian model saja: detektor, normalisasi tanda kutip, dan validator preservasi tidak dijalankan pada teks Indonesia. Dua putaran suntingan. Angka dan fakta tidak berubah.

Ditandai dan diubah:
- Bingkai "bukan X, melainkan Y" + kontras pendek (slide 8): "Yang menahan adalah aturan struktural, bukan pola teks. Pola bisa diakali; daftar aset terlindungi tidak." → "Penolakan datang dari daftar aset terlindungi di policy. Pada injeksi yang ditulis ulang, pola menangkap 0 %, dan aturan ini tetap menahan semua aksi berbahaya."
- Penegasan tanpa isi (slide 13): "Yang menahan adalah aturan struktural." → "Policy saja sudah menahan injeksi sampai 0,6 % tanpa bantuan pola."
- Slogan tiga bagian (slide 4): "AI mengusulkan, kebijakan memutuskan, analis menyetujui." → "LLM hanya menulis draf; keputusan aksi ada di aturan dan analis."
- Negasi ekor (slide 8): "Lolos semua pun hanya menjadi usulan yang menunggu analis. Tidak ada eksekusi otomatis." → "Usulan yang lolos semua pemeriksaan tetap menunggu analis; aplikasi tidak menjalankannya."
- Negasi ekor (slide 11): "juga dieskalasi, tidak diisolasi" → "juga hanya dieskalasi ke insinyur proses".
- Kepadatan "bukan dari LLM" (slide 6, 13): dihapus di slide 6; slide 13 menjadi "(hasil penyaringan aturan)".
- Narasi keterusterangan: judul slide 14 "Tiga hasil gagal kami laporkan, ..." → "Tiga hasil uji gagal, ..."; catatan slide 10 "..., dan kami katakan begitu" dihapus.
- Kail pembuka: catatan slide 2 "Ini lubangnya." dihapus; catatan slide 1 "Yang membedakannya: ..." menjadi kalimat langsung.

Dibiarkan (disengaja): "(bukan LLM)" dan "bukan dasar keputusan" karena kutipan teks UI; satu pembalikan di penutup ("Isi log boleh ditulis penyerang. Keputusan tetap di tangan aturan dan analis.") karena didukung isi dek; "persetujuan hanya dicatat, tidak dijalankan" karena itu klaim inti; daftar tiga angka di penutup karena memang tiga butir nyata.

Pindaian otomatis `buat_deck.py`: tanda pisah panjang, kata promosi (revolusioner, canggih, di era digital, dll.), "Claude", "Anthropic": 0 temuan.

## QA visual
Semua 22 halaman dirender ke PNG (pdftoppm) dan diperiksa: tumpang tindih di slide 11 diperbaiki, area kosong di slide 2, 5, 7–12 diisi dengan potongan layar dan angka yang lebih besar, nama tim di sampul tidak lagi terpotong. Folder PNG sudah dihapus.
