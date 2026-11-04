# TANYA_JAWAB: pertanyaan juri yang paling mungkin + jawaban jujur
Angka diambil dari `BUKTI_EVALUASI.md` dan `prototype/results/summary.json`. Kalau jawabannya belum ada, katakan "belum kami uji" dan sebutkan rencana uji.

## A. Teknis / AI (J1, J2)
1. **Kenapa pakai LLM kalau aturan lebih akurat?** Kami mengukurnya, dan memang benar: aturan 50 % vs LLM 35 % untuk kategori taktik (P2 gagal). Karena itu di v1.1 (sudah dikode, `perisai/v11.py`) kategori diambil dari aturan, dan LLM hanya menulis draf ringkasan bahasa Indonesia. Kami belum bisa membuktikan draf itu berguna. Itu uji berikutnya: penilaian buta oleh praktisi dari luar tim, dengan ringkasan aturan tulisan manusia (PRAREG v2.4; versi sebelumnya ternyata tidak buta). Draf juga dijaga di v1.2, sehingga hanya boleh mendeskripsikan dan tidak boleh menyarankan penutupan kasus atau aksi. Kontribusi utama kami adalah **lapisan pengaman** supaya asisten LLM mana pun aman dipakai di SOC. Lapisan ini berguna justru karena organisasi akan memakai LLM, yang besar maupun yang kecil.
2. **Deteksi 100 % itu tidak curang?** Itu in-sample, dan kami sudah menulisnya di prareg §0 sebelum hasil keluar. Kami lalu mengujinya dengan 4 keluarga baru yang diprareg (PRAREG v3), dan deteksi pola **turun ke 0 %**. Kami melaporkannya apa adanya.
3. **Bagaimana kalau penyerang memparafrasekan injeksi?** Itu sudah kami uji, dan pola memang lolos semua.
   - Upaya isolasi host dan blokir IP tetap 0 yang lolos, karena ditahan allowlist, aturan bukti, aset terlindungi, dan persetujuan manusia.
   - v1 kebobolan 4/176 di penutupan kasus.
   - v1.1 tidak pernah menutup kasus otomatis dan bertahan 0/176.
   - Penulis injeksi adalah orang yang sama dengan penulis firewall. Karena itu uji oleh red team luar tetap kami butuhkan.
4. **Satu yang lolos di ablasi itu apa?** Satu kasus discovery yang ditutup (`no_action`), karena detektor tidak menemukan sinyal berbobot ≥ medium. Ini celah nyata. Di v1 juga ada 3 rekaman serangan bersih yang ditutup otomatis. v1.1 sudah memperbaikinya: kasus tidak pernah ditutup otomatis (replay post-hoc 0/88).
5. **Kenapa ASR tanpa pengaman cuma 16,5 %?** Model 1,5B tidak terlalu patuh pada injeksi kami. Efek terbesar ada di tujuan blokir IP (18/44). Untuk tujuan menutup kasus, 7/44 kejadian terjadi juga tanpa injeksi (laju dasar). Model yang lebih besar dan lebih patuh kemungkinan lebih rentan. Itu belum kami uji.
6. **Kenapa model sekecil itu?** Supaya bisa jalan di laptop CPU satuan (±1,5 GB RAM) dengan lisensi Apache-2.0. Antarmuka modelnya bisa diganti. Model lain belum kami uji.
7. **Split-nya bocor?** Split per teknik ATT&CK, jadi tidak ada teknik yang sama di DEV dan UJI. Ada tes otomatis yang memeriksa ini. Kasus uji juga dikunci hash per kasus.
8. **Kenapa bootstrap klaster?** Unit injeksi yang memakai template sama tidak independen. Klaster P1 adalah 12 template, klaster P2 adalah 40 grup teknik. Koreksi Holm untuk 2 endpoint.
9. **Latensi 28 detik, apa tidak terlalu lama?** Untuk triase alert yang sudah tersaring aturan, ya cukup. Untuk aliran semua log, tidak. Rencananya, LLM hanya dipanggil untuk alert yang lolos saringan aturan. Antrean ini **belum** dikode; purwarupa memproses per kasus. Firewall dan policy berjalan dalam < 10 ms.
10. **Halusinasi?** Pernah terjadi: kata "terorisme" muncul padahal tidak ada di log, dan di uji tertahan draf sempat mengulang narasi penyerang ("pemeliharaan terjadwal, tiket bisa ditutup"). Penanganannya berlapis:
    - v1: URL, e-mail, IP, dan host yang tidak ada di field terstruktur disaring.
    - v1.1: ringkasan utama dari template aturan, draf AI diberi label, dan istilah eskalatif yang tidak ada di log dibuang.
    - v1.2.2: kalimat draf hanya tampil kalau menyebut bukti (judul aturan, field terstruktur, atau istilah kategori yang terpicu), dan tetap dibuang kalau menyarankan penutupan atau aksi, mengklaim keputusan pihak berwenang, meminta kredensial, atau menyalin teks log.
    - Di uji tertahan, gema injeksi turun dari 14/176 (v1.1) ke 0/176. Ukuran independen (draf menyebut target penyerang, G1/G2/G4) turun dari 6/132 ke 0/132.
    - Jujurnya, ini tetap penyaring daftar kata yang bisa diakali parafrase. Juri latihan kami meloloskan 25 probe baru di putaran 6, dan cek ulang 2 Nov masih meloloskan 12 dari 16. Karena itu draf AI hanya pelengkap berlabel, dan aksi tidak pernah diambil dari LLM.
    - Angka ini post-hoc. Riwayat koreksinya kami tulis terbuka: v1.2 pertama 4/176, v1.2.1 0/176 tetapi masih bocor lewat negasi dan "lalu lintas" (juri P5).
    - Kewajiban menunjuk event ID per kalimat masih rencana.
