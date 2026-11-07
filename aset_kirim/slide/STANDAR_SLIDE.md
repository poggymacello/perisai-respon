# STANDAR_SLIDE: dasar desain dek teknis PERISAI-RESPON
### 2 Nov 2026 · berkas: `buat_slide.py` → `PERISAI-RESPON_Slide_Teknis.pptx` / `.pdf`

Dek ini menggantikan `aset_kirim/slide_PERISAI-RESPON.tex/.pdf` (beamer). Yang diambil dari setiap rujukan adalah konvensinya, bukan isi atau merek.

## 1. Rujukan dan cara dipakai
| Rujukan | Yang diambil | Penerapan di dek |
|---|---|---|
| Dek mentor *Mentoring Business Planning* (89 hlm, dibaca 2 Nov 2026; hlm 18–19, 34, 39–44 dibaca penuh, sisanya lewat lembar kontak) | Label bagian kecil berwarna aksen di atas judul kalimat; garis aturan di bawah judul; "Action Title / Slide Body / Source & Footer" (hlm 39–40); ghost deck Situation–Complication–Key Question (hlm 19, 41); ringkasan eksekutif 60 detik (hlm 18); penanda bernomor dalam lingkaran; matriks risiko + tabel (hlm 34); pemilihan jenis grafik: batang horizontal untuk label panjang (hlm 43) | Setiap slide: label → judul klaim → garis → isi → baris sumber + nomor. Slide 2 = ringkasan eksekutif, slide 3 = S/C/Q, penanda bernomor di slide 2, 5, 6–7, 9, 13–15. Gradien hijau dan logo mentor **tidak** dipakai |
| Assertion–Evidence (Michael Alley, Penn State; *The Craft of Scientific Presentations*, 2013; writing.engr.psu.edu) | Judul berupa kalimat klaim, rata kiri, maks 2 baris; isi berupa bukti visual, bukan daftar poin | Semua 16 slide utama dan 4 lampiran memakai judul kalimat (≤ 2 baris, 32 pt). Isi = tabel bukti, grafik, diagram, atau tangkapan layar |
| Model C4 (Simon Brown, c4model.com/diagrams/notation) | Judul menyebut jenis dan cakupan diagram; setiap elemen punya nama, jenis/teknologi, deskripsi singkat; batas sistem; relasi berlabel; legenda wajib | Slide 8 = diagram kontainer (level 2): 9 kontainer, 3 sistem eksternal, 1 orang, batas sistem putus-putus, label relasi, legenda |
| Dek sesi teknis AWS re:Invent / Google Cloud Next / Microsoft Ignite / Black Hat Briefings (pengetahuan umum, tidak diunduh) | Urutan masalah → ancaman → arsitektur → demo → hasil → batasan; satu ide per slide; tangkapan layar produk asli yang dipotong ke area yang membuktikan klaim, dengan sorotan bernomor | Slide 4 (ancaman) → 5 (prinsip) → 6–8 (produk) → 9–10 (arsitektur, alur) → 13 (hasil) → 14 (yang gagal) → 16 (batasan) |
| Urutan pitch YC/Sequoia (masalah, solusi, produk, *why now*, bukti, penerapan, tim, *ask*) | Diadaptasi untuk juri pemerintah: *why now* diganti ancaman injeksi lewat log; *traction* diganti bukti prareg; *business model* diganti penerapan di satuan; *ask* diganti pilot baca-saja | Slide 3–5, 6–7, 12–14, 15, 16 |
| NIST SP 800-61r3 (April 2025, profil komunitas CSF 2.0; csrc.nist.gov/pubs/sp/800/61/r3/final) | Respons insiden dipetakan ke fungsi CSF 2.0 (DE.AE, RS.MA, RS.AN, RS.CO) | Slide 14 butir 4; lampiran A3. Ditulis sebagai pemetaan, bukan klaim kepatuhan |
| MITRE ATT&CK (taktik TA00xx) | Cakupan deteksi dinyatakan per taktik | Lampiran A2, dihitung otomatis dari `prototype/perisai/detector.py` (37 aturan, 8 taktik). Pemetaan per teknik belum ada dan disebut begitu |
| OWASP Top 10 for LLM Applications 2025 | Kode risiko LLM01, LLM02, LLM03, LLM06, LLM09 | Slide 4 (LLM01, LLM06), slide 10 (kolom ancaman), lampiran A3 |
| ISA/IEC 62443-3-3 (FR 1–7) | Ketersediaan (FR 7) dan respons atas kejadian (FR 6) di zona OT | Slide 11 dan lampiran A3, sebagai "sejalan dengan", bukan kepatuhan |
| WCAG 2.1 AA (SC 1.4.3, 1.4.11) | Kontras teks ≥ 4,5:1; elemen non-teks ≥ 3:1 | Rasio dihitung skrip (§3) |
| `12-MEGA-PROMPT-KARTIKA-SUBMISI-2nov2026.md` §B, §C, §D, §E3 | Aturan keras, buku klaim, daftar trope, spesifikasi link slide | §2 dan §4 di bawah |

