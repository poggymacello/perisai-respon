# YOUTUBE: bahan unggah video demo PERISAI-RESPON

Berkas video: `video\PERISAI-RESPON_demo_final.mp4` (narasi suara sintetis, dibuat dengan `video\suara.py` sesudah `susun.py`). Durasi 06:43.
Subtitle: `video\PERISAI-RESPON_demo.id.srt` (Bahasa Indonesia). Thumbnail: `video\thumbnail_youtube_1280x720.png`.

## Judul (70 karakter)
```
PERISAI-RESPON: triase insiden offline yang tidak bisa disetir isi log
```

## Deskripsi
```
PERISAI-RESPON adalah aplikasi desktop untuk memilah insiden dari log Windows secara offline di laptop. Aturan dan policy engine yang memutuskan, LLM lokal hanya menulis draf berlabel, dan setiap aksi berisiko menunggu persetujuan analis.

Unduh dan coba: https://github.com/poggymacello/perisai-respon/releases
Kode dan dokumentasi: https://github.com/poggymacello/perisai-respon
Slide penjelasan: https://github.com/poggymacello/perisai-respon/blob/main/aset_kirim/slide/PERISAI-RESPON_Slide_Teknis.pdf

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

#keamanansiber #incidentresponse #promptinjection
```

Tautan di deskripsi baru berfungsi penuh setelah rilis `v1.0.0` dibuat dan slide terbaru di-push. Kalau slide diunggah ke Google Drive, ganti baris "Slide penjelasan" dengan tautan Drive itu.

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
| Konten sintetis/diubah | Tidak (rekaman layar aplikasi asli dan suara asli anggota tim) |

## Uji penerimaan
- Putar dari jendela penyamaran: durasi di bawah 10:00, subtitle muncul, chapter tampil di bilah putar.
- Tautan di deskripsi bisa dibuka tanpa login.
- Scrub per detik: tidak ada nama pengguna, path pribadi, notifikasi, atau tab lain di frame mana pun.
