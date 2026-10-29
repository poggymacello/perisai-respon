# 12_QNA: pertanyaan juri yang paling mungkin + jawaban jujur
Angka diambil dari `05_BUKTI.md` dan `prototype/results/summary.json`. Kalau jawabannya belum ada, katakan "belum kami uji" dan sebutkan rencana uji.

## A. Teknis / AI (J1, J2)
1. **Kenapa pakai LLM kalau aturan lebih akurat?** Kami mengukurnya, dan memang benar: aturan 50 % vs LLM 35 % untuk kategori taktik (P2 gagal). Karena itu di v1.1 (sudah dikode, `perisai/v11.py`) kategori diambil dari aturan, dan LLM hanya menulis draf ringkasan bahasa Indonesia. Kami belum bisa membuktikan draf itu berguna. Itu uji berikutnya (penilaian buta oleh praktisi). Kontribusi utama kami adalah **lapisan pengaman** supaya asisten LLM mana pun aman dipakai di SOC. Lapisan ini berguna justru karena organisasi akan memakai LLM, yang besar maupun yang kecil.
2. **Deteksi 100 % itu tidak curang?** Itu in-sample, dan kami sudah menulisnya di prareg §0 sebelum hasil keluar. Angka yang kami pegang adalah ablasi detektor buta: 0,6 %.
3. **Bagaimana kalau penyerang memparafrasekan injeksi?** Pola bisa lolos. Tapi aksi tetap harus lolos allowlist, aturan bukti, aset terlindungi, dan persetujuan manusia. Ablasi detektor buta mensimulasikan kasus terburuk itu.
4. **Satu yang lolos di ablasi itu apa?** Satu kasus discovery yang ditutup (`no_action`), karena detektor tidak menemukan sinyal berbobot ≥ medium. Ini celah nyata. Di v1 juga ada 3 rekaman serangan bersih yang ditutup otomatis. v1.1 sudah memperbaikinya: kasus tidak pernah ditutup otomatis (replay post-hoc 0/88).
5. **Kenapa ASR tanpa pengaman cuma 16,5 %?** Model 1,5B tidak terlalu patuh pada injeksi kami. Efek terbesar ada di tujuan blokir IP (18/44). Untuk tujuan menutup kasus, 7/44 kejadian terjadi juga tanpa injeksi (laju dasar). Model yang lebih besar dan lebih patuh kemungkinan lebih rentan. Itu belum kami uji.
6. **Kenapa model sekecil itu?** Supaya bisa jalan di laptop CPU satuan (±1,5 GB RAM) dengan lisensi Apache-2.0. Antarmuka modelnya bisa diganti. Model lain belum kami uji.
7. **Split-nya bocor?** Split per teknik ATT&CK, jadi tidak ada teknik yang sama di DEV dan UJI. Ada tes otomatis yang memeriksa ini. Kasus uji juga dikunci hash per kasus.
8. **Kenapa bootstrap klaster?** Unit injeksi yang memakai template sama tidak independen. Klaster P1 adalah 12 template, klaster P2 adalah 40 grup teknik. Koreksi Holm untuk 2 endpoint.
9. **Latensi 28 detik, apa tidak terlalu lama?** Untuk triase alert yang sudah tersaring aturan, ya cukup. Untuk aliran semua log, tidak. Rencananya, LLM hanya dipanggil untuk alert yang lolos saringan aturan. Antrean ini **belum** dikode; purwarupa memproses per kasus. Firewall dan policy berjalan dalam < 10 ms.
10. **Halusinasi?** Pernah terjadi: kata "terorisme" muncul padahal tidak ada di log. Filter kami saat ini hanya menyaring URL, e-mail, IP, dan host. Ringkasan adalah draf yang wajib ditampilkan berdampingan dengan log asli. v1.1: ringkasan utama dari template aturan, draf AI diberi label, dan kalimat berisi istilah eskalatif yang tidak ada di log dibuang. Kewajiban menunjuk event ID per kalimat masih rencana.
11. **Apa bedanya dengan CaMeL / integrasi Wazuh-LLM?** Prinsipnya sama, dan kami tidak mengklaim prinsip itu sebagai temuan kami. Yang baru dari kami: jalur injeksi lewat log, offline di CPU, pola bahasa Indonesia, serta pengukuran ber-prareg dengan ablasi.
12. **Bisakah audit dipalsukan dengan menghitung ulang semua hash?** Bisa, oleh orang yang menguasai perangkat. Karena itu ada jangkar harian: hash terakhir dicatat di luar perangkat. Tanpa jangkar, yang bisa dideteksi hanya perubahan di tengah rantai.
13. **Bagaimana dengan model yang diganti diam-diam?** Cek hash model saat mulai **belum** diimplementasikan, termasuk di v1.1. Hash acuan sudah ada di `DATA.md`, dan ini pekerjaan berikutnya.

## B. Relevansi / satuan (J3, operator)
14. **Apakah satuan benar-benar butuh ini?** Kami belum mewawancarai personel. Pertanyaan validasinya sudah kami siapkan untuk Webinar 2. Yang terbuka di sumber publik: beban insiden menurut data BSSN dan peran koordinasi Kartika CSIRT.
15. **OT?** Belum dicakup. Kami tidak menemukan sumber terbuka bahwa satuan memakai SCADA berjaringan. Kalau ya, konektor Modbus/BACnet bisa ditambahkan di tahap 3.
16. **Log apa yang dibutuhkan?** Minimal Windows Event Log bawaan (Security). Sysmon bersifat opsional, tapi memperkaya hasil. Saat ini kami membaca format OTRF JSON. Pengimpor `.evtx` masih rencana.
17. **Apakah alat ini bisa bertindak sendiri?** Tidak. Di pilot, alat ini baca-saja. Aksi berisiko selalu menunggu persetujuan, dan aset kritis memerlukan keputusan komandan.
18. **Operator harus seahli apa?** Diperkirakan butuh 8 jam pelatihan (estimasi, diuji di pilot). Tampilan menunjukkan alasan setiap keputusan dalam bahasa Indonesia.
19. **Kenapa tidak pakai Llama?** *Acceptable Use Policy* Llama melarang penggunaan militer/perang. Qwen2.5 berlisensi Apache-2.0. Asal model dari luar negeri tetap jadi pertimbangan, jadi kami membuat antarmukanya model-agnostik dan menyediakan mode tanpa LLM.

## C. Kelayakan / bisnis
20. **Biaya?** Lisensi Rp0. Pilot cukup memakai perangkat yang sudah ada, ditambah pelatihan dan pendampingan `[ISI angka resmi]`.
21. **Siapa yang memelihara?** Usulannya: paket pembaruan aturan dan model bertanda tangan lewat Kartika CSIRT `[ASUMSI]`.
22. **TKDN?** Diperlukan untuk pengadaan nyata. Masuk tahap 3 `[ISI]`.

## D. Integritas
23. **Ini karya lama?** Komponen policy, pola injeksi, dan audit diadaptasi dari proyek tim sendiri, Kendali (MIT), yang juga diikutkan di FinTechathon. Domain, data, evaluasi, dan produknya baru. `[ISI: aturan karya ganda]`
24. **Pakai AI untuk menulis kode?** `[ISI: jawab jujur sesuai aturan lomba]`. Ikuti aturan lomba soal deklarasi AI (dicek setelah login).
25. **Ada data asli satuan?** Tidak ada. Hanya log publik berlabel dan event demo sintetis. Injeksi berupa string uji dengan host/IP fiktif dan domain `.invalid`.