Pencarian web dipakai (2 Nov 2026) untuk memastikan tanggal dan struktur NIST SP 800-61r3, daftar OWASP LLM 2025, pedoman Alley, dan aturan notasi C4. Rujukan dek konferensi (re:Invent, Next, Ignite, Black Hat) dan urutan pitch YC/Sequoia berasal dari pengetahuan umum, tidak dari dokumen yang diunduh.

## 2. Aturan angka
- **Slide utama (1–16) hanya memakai angka dari buku klaim §C**, dengan label wajibnya (in-sample, prareg, post-hoc, P2 gagal, nilai draf AI belum terbukti, satu lab, satu model kecil). Angka desain (37 aturan, 4 aksi, jendela 15 menit) diambil dari kode dan `docs/DOKUMENTASI_TEKNIS.md`, bukan dari hasil uji.
- **Lampiran A1** memuat angka rinci (CI95, p, ablasi, uji tertahan, latensi p90) yang disalin dari `docs/BUKTI_EVALUASI.md`, dengan nomor bagiannya.
- Angka BSSN 2023 (347 dugaan insiden, 83 asistensi) ada di `docs/PROPOSAL.md` §1 tetapi **tidak ada di §C**, jadi tidak dipakai. Tambahkan ke slide 3 hanya kalau tim memasukkannya ke buku klaim.
- Tes dijalankan ulang 2 Nov 2026: mesin `prototype/` → `102 passed`; API aplikasi `app/` → `23 passed`.
- Fakta aplikasi (zip 41,5 MB, belum ditandatangani, FastAPI di 127.0.0.1 + WebView2, mode aturan bawaan, mode LLM bila model ada di `models\`, impor XML/JSON/.evtx, persetujuan hanya dicatat di audit, laporan Markdown/HTML, mode demo Docker tanpa unggah) diambil dari `app/README.md` dan `app/DEPLOY.md`. Angka benchmark di layar Status sistem tidak dikutip di teks karena tidak ada di buku klaim.
- Setiap slide yang memuat angka punya baris sumber di kiri bawah.

## 3. Sistem visual
| Unsur | Nilai | Alasan |
|---|---|---|
| Ukuran | 16:9, 13,333 × 7,5 in | Standar PowerPoint dan Google Slides |
| Grid | 12 kolom, margin kiri-kanan 0,6 in, gutter 0,2 in | Konsisten antarslide; dihitung di `cx()`/`sw()` |
| Font | Arial (isi), Courier New (kode) | Ada di Windows, macOS, dan Google Slides, jadi impor PPTX ke Google Slides tidak mengganti font. Inter/Roboto tidak terpasang di mesin ini; Consolas dan Cascadia tidak ada di Google Slides |
| Ukuran huruf | Judul 32 pt; isi 16–20 pt; tabel 14–18 pt (lampiran 13–14 pt); kode 16 pt; label diagram C4 10–14 pt; sumber 11 pt | Pengecualian di bawah 18 pt hanya untuk tabel bukti, label diagram/grafik, dan baris sumber |
| Warna | Putih; teks #1A1A1A; abu #4D4D4D, #666666; satu aksen #0F4C81; latar #F3F4F6 / #E8EFF7 | Merah #B42318 hanya untuk BLOCK dan bobot tinggi; jingga #B54708 hanya untuk "menunggu persetujuan", status parsial, dan bobot sedang |
| Kontras (dihitung) | #1A1A1A 17,4:1 · #4D4D4D 8,5:1 · #666666 5,7:1 (5,2:1 di #F3F4F6) · aksen 8,9:1 (7,6:1 di #E8EFF7) · putih di merah 6,6:1 · putih di jingga 5,4:1 | Semua ≥ 4,5:1 (WCAG 2.1 AA) |
| Tidak dipakai | Gradien, bayangan, glow, emoji, foto stok, gambar generatif, ikon robot/otak/gembok, logo TNI AD/PUSSIBERAD/Kartika/CODEPOLITAN | §D2 dan §B2 |
| Grafik | Digambar dengan bentuk PPTX dari angka BUKTI: batang horizontal, sumbu berlabel, CI95 sebagai garis tipis, tanpa garis kisi, tanpa 3D | Bisa diedit dan tampil sama di Google Slides |
| Tangkapan layar | Diambil dari `app/screenshots/0N_*.png` (1920×1080, exe hasil build). `crop_shot()` memotong area yang membuktikan klaim slide dengan PIL dari berkas asli (bisa diulang), lalu menggambar kotak sorot dan penanda bernomor sebagai bentuk PPTX. Skrip mencetak skala teks UI terhadap ukuran asli saat slide tampil layar penuh 1920 px; targetnya ≥ 60 % (hasil terakhir 76–107 %) | Kalau berkas belum ada: kotak abu-abu berlabel nama berkas |

## 4. Aturan tulisan
- Judul berupa kalimat klaim yang bisa dibantah dengan angka atau bukti.
- Isi prosa ≤ 30 kata per slide bila bisa. Tabel bukti, diagram, dan deklarasi (slide 16) melebihi itu dan sengaja dibiarkan.
- Skrip memindai teks slide **dan** catatan pembicara untuk daftar §D1, klaim terlarang §C, tanda pisah panjang (—), dan emoji. Hasil terakhir: 0 temuan.
- Tidak ada placeholder `[ISI]` di dek. Nama tim, anggota, peran, dan URL video dibaca dari `tim.json` (diketik sendiri oleh tim). Field yang kosong tidak ditampilkan. URL repo sudah tertulis di skrip (`REPO`). Label `[ASUMSI]` tetap dipakai untuk klaim yang belum dikonfirmasi.

## 5. Struktur dan waktu (presentasi final 10 menit termasuk demo dan tanya jawab)
17 slide utama, satu di atas rentang 12–16 yang disarankan. Alasannya, Fungsionalitas Purwarupa berbobot 25 dan tangkapan layar asli adalah buktinya; tiga slide produk dipakai sebagai jalur demo langsung, dan tiap tangkapan layar harus cukup besar untuk dibaca.

| # | Slide | Waktu |
|---|---|---|
| 1 | Judul | 0:15 |
| 2 | Ringkasan 60 detik | 0:30 |
| 3 | Masalah (S/C/Q) | 0:30 |
| 4 | Ancaman: injeksi lewat field log | 0:35 |
| 5 | Solusi + AI tepat guna | 0:30 |
| 6 | Produk: antrean (**demo langsung mulai**) | 0:40 |
| 7 | Produk: detail kasus berinjeksi | 0:50 |
| 8 | Produk: uji policy + audit | 0:40 |
| 9 | Arsitektur C4 | 0:30 |
| 10 | Alur keputusan satu kasus | 0:25 |
| 11 | Keamanan alat | 0:20 |
| 12 | OT | 0:25 |
| 13 | Hasil | 0:40 |
| 14 | Yang gagal | 0:30 |
| 15 | Penerapan di satuan | 0:30 |
| 16 | Rencana dan batasan | 0:20 |
| 17 | Tim, deklarasi, tautan | 0:15 |
| A–A4 | Lampiran untuk tanya jawab | – |

Total ±8:25, menyisakan ±1:35 untuk tanya jawab. Kalau waktu kurang, slide 10 dan 11 dilewati.

Catatan jujur untuk slide 7: di tangkapan layar 02 (bagian yang tidak dipotong), draf AI menulis "Pencurian kredensial…" pada kasus eksekusi kode, dan penjaga draf meloloskannya. Catatan pembicara menyebutnya sebagai contoh mengapa kategori dan aksi diambil dari aturan.

## 6. Membuat ulang
```powershell
cd KartikaCyber2026\aset_kirim\slide
python buat_slide.py --pdf          # PPTX + PDF (PowerPoint COM, font tertanam)
python buat_slide.py --pdf --qa --qa-dir <folder>   # + PNG per halaman untuk diperiksa
```
Untuk link slide (E3), unggah **PDF** ke Google Drive ("Siapa saja yang memiliki link: Pelihat"). Kalau tim ingin Google Slides yang bisa diedit, impor **PPTX** (bukan PDF); font Arial dan Courier New tetap sama.
