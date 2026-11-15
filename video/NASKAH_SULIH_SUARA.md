# NASKAH SULIH SUARA: video demo PERISAI-RESPON

Durasi video tanpa suara: **06:43** (`PERISAI-RESPON_demo_tanpa_suara.mp4`). Naskah ini dibuat dari `alur.py`, sama dengan subtitle `PERISAI-RESPON_demo.id.srt`. Kalau narasi diubah, ubah `alur.py` lalu jalankan ulang `susun.py` supaya video, subtitle, dan naskah tetap sinkron.

## Cara merekam (satu kali jalan)
1. Pakai mikrofon headset atau USB di ruang yang tenang. Matikan notifikasi.
2. Putar `PERISAI-RESPON_demo_subtitle.mp4` tanpa suara di layar (subtitle jadi aba-aba). Di Audacity, tekan Rekam tepat saat video mulai diputar. Bacalah tiap baris saat subtitlenya muncul. Boleh memakai kata-kata sendiri asal isinya dan angkanya sama.
3. Kalau salah ucap, berhenti sebentar lalu ulangi kalimatnya. Potong bagian yang salah nanti tanpa menggeser waktu (pakai Edit > Remove Special > Split Delete atau isi dengan hening, bukan Delete biasa).
4. Audacity: pilih semua (Ctrl+A), Effect > Volume and Compression > **Loudness Normalization**, pilih *perceived loudness* **-16 LUFS**, centang *treat mono as dual-mono*. Puncak sebaiknya di bawah -1 dBTP (Effect > Limiter, limit to -1 dB bila perlu).
5. Pastikan panjang rekaman sama atau sedikit lebih pendek dari video. File > Export Audio > WAV (16-bit PCM), simpan sebagai `video\narasi.wav`.
6. Gabungkan suara ke video (dari folder `KartikaCyber2026`):

```powershell
$ff = (video\.venv\Scripts\python -c "import imageio_ffmpeg; print(imageio_ffmpeg.get_ffmpeg_exe())")
& $ff -i video\PERISAI-RESPON_demo_tanpa_suara.mp4 -i video\narasi.wav -map 0:v -map 1:a -c:v copy -c:a aac -b:a 192k -ar 48000 -shortest -movflags +faststart video\PERISAI-RESPON_demo_final.mp4
```

   Berkas yang diunggah ke YouTube: **`video\PERISAI-RESPON_demo_final.mp4`**, ditambah subtitle `PERISAI-RESPON_demo.id.srt` (YouTube Studio > Subtitles > Bahasa Indonesia > Upload file > With timing).
7. Tonton hasilnya sekali penuh: suara sinkron dengan layar, tidak ada bagian yang terpotong.

Tanpa musik, tanpa efek suara. Suara harus suara asli anggota tim (bukan TTS).

## Chapter

- 00:00 Masalah: log bisa ditulis penyerang
- 00:24 Kenapa penting untuk satuan
- 01:14 Demo: antrean dan kasus injeksi
- 02:29 Uji policy: isolasi DC01 ditolak
- 02:52 Persetujuan analis, audit, laporan CSIRT
- 03:58 Jalur OT
- 04:27 Hasil uji, termasuk yang gagal
- 05:36 Penerapan di satuan
- 06:21 Batasan dan tautan

## Naskah per waktu

