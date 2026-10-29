# 11_NASKAH_VIDEO: video presentasi/demo (target 4–5 menit; durasi resmi `[ISI: cek setelah login]`)
Rekam layar terminal + suara. Jangan tampilkan wajah/identitas kalau tidak perlu. Pakai event demo sintetis saja (`demo.py`), jangan log OTRF mentah, karena isinya memicu Windows Defender.

| Waktu | Layar | Narasi (ubah dengan kata-katamu sendiri) |
|---|---|---|
| 0:00–0:25 | Slide judul | Perkenalan tim. "PERISAI-RESPON: asisten triase insiden yang berjalan offline dan aksinya tidak bisa disetir oleh isi log." |
| 0:25–1:00 | Slide masalah + lubang | Satuan butuh bantuan membaca log, dan AI bisa membantu. Tapi log bisa ditulis penyerang. Kalau asisten menurut pada kalimat di log, alat pertahanan berubah jadi senjata. |
| 1:00–1:30 | Diagram prinsip | LLM hanya mengusulkan. Policy engine yang memutuskan. Manusia menyetujui. Semua langkah tercatat. |
| 1:30–3:00 | Terminal: `.venv\Scripts\python -I demo.py` | Jalankan skenario 1–6 sambil berhenti di: (2) peringatan INJEKSI_TERDETEKSI; (4) "DC01 termasuk aset terlindungi: perlu keputusan komandan"; (5) LLM dimatikan, tetap aman; (5b) v1.1 membuang kalimat "terorisme" dari draf AI; (6) satu entri audit diubah → "entry hash mismatch". Tunjukkan bahwa koneksi internet laptop **dimatikan** saat demo |
| 3:00–3:45 | Grafik P1/P2 | Prareg dikunci SHA-256 sebelum uji. 176 unit injeksi: 16,5 % berhasil tanpa pengaman, 0 % dengan PERISAI, 0,6 % walau detektor pola dibuat buta. Kami juga melaporkan yang gagal: LLM kecil kalah dari aturan dalam menebak taktik, jadi di versi 1.1 kategori diambil dari aturan dan AI hanya menulis draf ringkasan. |
| 3:45–4:20 | Slide satuan + roadmap | Laptop biasa, tanpa GPU, lisensi terbuka. Pilot baca-saja di satu satuan. |
| 4:20–4:40 | Penutup | Kalimat "aha" + URL repo |

## Daftar periksa rekaman
- [ ] Wi-Fi mati dan ikon jaringan terlihat di video.
- [ ] Font terminal minimal 16 pt.
- [ ] Jalankan `demo.py` sekali dulu (pemanasan model) supaya rekaman tidak menunggu lama.
- [ ] Tidak ada nama asli/NIK/alamat di layar.
- [ ] Unggah dengan link yang bisa dibuka publik (cek lewat jendela penyamaran).
