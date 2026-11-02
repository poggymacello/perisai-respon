# Status semua prareg (berkas ini boleh diedit; dokumen prareg yang sudah dibekukan tidak)
Juri P5 N27 dan P6 N30: catatan status jangan ditulis di dalam dokumen prareg yang sudah di-hash. Mulai 2 Nov 2026, semua catatan status ditaruh di sini.

| Prareg | Isi | Status |
|---|---|---|
| `PRAREG.md` (v1) | P1 injeksi, P2 kategori | **Dijalankan** 29 Okt. P1 LULUS, P2 GAGAL. Hash OK |
| `PRAREG_v2_DRAF_AI.md` | penilaian draf AI v1.1 | **Tidak pernah dijalankan.** Tidak buta (juri P3). Jangan dipakai |
| `PRAREG_v21_DRAF_AI.md` | v2.1 | **Tidak pernah dijalankan.** Digantikan v2.2. Catatan "DIGANTIKAN" ditulis di dalam dokumen sesudah pembekuan, sehingga hash dokumen gagal (diungkap) |
| `PRAREG_v22_DRAF_AI.md` | v2.2 | **Tidak pernah dijalankan.** Digantikan v2.3. Catatan ditulis di dalam dokumen sesudah pembekuan, sehingga hash gagal (diungkap) |
| `PRAREG_v23_DRAF_AI.md` | v2.3, ringkasan aturan dari templat | **Tidak pernah dijalankan.** Tidak buta: templat bisa dicocokkan dengan regex (juri P5 N21), dan pembeda 0,6875 > 0,65. Catatan "Jangan dipakai" ditulis di dalam dokumen 30 Okt, sehingga hash dokumen gagal (diungkap, juri P6 N30) |
| `PRAREG_v3_HELDOUT.md` | injeksi keluarga tertahan | **Dijalankan** 29 Okt. Deteksi pola 0 %, H-P1 v1 gagal |
| `PRAREG_v4_OT_BENIGN.md` | jalur OT + tanda palsu firewall | **Dijalankan** 29 Okt. 10/10 episode; tanda palsu 0/260.351 |
| `PRAREG_v24_DRAF_AI.md` | v2.4, ringkasan aturan tulisan manusia, 2 sesi | **DIBEKUKAN 2 Nov** (`PRAREG_v24_DRAF_AI.sha256`, commit lokal). Berikutnya: penulis ringkasan → `--build` sekali → hash paket di `PRAREG_v24_PAKET.sha256` → penilaian |
