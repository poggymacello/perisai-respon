# PRAREG v4 PERISAI-RESPON: jalur OT (HAI 21.03) dan tanda palsu firewall pada teks log asli

**Ditulis:** 29 Okt 2026, sebelum `test1`/`test4` HAI dinilai dan sebelum firewall dijalankan atas seluruh teks OTRF. Dibekukan dengan SHA-256 di `PRAREG_v4_OT_BENIGN.sha256`.

## 0. Yang sudah dilihat sebelum dokumen ini
- Kolom HAI: 79 tag proses dan 4 kolom label. Hanya nama kolom yang dilihat dari `test1`.
- Data **normal** `train1`, `train2`, dan `train3` dipakai untuk merancang detektor:
  - Percobaan pertama memakai profil `train1` dan kalibrasi `train2`. Hasilnya gagal: 99,97 % jendela berbunyi karena satu tag hampir konstan (`P1_PCV02Z`) bergeser antarhari.
  - Perbaikannya: span minimum 1 % dari |median|, profil `train1+train2`, kalibrasi di `train3`. Margin terpilih m = 0,1 dengan alarm palsu 0,38 % per jendela di `train3`.
- Data serangan HAI belum dinilai. Firewall belum dijalankan atas teks OTRF di luar 88 kasus uji dan 33 kasus DEV.

## A. Detektor OT (HAI 21.03, CC BY-SA 4.0)
- **Detektor** (`perisai/ot.py`):
  - amplop normal per tag dari kuantil 0,05–99,95 % data normal;
  - jendela 60 detik berbunyi bila ada tag yang keluar amplop selama ≥ 10 detik;
  - parameter dikunci di dokumen ini (`WINDOW_S`, `K_SECONDS`, kuantil, daftar margin, target alarm palsu 1 %).
- **Dinilai sekali** di `test1` dan `test4`:
  - **A1** recall jendela serangan;
  - **A2** laju alarm palsu pada jendela normal di berkas uji;
  - **A3** jumlah episode serangan yang tertangkap minimal satu jendela.
- **Kebijakan OT** (diuji di `tests/test_ot.py`, bukan diukur di sini):
  - aset proses (PLC/HMI/RTU/SIS/EWS) tidak pernah diisolasi atau diblokir sistem;
  - aksi akhir selalu eskalasi ke insinyur proses dan operator lapangan;
  - catatan HMI dipindai firewall;
  - draf AI disaring.
- **Prediksi:**
  - A2 ≤ 2 %.
  - A1 rendah, sekitar 20–50 %. Banyak serangan HAI dirancang tetap berada di rentang normal (*stealthy*), dan detektor amplop memang tidak menangkap serangan seperti itu.
  - Ini purwarupa jalur OT. Detektor ini **bukan** pesaing metode SOTA HAI.

## B. Tanda palsu firewall pada teks log asli
- Semua field teks bebas di 121 rekaman OTRF dipindai `firewall.scan_text` (kode beku, hash di `PRAREG_v3_HELDOUT.sha256`).
- Rekaman OTRF tidak memuat injeksi prompt, jadi **setiap field yang ditandai dihitung sebagai tanda palsu**.
- **B1** laju tanda palsu per field; **B2** laju tanda palsu per event yang punya teks bebas; daftar kode pola yang memicu.
- **Prediksi:** B1 < 0,1 %.
  - Kasus uji bersih menghasilkan 0/88 tanda palsu, tetapi kasus itu hanya 8 event per rekaman.
  - Pola yang paling mungkin memicu tanda palsu adalah kosakata seperti "bypass", "system:", atau dekode base64 dari script PowerShell.
- **Batas:** ini teks asli dari rekaman serangan lab, **bukan** log benign berlabel. Log benign Windows berlisensi jelas di bawah 1 GB tidak ditemukan. COMISET (CC BY 4.0) berukuran 36,6 GB, dan atomic-evtx tidak berlisensi. Data benign yang benar ada di bagian A, yaitu data normal HAI.
