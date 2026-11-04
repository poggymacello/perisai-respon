# Peta hash commit (ditulis ulang 4 Nov 2026)

Pesan commit di bawah ditulis ulang pada 4 Nov 2026 untuk menghapus baris co-author. **Isi berkas (tree), penulis, dan tanggal commit tidak berubah**; yang berubah hanya hash commit. Kolom *tree* membuktikan isinya identik: `git rev-parse <commit>^{tree}` pada hash lama (dari salinan lama) dan hash baru memberi nilai yang sama.

Berkas yang dibekukan dengan SHA-256 (PRAREG, manifest, hasil evaluasi) sengaja **tidak** diubah dan masih menyebut hash lama. Gunakan tabel ini untuk menerjemahkannya. Dokumen biasa sudah diperbarui ke hash baru.

| Hash lama | Hash baru | Tree (sama) | Pesan |
|---|---|---|---|
| `ed58c207e26b` | `2ea2c7050c09` | `88d0400e21c3` | Aplikasi desktop 1.0.0, slide teknis, video demo, dan sinkronisasi dokumen |
| `ce6281787dda` | `5b79858c8242` | `12b8bee2eca4` | README landing, requirements-demo, slide dan thumbnail sesuai standar submisi |
| `3459fb20f69a` | `fc12ae47b68c` | `787e9f14bddd` | Bekukan PRAREG v2.4 (penilaian buta) + v1.2.2 + aset kirim sesuai rulebook |