11. **Apa bedanya dengan CaMeL / integrasi Wazuh-LLM?** Prinsipnya sama, dan kami tidak mengklaim prinsip itu sebagai temuan kami. Yang baru dari kami: jalur injeksi lewat log, offline di CPU, pola bahasa Indonesia, serta pengukuran ber-prareg dengan ablasi.
12. **Bisakah audit dipalsukan dengan menghitung ulang semua hash?** Bisa, oleh orang yang menguasai perangkat. Karena itu kami mengusulkan jangkar harian: hash terakhir dicatat di luar perangkat. Ini prosedur, dan belum dikode atau diuji. Tanpa jangkar, yang bisa dideteksi hanya perubahan di tengah rantai.
13. **Bagaimana dengan model yang diganti diam-diam?** SHA-256 model dicek sebelum dimuat (`perisai/integrity.py`, ±2 detik). Kalau tidak cocok, model tidak dipakai, sistem jalan di mode aturan, dan statusnya tertulis di laporan. Ini ada tesnya. Harness evaluasi v1 yang di-hash tidak memakai cek ini, tetapi hash model dicatat di prareg.

## B. Relevansi / satuan (J3, operator)
14. **Apakah satuan benar-benar butuh ini?** Kami belum mewawancarai personel. Pertanyaan validasinya sudah kami siapkan untuk Webinar 2. Yang terbuka di sumber publik: beban insiden menurut data BSSN dan peran koordinasi Kartika CSIRT.
15. **OT?** Ada purwarupa jalur OT di data HAI 21.03 (testbed ICS boiler/turbin/air, CC BY-SA 4.0).
    - Detektor amplop normal dilatih dan dikalibrasi hanya di data normal, diprareg, lalu dinilai sekali: **10/10 episode serangan tertangkap**. Alarm palsu 5,4 % di satu berkas uji dan 0 % di berkas lain.
    - Detektornya sederhana dan tidak kami bandingkan dengan metode HAICon.
    - Nilai utamanya di **kebijakan**: PLC/HMI tidak pernah diputus oleh sistem, karena memutus pengendali bisa menghentikan proses fisik. Keputusan ada di insinyur proses.
    - Kami belum tahu apakah satuan memakai SCADA berjaringan. Ini akan kami tanyakan di Webinar 2.
16. **Log apa yang dibutuhkan?** Minimal Windows Event Log bawaan (Security). Sysmon opsional, tapi memperkaya hasil. `triase.py` membaca ekspor `wevtutil qe … /f:xml` atau `Get-WinEvent … ToXml()` langsung dari PC operator, tanpa agen tambahan, dan juga JSON Winlogbeat. Berkas `.evtx` biner diubah dulu dengan `wevtutil qe berkas.evtx /lf:true /f:xml > berkas.xml`.
17. **Apakah alat ini bisa bertindak sendiri?** Tidak. Di pilot, alat ini baca-saja. Aksi berisiko selalu menunggu persetujuan, dan aset kritis memerlukan keputusan komandan.
18. **Operator harus seahli apa?** Diperkirakan butuh 8 jam pelatihan (estimasi, diuji di pilot). Tampilan menunjukkan alasan setiap keputusan dalam bahasa Indonesia.
19. **Kenapa tidak pakai Llama?** *Acceptable Use Policy* Llama melarang penggunaan militer/perang. Qwen2.5 berlisensi Apache-2.0. Asal model dari luar negeri tetap jadi pertimbangan, jadi kami membuat antarmukanya model-agnostik dan menyediakan mode tanpa LLM.

## C. Kelayakan / bisnis
20. **Biaya?** Lisensi Rp0. Pilot cukup memakai perangkat yang sudah ada, ditambah pelatihan dan pendampingan `[ISI angka resmi]`.
21. **Siapa yang memelihara?** Usulannya: paket pembaruan aturan dan model bertanda tangan lewat Kartika CSIRT `[ASUMSI]`.
22. **TKDN?** Diperlukan untuk pengadaan nyata. Masuk tahap 3 `[ISI]`.

## D. Integritas
23. **Ini karya lama?** Komponen policy, pola injeksi, dan audit diadaptasi dari proyek tim sendiri, Kendali (MIT), yang juga diikutkan di FinTechathon. Domain, data, evaluasi, dan produknya baru, dan dikerjakan sejak 29 Okt 2026. Rulebook membolehkan karya pre-existing sebagai dasar asalkan dideklarasikan (S&K 5.3); deklarasinya ada di `README.md` dan `PROPOSAL.md` §8.
24. **Pakai AI untuk menulis kode?** Ya. Rulebook tidak punya aturan khusus soal AI generatif, tetapi S&K 5.4 meminta atribusi untuk model AI dan tools pihak ketiga, jadi kami mendeklarasikannya di `README.md` (bagian Deklarasi). Setiap anggota bisa menjelaskan arsitektur dan kodenya. `[ISI: sesuaikan dengan peran nyata tiap anggota]`
25. **Ada data asli satuan?** Tidak ada. Hanya log publik berlabel dan event demo sintetis. Injeksi berupa string uji dengan host/IP fiktif dan domain `.invalid`.