| Waktu | Di layar | Yang diucapkan |
|---|---|---|
| 00:00-00:06 | Kartu judul | `00:00` PERISAI-RESPON memilah insiden dari log Windows secara offline. |
| 00:06-00:24 | Kasus K-0004: field CommandLine berisi instruksi, ditandai firewall (diperbesar) | `00:06` Masalahnya, isi log bisa ditulis penyerang. `00:10` Di sini penyerang menyelipkan perintah untuk AI di baris PowerShell: isolasi DC01. `00:17` Aplikasi menandainya sebagai data, tidak menurutinya, dan menyerahkan kasus ke analis. |
| 00:24-00:26 | Kartu: Log satuan tidak boleh keluar ke cloud, dan isinya bisa ditulis penyerang. | (diam) |
| 00:26-00:37 | Aplikasi baru dibuka, antrean kosong | `00:27` Log satuan memuat nama host, akun, dan alamat internal. `00:31` Karena itu log tidak boleh dikirim ke layanan AI di cloud. |
| 00:37-00:44 | Penanda Offline 127.0.0.1 di kanan atas | `00:37` PERISAI-RESPON berjalan di laptop dan hanya menerima koneksi dari perangkat itu sendiri. |
| 00:44-00:52 | Status sistem, kartu Jaringan | `00:45` Status sistem: alamat 127.0.0.1, akses ke host lain diblokir, tanpa telemetri. |
| 00:52-00:59 | Status sistem, kartu Model lokal (hash cocok) | `00:52` Modelnya juga lokal, Qwen2.5 1,5B, dan hash berkasnya dicek sebelum dipakai. |
| 00:59-01:14 | Status sistem, kartu Mode analisis | `00:59` Isi log juga bisa menyetir asisten AI yang membacanya. `01:04` Karena itu kategori dan aksi diambil dari aturan. `01:08` LLM hanya menulis draf ringkasan, dan hanya kalau analis memintanya. |
| 01:14-01:16 | Kartu: Demo dengan log contoh sintetis, dari antrean kasus sampai laporan CSIRT. | (diam) |
| 01:16-01:23 | Klik Muat data contoh | `01:17` Kita mulai dari sesi kosong dan memuat log contoh dengan host fiktif. |
| 01:23-01:33 | Ringkasan antrean dan tabel kasus | `01:23` Event dikelompokkan menjadi kasus. `01:26` Tiap kasus punya kategori ATT&CK, severity, dan status dari mesin aturan. |
| 01:33-01:39 | Filter Injeksi terdeteksi | `01:33` Filter ini menampilkan kasus yang lognya memuat instruksi tersembunyi. |
| 01:39-01:46 | Buka K-0004 (WS-KEU02), banner merah | `01:40` Kasus WS-KEU02. Banner merah menyebut lokasi instruksinya: field CommandLine. |
| 01:46-01:55 | Teks CommandLine ditampilkan sebagai teks biasa | `01:47` Teks log ditampilkan sebagai teks biasa. Teks itu tidak dijalankan dan tidak disalin ke laporan. |
| 01:55-02:04 | Kartu Keputusan dan alasan policy | `01:55` Keputusan diambil oleh aturan v1.2.2, bukan oleh LLM, dan alasan policy-nya ditulis satu per satu. |
| 02:04-02:10 | Klik Buat draf AI, bilah proses | `02:04` Draf AI dibuat hanya atas permintaan analis. Waktu tunggunya kami potong. |
| 02:10-02:29 | Draf AI berlabel, label waktu tunggu dipotong (diperbesar) | `02:11` Draf ini berlabel bukan dasar keputusan. `02:15` Cek silang membandingkan kategori yang disebut draf dengan temuan aturan. `02:21` Kalau berbeda, draf ditandai bertentangan dan dicatat di audit. Kategori tetap eksekusi kode dari aturan. |
| 02:29-02:39 | Uji usulan: isolasi DC01, detektor pola dimatikan | `02:30` Skenario terburuk: LLM sudah tersetir dan mengusulkan isolasi DC01. `02:35` Detektor pola injeksi kami matikan. |
| 02:39-02:52 | Hasil BLOCK dan alasannya (diperbesar) | `02:39` Policy tetap menolak: BLOCK, karena DC01 aset terlindungi. `02:44` Aturan ini melihat target aksi, jadi tetap bekerja walau kalimat serangannya tidak dikenali. |
| 02:52-03:03 | Buka K-0002 (WS-OPS07), menunggu persetujuan | `02:52` Kasus WS-OPS07: proses dari folder Public mengakses LSASS. `02:57` Aturan mengusulkan isolasi host, dan statusnya menunggu persetujuan. |
| 03:03-03:14 | Setujui aksi, isi nama dan catatan | `03:04` Aksi berisiko tidak berjalan sendiri. Analis menyetujuinya dengan nama dan catatan. |
| 03:14-03:20 | Riwayat: disetujui analis, nomor entri audit | `03:14` Persetujuan itu dicatat, tidak dieksekusi. Aplikasi ini baca-saja. |
| 03:20-03:27 | Jejak audit berantai SHA-256 | `03:20` Setiap langkah masuk jejak audit. Tiap entri memuat hash SHA-256 entri sebelumnya. |
| 03:27-03:33 | Verifikasi integritas: rantai utuh | `03:28` Verifikasi menghitung ulang seluruh rantai dari berkas. |
| 03:33-03:45 | Uji deteksi perubahan: salinan gagal, asli utuh (diperbesar) | `03:33` Uji ini mengubah persetujuan tadi menjadi dieksekusi: true di salinan. `03:39` Verifikasi salinan langsung gagal, dan berkas aslinya tetap utuh. |
| 03:45-03:53 | Laporan CSIRT, tombol unduh dan cetak | `03:45` Laporan CSIRT disusun dari kasus dan jejak audit, lalu bisa diunduh atau dicetak ke PDF. |
| 03:53-03:58 | Gulir laporan ke bagian tindakan analis | `03:53` Teks bebas dari log tidak ikut disalin ke laporan. |
| 03:58-04:00 | Kartu: Jalur OT: PLC dan HMI tidak pernah diputus oleh sistem. | (diam) |
| 04:00-04:08 | Jalur OT: grafik amplop normal | `04:01` Pada telemetri proses bergaya HAI 21.03, satu tag aliran keluar dari amplop normal. |
| 04:08-04:16 | Catatan HMI (teks bebas) | `04:08` Catatan HMI mengaku komandan memerintahkan PLC-P1 diputus. Firewall pola tidak menandainya. |
| 04:16-04:27 | Keputusan OT: putus PLC-P1 ditolak (diperbesar) | `04:16` Usulan itu tetap ditolak aturan aset OT, karena memutus PLC bisa menghentikan proses fisik. `04:24` Kasus dieskalasi ke insinyur proses. |
| 04:27-04:29 | Kartu: Hasil uji kami, termasuk yang gagal. | (diam) |
| 04:29-04:48 | Kartu: Injeksi lewat log yang berhasil (16,5 % → 0 %) | `04:30` Rencana uji kami kunci dengan SHA-256 sebelum dijalankan. `04:35` Pada 176 unit uji, injeksi yang berhasil turun dari 16,5 persen ke 0 persen. `04:41` Pola deteksinya dibuat dengan mengetahui keluarga injeksi ini, jadi hasilnya in-sample. |
| 04:48-04:55 | Kartu: Detektor pola dimatikan, policy tetap menahan (0,6 %) | `04:49` Dengan detektor pola dimatikan, yang lolos 0,6 persen, satu dari 176. |
| 04:55-05:14 | Kartu: Injeksi baru yang ditulis ulang (0 % terdeteksi pola) | `04:55` Injeksi yang ditulis ulang lolos dari pola deteksi: 0 persen terdeteksi. `05:01` Tetapi isolasi dan blokir palsu yang lolos tetap 0. `05:06` Versi 1 kebobolan 4 dari 176 lewat penutupan kasus; kini kasus tidak pernah ditutup otomatis. |
| 05:14-05:26 | Kartu: Uji P2 gagal: LLM kalah dari aturan (35,2 % vs 50,0 %) | `05:14` Uji P2 gagal. LLM 1,5B kalah dari aturan dalam menebak taktik, 35,2 lawan 50,0 persen. `05:21` Karena itu kategori dan aksi diambil dari aturan. |
| 05:26-05:36 | Kartu: Jalur OT dan tanda palsu (10/10) | `05:26` Di jalur OT, 10 dari 10 episode serangan HAI 21.03 tertangkap. `05:31` Alarm palsunya 5,4 persen dan 0 persen di dua berkas uji. |
| 05:36-05:39 | Kartu: Penerapan di satuan: laptop biasa, lisensi Rp0, pilot baca-saja. | (diam) |
| 05:39-05:53 | Status sistem: Uji kinerja di perangkat ini | `05:39` Di CPU laptop tanpa GPU, firewall dan policy butuh kurang dari 10 milidetik per kasus. `05:46` Dengan LLM, median 28,7 detik per kasus. Tombol ini mengukur ulang di perangkat penguji. |
| 05:53-06:04 | Tabel lisensi dan asal-usul | `05:54` Lisensinya Rp0. Qwen2.5 berlisensi Apache-2.0. `05:58` Llama tidak dipakai karena lisensinya melarang penggunaan militer. |
| 06:04-06:11 | Impor log: perintah wevtutil dan .evtx | `06:04` Untuk pilot, log diekspor dengan wevtutil, atau berkas .evtx diimpor langsung. |
| 06:11-06:21 | Impor contoh_wevtutil.xml, hasil impor | `06:12` Usulan kami pilot baca-saja di satu satuan. `06:15` Aplikasi membaca log dan menulis laporan, tanpa menyentuh sistem. |
| 06:21-06:36 | Kartu batasan | `06:22` Batasannya: pola injeksi tidak tahan parafrase, dan LLM kecil kalah dari aturan. `06:28` Nilai draf AI juga belum terbukti. `06:31` Exe belum ditandatangani dan baru diuji di Windows 11. |
| 06:36-06:43 | Kartu penutup: URL repo, ajakan unduh | `06:37` Aplikasi, kode, dan hasil uji ada di tautan ini. Silakan unduh dan coba. |

Angka di naskah hanya dari buku klaim (mega prompt 2 Nov, bagian C). Jangan menambah angka lain saat merekam.
