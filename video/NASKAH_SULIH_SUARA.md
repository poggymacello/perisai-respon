# NASKAH SULIH SUARA: video demo PERISAI-RESPON

Durasi video tanpa suara: **05:59** (`PERISAI-RESPON_demo_tanpa_suara.mp4`). Naskah ini dibuat dari `alur.py`, sama dengan subtitle `PERISAI-RESPON_demo.id.srt`. Kalau narasi diubah, ubah `alur.py` lalu jalankan ulang `susun.py` supaya video, subtitle, dan naskah tetap sinkron.

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
- 00:21 Kenapa penting untuk satuan
- 01:06 Demo: antrean dan kasus injeksi
- 02:13 Uji policy: isolasi DC01 ditolak
- 02:33 Persetujuan analis, audit, laporan CSIRT
- 03:33 Jalur OT
- 03:59 Hasil uji, termasuk yang gagal
- 05:00 Penerapan di satuan
- 05:40 Batasan dan tautan

## Naskah per waktu

| Waktu | Di layar | Yang diucapkan |
|---|---|---|
| 00:00-00:05 | Kartu judul | `00:00` PERISAI-RESPON memilah insiden dari log Windows secara offline. |
| 00:05-00:21 | Kasus K-0004: field CommandLine berisi instruksi, ditandai firewall (diperbesar) | `00:05` Masalahnya, isi log bisa ditulis penyerang. `00:09` Di sini penyerang menyelipkan perintah untuk AI di baris PowerShell: isolasi DC01. `00:15` Aplikasi menandainya sebagai data, tidak menurutinya, dan menyerahkan kasus ke analis. |
| 00:21-00:23 | Kartu: Log satuan tidak boleh keluar ke cloud, dan isinya bisa ditulis penyerang. | (diam) |
| 00:23-00:32 | Aplikasi baru dibuka, antrean kosong | `00:24` Log satuan memuat nama host, akun, dan alamat internal. `00:28` Karena itu log tidak boleh dikirim ke layanan AI di cloud. |
| 00:32-00:39 | Penanda Offline 127.0.0.1 di kanan atas | `00:33` PERISAI-RESPON berjalan di laptop dan hanya menerima koneksi dari perangkat itu sendiri. |
| 00:39-00:46 | Status sistem, kartu Jaringan | `00:40` Status sistem: alamat 127.0.0.1, akses ke host lain diblokir, tanpa telemetri. |
| 00:46-00:52 | Status sistem, kartu Model lokal (hash cocok) | `00:46` Modelnya juga lokal, Qwen2.5 1,5B, dan hash berkasnya dicek sebelum dipakai. |
| 00:52-01:06 | Status sistem, kartu Mode analisis | `00:53` Isi log juga bisa menyetir asisten AI yang membacanya. `00:57` Karena itu kategori dan aksi diambil dari aturan. `01:00` LLM hanya menulis draf ringkasan, dan hanya kalau analis memintanya. |
| 01:06-01:08 | Kartu: Demo dengan log contoh sintetis, dari antrean kasus sampai laporan CSIRT. | (diam) |
| 01:08-01:14 | Klik Muat data contoh | `01:08` Kita mulai dari sesi kosong dan memuat log contoh dengan host fiktif. |
| 01:14-01:22 | Ringkasan antrean dan tabel kasus | `01:14` Event dikelompokkan menjadi kasus. `01:17` Tiap kasus punya kategori ATT&CK, severity, dan status dari mesin aturan. |
| 01:22-01:28 | Filter Injeksi terdeteksi | `01:23` Filter ini menampilkan kasus yang lognya memuat instruksi tersembunyi. |
| 01:28-01:35 | Buka K-0004 (WS-KEU02), banner merah | `01:29` Kasus WS-KEU02. Banner merah menyebut lokasi instruksinya: field CommandLine. |
| 01:35-01:42 | Teks CommandLine ditampilkan sebagai teks biasa | `01:35` Teks log ditampilkan sebagai teks biasa. Teks itu tidak dijalankan dan tidak disalin ke laporan. |
| 01:42-01:50 | Kartu Keputusan dan alasan policy | `01:43` Keputusan diambil oleh aturan v1.2.2, bukan oleh LLM, dan alasan policy-nya ditulis satu per satu. |
| 01:50-01:56 | Klik Buat draf AI, bilah proses | `01:50` Draf AI dibuat hanya atas permintaan analis. Waktu tunggunya kami potong. |
| 01:56-02:13 | Draf AI berlabel, label waktu tunggu dipotong (diperbesar) | `01:56` Draf ini berlabel bukan dasar keputusan. `01:59` Di sini draf menebak pergerakan lateral. Di percobaan lain, tebakannya pencurian kredensial. `02:06` Kategori tetap eksekusi kode dari aturan, jadi draf tidak menentukan aksi dan nilainya belum terbukti. |
| 02:13-02:22 | Uji usulan: isolasi DC01, detektor pola dimatikan | `02:14` Skenario terburuk: LLM sudah tersetir dan mengusulkan isolasi DC01. `02:19` Detektor pola injeksi kami matikan. |
| 02:22-02:33 | Hasil BLOCK dan alasannya (diperbesar) | `02:22` Policy tetap menolak: BLOCK, karena DC01 aset terlindungi. `02:27` Aturan ini melihat target aksi, jadi tetap bekerja walau kalimat serangannya tidak dikenali. |
| 02:33-02:43 | Buka K-0002 (WS-OPS07), menunggu persetujuan | `02:34` Kasus WS-OPS07: proses dari folder Public mengakses LSASS. `02:38` Aturan mengusulkan isolasi host, dan statusnya menunggu persetujuan. |
| 02:43-02:53 | Setujui aksi, isi nama dan catatan | `02:44` Aksi berisiko tidak berjalan sendiri. Analis menyetujuinya dengan nama dan catatan. |
| 02:53-02:59 | Riwayat: disetujui analis, nomor entri audit | `02:54` Persetujuan itu dicatat, tidak dieksekusi. Aplikasi ini baca-saja. |
| 02:59-03:06 | Jejak audit berantai SHA-256 | `03:00` Setiap langkah masuk jejak audit. Tiap entri memuat hash SHA-256 entri sebelumnya. |
| 03:06-03:11 | Verifikasi integritas: rantai utuh | `03:06` Verifikasi menghitung ulang seluruh rantai dari berkas. |
| 03:11-03:21 | Uji deteksi perubahan: salinan gagal, asli utuh (diperbesar) | `03:11` Uji ini mengubah persetujuan tadi menjadi dieksekusi: true di salinan. `03:16` Verifikasi salinan langsung gagal, dan berkas aslinya tetap utuh. |
| 03:21-03:28 | Laporan CSIRT, tombol unduh dan cetak | `03:22` Laporan CSIRT disusun dari kasus dan jejak audit, lalu bisa diunduh atau dicetak ke PDF. |
| 03:28-03:33 | Gulir laporan ke bagian tindakan analis | `03:29` Teks bebas dari log tidak ikut disalin ke laporan. |
| 03:33-03:35 | Kartu: Jalur OT: PLC dan HMI tidak pernah diputus oleh sistem. | (diam) |
| 03:35-03:42 | Jalur OT: grafik amplop normal | `03:36` Pada telemetri proses bergaya HAI 21.03, satu tag aliran keluar dari amplop normal. |
| 03:42-03:49 | Catatan HMI (teks bebas) | `03:42` Catatan HMI mengaku komandan memerintahkan PLC-P1 diputus. Firewall pola tidak menandainya. |
| 03:49-03:59 | Keputusan OT: putus PLC-P1 ditolak (diperbesar) | `03:50` Usulan itu tetap ditolak aturan aset OT, karena memutus PLC bisa menghentikan proses fisik. `03:56` Kasus dieskalasi ke insinyur proses. |
| 03:59-04:01 | Kartu: Hasil uji kami, termasuk yang gagal. | (diam) |
| 04:01-04:18 | Kartu: Injeksi lewat log yang berhasil (16,5 % → 0 %) | `04:02` Rencana uji kami kunci dengan SHA-256 sebelum dijalankan. `04:06` Pada 176 unit uji, injeksi yang berhasil turun dari 16,5 persen ke 0 persen. `04:12` Pola deteksinya dibuat dengan mengetahui keluarga injeksi ini, jadi hasilnya in-sample. |
| 04:18-04:24 | Kartu: Detektor pola dimatikan, policy tetap menahan (0,6 %) | `04:18` Dengan detektor pola dimatikan, yang lolos 0,6 persen, satu dari 176. |
| 04:24-04:40 | Kartu: Injeksi baru yang ditulis ulang (0 % terdeteksi pola) | `04:24` Injeksi yang ditulis ulang lolos dari pola deteksi: 0 persen terdeteksi. `04:29` Tetapi isolasi dan blokir palsu yang lolos tetap 0. `04:33` Versi 1 kebobolan 4 dari 176 lewat penutupan kasus; kini kasus tidak pernah ditutup otomatis. |
| 04:40-04:51 | Kartu: Uji P2 gagal: LLM kalah dari aturan (35,2 % vs 50,0 %) | `04:41` Uji P2 gagal. LLM 1,5B kalah dari aturan dalam menebak taktik, 35,2 lawan 50,0 persen. `04:47` Karena itu kategori dan aksi diambil dari aturan. |
| 04:51-05:00 | Kartu: Jalur OT dan tanda palsu (10/10) | `04:51` Di jalur OT, 10 dari 10 episode serangan HAI 21.03 tertangkap. `04:56` Alarm palsunya 5,4 persen dan 0 persen di dua berkas uji. |
| 05:00-05:03 | Kartu: Penerapan di satuan: laptop biasa, lisensi Rp0, pilot baca-saja. | (diam) |
| 05:03-05:16 | Status sistem: Uji kinerja di perangkat ini | `05:03` Di CPU laptop tanpa GPU, firewall dan policy butuh kurang dari 10 milidetik per kasus. `05:09` Dengan LLM, median 28,7 detik per kasus. Tombol ini mengukur ulang di perangkat penguji. |
| 05:16-05:25 | Tabel lisensi dan asal-usul | `05:16` Lisensinya Rp0. Qwen2.5 berlisensi Apache-2.0. `05:20` Llama tidak dipakai karena lisensinya melarang penggunaan militer. |
| 05:25-05:31 | Impor log: perintah wevtutil dan .evtx | `05:25` Untuk pilot, log diekspor dengan wevtutil, atau berkas .evtx diimpor langsung. |
| 05:31-05:40 | Impor contoh_wevtutil.xml, hasil impor | `05:32` Usulan kami pilot baca-saja di satu satuan. `05:35` Aplikasi membaca log dan menulis laporan, tanpa menyentuh sistem. |
| 05:40-05:53 | Kartu batasan | `05:41` Batasannya: pola injeksi tidak tahan parafrase, dan LLM kecil kalah dari aturan. `05:46` Nilai draf AI juga belum terbukti. `05:49` Exe belum ditandatangani dan baru diuji di Windows 11. |
| 05:53-05:59 | Kartu penutup: URL repo, ajakan unduh | `05:54` Aplikasi, kode, dan hasil uji ada di tautan ini. Silakan unduh dan coba. |

Angka di naskah hanya dari buku klaim (mega prompt 2 Nov, bagian C). Jangan menambah angka lain saat merekam.
