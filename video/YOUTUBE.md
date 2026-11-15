# YOUTUBE: bahan unggah video demo PERISAI-RESPON

Berkas video: `video\PERISAI-RESPON_demo_final.mp4` (narasi suara sintetis, dibuat dengan `video\suara.py` sesudah `susun.py`). Durasi 06:43.
Subtitle: `video\PERISAI-RESPON_demo.id.srt` (Bahasa Indonesia). Thumbnail: `video\thumbnail_youtube_1280x720.png`.

## Judul (99 karakter)
```
PERISAI-RESPON: triase insiden offline yang tak bisa disetir isi log | Kartika Cyber Hackathon 2026
```

## Deskripsi
```
PERISAI-RESPON adalah aplikasi desktop untuk memilah insiden dari log Windows secara offline di laptop. Aturan dan policy engine yang memutuskan aksi. LLM lokal hanya menulis draf berlabel, dan setiap draf dicek silang terhadap temuan aturan. Aksi berisiko selalu menunggu persetujuan analis, dan setiap langkah tercatat di audit berantai SHA-256.

Karya Tim PERISAI Siber Ganesha (Poggy Macello Gultom, Mohammad Ari Alexander Aziz, Hasri Fayadh Muqaffa) untuk Kartika Cyber Hackathon 2026, kategori Penangkalan.

Coba di browser: https://perisai-respon.vercel.app/
Unduh aplikasi (Windows 10/11, tanpa internet): https://github.com/poggymacello/perisai-respon/releases/tag/v1.1.0
Kode dan dokumentasi: https://github.com/poggymacello/perisai-respon
Slide: https://drive.google.com/file/d/1bz-MT65_ZECsbbrfhz__k0_rRdGYFESU/view

Hasil uji (run sendiri; rincian dan yang gagal ada di README):
- Injeksi lewat log yang berhasil: 16,5 % menjadi 0 % (176 unit uji), dan 0,6 % walau detektor pola dimatikan
- Cek silang menandai 175 dari 421 draf AI (41,6 %) yang menyebut kategori di luar temuan aturan
- Jalur OT (HAI 21.03): 10 dari 10 episode serangan tertangkap

Chapter:
00:00 Masalah: log bisa ditulis penyerang
00:24 Kenapa penting untuk satuan
01:14 Demo: antrean dan kasus injeksi
02:29 Uji policy: isolasi DC01 ditolak
02:52 Persetujuan analis, audit, laporan CSIRT
03:58 Jalur OT
04:27 Hasil uji, termasuk yang gagal
05:36 Penerapan di satuan
06:21 Batasan dan tautan

Data uji: OTRF Security-Datasets (log Windows) dan HAI 21.03 (CC BY-SA 4.0, telemetri proses). Data di video ini sintetis, dengan host fiktif *.batalyon.lab.
Model: Qwen2.5-1.5B-Instruct (Apache-2.0), berjalan lokal di CPU. Llama tidak dipakai karena lisensinya melarang penggunaan militer.
Narasi memakai suara sintetis (Microsoft Edge TTS, id-ID-ArdiNeural) yang membacakan naskah tim.
Alat bantu AI dipakai saat pengembangan; rinciannya ada di bagian Deklarasi README repo.

#keamanansiber #incidentresponse #promptinjection #KartikaCyberHackathon
```

Tautan rilis dan kode baru bisa dibuka juri setelah repo dibuka ke publik.

## Pengaturan
| Pengaturan | Nilai |
|---|---|
| Visibilitas | **Publik** (form meminta bisa diakses publik; *Unlisted* hanya kalau panitia mengonfirmasi boleh) |
| Penonton | Tidak, video ini tidak dibuat untuk anak-anak |
| Kategori | Sains & Teknologi |
| Bahasa video | Bahasa Indonesia |
| Subtitle | Unggah `PERISAI-RESPON_demo.id.srt` (With timing), bahasa Indonesia |
| Thumbnail | `thumbnail_youtube_1280x720.png` |
| Komentar | boleh dimatikan |
| Konten sintetis/diubah | Tidak. Rekaman layarnya asli, dan narasi TTS tidak meniru orang sungguhan. Penggunaan suara sintetis tetap dinyatakan di deskripsi |

## Uji penerimaan
- Putar dari jendela penyamaran: durasi di bawah 10:00, subtitle muncul, chapter tampil di bilah putar.
- Tautan di deskripsi bisa dibuka tanpa login.
- Scrub per detik: tidak ada nama pengguna, path pribadi, notifikasi, atau tab lain di frame mana pun.
